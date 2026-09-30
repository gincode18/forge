"""Execute model/planner turns, committing each observable boundary."""
import asyncio
import json
from contextlib import aclosing
from dataclasses import asdict

from sqlalchemy.orm import Session

from forge.adapters.sqlite.database import Database
from forge.adapters.sqlite.models import AgentVersionRecord, StepRecord, utc_now
from forge.adapters.sqlite.repositories import RunRepository
from forge.application.errors import ResourceNotFoundError
from forge.domain.runs import RunStatus
from forge.domain.steps import StepKind, StepStatus
from forge.runtime.ports import (
    ContinueAction,
    FinalAction,
    ModelMessage,
    ModelProvider,
    ModelResult,
    Planner,
    ProviderError,
    ToolAction,
)


def _fail_step(
    database: Database, run_id: str, step_id: str, kind: str, exc: Exception,
    *, terminal: bool = True, reason: str | None = None,
) -> bool:
    with Session(database.engine) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        step = session.get(StepRecord, step_id)
        if run is None or step is None:
            raise ResourceNotFoundError("run", run_id)
        if run.status != RunStatus.RUNNING.value:
            return False
        step.status = StepStatus.FAILED.value
        step.error = {
            "type": type(exc).__name__,
            "message": str(exc) if isinstance(exc, (ProviderError, TimeoutError)) else "run execution failed",
        }
        step.finished_at = utc_now()
        runs.append_event(run_id, f"{kind}.failed", {"step_id": step_id})
        if terminal:
            reason = reason or ("timeout" if isinstance(exc, TimeoutError) else "error")
            runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": reason})
        session.commit()
        return True


def _start_step(database, run_id, kind, input, max_steps, deadline, attempt=1):
    with Session(database.engine) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        if run is None:
            raise ResourceNotFoundError("run", run_id)
        if run.status != RunStatus.RUNNING.value:
            return None
        reason = None
        if len(runs.steps(run_id)) >= max_steps:
            reason = "max_steps"
        elif asyncio.get_running_loop().time() >= deadline:
            reason = "timeout"
        if reason:
            runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": reason})
            session.commit()
            return None
        step = runs.create_step(run_id=run_id, kind=kind, input=input, status=StepStatus.RUNNING)
        step.started_at = utc_now()
        step.attempt = attempt
        runs.append_event(run_id, "model.requested" if kind == StepKind.MODEL else "planner.started", {
            "step_id": step.id,
        })
        step_id = step.id
        session.commit()
        return step_id


def _delta(database, run_id, step_id, text):
    with Session(database.engine) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        if run is not None and run.status == RunStatus.RUNNING.value:
            runs.append_event(run_id, "model.delta", {"step_id": step_id, "text": text})
            session.commit()


async def _model(database, run_id, step_id, provider, instructions, input, messages, output_cap):
    if not callable(getattr(provider, "stream", None)):
        context = input if not messages else json.dumps([
            {"role": "user", "text": input}, *[asdict(message) for message in messages],
        ])
        return await provider.complete(instructions=instructions, input=context)
    response = None
    pending = []
    pending_size = 0
    count = 0

    def flush(*, final=False):
        nonlocal pending_size, count
        if pending and (count < 127 or final):
            _delta(database, run_id, step_id, "".join(pending))
            pending.clear()
            pending_size = 0
            count += 1

    async def ticker():
        while True:
            await asyncio.sleep(0.1)
            flush()

    timer = asyncio.create_task(ticker())
    try:
        async with aclosing(provider.stream(
            instructions=instructions, input=input, messages=messages, max_output_tokens=output_cap,
        )) as stream:
            async for item in stream:
                if response is not None:
                    raise ValueError("provider stream yielded after final result")
                if isinstance(item, ModelResult):
                    response = item
                elif item.text:
                    pending.append(item.text)
                    pending_size += len(item.text)
                    if count == 0 or pending_size >= 1024:
                        flush()
        flush(final=True)
    finally:
        timer.cancel()
        await asyncio.gather(timer, return_exceptions=True)
    if response is None:
        raise ValueError("provider stream did not return a final result")
    return response


