"""Own in-process runs independently of HTTP connections."""
import asyncio
import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.adapters.sqlite.database import Database
from forge.adapters.sqlite.models import (
    AgentVersionRecord,
    ApprovalRecord,
    RunCheckpointRecord,
    RunRecord,
    StepRecord,
    utc_now,
)
from forge.adapters.sqlite.repositories import RunRepository
from forge.application.approvals import resolve_approval
from forge.application.errors import ResourceNotFoundError
from forge.config import Settings
from forge.domain.runs import InvalidRunTransition, RunStatus
from forge.domain.steps import StepStatus
from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FakeProvider
from forge.runtime.gemini import GeminiProvider
from forge.runtime.ports import ModelProvider, ProviderError
from forge.runtime.react import ReActPlanner

logger = logging.getLogger(__name__)


class RunSupervisor:
    def __init__(self, database: Database, settings: Settings | None = None) -> None:
        self.database = database
        self.settings = settings
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.provider = FakeProvider()
        self.planner = ReActPlanner()
        self.timeout_seconds: float | None = None

    def start(self, run_id: str) -> RunRecord:
        if run_id in self.tasks:
            if not self.tasks[run_id].done():
                raise InvalidRunTransition("run is already scheduled")
            self.tasks.pop(run_id)
        with Session(self.database.engine, expire_on_commit=False) as session:
            run = RunRepository(session).get(run_id)
            if run is None:
                raise ResourceNotFoundError("run", run_id)
            resuming = run.status == RunStatus.RUNNING.value and session.get(RunCheckpointRecord, run_id) is not None
            if run.status != RunStatus.QUEUED.value and not resuming:
                raise InvalidRunTransition(f"cannot start run in state {run.status}")
            version = session.get(AgentVersionRecord, run.agent_version_id)
            if version is None:
                raise ResourceNotFoundError("agent version", run.agent_version_id)
            if version.provider not in {"fake", "gemini"} or version.planner != "react":
                raise ValueError("only no-tool fake or Gemini agents with the react planner can run")
            provider: ModelProvider = self.provider if version.provider == "fake" else GeminiProvider(
                version.model, api_key=(
                    self.settings.gemini_api_key.get_secret_value()
                    if self.settings and self.settings.gemini_api_key
                    else os.environ.get("GEMINI_API_KEY")
                )
            )
            if not resuming:
                RunRepository(session).transition(run, RunStatus.RUNNING, "run.started")
            session.commit()
            self.tasks[run_id] = asyncio.create_task(self._execute(run_id, provider))
            def cleanup(task):
                if self.tasks.get(run_id) is task:
                    self.tasks.pop(run_id, None)
            self.tasks[run_id].add_done_callback(cleanup)
            return run

    def cancel(self, run_id: str) -> RunRecord:
        with Session(self.database.engine, expire_on_commit=False) as session:
            runs = RunRepository(session)
            run = runs.get(run_id)
            if run is None:
                raise ResourceNotFoundError("run", run_id)
            active = session.scalars(select(StepRecord).where(
                StepRecord.run_id == run_id, StepRecord.status == StepStatus.RUNNING.value
            )).all()
            for step in active:
                step.status = StepStatus.CANCELLED.value
                step.finished_at = utc_now()
                runs.append_event(run_id, f"{step.kind}.cancelled", {"step_id": step.id})
            runs.transition(run, RunStatus.CANCELLED, "run.cancelled")
            for approval in session.scalars(select(ApprovalRecord).where(ApprovalRecord.run_id == run_id, ApprovalRecord.status == 'pending')):
                approval.status = 'cancelled'
                approval.resolved_at = utc_now()
                runs.append_event(run_id, 'approval.cancelled', {'approval_id': approval.id})
            session.commit()
            task = self.tasks.get(run_id)
            if task is not None:
                task.cancel()
            return run

    def resolve(self, approval_id: str, approved: bool) -> ApprovalRecord:
        # Discover provider availability before consuming a durable human decision.
        with Session(self.database.engine) as session:
            approval = session.get(ApprovalRecord, approval_id)
            if approval is None:
                raise ResourceNotFoundError('approval', approval_id)
            if approval.status != 'pending':
                raise InvalidRunTransition('approval is no longer pending')
            run = RunRepository(session).get(approval.run_id)
            version = session.get(AgentVersionRecord, run.agent_version_id)
            if version.provider == 'gemini':
                GeminiProvider(version.model, api_key=(
                    self.settings.gemini_api_key.get_secret_value()
                    if self.settings and self.settings.gemini_api_key else os.environ.get('GEMINI_API_KEY')
                ))
        approval = resolve_approval(self.database, approval_id, approved)
        self.start(approval.run_id)
        return approval

    async def _execute(self, run_id: str, provider: ModelProvider) -> None:
        try:
            await execute_fake_run(
                self.database, run_id, provider, self.planner,
                timeout_seconds=self.timeout_seconds, claimed=True,
                workspace_root=self.settings.resolved_data_dir / 'workspaces' if self.settings else None,
                subprocess_allowlist=tuple(tuple(argv) for argv in self.settings.subprocess_allowlist) if self.settings else (),
            )
        except Exception as exc:
            # Never render arbitrary SDK exception chains or transport headers.
            safe = RuntimeError(str(exc) if isinstance(exc, ProviderError) else "run execution failed")
            logger.error("Run failed: %s", run_id, exc_info=(RuntimeError, safe, None))
            with Session(self.database.engine) as session:
                runs = RunRepository(session)
                run = runs.get(run_id)
                if run is not None and run.status == RunStatus.RUNNING.value:
                    self._close_steps(runs, run_id, "failed", "RuntimeError")
                    runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "error"})
                    session.commit()

    @staticmethod
    def _close_steps(runs: RunRepository, run_id: str, event: str, error: str) -> None:
        active = runs.session.scalars(select(StepRecord).where(
            StepRecord.run_id == run_id, StepRecord.status == StepStatus.RUNNING.value
        )).all()
        for step in active:
            step.status = StepStatus.FAILED.value
            step.error = {"type": error, "message": "run execution stopped"}
            step.finished_at = utc_now()
            payload = {'step_id': step.id}
            if step.kind == 'tool' and event == 'failed':
                run = runs.get(run_id)
                version = runs.session.get(AgentVersionRecord, run.agent_version_id)
                tool_name = step.input.get('name', '')
                token = next((key for key in version.tools if key.split('@')[0] == tool_name), '')
                payload.update(tool_name=tool_name, tool_version=token.partition('@')[2],
                               call_id=step.input.get('id'), output={'error': 'run_execution_stopped'}, duration_ms=0)
            runs.append_event(run_id, f"{step.kind}.{event}", payload)

    def recover(self, *, resume: bool = True) -> None:
        """Resume only undispatched decisions; interrupt uncertain side effects."""
        ready = []
        with Session(self.database.engine) as session:
            runs = RunRepository(session)
            active = session.scalars(
                select(RunRecord).where(RunRecord.status == RunStatus.RUNNING.value)
            )
            for run in active:
                checkpoint = session.get(RunCheckpointRecord, run.id)
                approval = (session.get(ApprovalRecord, checkpoint.payload['approval_id'])
                            if checkpoint else None)
                if (checkpoint and not checkpoint.payload.get('execution_started')
                        and approval and approval.status in ('approved', 'rejected')):
                    ready.append(run.id)
                    continue
                self._close_steps(runs, run.id, "interrupted", "Interrupted")
                runs.transition(run, RunStatus.INTERRUPTED, "run.interrupted")
            session.commit()
        if resume:
            for run_id in ready:
                try:
                    self.start(run_id)
                except ValueError:
                    # Credentials may be unavailable after restart. Leave the
                    # committed decision dispatchable via the existing start route.
                    logger.warning('Approved run cannot dispatch: %s', run_id)

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.recover(resume=False)
