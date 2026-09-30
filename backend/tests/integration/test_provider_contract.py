"""Both providers meet the same offline, provider-neutral streaming contract."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.genai import types

from forge.runtime.fake import FakeProvider
from forge.runtime.gemini import GeminiProvider
from forge.runtime.ports import ModelDelta, ModelResult


def offline_gemini(*, streaming):
    response = types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(role="model", parts=[types.Part(text="Hello")]),
            finish_reason=types.FinishReason.STOP,
        )],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=3, candidates_token_count=1, total_token_count=4,
        ),
    )

    async def stream(**kwargs):
        async def chunks():
            yield response
        return chunks()

    models = SimpleNamespace(generate_content=AsyncMock(return_value=response))
    if streaming:
        models.generate_content_stream = stream
    return GeminiProvider("offline", client=SimpleNamespace(aio=SimpleNamespace(models=models)))


@pytest.mark.parametrize("provider", ["fake", "gemini", "gemini-legacy-double"])
def test_provider_stream_contract_is_offline_and_has_one_terminal_result(provider):
    adapter = FakeProvider({"Hi": "Hello"}) if provider == "fake" else offline_gemini(streaming=provider == "gemini")

    async def exercise():
        return [item async for item in adapter.stream(instructions="Be brief", input="Hi")]

    events = asyncio.run(exercise())
    assert events and isinstance(events[-1], ModelResult)
    assert sum(isinstance(item, ModelResult) for item in events) == 1
    assert all(isinstance(item, ModelDelta) for item in events[:-1])
    assert "".join(item.text for item in events[:-1]) == events[-1].text == "Hello"
    assert events[-1].usage.total_tokens == 4
    assert events[-1].usage.input_tokens == 3
    assert events[-1].usage.output_tokens == 1
    assert events[-1].latency_ms >= 0
    assert events[-1].finish_reason == "STOP"
