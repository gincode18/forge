"""Gemini security boundaries, using only synthetic credentials and offline SDK doubles."""
import asyncio
import traceback
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from forge.runtime.gemini import GeminiProvider
from forge.runtime.ports import ProviderError

SYNTHETIC_KEY = "SYNTHETIC-gemini-key-never-real"


def response():
    return SimpleNamespace(
        text="Hello", usage_metadata=None, candidates=[], response_id="offline"
    )


def offline_client():
    return SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=AsyncMock(return_value=response())),
            aclose=AsyncMock(),
        ),
        close=Mock(),
    )


@pytest.mark.parametrize("stage", ["construction", "transport", "normalization"])
def test_ordinary_sdk_failures_are_safe(stage, monkeypatch):
    client = offline_client()
    failure = httpx.LocalProtocolError(f"invalid header: {SYNTHETIC_KEY}")
    factory = Mock(return_value=client)
    if stage == "construction":
        factory.side_effect = failure
    elif stage == "transport":
        client.aio.models.generate_content.side_effect = failure
    else:
        class BrokenResponse:
            @property
            def text(self):
                raise failure
        client.aio.models.generate_content.return_value = BrokenResponse()
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", factory)
    with pytest.raises(ProviderError) as caught:
        asyncio.run(GeminiProvider("offline", api_key=SYNTHETIC_KEY).complete(
            instructions="Hi", input="Hi"
        ))
    assert caught.value.code == "request_failed"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert SYNTHETIC_KEY not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("outcome", ["success", "request_failure", "empty_response", "cancelled"])
@pytest.mark.parametrize("cleanup", ["ok", "async", "sync", "both"])
def test_owned_cleanup_preserves_primary_outcome(outcome, cleanup, monkeypatch):
    client = offline_client()
    if outcome == "request_failure":
        client.aio.models.generate_content.side_effect = RuntimeError(SYNTHETIC_KEY)
    elif outcome == "empty_response":
        client.aio.models.generate_content.return_value.text = None
    elif outcome == "cancelled":
        client.aio.models.generate_content.side_effect = asyncio.CancelledError()
    if cleanup in {"async", "both"}:
        client.aio.aclose.side_effect = RuntimeError(SYNTHETIC_KEY)
    if cleanup in {"sync", "both"}:
        client.close.side_effect = RuntimeError(SYNTHETIC_KEY)
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", Mock(return_value=client))
    operation = GeminiProvider("offline", api_key=SYNTHETIC_KEY).complete(
        instructions="Hi", input="Hi"
    )
    if outcome == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(operation)
    elif outcome != "success" or cleanup != "ok":
        with pytest.raises(ProviderError) as caught:
            asyncio.run(operation)
        expected = {
            "request_failure": "request_failed", "empty_response": "empty_response",
            "success": "cleanup_failed",
        }[outcome]
        assert caught.value.code == expected
        assert caught.value.__cause__ is None
        assert SYNTHETIC_KEY not in "".join(traceback.format_exception(caught.value))
    else:
        assert asyncio.run(operation).text == "Hello"
    client.aio.aclose.assert_awaited_once_with()
    client.close.assert_called_once_with()


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled"])
def test_injected_clients_are_never_closed(outcome):
    client = offline_client()
    if outcome == "failure":
        client.aio.models.generate_content.side_effect = RuntimeError(SYNTHETIC_KEY)
    elif outcome == "cancelled":
        client.aio.models.generate_content.side_effect = asyncio.CancelledError()
    operation = GeminiProvider("offline", client=client).complete(instructions="Hi", input="Hi")
    if outcome == "success":
        assert asyncio.run(operation).text == "Hello"
    else:
        exception = ProviderError if outcome == "failure" else asyncio.CancelledError
        with pytest.raises(exception):
            asyncio.run(operation)
    client.aio.aclose.assert_not_awaited()
    client.close.assert_not_called()


@pytest.mark.parametrize("cancel", ["task", "timeout"])
def test_real_cancellation_and_deadline_survive_cleanup_failure(cancel, monkeypatch):
    client = offline_client()
    client.aio.aclose.side_effect = RuntimeError(SYNTHETIC_KEY)
    client.close.side_effect = RuntimeError(SYNTHETIC_KEY)
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", Mock(return_value=client))

    async def exercise():
        entered = asyncio.Event()

        async def blocked(**kwargs):
            entered.set()
            await asyncio.Event().wait()

        client.aio.models.generate_content.side_effect = blocked
        provider = GeminiProvider("offline", api_key=SYNTHETIC_KEY)
        if cancel == "timeout":
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.01):
                    await provider.complete(instructions="Hi", input="Hi")
        else:
            task = asyncio.create_task(provider.complete(instructions="Hi", input="Hi"))
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    asyncio.run(exercise())
    client.aio.aclose.assert_awaited_once_with()
    client.close.assert_called_once_with()
