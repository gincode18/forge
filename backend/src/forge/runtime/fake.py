"""Scripted provider and finish-only planner for no-key runtime tests."""
import re
from collections.abc import AsyncIterator
from dataclasses import replace

from forge.runtime.ports import (
    FinalAction,
    ModelDelta,
    ModelMessage,
    ModelResult,
    ModelUsage,
    ProviderError,
)


class FakeProvider:
    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}

    async def complete(self, *, instructions: str, input: str) -> ModelResult:
        text = self.responses.get(input, f"Fake response to: {input}")
        input_tokens = len(instructions.split()) + len(input.split())
        output_tokens = len(text.split())
        return ModelResult(
            text=text,
            provider="fake", model="deterministic", finish_reason="STOP",
            usage=ModelUsage(input_tokens, output_tokens, input_tokens + output_tokens),
            latency_ms=0.0,
        )

    async def stream(
        self, *, instructions: str, input: str,
        messages: tuple[ModelMessage, ...] = (), max_output_tokens: int = 2048,
    ) -> AsyncIterator[ModelDelta | ModelResult]:
        result = await self.complete(instructions=instructions, input=input)
        history_tokens = sum(len(message.text.split()) for message in messages)
        usage = result.usage
        if history_tokens:
            usage = ModelUsage(
                usage.input_tokens + history_tokens, usage.output_tokens,
                usage.total_tokens + history_tokens,
            )
            result = replace(result, usage=usage)
        if usage.output_tokens > max_output_tokens:
            raise ProviderError("fake", "incomplete_response", "Fake response exceeded output budget")
        for text in re.findall(r"\S+\s*|\s+", result.text):
            yield ModelDelta(text)
        yield result


class FinalPlanner:
    def decide(self, response: str) -> FinalAction:
        return FinalAction(text=response)
