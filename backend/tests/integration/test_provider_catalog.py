from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forge.api.app import create_app
from forge.config import Settings


def test_catalog_lists_offline_defaults_without_credentials(client: TestClient) -> None:
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    providers = {item["id"]: item for item in response.json()}
    assert providers["fake"] == {
        "id": "fake", "configured": True, "default_model": "deterministic"
    }
    assert providers["gemini"] == {
        "id": "gemini", "configured": False, "default_model": "gemini-3.5-flash-lite"
    }


@pytest.mark.parametrize("source", ["settings", "environment"])
def test_catalog_exposes_only_configuration_boolean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        GEMINI_API_KEY="synthetic-catalog-secret" if source == "settings" else None,
    )
    if source == "environment":
        monkeypatch.setenv("GEMINI_API_KEY", "synthetic-catalog-secret")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        assert response.json()[1]["configured"] is True
        assert "synthetic-catalog-secret" not in response.text
        assert all(
            set(item) == {"id", "configured", "default_model"}
            for item in response.json()
        )