async def execute_fake_run(
    database: Database, run_id: str, provider: ModelProvider, planner: Planner,
    *, timeout_seconds: float | None = None, claimed: bool = False,
) -> None:
    """Compatibility entry point for fake and real providers; no transaction spans awaits."""
    if timeout_seconds is not None and timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    deadline = (asyncio.get_running_loop().time() + timeout_seconds
                if timeout_seconds is not None else float("inf"))
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
        max_cost = version.max_cost_usd
        input_rate = version.input_cost_per_million
        output_rate = version.output_cost_per_million
        deadline = min(deadline, asyncio.get_running_loop().time() + version.timeout_seconds)
        max_retries = version.max_retries
        max_tokens = version.max_tokens
        max_output_tokens = version.max_output_tokens
        if not claimed and run.status == RunStatus.QUEUED.value:
            runs.transition(run, RunStatus.RUNNING, "run.started")
        elif not claimed or run.status != RunStatus.RUNNING.value:
            raise ValueError("run is not runnable")
        session.commit()
    prepare = getattr(planner, "prepare", None)
    if callable(prepare):
        instructions = prepare(instructions)
    messages = ()
    total_tokens = 0
    total_cost = 0.0
    usage_known = True
    attempt = 1
    while True:
        model_input = {"instructions": instructions, "input": input}
        if messages:
            model_input["messages"] = [asdict(message) for message in messages]
        step_id = _start_step(database, run_id, StepKind.MODEL, model_input, max_steps, deadline, attempt)
        if step_id is None:
            return
        try:
            async with asyncio.timeout_at(deadline):
                output_cap = max_output_tokens
                if max_tokens is not None:
                    output_cap = min(output_cap, max_tokens - total_tokens)
                response = await _model(
                    database, run_id, step_id, provider, instructions, input, messages, output_cap,
                )
                if response.finish_reason not in {None, "STOP"}:
                    raise ProviderError(response.provider, "incomplete_response", "Model response was incomplete")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            retry = isinstance(exc, ProviderError) and exc.retryable and attempt <= max_retries
            usage_known = False
            reason = "retry_exhausted" if isinstance(exc, ProviderError) and exc.retryable else None
            if isinstance(exc, ProviderError) and (max_tokens is not None or max_cost is not None):
                # Failed requests have no normalized usage; never assume they were free.
                retry = False
                reason = "usage_unavailable"
            if not _fail_step(database, run_id, step_id, "model", exc, terminal=not retry, reason=reason):
                raise
            if not retry:
                raise
            with Session(database.engine) as session:
                runs = RunRepository(session)
                run = runs.get(run_id)
                if run is None or run.status != RunStatus.RUNNING.value:
                    return
                if len(runs.steps(run_id)) >= max_steps:
                    runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "max_steps"})
                    session.commit()
                    return
                runs.append_event(run_id, "model.retry", {
                    "step_id": step_id, "attempt": attempt + 1, "code": exc.code,
                })
                session.commit()
            try:
                async with asyncio.timeout_at(deadline):
                    await asyncio.sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))
            except TimeoutError:
                with Session(database.engine) as session:
                    runs = RunRepository(session)
                    run = runs.get(run_id)
                    if run is not None and run.status == RunStatus.RUNNING.value:
                        runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "timeout"})
                        session.commit()
                raise
            attempt += 1
            continue
        with Session(database.engine) as session:
            runs = RunRepository(session)
            run = runs.get(run_id)
            if run.status != RunStatus.RUNNING.value:
                return
            step = session.get(StepRecord, step_id)
            step.status = StepStatus.COMPLETED.value
            normalized = asdict(response)
            if response.usage is None:
                usage_known = False
            if response.usage is not None:
                total_tokens += response.usage.total_tokens
                if input_rate is not None and output_rate is not None:
                    cost = (response.usage.input_tokens * input_rate
                            + response.usage.output_tokens * output_rate) / 1_000_000
                    normalized["cost_usd"] = cost
                    total_cost += cost
            step.output = normalized
            step.finished_at = utc_now()
            runs.append_event(run_id, "model.completed", {
                "step_id": step_id, **normalized,
                "total_tokens": total_tokens if usage_known else None,
                "total_cost_usd": total_cost if usage_known and input_rate is not None and output_rate is not None else None,
            })
            if response.usage is not None and response.usage.output_tokens > max_output_tokens:
                runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "max_output_tokens"})
                session.commit()
                return
            if response.usage is None and (max_tokens is not None or max_cost is not None):
                runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "usage_unavailable"})
                session.commit()
                return
            if max_cost is not None and total_cost >= max_cost:
                runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "max_cost_usd"})
                session.commit()
                return
            if max_tokens is not None and total_tokens >= max_tokens:
                runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "max_tokens"})
                session.commit()
                return
            session.commit()
        planner_step_id = _start_step(database, run_id, StepKind.PLANNER, {
            "response": response.text,
        }, max_steps, deadline)
        if planner_step_id is None:
            return
        try:
            action = (ToolAction(response.tool_calls[0].name, response.tool_calls[0].arguments)
                      if response.tool_calls else planner.decide(response.text))
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("run wall-clock limit exceeded")
        except Exception as exc:
            _fail_step(database, run_id, planner_step_id, "planner", exc)
            raise
        with Session(database.engine) as session:
            runs = RunRepository(session)
            run = runs.get(run_id)
            if run.status != RunStatus.RUNNING.value:
                return
            step = session.get(StepRecord, planner_step_id)
            step.status = StepStatus.COMPLETED.value
            decision = ("tool" if isinstance(action, ToolAction) else
                        "continue" if isinstance(action, ContinueAction) else "finish")
            step.output = {"action": decision, **asdict(action)}
            step.finished_at = utc_now()
            runs.append_event(run_id, "planner.decided", {"step_id": planner_step_id, "action": decision})
            if isinstance(action, FinalAction):
                runs.transition(run, RunStatus.COMPLETED, "run.completed", {"result": action.text})
            if isinstance(action, ToolAction):
                runs.transition(run, RunStatus.FAILED, "run.failed", {"reason": "tool_disabled"})
            session.commit()
        if isinstance(action, (FinalAction, ToolAction)):
            return
        messages += (ModelMessage("assistant", response.text), ModelMessage("user", action.text))
        attempt = 1
