"""Offline doubles implement the documented awaited SDK async iterator."""
import asyncio
import traceback
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from google.genai import errors, types

from forge.runtime.gemini import GeminiProvider
from forge.runtime.ports import (
    ModelDelta,
    ModelMessage,
    ModelResult,
    ModelUsage,
    ProviderError,
)


@pytest.mark.parametrize("status,retryable", [(401, False), (429, True), (500, True), (503, True)])
@pytest.mark.parametrize("mode", ["stream", "complete"])
def test_transient_failures_are_retryable_and_credential_safe(status, retryable, mode):
    key = "SYNTHETIC-stream-key"
    error = errors.APIError(status, {"message": key})
    client = client_for([chunk("partial"), error])
    client.aio.models.generate_content = AsyncMock(side_effect=error)
    provider = GeminiProvider("offline", client=client)
    with pytest.raises(ProviderError) as caught:
        asyncio.run(collect(provider) if mode == "stream" else provider.complete(instructions="Hi", input="Hi"))
    assert caught.value.retryable is retryable
    assert caught.value.code == "request_failed"
    assert caught.value.__cause__ is None
    assert key not in "".join(traceback.format_exception(caught.value))


def test_stream_normalizes_tool_calls_and_allowlisted_metadata():
    call = types.FunctionCall(name="lookup", args={"q": "hello"}, id="call-1")
    client = client_for([chunk(
        finish=types.FinishReason.STOP, parts=[types.Part(function_call=call)],
        model_version="offline-version", sdk_headers={"authorization": "SYNTHETIC-secret"},
    )])
    result = asyncio.run(collect(GeminiProvider("offline", client=client)))[-1]
    from forge.runtime.ports import ToolCall
    assert result.tool_calls == (ToolCall("lookup", {"q": "hello"}, "call-1"),)
    assert result.text == ""
    assert result.metadata == {"model_version": "offline-version"}
    assert "SYNTHETIC-secret" not in repr(result)


@pytest.mark.parametrize("finish,code", [
    ("SAFETY", "blocked_response"), ("RECITATION", "blocked_response"),
    ("BLOCKLIST", "blocked_response"), ("PROHIBITED_CONTENT", "blocked_response"),
    ("SPII", "blocked_response"), ("MAX_TOKENS", "incomplete_response"),
    ("MALFORMED_FUNCTION_CALL", "incomplete_response"),
])
@pytest.mark.parametrize("mode", ["stream", "complete"])
def test_unsafe_or_truncated_response_never_becomes_success(finish, code, mode):
    response = chunk("partial", finish=types.FinishReason(finish))
    client = client_for([response])
    client.aio.models.generate_content = AsyncMock(return_value=response)
    provider = GeminiProvider("offline", client=client)
    with pytest.raises(ProviderError) as caught:
        asyncio.run(collect(provider) if mode == "stream" else provider.complete(instructions="Hi", input="Hi"))
    assert caught.value.code == code
    assert not caught.value.retryable


def test_empty_stream_and_prompt_block_fail_clearly():
    for chunks, code in [([], "empty_response"), ([chunk(prompt_feedback=SimpleNamespace(block_reason=types.BlockedReason.SAFETY))], "blocked_response")]:
        with pytest.raises(ProviderError) as caught:
            asyncio.run(collect(GeminiProvider("offline", client=client_for(chunks))))
        assert caught.value.code == code


def test_stream_source_is_closed_on_early_consumer_exit(monkeypatch):
    class Source:
        def __aiter__(self):
            return self

        async def __anext__(self):
            return chunk("one delta")

        aclose = AsyncMock()

    source = Source()
    client = client_for([])
    client.aio.models.generate_content_stream.return_value = source
    client.aio.models.generate_content_stream.side_effect = None
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", Mock(return_value=client))

    async def exercise():
        stream = GeminiProvider("offline", api_key="SYNTHETIC-only").stream(instructions="Hi", input="Hi")
        assert await anext(stream) == ModelDelta("one delta")
        await stream.aclose()

    asyncio.run(exercise())
    source.aclose.assert_awaited_once()
    client.aio.aclose.assert_awaited_once()
    client.close.assert_called_once()


