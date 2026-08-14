"""Agent identity and immutable executable configuration."""

from dataclasses import dataclass
from datetime import datetime


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
