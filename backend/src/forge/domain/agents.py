"""Agent identity and immutable executable configuration."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Stable identity and human-facing metadata for an agent."""

    id: str
    name: str
    description: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AgentVersion:
    """Immutable configuration captured for reproducible runs."""

    id: str
    agent_id: str
    version: int
    instructions: str
    provider: str
    model: str
    planner: str
    tools: tuple[str, ...]
    max_steps: int
    created_at: datetime
    timeout_seconds: float = 30
    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_retries: int = 2
    max_output_tokens: int = 2048
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None

    def __post_init__(self) -> None:
        validate_run_limits(
            timeout_seconds=self.timeout_seconds,
            max_tokens=self.max_tokens,
            max_cost_usd=self.max_cost_usd,
            max_retries=self.max_retries,
            max_output_tokens=self.max_output_tokens,
            input_cost_per_million=self.input_cost_per_million,
            output_cost_per_million=self.output_cost_per_million,
        )


def validate_run_limits(
    *,
    timeout_seconds: float,
    max_tokens: int | None,
    max_cost_usd: float | None,
    max_retries: int,
    max_output_tokens: int,
    input_cost_per_million: float | None,
    output_cost_per_million: float | None,
) -> None:
    """Validate budgets without assuming provider pricing."""
    for name, value in (
        ("timeout_seconds", timeout_seconds),
        ("max_cost_usd", max_cost_usd),
    ):
        if value is not None and (not isfinite(value) or value <= 0):
            raise ValueError(f"{name} must be finite and positive")
    for name, value in (
        ("max_tokens", max_tokens),
        ("max_output_tokens", max_output_tokens),
    ):
        if value is not None and (type(value) is not int or value <= 0):
            raise ValueError(f"{name} must be a positive integer")
    if type(max_retries) is not int or not 0 <= max_retries <= 5:
        raise ValueError("max_retries must be an integer between 0 and 5")
    for rate in (input_cost_per_million, output_cost_per_million):
        if rate is not None and (not isfinite(rate) or rate < 0):
            raise ValueError("cost rates must be finite and nonnegative")
    if max_cost_usd is not None and (
        input_cost_per_million is None or output_cost_per_million is None
    ):
        raise ValueError("max_cost_usd requires explicit input and output cost rates")
