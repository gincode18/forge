"""Typed execution events persisted as the run trace."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    run_id: str
    sequence: int
    type: str
    payload: dict[str, Any]
    schema_version: int
    created_at: datetime
