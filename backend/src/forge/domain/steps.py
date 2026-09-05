"""Typed units of work performed while executing a run."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class StepKind(StrEnum):
    """The runtime boundary represented by a step."""

    MODEL = "model"
    PLANNER = "planner"
    TOOL = "tool"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    APPROVAL = "approval"
    FINAL = "final"


class StepStatus(StrEnum):
    """Lifecycle state of one runtime step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Step:
    """One ordered, inspectable operation belonging to a run."""

    id: str
    run_id: str
    sequence: int
    kind: StepKind
    status: StepStatus
    input: dict[str, Any]
    output: dict[str, Any] | None
    attempt: int
    error: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
