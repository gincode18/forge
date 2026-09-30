"""Regression checks discovered during the combined Phase 3 review."""
import asyncio

import pytest
from test_runtime_loop import new_run, trace

from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FinalPlanner
from forge.runtime.ports import (
    ContinueAction,
    FinalAction,
    ModelResult,
    ModelUsage,
    ProviderError,
)


def test_legacy_completion_receives_ordered_history(client):
    run_id = new_run(client)
    inputs = []

    class Legacy:
        async def complete(self, *, instructions, input):
            inputs.append(input)
            return ModelResult("first" if len(inputs) == 1 else "done", "fake", "legacy")

    class Planning:
        def decide(self, response):
            return ContinueAction("Continue now") if response == "first" else FinalAction(response)

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Legacy(), Planning()))
    assert inputs[0] == "Hello"
    assert "first" in inputs[1]
    assert inputs[1].index("Hello") < inputs[1].index("first") < inputs[1].index("Continue now")


def test_unknown_usage_and_unpriced_cost_remain_unknown_in_events(client):
    run_id = new_run(client)

    class Unknown:
        async def complete(self, **kwargs):
            return ModelResult("done", "fake", "unknown")

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Unknown(), FinalPlanner()))
    completed = next(e for e in trace(client, run_id, "events") if e["type"] == "model.completed")
    assert completed["payload"]["total_tokens"] is None
    assert completed["payload"]["total_cost_usd"] is None


def test_unpriced_known_usage_does_not_imply_free_run(client):
    run_id = new_run(client)

    class Known:
        async def complete(self, **kwargs):
            return ModelResult("done", "fake", "known", usage=ModelUsage(1, 2, 3))

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Known(), FinalPlanner()))
    completed = next(e for e in trace(client, run_id, "events") if e["type"] == "model.completed")
    assert completed["payload"]["total_tokens"] == 3
    assert completed["payload"]["total_cost_usd"] is None


def test_runtime_rejects_truncated_normalized_result(client):
    run_id = new_run(client)

    class Truncated:
        async def complete(self, **kwargs):
            return ModelResult("partial", "fake", "broken", finish_reason="MAX_TOKENS")

    with pytest.raises(ProviderError, match="incomplete"):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Truncated(), FinalPlanner()))
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "failed"
    assert not any(e["type"] == "run.completed" for e in trace(client, run_id, "events"))


def test_version_timeout_can_exceed_previous_default(client, monkeypatch):
    run_id = new_run(client, timeout_seconds=60)
    deadlines = []
    original = asyncio.timeout_at

    def observe(deadline):
        deadlines.append(deadline - asyncio.get_running_loop().time())
        return original(deadline)

    monkeypatch.setattr("forge.runtime.engine.asyncio.timeout_at", observe)

    class Quick:
        async def complete(self, **kwargs):
            return ModelResult("done", "fake", "quick")

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Quick(), FinalPlanner()))
    assert 59 < deadlines[0] <= 60


def test_retry_backoff_obeys_run_deadline(client):
    run_id = new_run(client, timeout_seconds=0.02)
    calls = []

    class Flaky:
        async def complete(self, **kwargs):
            calls.append(True)
            raise ProviderError("fake", "unavailable", "Temporary", retryable=True)

    with pytest.raises(TimeoutError):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Flaky(), FinalPlanner()))
    assert calls == [True]
    assert trace(client, run_id, "events")[-1]["payload"]["reason"] == "timeout"


def test_cancellation_during_retry_backoff_never_starts_next_attempt(client, monkeypatch):
    run_id = new_run(client)
    calls = []

    class Flaky:
        async def complete(self, **kwargs):
            calls.append(True)
            raise ProviderError("fake", "unavailable", "Temporary", retryable=True)

    async def exercise():
        entered = asyncio.Event()

        async def blocked_backoff(delay):
            entered.set()
            await asyncio.Event().wait()

        monkeypatch.setattr("forge.runtime.engine.asyncio.sleep", blocked_backoff)
        task = asyncio.create_task(execute_fake_run(
            client.app.state.database, run_id, Flaky(), FinalPlanner(),
        ))
        await entered.wait()
        client.app.state.supervisor.cancel(run_id)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    assert calls == [True]
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "cancelled"
    assert len(trace(client, run_id, "steps")) == 1
    assert trace(client, run_id, "events")[-1]["type"] == "run.cancelled"
