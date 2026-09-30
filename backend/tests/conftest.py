from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forge.api.app import create_app
from forge.config import Settings


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Default API tests must never read developer credentials or call a real model.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings)) as test_client:
        yield test_client
