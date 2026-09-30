import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from forge.adapters.sqlite.repositories import RunRepository
from forge.api.app import create_app
from forge.api.routes.runs import stream_events
from forge.config import Settings
from forge.domain.runs import RunStatus
from forge.domain.steps import StepKind, StepStatus
from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FakeProvider, FinalPlanner
from forge.runtime.ports import FinalAction, ModelResult
from forge.runtime.supervisor import RunSupervisor


def test_fake_runtime_persists_model_step_and_final_trace(client: TestClient) -> None:
    agent = client.post(
        "/api/v1/agents",
        json={"name": "Example", "instructions": "Be clear."},
    ).json()
    created = client.post(
        "/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}
    ).json()

    asyncio.run(
        execute_fake_run(
            client.app.state.database,
            created["id"],
            FakeProvider({"Hello": "Hello from the fake model."}),
            FinalPlanner(),
        )
    )

    run = client.get(f"/api/v1/runs/{created['id']}").json()
    steps = client.get(f"/api/v1/runs/{created['id']}/steps").json()
    events = client.get(f"/api/v1/runs/{created['id']}/events").json()
    assert run["status"] == "completed"
    assert [(step["kind"], step["status"]) for step in steps] == [
        ("model", "completed"), ("planner", "completed")
    ]
    assert steps[0]["input"] == {"instructions": "Be clear.", "input": "Hello"}
    assert steps[0]["output"] == {"text": "Hello from the fake model."}
    assert [event["type"] for event in events] == [
        "run.created", "run.started", "model.requested", "model.completed",
        "planner.started", "planner.decided", "run.completed",
    ]
    assert [event["sequence"] for event in events] == list(range(1, 8))
    assert events[-1]["payload"]["result"] == "Hello from the fake model."


def test_fake_provider_failure_leaves_durable_failed_trace(client: TestClient) -> None:
    agent = client.post(
        "/api/v1/agents", json={"name": "Failing", "instructions": "Try."}
    ).json()
    run_id = client.post(
        "/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}
    ).json()["id"]

    class FailingProvider:
        async def complete(self, *, instructions: str, input: str) -> ModelResult:
            raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        asyncio.run(
            execute_fake_run(client.app.state.database, run_id, FailingProvider(), FinalPlanner())
        )

    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "failed"
    steps = client.get(f"/api/v1/runs/{run_id}/steps").json()
    assert steps[0]["status"] == "failed"
    assert steps[0]["error"]["type"] == "RuntimeError"
    events = client.get(f"/api/v1/runs/{run_id}/events").json()
    assert [event["type"] for event in events][-2:] == ["model.failed", "run.failed"]


def test_start_endpoint_runs_fake_agent_without_a_model_key(client: TestClient) -> None:
    agent = client.post(
        "/api/v1/agents", json={"name": "Runnable", "instructions": "Be clear."}
    ).json()
    run_id = client.post(
        "/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}
    ).json()["id"]

    accepted = client.post(f"/api/v1/runs/{run_id}/start")
    assert accepted.status_code == 202
    assert accepted.json()["id"] == run_id

    deadline = time.monotonic() + 2
    run = client.get(f"/api/v1/runs/{run_id}").json()
    while time.monotonic() < deadline:
        run = client.get(f"/api/v1/runs/{run_id}").json()
        if run["status"] == "completed":
            break
        time.sleep(0.01)

    assert run["status"] == "completed"
    events = client.get(f"/api/v1/runs/{run_id}/events").json()
    assert events[-1]["payload"]["result"] == "Fake response to: Hello"

    duplicate = client.post(f"/api/v1/runs/{run_id}/start")
    assert duplicate.status_code == 409
    assert duplicate.json()["request_id"] == duplicate.headers["X-Request-ID"]


def test_start_rejects_non_fake_agent_without_changing_run(client: TestClient) -> None:
    agent = client.post(
        "/api/v1/agents",
        json={"name": "External", "instructions": "Try.", "provider": "remote"},
    ).json()
    run_id = client.post(
        "/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}
    ).json()["id"]

    response = client.post(f"/api/v1/runs/{run_id}/start")

    assert response.status_code == 422
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "queued"
    assert [event["type"] for event in client.get(f"/api/v1/runs/{run_id}/events").json()] == ["run.created"]


