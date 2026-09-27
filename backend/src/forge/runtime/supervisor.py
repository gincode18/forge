"""Own in-process fake runs independently of HTTP connections."""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.adapters.sqlite.database import Database
from forge.adapters.sqlite.models import (
    AgentVersionRecord,
    RunRecord,
    StepRecord,
    utc_now,
)
from forge.adapters.sqlite.repositories import RunRepository
from forge.application.errors import ResourceNotFoundError
from forge.domain.runs import InvalidRunTransition, RunStatus
from forge.domain.steps import StepStatus
from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FakeProvider, FinalPlanner

logger = logging.getLogger(__name__)


class RunSupervisor:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.provider = FakeProvider()
        self.planner = FinalPlanner()
        self.timeout_seconds = 30.0

    def start(self, run_id: str) -> RunRecord:
        if run_id in self.tasks:
            raise InvalidRunTransition("run is already scheduled")
        with Session(self.database.engine, expire_on_commit=False) as session:
            run = RunRepository(session).get(run_id)
            if run is None:
                raise ResourceNotFoundError("run", run_id)
            if run.status != RunStatus.QUEUED.value:
                raise InvalidRunTransition(f"cannot start run in state {run.status}")
            version = session.get(AgentVersionRecord, run.agent_version_id)
            if version is None:
                raise ResourceNotFoundError("agent version", run.agent_version_id)
            if version.provider != "fake" or version.tools or version.planner != "react":
                raise ValueError("only no-tool fake agents can run in this slice")
            RunRepository(session).transition(run, RunStatus.RUNNING, "run.started")
            session.commit()
            self.tasks[run_id] = asyncio.create_task(self._execute(run_id))
            self.tasks[run_id].add_done_callback(lambda _: self.tasks.pop(run_id, None))
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
            session.commit()
            task = self.tasks.get(run_id)
            if task is not None:
                task.cancel()
            return run

    async def _execute(self, run_id: str) -> None:
        try:
            await execute_fake_run(
                self.database, run_id, self.provider, self.planner,
                timeout_seconds=self.timeout_seconds, claimed=True,
            )
        except Exception:
            logger.exception("Fake run failed: %s", run_id)
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
            runs.append_event(run_id, f"{step.kind}.{event}", {"step_id": step.id})

    def recover(self) -> None:
        """Mark abandoned running work interrupted at API startup."""
        with Session(self.database.engine) as session:
            runs = RunRepository(session)
            active = session.scalars(
                select(RunRecord).where(RunRecord.status == RunStatus.RUNNING.value)
            )
            for run in active:
                self._close_steps(runs, run.id, "interrupted", "Interrupted")
                runs.transition(run, RunStatus.INTERRUPTED, "run.interrupted")
            session.commit()

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.recover()
