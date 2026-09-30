from fastapi.testclient import TestClient

from forge.api.app import create_app
from forge.config import Settings


def test_empty_settings_key_is_not_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path, GEMINI_API_KEY="")
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/providers").json()[1]["configured"] is False
