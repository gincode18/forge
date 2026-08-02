from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint_returns_service_metadata() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "forge-api",
        "version": "0.1.0",
    }
