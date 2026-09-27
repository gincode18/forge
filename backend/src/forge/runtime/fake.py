"""Scripted provider and finish-only planner for no-key runtime tests."""
from forge.runtime.ports import FinalAction


class FakeProvider:
    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}

    async def complete(self, *, instructions: str, input: str) -> str:
        return self.responses.get(input, f"Fake response to: {input}")


class FinalPlanner:
    def decide(self, response: str) -> FinalAction:
        return FinalAction(text=response)