def test_start_rejects_unsupported_planner_without_scheduling(client: TestClient) -> None:
    agent = client.post(
        "/api/v1/agents",
        json={"name": "Other planner", "instructions": "Try.", "planner": "other"},
    ).json()
    run_id = client.post(
        "/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}
    ).json()["id"]

    response = client.post(f"/api/v1/runs/{run_id}/start")

    assert response.status_code == 422
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "queued"
    assert run_id not in client.app.state.supervisor.tasks


def test_queued_run_cancellation_is_durable_and_cannot_start(client: TestClient) -> None:
    agent = client.post("/api/v1/agents", json={"name": "Cancel", "instructions": "Stop."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}).json()["id"]

    response = client.post(f"/api/v1/runs/{run_id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert [event["type"] for event in client.get(f"/api/v1/runs/{run_id}/events").json()] == [
        "run.created", "run.cancelled"
    ]
    assert client.post(f"/api/v1/runs/{run_id}/start").status_code == 409
    assert client.post(f"/api/v1/runs/{run_id}/cancel").status_code == 409


def test_running_cancellation_closes_active_step_without_late_completion(client: TestClient) -> None:
    class WaitingProvider:
        async def complete(self, *, instructions: str, input: str) -> ModelResult:
            await asyncio.Event().wait()
            return ModelResult(text="too late", provider="fake", model="deterministic")

    client.app.state.supervisor.provider = WaitingProvider()
    agent = client.post("/api/v1/agents", json={"name": "Slow", "instructions": "Wait."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}).json()["id"]
    assert client.post(f"/api/v1/runs/{run_id}/start").status_code == 202
    deadline = time.monotonic() + 2
    while not client.get(f"/api/v1/runs/{run_id}/steps").json() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert client.get(f"/api/v1/runs/{run_id}/steps").json()[0]["status"] == "running"

    assert client.post(f"/api/v1/runs/{run_id}/cancel").json()["status"] == "cancelled"
    assert client.get(f"/api/v1/runs/{run_id}/steps").json()[0]["status"] == "cancelled"
    assert client.get(f"/api/v1/runs/{run_id}/events").json()[-1]["type"] == "run.cancelled"
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "cancelled"


def test_max_steps_limits_model_and_planner_boundaries(client: TestClient) -> None:
    agent = client.post("/api/v1/agents", json={
        "name": "One step", "instructions": "Finish.", "max_steps": 1
    }).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider(), FinalPlanner()))
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "failed"
    assert [s["kind"] for s in client.get(f"/api/v1/runs/{run_id}/steps").json()] == ["model"]
    assert client.get(f"/api/v1/runs/{run_id}/events").json()[-1]["payload"]["reason"] == "max_steps"


