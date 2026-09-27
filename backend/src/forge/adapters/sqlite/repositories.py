"""Repository implementations backed by a SQLAlchemy session."""

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from forge.adapters.sqlite.models import (
    AgentRecord,
    AgentVersionRecord,
    EventRecord,
    RunRecord,
    StepRecord,
    utc_now,
)
from forge.domain.runs import RunStatus
from forge.domain.steps import StepKind, StepStatus


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
        run.events.append(
            EventRecord(
                id=str(uuid4()),
                sequence=1,
                type="run.created",
                payload={"status": RunStatus.QUEUED.value, "request_id": request_id},
                schema_version=1,
                created_at=now,
            )
        )
        self.session.add(run)
        self.session.flush()
        return run

    def list_all(self) -> list[RunRecord]:
        return list(
            self.session.scalars(select(RunRecord).order_by(RunRecord.created_at.desc()))
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
        step = StepRecord(
            id=str(uuid4()),
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
