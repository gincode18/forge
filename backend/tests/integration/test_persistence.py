from pathlib import Path

from fastapi.testclient import TestClient

from forge.api.app import create_app
from forge.config import Settings


def test_agents_survive_application_restart(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)

    with TestClient(create_app(settings)) as first_client:
        created = first_client.post(
            "/api/v1/agents",
            json={"name": "Persistent Agent", "instructions": "Remember me."},
        )
        assert created.status_code == 201
        agent_id = created.json()["id"]

    with TestClient(create_app(settings)) as restarted_client:
        response = restarted_client.get(f"/api/v1/agents/{agent_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Persistent Agent"


def test_run_creation_request_id_survives_restart(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)

    with TestClient(create_app(settings)) as first_client:
        agent = first_client.post(
            "/api/v1/agents",
            json={"name": "Traceable Agent", "instructions": "Explain actions."},
        ).json()
        created = first_client.post(
            "/api/v1/runs",
            json={"agent_id": agent["id"], "input": "Inspect the trace."},
        )
        assert created.status_code == 201
        run_id = created.json()["id"]
        creation_request_id = created.headers["X-Request-ID"]

    with TestClient(create_app(settings)) as restarted_client:
        run = restarted_client.get(f"/api/v1/runs/{run_id}")
        events = restarted_client.get(f"/api/v1/runs/{run_id}/events")

    assert run.status_code == 200
    assert events.json()[0]["run_id"] == run_id
    assert events.json()[0]["payload"]["request_id"] == creation_request_id
