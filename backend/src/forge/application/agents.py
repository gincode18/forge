"""Agent creation, versioning, and query use cases."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from forge.adapters.sqlite.models import AgentRecord, AgentVersionRecord
from forge.adapters.sqlite.repositories import AgentRepository
from forge.application.errors import ResourceNotFoundError
from forge.domain.agents import validate_run_limits


@dataclass(frozen=True, slots=True)
class AgentConfig:
    instructions: str
    provider: str = "fake"
    model: str = "deterministic"
    planner: str = "react"
    tools: list[str] = field(default_factory=list)
    max_steps: int = 12
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


def create_agent(
    session: Session,
    *,
    name: str,
    description: str | None,
    config: AgentConfig,
) -> AgentRecord:
    repository = AgentRepository(session)
    agent = repository.create(
        name=name,
        description=description,
        instructions=config.instructions,
        provider=config.provider,
        model=config.model,
        planner=config.planner,
        tools=config.tools,
        max_steps=config.max_steps,
        timeout_seconds=config.timeout_seconds,
        max_tokens=config.max_tokens,
        max_cost_usd=config.max_cost_usd,
        max_retries=config.max_retries,
        max_output_tokens=config.max_output_tokens,
        input_cost_per_million=config.input_cost_per_million,
        output_cost_per_million=config.output_cost_per_million,
    )
    session.commit()
    return agent


def list_agents(session: Session) -> list[AgentRecord]:
    return AgentRepository(session).list_all()


def get_agent(session: Session, agent_id: str) -> AgentRecord:
    agent = AgentRepository(session).get(agent_id)
    if agent is None:
        raise ResourceNotFoundError("agent", agent_id)
    return agent


def create_agent_version(
    session: Session, agent_id: str, config: AgentConfig
) -> AgentVersionRecord:
    repository = AgentRepository(session)
    agent = repository.get(agent_id)
    if agent is None:
        raise ResourceNotFoundError("agent", agent_id)
    version = repository.add_version(
        agent,
        instructions=config.instructions,
        provider=config.provider,
        model=config.model,
        planner=config.planner,
        tools=config.tools,
        max_steps=config.max_steps,
        timeout_seconds=config.timeout_seconds,
        max_tokens=config.max_tokens,
        max_cost_usd=config.max_cost_usd,
        max_retries=config.max_retries,
        max_output_tokens=config.max_output_tokens,
        input_cost_per_million=config.input_cost_per_million,
        output_cost_per_million=config.output_cost_per_million,
    )
    session.commit()
    return version