@pytest.mark.parametrize("mode", ["stream", "complete"])
def test_complete_and_stream_keep_thought_usage_and_tool_calls(mode):
    response = chunk("answer", finish=types.FinishReason.STOP, usage=types.GenerateContentResponseUsageMetadata(
        prompt_token_count=4, candidates_token_count=6, thoughts_token_count=3, total_token_count=13,
    ), parts=[types.Part(function_call=types.FunctionCall(name="lookup", args={"q": "x"}))], model_version="offline")
    client = client_for([response])
    client.aio.models.generate_content = AsyncMock(return_value=response)
    provider = GeminiProvider("offline", client=client)
    result = asyncio.run(collect(provider))[-1] if mode == "stream" else asyncio.run(provider.complete(instructions="Hi", input="Hi"))
    assert result.usage == ModelUsage(4, 9, 13)
    assert result.tool_calls[0].name == "lookup"
    assert result.metadata == {"model_version": "offline"}


@pytest.mark.parametrize("mode", ["stream", "complete"])
def test_partial_usage_is_unknown_not_fabricated_zero(mode):
    response = chunk("answer", finish=types.FinishReason.STOP, usage=types.GenerateContentResponseUsageMetadata())
    client = client_for([response])
    client.aio.models.generate_content = AsyncMock(return_value=response)
    provider = GeminiProvider("offline", client=client)
    result = asyncio.run(collect(provider))[-1] if mode == "stream" else asyncio.run(provider.complete(instructions="Hi", input="Hi"))
    assert result.usage is None


def test_native_stream_without_terminal_finish_does_not_complete():
    with pytest.raises(ProviderError) as caught:
        asyncio.run(collect(GeminiProvider("offline", client=client_for([chunk("partial")]))))
    assert caught.value.code == "incomplete_response"


@pytest.mark.parametrize("cleanup", ["source", "lookup", "async", "sync"])
@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled"])
def test_stream_cleanup_is_safe_and_preserves_primary_outcome(cleanup, outcome, monkeypatch):
    secret = "SYNTHETIC-stream-cleanup-secret"

    class Source:
        def __aiter__(self):
            return self

        async def __anext__(self):
            if outcome == "failure":
                raise RuntimeError(secret)
            if outcome == "cancelled":
                raise asyncio.CancelledError()
            if hasattr(self, "done"):
                raise StopAsyncIteration
            self.done = True
            return chunk("answer", finish=types.FinishReason.STOP)

        @property
        def aclose(self):
            if cleanup == "lookup":
                raise RuntimeError(secret)
            return AsyncMock(side_effect=RuntimeError(secret) if cleanup == "source" else None)

    client = client_for([])
    client.aio.models.generate_content_stream.side_effect = None
    client.aio.models.generate_content_stream.return_value = Source()
    if cleanup == "async":
        client.aio.aclose.side_effect = RuntimeError(secret)
    if cleanup == "sync":
        client.close.side_effect = RuntimeError(secret)
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", Mock(return_value=client))
    provider = GeminiProvider("offline", api_key=secret)
    expected = asyncio.CancelledError if outcome == "cancelled" else ProviderError
    with pytest.raises(expected) as caught:
        asyncio.run(collect(provider))
    if outcome != "cancelled":
        assert caught.value.code == ("cleanup_failed" if outcome == "success" else "request_failed")
        assert secret not in "".join(traceback.format_exception(caught.value))
    client.aio.aclose.assert_awaited_once()
    client.close.assert_called_once()


def test_completion_can_return_tool_call_without_text():
    response = chunk(finish=types.FinishReason.STOP, parts=[types.Part(function_call=types.FunctionCall(name="lookup", args={}))])
    client = client_for([])
    client.aio.models.generate_content = AsyncMock(return_value=response)
    result = asyncio.run(GeminiProvider("offline", client=client).complete(instructions="Hi", input="Hi"))
    assert result.text == ""
    assert result.tool_calls[0].name == "lookup"


