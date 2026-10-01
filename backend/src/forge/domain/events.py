"""Typed execution events persisted as the run trace."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    run_id: str
    sequence: int
    type: str
    payload: dict[str, Any]
    schema_version: int
    created_at: datetime


class ToolBoundaryPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    step_id: str
    tool_name: str
    tool_version: str
    call_id: str | None


class ToolRequestPayload(ToolBoundaryPayload):
    arguments: dict[str, Any]


class ToolPolicyPayload(ToolBoundaryPayload):
    decision: Literal['allow', 'deny', 'require_approval']
    reason: str


class ToolOutcomePayload(ToolBoundaryPayload):
    output: dict[str, Any]
    duration_ms: float = Field(ge=0)


TOOL_EVENT_PAYLOADS = {
    'tool.requested': ToolRequestPayload,
    'tool.policy': ToolPolicyPayload,
    'tool.started': ToolBoundaryPayload,
    'tool.completed': ToolOutcomePayload,
    'tool.failed': ToolOutcomePayload,
    'tool.denied': ToolOutcomePayload,
}
