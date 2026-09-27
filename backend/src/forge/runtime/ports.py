"""Minimal boundaries for deterministic, no-tool execution."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FinalAction:
    text: str


class ModelProvider(Protocol):
    async def complete(self, *, instructions: str, input: str) -> str: ...


class Planner(Protocol):
    def decide(self, response: str) -> FinalAction: ...
