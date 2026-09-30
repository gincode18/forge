"""Agent definition and immutable-version endpoints."""

from fastapi import APIRouter, status

from forge.adapters.sqlite.models import AgentRecord
from forge.api.dependencies import SessionDependency
from forge.api.schemas import (
    AgentConfigRequest,
    AgentDetailResponse,
    AgentResponse,
    AgentVersionResponse,
    CreateAgentRequest,
)
from forge.application.agents import (
    AgentConfig,
    create_agent,
    create_agent_version,
    get_agent,
    list_agents,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def _config(request: AgentConfigRequest) -> AgentConfig:
    return AgentConfig(
        instructions=request.instructions,
        provider=request.provider,
        model=request.model,
        planner=request.planner,
        tools=request.tools,
        max_steps=request.max_steps,
        timeout_seconds=request.timeout_seconds,
        max_tokens=request.max_tokens,
        max_cost_usd=request.max_cost_usd,
        max_retries=request.max_retries,
        max_output_tokens=request.max_output_tokens,
        input_cost_per_million=request.input_cost_per_million,
        output_cost_per_million=request.output_cost_per_million,
    )


def _agent_response(agent: AgentRecord) -> AgentResponse:
    versions = agent.versions
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        created_at=agent.created_at,
        latest_version=AgentVersionResponse.model_validate(versions[-1]),
    )


@router.post(
    "", response_model=AgentDetailResponse, status_code=status.HTTP_201_CREATED
)
def post_agent(
    request: CreateAgentRequest, session: SessionDependency
) -> AgentDetailResponse:
    agent = create_agent(
        session,
        name=request.name,
        description=request.description,
        config=_config(request),
    )
    versions = [AgentVersionResponse.model_validate(item) for item in agent.versions]
    return AgentDetailResponse(**_agent_response(agent).model_dump(), versions=versions)


@router.get("", response_model=list[AgentResponse])
def get_agents(session: SessionDependency) -> list[AgentResponse]:
    return [_agent_response(agent) for agent in list_agents(session)]


@router.get("/{agent_id}", response_model=AgentDetailResponse)
def get_agent_by_id(agent_id: str, session: SessionDependency) -> AgentDetailResponse:
    agent = get_agent(session, agent_id)
    versions = [AgentVersionResponse.model_validate(item) for item in agent.versions]
    return AgentDetailResponse(**_agent_response(agent).model_dump(), versions=versions)


@router.post(
    "/{agent_id}/versions",
    response_model=AgentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_agent_version(
    agent_id: str, request: AgentConfigRequest, session: SessionDependency
) -> AgentVersionResponse:
    version = create_agent_version(session, agent_id, _config(request))
    return AgentVersionResponse.model_validate(version)
