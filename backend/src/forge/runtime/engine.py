"""Execute a queued no-tool run through a provider and planner."""
import asyncio
from dataclasses import asdict

from sqlalchemy.orm import Session

from forge.adapters.sqlite.database import Database
from forge.adapters.sqlite.models import AgentVersionRecord, StepRecord, utc_now
from forge.adapters.sqlite.repositories import RunRepository
from forge.application.errors import ResourceNotFoundError
from forge.domain.runs import RunStatus
from forge.domain.steps import StepKind, StepStatus
from forge.runtime.ports import ModelProvider, Planner


def _fail_step(database: Database, run_id: str, step_id: str, kind: str, exc: Exception) -> None:
    with Session(database.engine) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        step = session.get(StepRecord, step_id)
        if run is None or step is None:
            raise ResourceNotFoundError("run", run_id)
        if run.status != RunStatus.RUNNING.value:
            return
        step.status = StepStatus.FAILED.value
        step.error = {"type": type(exc).__name__, "message": str(exc)}
        step.finished_at = utc_now()
        runs.append_event(run_id, f"{kind}.failed", {"step_id": step_id})
        reason = "timeout" if isinstance(exc, TimeoutError) else "error"
        runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": reason})
        session.commit()


async def execute_fake_run(
    database: Database, run_id: str, provider: ModelProvider, planner: Planner,
    *, timeout_seconds: float = 30.0, claimed: bool = False,
) -> None:
    """Persist each boundary; never keep a DB transaction open during a model call."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    with Session(database.engine, expire_on_commit=False) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        if run is None:
            raise ResourceNotFoundError("run", run_id)
        version = session.get(AgentVersionRecord, run.agent_version_id)
        if version is None:
            raise ResourceNotFoundError("agent version", run.agent_version_id)
        if version.provider not in {"fake", "gemini"} or version.tools or version.planner != "react":
            raise ValueError("only no-tool fake or Gemini agents with the react planner can run")
        instructions, input, max_steps = version.instructions, run.input, version.max_steps
        if not claimed and run.status == RunStatus.QUEUED.value:
            runs.transition(run, RunStatus.RUNNING, "run.started")
        elif not claimed or run.status != RunStatus.RUNNING.value:
            raise ValueError("run is not runnable")
        step = runs.create_step(
            run_id=run_id,
            kind=StepKind.MODEL,
            input={"instructions": instructions, "input": input},
            status=StepStatus.RUNNING,
        )
        step.started_at = utc_now()
        runs.append_event(run_id, "model.requested", {"step_id": step.id})
        step_id = step.id
        session.commit()

    try:
        async with asyncio.timeout_at(deadline):
            response = await provider.complete(instructions=instructions, input=input)
    except asyncio.CancelledError:
        # A supervisor cancellation has already committed the terminal transition.
        raise
    except Exception as exc:
        _fail_step(database, run_id, step_id, "model", exc)
        raise

    with Session(database.engine) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        if run is None:
            raise ResourceNotFoundError("run", run_id)
        if run.status != RunStatus.RUNNING.value:
            return
        step = session.get(StepRecord, step_id)
        if step is None:
            raise ResourceNotFoundError("run", run_id)
        step.status = StepStatus.COMPLETED.value
        step.output = {"text": response.text} if response.provider == "fake" else asdict(response)
        step.finished_at = utc_now()
        runs.append_event(run_id, "model.completed", {
            "step_id": step_id, "text": response.text,
            **({"usage": asdict(response.usage), "latency_ms": response.latency_ms,
                "finish_reason": response.finish_reason} if response.usage else {}),
        })
        if max_steps < 2:
            runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "max_steps"})
            session.commit()
            return
        if asyncio.get_running_loop().time() >= deadline:
            runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "timeout"})
            session.commit()
            return
        planner_step = runs.create_step(
            run_id=run_id,
            kind=StepKind.PLANNER,
            input={"response": response.text},
            status=StepStatus.RUNNING,
        )
        planner_step.started_at = utc_now()
        runs.append_event(run_id, "planner.started", {"step_id": planner_step.id})
        planner_step_id = planner_step.id
        session.commit()

    try:
        action = planner.decide(response.text)
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("run wall-clock limit exceeded")
    except Exception as exc:
        _fail_step(database, run_id, planner_step_id, "planner", exc)
        raise

    with Session(database.engine) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        planner_step = session.get(StepRecord, planner_step_id)
        if run is None or planner_step is None:
            raise ResourceNotFoundError("run", run_id)
        if run.status != RunStatus.RUNNING.value:
            return
        planner_step.status = StepStatus.COMPLETED.value
        planner_step.output = {"action": "finish", "text": action.text}
        planner_step.finished_at = utc_now()
        runs.append_event(run_id, "planner.decided", {"step_id": planner_step_id, "action": "finish"})
        runs.transition(run, RunStatus.COMPLETED, "run.completed", {"result": action.text})
        session.commit()
