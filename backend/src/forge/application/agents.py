"""Agent creation, versioning, and query use cases."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from forge.adapters.sqlite.models import AgentRecord, AgentVersionRecord
from forge.adapters.sqlite.repositories import AgentRepository
from forge.application.errors import ResourceNotFoundError


@dataclass(frozen=True, slots=True)
class AgentConfig:
    instructions: str
    provider: str = "fake"
    model: str = "deterministic"
    planner: str = "react"
    tools: list[str] = field(default_factory=list)
    max_steps: int = 12


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
    )
    session.commit()
    return version
