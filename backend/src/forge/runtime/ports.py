"""Provider-neutral streaming values and planner actions."""
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class FinalAction:
    text: str


@dataclass(frozen=True, slots=True)
class ContinueAction:
    text: str


@dataclass(frozen=True, slots=True)
class ToolAction:
    name: str
    arguments: dict


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: str
    text: str


@dataclass(frozen=True, slots=True)
class ModelDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: dict
    id: str | None = None


@dataclass(frozen=True, slots=True)
class TextContentBlock:
    type: Literal["text"] = field(default="text", init=False)
    text: str


@dataclass(frozen=True, slots=True)
class ToolCallContentBlock:
    type: Literal["tool_call"] = field(default="tool_call", init=False)
    tool_call: ToolCall


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
    tool_calls: tuple[ToolCall, ...] = ()
    metadata: dict = field(default_factory=dict)
    content_blocks: tuple[TextContentBlock | ToolCallContentBlock, ...] = field(init=False)

    def __post_init__(self) -> None:
        blocks = ((TextContentBlock(self.text),) if self.text else ())
        object.__setattr__(self, "content_blocks", blocks + tuple(
            ToolCallContentBlock(call) for call in self.tool_calls
        ))


class ProviderError(Exception):
    def __init__(
        self, provider: str, code: str, message: str, *, retryable: bool = False
    ) -> None:
        self.provider = provider
        self.code = code
        self.retryable = retryable
        super().__init__(message)


class ModelProvider(Protocol):
    async def complete(self, *, instructions: str, input: str) -> ModelResult: ...

    def stream(
        self, *, instructions: str, input: str,
        messages: tuple[ModelMessage, ...] = (), max_output_tokens: int = 2048,
    ) -> AsyncIterator[ModelDelta | ModelResult]:
        """Yield deltas followed by exactly one final result on success."""
        ...


class Planner(Protocol):
    def decide(self, response: str) -> FinalAction | ContinueAction | ToolAction: ...
