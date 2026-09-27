from fastapi.testclient import TestClient

from forge.adapters.sqlite.repositories import RunRepository
from forge.domain.steps import StepKind, StepStatus


def create_agent(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/agents",
        json={
            "name": "Home Agent",
            "description": "A small local Forge agent",
            "instructions": "Help operate the home lab safely.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_agent_versions_are_immutable_snapshots(client: TestClient) -> None:
    agent = create_agent(client)
    agent_id = str(agent["id"])

    version_response = client.post(
        f"/api/v1/agents/{agent_id}/versions",
        json={
            "instructions": "Help operate the home lab and explain every action.",
            "provider": "fake",
            "model": "deterministic-v2",
        },
    )

    assert version_response.status_code == 201
    assert version_response.json()["version"] == 2

    detail = client.get(f"/api/v1/agents/{agent_id}")
    versions = detail.json()["versions"]
    assert [item["version"] for item in versions] == [1, 2]
    assert versions[0]["instructions"] == "Help operate the home lab safely."


def test_queued_run_is_pinned_and_emits_created_event(client: TestClient) -> None:
    agent = create_agent(client)
    agent_id = str(agent["id"])
    version_id = str(agent["latest_version"]["id"])  # type: ignore[index]

    response = client.post(
        "/api/v1/runs",
        json={"agent_id": agent_id, "input": "Check the home lab status."},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["agent_version_id"] == version_id
    assert run["status"] == "queued"

    events = client.get(f"/api/v1/runs/{run['id']}/events")
    assert events.status_code == 200
    assert events.json()[0]["type"] == "run.created"
    assert events.json()[0]["sequence"] == 1
    assert events.json()[0]["payload"]["request_id"] == response.headers["X-Request-ID"]
    assert events.json()[0]["run_id"] == run["id"]


def test_missing_agent_returns_structured_404(client: TestClient) -> None:
    response = client.get("/api/v1/agents/missing")

    assert response.status_code == 404
    assert response.json()["resource"] == "agent"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_validation_errors_include_request_id_header(client: TestClient) -> None:
    response = client.post("/api/v1/agents", json={"name": ""})

    assert response.status_code == 422
    assert response.headers["X-Request-ID"]


def test_run_steps_are_persisted_and_returned_in_order(client: TestClient) -> None:
    agent = create_agent(client)
    run_response = client.post(
        "/api/v1/runs",
        json={"agent_id": agent["id"], "input": "Inspect the runtime."},
    )
    run_id = run_response.json()["id"]

    with next(client.app.state.database.session()) as session:
        repository = RunRepository(session)
        repository.create_step(
            run_id=run_id,
            kind=StepKind.PLANNER,
            input={"messages": 1},
        )
        repository.create_step(
            run_id=run_id,
            kind=StepKind.MODEL,
            input={"model": "deterministic"},
            status=StepStatus.RUNNING,
            attempt=2,
        )
        session.commit()

    response = client.get(f"/api/v1/runs/{run_id}/steps")

    assert response.status_code == 200
    assert [step["sequence"] for step in response.json()] == [1, 2]
    assert response.json()[0]["kind"] == "planner"
    assert response.json()[1]["status"] == "running"
    assert response.json()[1]["attempt"] == 2


def test_steps_for_missing_run_return_structured_404(client: TestClient) -> None:
    response = client.get("/api/v1/runs/missing/steps")

    assert response.status_code == 404
    assert response.json()["resource"] == "run"
