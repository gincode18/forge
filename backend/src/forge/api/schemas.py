"""Versioned HTTP request and response contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderResponse(BaseModel):
    id: str
    configured: bool
    default_model: str


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
    timeout_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)
    max_tokens: int | None = Field(default=None, gt=0)
    max_cost_usd: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    max_retries: int = Field(default=2, ge=0, le=5)
    max_output_tokens: int = Field(default=2048, gt=0)
    input_cost_per_million: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    output_cost_per_million: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )

    @model_validator(mode="after")
    def cost_requires_rates(self) -> "AgentConfigRequest":
        if self.max_cost_usd is not None and (
            self.input_cost_per_million is None or self.output_cost_per_million is None
        ):
            raise ValueError(
                "max_cost_usd requires explicit input and output cost rates"
            )
        return self


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
    timeout_seconds: float
    max_tokens: int | None
    max_cost_usd: float | None
    max_retries: int
    max_output_tokens: int
    input_cost_per_million: float | None
    output_cost_per_million: float | None
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
    correlation_id: str | None = None
    causation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    step_id: str | None = None


class StepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    sequence: int
    correlation_id: str | None = None
    causation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    kind: str
    status: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    attempt: int
    error: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    request_id: str
    resource: str | None = None
    resource_id: str | None = None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    step_id: str
    tool_name: str
    tool_version: str
    arguments: dict[str, Any]
    status: Literal['pending', 'approved', 'rejected', 'cancelled']
    created_at: datetime
    resolved_at: datetime | None


class ResolveApprovalRequest(BaseModel):
    approved: bool


class ToolResponse(BaseModel):
    name: str
    version: str
    key: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    capabilities: list[str]
    risk: Literal['low', 'sensitive']
    timeout_seconds: float
    max_output_bytes: int
    default_policy: Literal['allow', 'require_approval']
    security_warning: str


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    path: str
    size_bytes: int
    media_type: str
    created_at: datetime
    expired: bool = False
