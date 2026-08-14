"""Versioned HTTP request and response contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    database: Literal["ready"]


class AgentConfigRequest(BaseModel):
    instructions: str = Field(min_length=1)
    provider: str = Field(default="fake", min_length=1, max_length=80)
    model: str = Field(default="deterministic", min_length=1, max_length=160)
    planner: str = Field(default="react", min_length=1, max_length=80)
    tools: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=12, ge=1, le=100)


class CreateAgentRequest(AgentConfigRequest):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class AgentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    version: int
    instructions: str
    provider: str
    model: str
    planner: str
    tools: list[str]
    max_steps: int
    created_at: datetime


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    latest_version: AgentVersionResponse


class AgentDetailResponse(AgentResponse):
    versions: list[AgentVersionResponse]


class CreateRunRequest(BaseModel):
    agent_id: str
    agent_version_id: str | None = None
    input: str = Field(min_length=1)


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_version_id: str
    input: str
    status: str
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    sequence: int
    type: str
    payload: dict[str, Any]
    schema_version: int
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    resource: str | None = None
    resource_id: str | None = None
