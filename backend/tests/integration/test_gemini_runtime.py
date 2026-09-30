"""Offline Phase 3 contract and first real-provider runtime slice."""
import time
from types import SimpleNamespace

import pytest
from google.genai import errors, types

from forge.runtime.fake import FakeProvider
from forge.runtime.gemini import GeminiProvider
from forge.runtime.ports import ModelResult, ProviderError


def test_fake_provider_uses_normalized_contract():
    import asyncio

    result = asyncio.run(FakeProvider().complete(instructions="Be brief", input="Hi"))
    assert isinstance(result, ModelResult)
    assert result.text == "Fake response to: Hi"
    assert result.provider == "fake"


def test_dotenv_key_is_secret_and_reaches_supervisor(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from forge.api.app import create_app
    from forge.config import Settings

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text("GEMINI_API_KEY=dotenv-test-key\n")
    settings = Settings(_env_file=dotenv, data_dir=tmp_path / "data")
    assert "dotenv-test-key" not in repr(settings)
    assert settings.gemini_api_key.get_secret_value() == "dotenv-test-key"
    received = []

    class OfflineGemini:
        def __init__(self, model, *, api_key):
            received.append(api_key)

        async def complete(self, *, instructions, input):
            return ModelResult(text="Hello", provider="gemini", model="test-model")

    monkeypatch.setattr("forge.runtime.supervisor.GeminiProvider", OfflineGemini)
    with TestClient(create_app(settings)) as api:
        agent = api.post("/api/v1/agents", json={
            "name": "dotenv", "instructions": "Hi", "provider": "gemini",
            "model": "test-model",
        }).json()
        run_id = api.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
        assert api.post(f"/api/v1/runs/{run_id}/start").status_code == 202
        assert received == ["dotenv-test-key"]


def test_environment_key_overrides_dotenv(tmp_path, monkeypatch):
    from forge.config import Settings

    dotenv = tmp_path / ".env"
    dotenv.write_text("GEMINI_API_KEY=dotenv-test-key\n")
    monkeypatch.setenv("GEMINI_API_KEY", "environment-test-key")
    settings = Settings(_env_file=dotenv)
    assert settings.gemini_api_key.get_secret_value() == "environment-test-key"


def test_gemini_adapter_normalizes_sdk_response_without_network():
    import asyncio

    class Models:
        async def generate_content(self, *, model, contents, config):
            assert model == "gemini-3.5-flash-lite"
            assert contents == "Hi"
            assert isinstance(config, types.GenerateContentConfig)
            assert config.system_instruction == "Be brief"
            return SimpleNamespace(
                text="Hello from Gemini",
                candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
                usage_metadata=SimpleNamespace(
                    prompt_token_count=4, candidates_token_count=6, total_token_count=10
                ),
                response_id="response-123",
            )

    client = SimpleNamespace(aio=SimpleNamespace(models=Models()))
    result = asyncio.run(GeminiProvider("gemini-3.5-flash-lite", client=client).complete(
        instructions="Be brief", input="Hi"
    ))
    assert result.text == "Hello from Gemini"
    assert result.finish_reason == "STOP"
    assert result.usage.input_tokens == 4
    assert result.usage.output_tokens == 6
    assert result.usage.total_tokens == 10
    assert result.request_id == "response-123"
    assert result.latency_ms >= 0


def test_gemini_start_requires_key_and_keeps_run_queued(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    agent = client.post("/api/v1/agents", json={
        "name": "Gemini", "instructions": "Be brief", "provider": "gemini",
        "model": "gemini-3.5-flash-lite"
    }).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    response = client.post(f"/api/v1/runs/{run_id}/start")
    assert response.status_code == 422
    assert "GEMINI_API_KEY" in response.json()["detail"]
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "queued"


def test_gemini_sdk_error_never_exposes_sensitive_response():
    import asyncio

    class Models:
        async def generate_content(self, **kwargs):
            raise errors.ClientError(401, {"message": "private-key-in-error"})

    client = SimpleNamespace(aio=SimpleNamespace(models=Models()))
    with pytest.raises(ProviderError, match="Gemini request failed") as caught:
        asyncio.run(GeminiProvider("gemini-3.5-flash-lite", client=client).complete(
            instructions="Be brief", input="Hi"
        ))
    assert caught.value.code == "request_failed"
    assert "private-key-in-error" not in str(caught.value)


def test_gemini_run_persists_normalized_usage_and_trace(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    class OfflineGemini:
        def __init__(self, model, *, api_key):
            assert model == "gemini-3.5-flash-lite"
            assert api_key == "test-key-not-real"

        async def complete(self, *, instructions, input):
            assert instructions == "Be brief"
            assert input == "Hi"
            from forge.runtime.ports import ModelUsage
            return ModelResult(
                text="Hello from Gemini", provider="gemini", model="gemini-3.5-flash-lite",
                finish_reason="STOP", usage=ModelUsage(4, 6, 10),
                request_id="response-123", latency_ms=12.3,
            )
    monkeypatch.setattr("forge.runtime.supervisor.GeminiProvider", OfflineGemini)
    agent = client.post("/api/v1/agents", json={
        "name": "Gemini", "instructions": "Be brief", "provider": "gemini",
        "model": "gemini-3.5-flash-lite"
    }).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    assert client.post(f"/api/v1/runs/{run_id}/start").status_code == 202
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        run = client.get(f"/api/v1/runs/{run_id}").json()
        if run["status"] == "completed":
            break
        time.sleep(0.01)
    assert run["status"] == "completed"
    steps = client.get(f"/api/v1/runs/{run_id}/steps").json()
    assert steps[0]["output"]["usage"] == {"input_tokens": 4, "output_tokens": 6, "total_tokens": 10}
    assert steps[0]["output"]["finish_reason"] == "STOP"
    assert steps[0]["output"]["latency_ms"] == 12.3
    assert client.get(f"/api/v1/runs/{run_id}/events").json()[-1]["payload"]["result"] == "Hello from Gemini"


@pytest.mark.parametrize("stage", ["construction", "transport", "normalization", "async_cleanup", "sync_cleanup"])
def test_gemini_failure_never_persists_or_logs_credentials(client, monkeypatch, caplog, stage):
    import json
    import logging
    import traceback
    from unittest.mock import AsyncMock, Mock

    import httpx

    from forge.runtime.supervisor import logger

    # Migration logging configuration may disable existing loggers. Capture the
    # actual supervisor traceback, not a vacuous assertion over an empty log.
    monkeypatch.setattr(logger, "disabled", False)
    monkeypatch.setattr(logger, "propagate", True)
    caplog.set_level(logging.ERROR, logger=logger.name)
    key = "SYNTHETIC-gemini-integration-key-never-real"
    monkeypatch.setenv("GEMINI_API_KEY", key)
    failure = httpx.LocalProtocolError(f"invalid API-key header: {key}")
    response = SimpleNamespace(text="Hello", usage_metadata=None, candidates=[], response_id="offline")
    sdk = SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=AsyncMock(return_value=response)),
            aclose=AsyncMock(),
        ),
        close=Mock(),
    )
    factory = Mock(return_value=sdk)
    if stage == "construction":
        factory.side_effect = failure
    elif stage == "transport":
        sdk.aio.models.generate_content.side_effect = failure
    elif stage == "normalization":
        class BrokenResponse:
            @property
            def usage_metadata(self):
                raise failure
            text = "Hello"
        sdk.aio.models.generate_content.return_value = BrokenResponse()
    elif stage == "async_cleanup":
        sdk.aio.aclose.side_effect = failure
    else:
        sdk.close.side_effect = failure
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", factory)
    agent = client.post("/api/v1/agents", json={
        "name": "Offline security", "instructions": "Hi", "provider": "gemini", "model": "offline",
    }).json()
    run_id = client.post("/api/v1/runs", json={"agent_id": agent["id"], "input": "Hi"}).json()["id"]
    assert client.post(f"/api/v1/runs/{run_id}/start").status_code == 202
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        run = client.get(f"/api/v1/runs/{run_id}").json()
        if run["status"] in {"failed", "completed"}:
            break
        time.sleep(0.01)
    assert run["status"] == "failed"
    steps = client.get(f"/api/v1/runs/{run_id}/steps").json()
    events = client.get(f"/api/v1/runs/{run_id}/events").json()
    assert steps[0]["error"] == {
        "type": "ProviderError",
        "message": "Gemini cleanup failed" if stage.endswith("cleanup") else "Gemini request failed",
    }
    assert any(event["type"] == "model.failed" for event in events)
    assert key not in json.dumps({"run": run, "steps": steps, "events": events})
    assert key not in caplog.text
    assert any(
        record.name == logger.name and record.exc_info
        and record.getMessage() == f"Run failed: {run_id}"
        for record in caplog.records
    )
    for record in caplog.records:
        assert key not in record.getMessage()
        if record.exc_info:
            assert key not in "".join(traceback.format_exception(*record.exc_info))
