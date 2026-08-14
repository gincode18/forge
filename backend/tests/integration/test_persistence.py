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
