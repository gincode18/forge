import asyncio

import pytest

from forge.runtime.fake import FakeProvider
from forge.runtime.ports import (
    ModelDelta,
    ModelMessage,
    ModelResult,
    ModelUsage,
    ProviderError,
)


def test_fake_stream_accounts_for_history_and_enforces_output_budget():
    async def exercise(max_tokens):
        return [item async for item in FakeProvider({"Hi": "Hello friend"}).stream(
            instructions="Be brief", input="Hi", max_output_tokens=max_tokens,
            messages=(ModelMessage("assistant", "previous answer"),),
        )]
    events = asyncio.run(exercise(2))
    assert events[-1].usage == ModelUsage(5, 2, 7)


def test_fake_stream_enforces_output_budget():
    async def exercise():
        return [item async for item in FakeProvider({"Hi": "Hello friend"}).stream(
            instructions="Be brief", input="Hi", max_output_tokens=1,
        )]
    with pytest.raises(ProviderError) as caught:
        asyncio.run(exercise())
    assert caught.value.code == "incomplete_response"



def test_fake_stream_is_repeatable_and_normalized():
    provider = FakeProvider({"Hi": "Hello friend"})
    assert hasattr(provider, "stream"), "fake streaming is missing"

    async def consume():
        return [item async for item in provider.stream(
            instructions="Be brief", input="Hi", max_output_tokens=10,
        )]

    first = asyncio.run(consume())
    assert first == asyncio.run(consume())
    assert first[:-1] == [ModelDelta("Hello "), ModelDelta("friend")]
    assert first[-1] == asyncio.run(provider.complete(instructions="Be brief", input="Hi"))
    assert isinstance(first[-1], ModelResult)
    assert first[-1].usage == ModelUsage(3, 2, 5)
    assert first[-1].latency_ms == 0.0
