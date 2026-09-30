"""Provider-neutral results for no-tool execution."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FinalAction:
    text: str


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class ModelResult:
    text: str
    provider: str
    model: str
    finish_reason: str | None = None
    usage: ModelUsage | None = None
    request_id: str | None = None
    latency_ms: float | None = None


class ProviderError(Exception):
    def __init__(self, provider: str, code: str, message: str) -> None:
        self.provider = provider
        self.code = code
        super().__init__(message)


class ModelProvider(Protocol):
    async def complete(self, *, instructions: str, input: str) -> ModelResult: ...


class Planner(Protocol):
    def decide(self, response: str) -> FinalAction: ...
