"""Repository implementations backed by a SQLAlchemy session."""

from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from forge.adapters.sqlite.models import (
    AgentRecord,
    AgentVersionRecord,
    ApprovalRecord,
    ArtifactRecord,
    EventRecord,
    RunRecord,
    StepRecord,
    utc_now,
)
from forge.domain.events import TOOL_EVENT_PAYLOADS
from forge.domain.runs import InvalidRunTransition, Run, RunStatus
from forge.domain.steps import StepKind, StepStatus
from forge.domain.trace import span_id_for_step, trace_id_for_run
from forge.observability.logging import queue_event_log


class AgentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        name: str,
        description: str | None,
        instructions: str,
        provider: str,
        model: str,
        planner: str,
        tools: list[str],
        max_steps: int,
        timeout_seconds: float = 30,
        max_tokens: int | None = None,
        max_cost_usd: float | None = None,
        max_retries: int = 2,
        max_output_tokens: int = 2048,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
    ) -> AgentRecord:
        agent = AgentRecord(id=str(uuid4()), name=name, description=description)
        agent.versions.append(
            AgentVersionRecord(
                id=str(uuid4()),
                version=1,
                instructions=instructions,
                provider=provider,
                model=model,
                planner=planner,
                tools=tools,
                max_steps=max_steps,
                timeout_seconds=timeout_seconds,
                max_tokens=max_tokens,
                max_cost_usd=max_cost_usd,
                max_retries=max_retries,
                max_output_tokens=max_output_tokens,
                input_cost_per_million=input_cost_per_million,
                output_cost_per_million=output_cost_per_million,
            )
        )
        self.session.add(agent)
        self.session.flush()
        return agent

    def list_all(self) -> list[AgentRecord]:
        statement = (
            select(AgentRecord)
            .options(selectinload(AgentRecord.versions))
            .order_by(AgentRecord.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get(self, agent_id: str) -> AgentRecord | None:
        statement = (
            select(AgentRecord)
            .where(AgentRecord.id == agent_id)
            .options(selectinload(AgentRecord.versions))
        )
        return self.session.scalar(statement)

    def add_version(
        self,
        agent: AgentRecord,
        *,
        instructions: str,
        provider: str,
        model: str,
        planner: str,
        tools: list[str],
        max_steps: int,
        timeout_seconds: float = 30,
        max_tokens: int | None = None,
        max_cost_usd: float | None = None,
        max_retries: int = 2,
        max_output_tokens: int = 2048,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
    ) -> AgentVersionRecord:
        latest = self.session.scalar(
            select(func.max(AgentVersionRecord.version)).where(
                AgentVersionRecord.agent_id == agent.id
            )
        )
        version = AgentVersionRecord(
            id=str(uuid4()),
            agent_id=agent.id,
            version=(latest or 0) + 1,
            instructions=instructions,
            provider=provider,
            model=model,
            planner=planner,
            tools=tools,
            max_steps=max_steps,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            max_retries=max_retries,
            max_output_tokens=max_output_tokens,
            input_cost_per_million=input_cost_per_million,
            output_cost_per_million=output_cost_per_million,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def get_version(self, version_id: str) -> AgentVersionRecord | None:
        return self.session.get(AgentVersionRecord, version_id)

    def latest_version(self, agent_id: str) -> AgentVersionRecord | None:
        statement = (
            select(AgentVersionRecord)
            .where(AgentVersionRecord.agent_id == agent_id)
            .order_by(AgentVersionRecord.version.desc())
            .limit(1)
        )
        return self.session.scalar(statement)


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, *, agent_version_id: str, input: str, request_id: str
    ) -> RunRecord:
        now = utc_now()
        run = RunRecord(
            id=str(uuid4()),
            agent_version_id=agent_version_id,
            input=input,
            status=RunStatus.QUEUED.value,
            created_at=now,
            updated_at=now,
        )
        self.session.add(run)
        self.session.flush()
        self.append_event(run.id, "run.created", {
            "status": RunStatus.QUEUED.value, "request_id": request_id,
        })
        return run

    def list_all(self) -> list[RunRecord]:
        return list(
            self.session.scalars(
                select(RunRecord).order_by(RunRecord.created_at.desc())
            )
        )

    def get(self, run_id: str) -> RunRecord | None:
        return self.session.get(RunRecord, run_id)

    def events(self, run_id: str) -> list[EventRecord]:
        statement = (
            select(EventRecord)
            .where(EventRecord.run_id == run_id)
            .order_by(EventRecord.sequence)
        )
        return list(self.session.scalars(statement))

    def events_after(self, run_id: str, sequence: int) -> list[EventRecord]:
        return list(
            self.session.scalars(
                select(EventRecord)
                .where(EventRecord.run_id == run_id, EventRecord.sequence > sequence)
                .order_by(EventRecord.sequence)
            )
        )

    def append_event(
        self, run_id: str, type: str, payload: dict[str, object],
        *, causation_id: str | None = None,
    ) -> EventRecord:
        if type in TOOL_EVENT_PAYLOADS:
            payload = TOOL_EVENT_PAYLOADS[type].model_validate(payload).model_dump(mode='json')
        last_sequence = self.session.scalar(
            select(func.max(EventRecord.sequence)).where(EventRecord.run_id == run_id)
        )
        step_id = payload.get("step_id")
        step_id = step_id if isinstance(step_id, str) else None
        if step_id is None and type.startswith("approval."):
            approval = self.session.get(ApprovalRecord, payload.get("approval_id"))
            if approval is not None and approval.run_id == run_id:
                step_id = approval.step_id
        if causation_id is not None:
            predecessor = self.session.get(EventRecord, causation_id)
            if predecessor is None or predecessor.run_id != run_id:
                raise ValueError("causation_id must identify a prior event in this run")
        else:
            predecessor = self._predecessor(run_id, type, payload, step_id)
        if step_id is None and type in {"artifact.created", "artifact.expired"} and predecessor:
            step_id = predecessor.step_id
        event = EventRecord(
            id=str(uuid4()),
            run_id=run_id,
            sequence=(last_sequence or 0) + 1,
            type=type,
            payload=payload,
            schema_version=2,
            correlation_id=run_id,
            causation_id=predecessor.id if predecessor else None,
            trace_id=trace_id_for_run(run_id),
            span_id=span_id_for_step(step_id) if step_id else None,
            step_id=step_id,
        )
        self.session.add(event)
        if step_id and type in {"model.requested", "planner.started", "tool.requested"}:
            step = self.session.get(StepRecord, step_id)
            if step is not None and step.correlation_id is not None:
                step.causation_id = event.causation_id
        self.session.flush()
        has_step_timing = type.rsplit(".", 1)[-1] in {
            "completed", "decided", "failed", "denied", "cancelled", "interrupted",
        }
        queue_event_log(
            self.session, event,
            step=self.session.get(StepRecord, step_id) if step_id and has_step_timing else None,
            run=self.get(run_id) if type in {"run.completed", "run.failed", "run.cancelled", "run.interrupted"} else None,
        )
        return event

    def _predecessor(self, run_id, type, payload, step_id):
        """Select only known semantic edges, never the last chronological event."""
        families = {
            "run.started": {"run.created"},
            "model.requested": {"run.started", "planner.decided", "tool.completed", "tool.failed", "tool.denied", "model.retry"},
            "model.delta": {"model.requested"},
            "model.completed": {"model.requested"},
            "model.failed": {"model.requested"},
            "model.retry": {"model.failed"},
            "planner.started": {"model.completed"},
            "planner.decided": {"planner.started"},
            "planner.failed": {"planner.started"},
            "tool.requested": {"planner.decided"},
            "tool.policy": {"tool.requested"},
            "approval.requested": {"tool.policy"},
            "approval.resolved": {"approval.requested"},
            "approval.cancelled": {"approval.requested"},
            "tool.started": {"tool.policy", "approval.resolved"},
            "tool.completed": {"tool.started"},
            "tool.failed": {"tool.started", "tool.policy", "approval.resolved"},
            "tool.denied": {"tool.policy", "approval.resolved"},
            "run.paused": {"approval.requested"},
            "run.resumed": {"approval.resolved"},
            "run.completed": {"planner.decided"},
            "run.failed": {"model.failed", "planner.failed", "tool.failed", "tool.denied", "model.completed", "planner.decided"} if step_id else set(),
            "model.cancelled": {"model.requested"},
            "model.interrupted": {"model.requested"},
            "planner.cancelled": {"planner.started"},
            "planner.interrupted": {"planner.started"},
            "tool.cancelled": {"tool.started", "approval.requested", "tool.requested"},
            "tool.interrupted": {"tool.started", "approval.requested", "tool.requested"},
            "run.cancelled": {"model.cancelled", "planner.cancelled", "tool.cancelled"} if step_id else {"run.created"},
            "run.interrupted": {"model.interrupted", "planner.interrupted", "tool.interrupted"} if step_id else set(),
            "artifact.created": {"tool.completed"},
            "artifact.expired": {"artifact.created"},
        }
        same_step = type in {
            "model.delta", "model.completed", "model.failed", "model.retry",
            "planner.decided", "planner.failed", "tool.policy", "approval.requested",
            "approval.resolved", "approval.cancelled", "tool.started", "tool.completed",
            "tool.failed", "tool.denied", "run.failed", "model.cancelled", "model.interrupted",
            "planner.cancelled", "planner.interrupted", "tool.cancelled", "tool.interrupted",
            "run.interrupted",
        }
        same_step = same_step or (type == "run.cancelled" and step_id is not None)
        candidates = families.get(type, set())
        if not candidates:
            return None
        statement = select(EventRecord).where(
            EventRecord.run_id == run_id, EventRecord.type.in_(candidates),
        ).order_by(EventRecord.sequence.desc())
        for event in self.session.scalars(statement):
            event_step = event.step_id or event.payload.get("step_id")
            if same_step and (step_id is None or event_step != step_id):
                continue
            if (type.startswith("approval.") and event.type.startswith("approval.")
                    and payload.get("approval_id") != event.payload.get("approval_id")):
                continue
            if (type.startswith("tool.") and type not in {"tool.cancelled", "tool.interrupted"}
                    and same_step and event.type.startswith("tool.")
                    and payload.get("call_id") != event.payload.get("call_id")):
                continue
            if (type in {"tool.failed", "tool.denied"} and event.type == "tool.policy"
                    and event.payload.get("decision") != "deny"):
                continue
            if type == "tool.requested" and event.payload.get("action") != "tool":
                continue
            if type == "model.requested" and event.type == "planner.decided" and event.payload.get("action") != "continue":
                continue
            if type == "run.completed" and event.payload.get("action") != "finish":
                continue
            if type == "artifact.created":
                artifact = self.session.get(ArtifactRecord, payload.get("id"))
                output = event.payload.get("output", {})
                if artifact is None or artifact.run_id != run_id or event.payload.get("tool_name") != "filesystem_write" or output.get("path") != artifact.path:
                    continue
            if type == "artifact.expired" and event.payload.get("id") != payload.get("id"):
                continue
            return event
        return None

    def transition(
        self,
        record: RunRecord,
        target: RunStatus,
        event_type: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        now = utc_now()
        run = Run(
            id=record.id,
            agent_version_id=record.agent_version_id,
            input=record.input,
            status=RunStatus(record.status),
            created_at=record.created_at,
            updated_at=record.updated_at,
        ).transition(target, at=now)
        result = self.session.execute(
            update(RunRecord)
            .where(RunRecord.id == record.id, RunRecord.status == record.status)
            .values(status=target.value, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise InvalidRunTransition("run status changed concurrently")
        record.status = run.status.value
        record.updated_at = now
        self.append_event(record.id, event_type, payload or {"status": target.value})

    def create_step(
        self,
        *,
        run_id: str,
        kind: StepKind,
        input: dict[str, object],
        status: StepStatus = StepStatus.PENDING,
        attempt: int = 1,
    ) -> StepRecord:
        next_sequence = self.session.scalar(
            select(func.max(StepRecord.sequence)).where(StepRecord.run_id == run_id)
        )
        step_id = str(uuid4())
        step = StepRecord(
            id=step_id,
            correlation_id=run_id,
            trace_id=trace_id_for_run(run_id),
            span_id=span_id_for_step(step_id),
            run_id=run_id,
            sequence=(next_sequence or 0) + 1,
            kind=kind.value,
            status=status.value,
            input=input,
            attempt=attempt,
        )
        self.session.add(step)
        self.session.flush()
        return step

    def steps(self, run_id: str) -> list[StepRecord]:
        statement = (
            select(StepRecord)
            .where(StepRecord.run_id == run_id)
            .order_by(StepRecord.sequence)
        )
        return list(self.session.scalars(statement))
