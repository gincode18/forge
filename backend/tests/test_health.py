from uuid import UUID

from fastapi.testclient import TestClient

from forge.api.app import create_app
from forge.config import Settings


def test_health_endpoint_returns_service_and_database_metadata(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "forge-api",
        "version": "0.1.0",
        "database": "ready",
    }


def test_requests_receive_distinct_server_generated_ids(client: TestClient) -> None:
    first = client.get("/api/v1/health", headers={"X-Request-ID": "client-value"})
    second = client.get("/api/v1/health")

    assert first.headers["X-Request-ID"] != "client-value"
    assert UUID(first.headers["X-Request-ID"])
    assert UUID(second.headers["X-Request-ID"])
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_request_id_is_exposed_to_dashboard_origin(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health", headers={"Origin": "http://localhost:3000"}
    )

    assert response.headers["X-Request-ID"]
    assert "X-Request-ID" in response.headers["Access-Control-Expose-Headers"]


def test_unhandled_errors_keep_request_id_without_leaking_details(tmp_path) -> None:
    app = create_app(Settings(data_dir=tmp_path))

    def fail() -> None:
        raise RuntimeError("sensitive internal detail")

    app.add_api_route("/fail", fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/fail")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error",
        "request_id": response.headers["X-Request-ID"],
    }