def test_wall_clock_timeout_closes_model_step(client: TestClient) -> None:
    class WaitingProvider:
        async def complete(self, *, instructions: str, input: str) -> ModelResult:
            await asyncio.Event().wait()
            return ModelResult(text="never", provider="fake", model="deterministic")

    agent = client.post("/api/v1/agents", json={"name": "Timeout", "instructions": "Wait."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    with pytest.raises(TimeoutError):
        asyncio.run(execute_fake_run(
            client.app.state.database, run_id, WaitingProvider(), FinalPlanner(), timeout_seconds=0.01
        ))
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "failed"
    assert client.get(f"/api/v1/runs/{run_id}/steps").json()[0]["error"]["type"] == "TimeoutError"
    assert client.get(f"/api/v1/runs/{run_id}/events").json()[-1]["payload"]["reason"] == "timeout"


def test_provider_error_after_cancellation_cannot_overwrite_terminal_trace(client: TestClient) -> None:
    agent = client.post("/api/v1/agents", json={"name": "Race error", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]

    class CancellingProvider:
        async def complete(self, *, instructions: str, input: str) -> ModelResult:
            client.app.state.supervisor.cancel(run_id)
            raise RuntimeError("late error")

    with pytest.raises(RuntimeError, match="late error"):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, CancellingProvider(), FinalPlanner()))
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "cancelled"
    assert client.get(f"/api/v1/runs/{run_id}/steps").json()[0]["status"] == "cancelled"
    assert client.get(f"/api/v1/runs/{run_id}/events").json()[-1]["type"] == "run.cancelled"


def test_wall_clock_limit_also_covers_planner(client: TestClient) -> None:
    class SlowPlanner:
        def decide(self, response: str) -> FinalAction:
            time.sleep(0.02)
            return FinalAction(text=response)

    agent = client.post("/api/v1/agents", json={"name": "Planner time", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    with pytest.raises(TimeoutError):
        asyncio.run(execute_fake_run(
            client.app.state.database, run_id, FakeProvider(), SlowPlanner(), timeout_seconds=0.01
        ))
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "failed"
    assert client.get(f"/api/v1/runs/{run_id}/steps").json()[-1]["error"]["type"] == "TimeoutError"


def test_second_supervisor_cannot_schedule_claimed_run(client: TestClient) -> None:
    agent = client.post("/api/v1/agents", json={"name": "Once", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    class WaitingProvider:
        async def complete(self, *, instructions: str, input: str) -> str:
            await asyncio.Event().wait()
            return "never"

    client.app.state.supervisor.provider = WaitingProvider()
    first = client.post(f"/api/v1/runs/{run_id}/start")
    assert first.status_code == 202
    assert first.json()["status"] == "running"
    other = RunSupervisor(client.app.state.database)
    with pytest.raises(Exception, match="cannot start run"):
        other.start(run_id)
    assert [e["type"] for e in client.get(f"/api/v1/runs/{run_id}/events").json()].count("run.started") == 1


def test_sse_replays_persisted_events_after_sequence_and_ends(client: TestClient) -> None:
    agent = client.post("/api/v1/agents", json={"name": "Stream", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider(), FinalPlanner()))
    response = client.get(f"/api/v1/runs/{run_id}/stream", headers={"Last-Event-ID": "3"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [dict(line.split(": ", 1) for line in frame.splitlines())
              for frame in response.text.strip().split("\n\n")]
    assert [int(frame["id"]) for frame in frames] == [4, 5, 6, 7]
    assert [frame["event"] for frame in frames] == [
        "model.completed", "planner.started", "planner.decided", "run.completed"
    ]
    assert json.loads(frames[-1]["data"])["payload"]["result"] == "Fake response to: Hi"
    assert client.get(f"/api/v1/runs/{run_id}/stream", headers={"Last-Event-ID": "7"}).text == ""
    assert client.get(f"/api/v1/runs/{run_id}/stream", headers={"Last-Event-ID": "nope"}).status_code == 422
    assert client.get("/api/v1/runs/missing/stream").status_code == 404


def test_sse_initial_cursor_can_be_passed_in_query_for_eventsource(client: TestClient) -> None:
    agent = client.post("/api/v1/agents", json={"name": "Cursor", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider(), FinalPlanner()))

    response = client.get(f"/api/v1/runs/{run_id}/stream?since=5")
    assert [line for line in response.text.splitlines() if line.startswith("id: ")] == [
        "id: 6", "id: 7"
    ]
    assert client.get(f"/api/v1/runs/{run_id}/stream?since=-1").status_code == 422
    assert client.get(f"/api/v1/runs/{run_id}/stream?since=oops").status_code == 422

    # Native EventSource reconnects provide Last-Event-ID; it overrides the
    # initial query cursor and must not replay events the browser already saw.
    response = client.get(
        f"/api/v1/runs/{run_id}/stream?since=1", headers={"Last-Event-ID": "6"}
    )
    assert [line for line in response.text.splitlines() if line.startswith("id: ")] == ["id: 7"]


def test_sse_follows_live_run_until_terminal_event(client: TestClient) -> None:
    class SlowProvider:
        async def complete(self, *, instructions: str, input: str) -> ModelResult:
            await asyncio.sleep(0.08)
            return ModelResult(text="live result", provider="fake", model="deterministic")

    client.app.state.supervisor.provider = SlowProvider()
    agent = client.post("/api/v1/agents", json={"name": "Live", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    assert client.post(f"/api/v1/runs/{run_id}/start").status_code == 202
    response = client.get(f"/api/v1/runs/{run_id}/stream", headers={"Last-Event-ID": "1"})
    frames = [dict(line.split(": ", 1) for line in frame.splitlines())
              for frame in response.text.strip().split("\n\n")]
    assert [int(frame["id"]) for frame in frames] == list(range(2, 8))
    assert frames[-1]["event"] == "run.completed"
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "completed"


def test_stream_disconnect_does_not_cancel_running_work(client: TestClient) -> None:
    class WaitingProvider:
        async def complete(self, *, instructions: str, input: str) -> str:
            await asyncio.Event().wait()
            return "never"

    client.app.state.supervisor.provider = WaitingProvider()
    agent = client.post("/api/v1/agents", json={"name": "Disconnect", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    assert client.post(f"/api/v1/runs/{run_id}/start").status_code == 202

    async def disconnect() -> str:
        request = Request({"type": "http", "app": client.app})
        response = await stream_events(run_id, request, None, 0)
        first = await anext(response.body_iterator)
        await response.body_iterator.aclose()
        return first

    assert "event: run.created" in asyncio.run(disconnect())
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "running"
    assert client.post(f"/api/v1/runs/{run_id}/cancel").status_code == 200


def test_stream_does_not_miss_terminal_commit_between_queries(client: TestClient, monkeypatch) -> None:
    agent = client.post("/api/v1/agents", json={"name": "Race", "instructions": "Go."}).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    original = RunRepository.events_after
    triggered = False

    def commit_between_queries(repository, target, cursor):
        nonlocal triggered
        result = original(repository, target, cursor)
        if not triggered:
            triggered = True
            with Session(client.app.state.database.engine) as session:
                runs = RunRepository(session)
                runs.transition(runs.get(run_id), RunStatus.CANCELLED, "run.cancelled")
                session.commit()
        return result

    monkeypatch.setattr(RunRepository, "events_after", commit_between_queries)
    response = client.get(f"/api/v1/runs/{run_id}/stream")
    assert "event: run.cancelled" in response.text


def test_planner_failure_does_not_mark_successful_model_failed(client: TestClient) -> None:
    agent = client.post(
        "/api/v1/agents", json={"name": "Planner", "instructions": "Try."}
    ).json()
    run_id = client.post(
        "/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}
    ).json()["id"]

    class FailingPlanner:
        def decide(self, response: str) -> FinalAction:
            raise RuntimeError("cannot decide")

    with pytest.raises(RuntimeError, match="cannot decide"):
        asyncio.run(
            execute_fake_run(client.app.state.database, run_id, FakeProvider(), FailingPlanner())
        )

    steps = client.get(f"/api/v1/runs/{run_id}/steps").json()
    assert [(step["kind"], step["status"]) for step in steps] == [
        ("model", "completed"), ("planner", "failed")
    ]
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "failed"


def test_abandoned_running_run_is_interrupted_on_restart(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    with TestClient(create_app(settings)) as first:
        agent = first.post(
            "/api/v1/agents", json={"name": "Abandoned", "instructions": "Try."}
        ).json()
        run_id = first.post(
            "/api/v1/runs", json={"agent_id": agent["id"], "input": "Hello"}
        ).json()["id"]
        with next(first.app.state.database.session()) as session:
            repository = RunRepository(session)
            record = repository.get(run_id)
            assert record is not None
            repository.transition(record, RunStatus.RUNNING, "run.started")
            session.commit()

    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(f"/api/v1/runs/{run_id}").json()["status"] == "interrupted"
        events = restarted.get(f"/api/v1/runs/{run_id}/events").json()
        assert [event["type"] for event in events] == [
            "run.created", "run.started", "run.interrupted"
        ]


def test_recovery_closes_abandoned_active_step(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    with TestClient(create_app(settings)) as first:
        agent = first.post("/api/v1/agents", json={"name": "Recovery", "instructions": "Go."}).json()
        run_id = first.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
        with Session(first.app.state.database.engine) as session:
            repository = RunRepository(session)
            record = repository.get(run_id)
            assert record is not None
            repository.transition(record, RunStatus.RUNNING, "run.started")
            repository.create_step(run_id=run_id, kind=StepKind.MODEL, input={"input": "Hi"}, status=StepStatus.RUNNING)
            session.commit()
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(f"/api/v1/runs/{run_id}").json()["status"] == "interrupted"
        step = restarted.get(f"/api/v1/runs/{run_id}/steps").json()[0]
        assert step["status"] == "failed"
        assert step["error"]["type"] == "Interrupted"
        assert step["finished_at"] is not None
        events = restarted.get(f"/api/v1/runs/{run_id}/events").json()
        assert [e["type"] for e in events][-2:] == ["model.interrupted", "run.interrupted"]