@pytest.mark.parametrize("cancel", ["task", "timeout"])
def test_stream_cancellation_and_timeout_survive_cleanup_failure(cancel, monkeypatch):
    client = client_for([])
    client.aio.aclose.side_effect = RuntimeError("SYNTHETIC-cleanup-secret")
    client.close.side_effect = RuntimeError("SYNTHETIC-cleanup-secret")
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", Mock(return_value=client))

    async def exercise():
        entered = asyncio.Event()

        async def chunks():
            entered.set()
            await asyncio.Event().wait()
            yield chunk("never")

        client.aio.models.generate_content_stream.side_effect = lambda **kw: chunks()
        provider = GeminiProvider("offline", api_key="SYNTHETIC-only")
        if cancel == "timeout":
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.01):
                    await collect(provider)
        else:
            task = asyncio.create_task(collect(provider))
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    asyncio.run(exercise())
    client.aio.aclose.assert_awaited_once()
    client.close.assert_called_once()


@pytest.mark.parametrize("stage", ["construction", "initialization", "consumption", "normalization"])
def test_stream_sdk_failure_never_leaks_credential(stage, monkeypatch):
    secret = "SYNTHETIC-stream-security-secret"
    failure = RuntimeError(secret)
    client = client_for([chunk("answer", finish=types.FinishReason.STOP)])
    factory = Mock(return_value=client)
    if stage == "construction":
        factory.side_effect = failure
    elif stage == "initialization":
        client.aio.models.generate_content_stream.side_effect = failure
    elif stage == "consumption":
        client = client_for([chunk("partial"), failure])
        factory.return_value = client
    else:
        class BrokenResponse:
            candidates = ()
            @property
            def text(self):
                raise failure
        client = client_for([BrokenResponse()])
        factory.return_value = client
    monkeypatch.setattr("forge.runtime.gemini.genai.Client", factory)
    with pytest.raises(ProviderError) as caught:
        asyncio.run(collect(GeminiProvider("offline", api_key=secret)))
    assert caught.value.code == "request_failed"
    assert secret not in "".join(traceback.format_exception(caught.value))


def chunk(text=None, *, finish=None, usage=None, parts=None, **extra):
    return SimpleNamespace(
        text=text, candidates=[SimpleNamespace(
            finish_reason=finish, content=SimpleNamespace(parts=parts or []),
        )], usage_metadata=usage, response_id="offline-id", **extra,
    )


def client_for(chunks):
    async def iterator():
        for item in chunks:
            if isinstance(item, BaseException):
                raise item
            yield item
    return SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(
            generate_content_stream=AsyncMock(side_effect=lambda **kw: iterator()),
        ), aclose=AsyncMock()), close=Mock(),
    )


async def collect(provider, **kwargs):
    return [item async for item in provider.stream(instructions="Be brief", input="Hi", **kwargs)]


def test_stream_yields_deltas_then_one_final_with_cumulative_usage():
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=4, candidates_token_count=6, thoughts_token_count=3,
        total_token_count=13,
    )
    client = client_for([
        chunk("Hello "), chunk("world", finish=types.FinishReason.STOP, usage=usage),
    ])
    provider = GeminiProvider("offline-model", client=client)
    assert hasattr(provider, "stream"), "Gemini streaming is missing"
    events = asyncio.run(collect(provider, messages=(ModelMessage("assistant", "previous"),), max_output_tokens=12))
    assert events[:-1] == [ModelDelta("Hello "), ModelDelta("world")]
    result = events[-1]
    assert isinstance(result, ModelResult)
    assert result.text == "Hello world"
    assert result.usage == ModelUsage(4, 9, 13)
    assert result.finish_reason == "STOP"
    assert result.request_id == "offline-id" and result.latency_ms >= 0
    kwargs = client.aio.models.generate_content_stream.call_args.kwargs
    assert kwargs["model"] == "offline-model"
    assert kwargs["config"].system_instruction == "Be brief"
    assert kwargs["config"].max_output_tokens == 12
    assert [(item.role, item.parts[0].text) for item in kwargs["contents"]] == [("user", "Hi"), ("model", "previous")]
    client.aio.aclose.assert_not_awaited()
    client.close.assert_not_called()
