import pytest
from fastapi.testclient import TestClient


def test_limits_are_persisted_per_immutable_version(client: TestClient) -> None:
    limits = {
        "timeout_seconds": 4.5,
        "max_tokens": 100,
        "max_cost_usd": 0.25,
        "max_retries": 3,
        "max_output_tokens": 50,
        "input_cost_per_million": 0.5,
        "output_cost_per_million": 1.5,
        "max_steps": 7,
    }
    agent = client.post(
        "/api/v1/agents", json=dict(name="Limits", instructions="Test", **limits)
    ).json()
    original = agent["latest_version"]
    pinned_run = client.post(
        "/api/v1/runs", json={"agent_id": agent["id"], "input": "Inspect"}
    ).json()
    assert pinned_run["agent_version_id"] == original["id"]
    for key, value in limits.items():
        assert original[key] == value
    response = client.post(
        f"/api/v1/agents/{agent['id']}/versions",
        json={"instructions": "New", "timeout_seconds": 12},
    )
    assert response.status_code == 201
    assert response.json()["timeout_seconds"] == 12
    assert response.json()["max_tokens"] is None
    versions = client.get(f"/api/v1/agents/{agent['id']}").json()["versions"]
    for key in ("id", "instructions", *limits):
        assert versions[0][key] == original[key]
    assert versions[1]["max_retries"] == 2
    assert (
        client.get(f"/api/v1/runs/{pinned_run['id']}").json()["agent_version_id"]
        == original["id"]
    )
    invalid = client.post(
        f"/api/v1/agents/{agent['id']}/versions",
        json={"instructions": "Invalid", "max_cost_usd": 1},
    )
    assert invalid.status_code == 422
    assert len(client.get(f"/api/v1/agents/{agent['id']}").json()["versions"]) == 2


@pytest.mark.parametrize(
    "limits",
    [
        {"timeout_seconds": 0},
        {"timeout_seconds": "Infinity"},
        {"timeout_seconds": "NaN"},
        {"max_tokens": 0},
        {"max_output_tokens": 0},
        {"max_retries": -1},
        {"max_retries": 6},
        {"max_retries": 1.5},
        {"max_cost_usd": 0},
        {"max_cost_usd": 1},
        {"input_cost_per_million": -1},
        {"output_cost_per_million": "Infinity"},
    ],
)
def test_invalid_limits_are_rejected(client: TestClient, limits: dict) -> None:
    response = client.post(
        "/api/v1/agents", json=dict(name="Invalid", instructions="Test", **limits)
    )
    assert response.status_code == 422
    assert client.get("/api/v1/agents").json() == []
