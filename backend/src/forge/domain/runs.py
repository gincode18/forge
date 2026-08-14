"""Run state and transition invariants."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class InvalidRunTransition(ValueError):
    """Raised when a run attempts an invalid state transition."""


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


TERMINAL_RUN_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
    RunStatus.INTERRUPTED,
}

_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.QUEUED: frozenset(
        {RunStatus.RUNNING, RunStatus.CANCELLED, RunStatus.INTERRUPTED}
    ),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.WAITING_FOR_APPROVAL,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.INTERRUPTED,
        }
    ),
    RunStatus.WAITING_FOR_APPROVAL: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.INTERRUPTED,
        }
    ),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
    RunStatus.INTERRUPTED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class Run:
    """One execution request pinned to an immutable agent version."""

    id: str
    agent_version_id: str
    input: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime

    def transition(self, target: RunStatus, *, at: datetime) -> "Run":
        """Return a new run state after validating the transition."""

        if target not in _ALLOWED_TRANSITIONS[self.status]:
            msg = f"cannot transition run from {self.status} to {target}"
            raise InvalidRunTransition(msg)
        return replace(self, status=target, updated_at=at)
