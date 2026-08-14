"""Queued run and event query use cases."""

from sqlalchemy.orm import Session

from forge.adapters.sqlite.models import EventRecord, RunRecord
from forge.adapters.sqlite.repositories import AgentRepository, RunRepository
from forge.application.errors import ResourceNotFoundError


def create_run(
    session: Session,
    *,
    agent_id: str,
    input: str,
    agent_version_id: str | None = None,
) -> RunRecord:
    agents = AgentRepository(session)
    if agent_version_id:
        version = agents.get_version(agent_version_id)
        if version is None or version.agent_id != agent_id:
            raise ResourceNotFoundError("agent version", agent_version_id)
    else:
        version = agents.latest_version(agent_id)
        if version is None:
            raise ResourceNotFoundError("agent", agent_id)

    run = RunRepository(session).create(agent_version_id=version.id, input=input)
    session.commit()
    return run


def list_runs(session: Session) -> list[RunRecord]:
    return RunRepository(session).list_all()


def get_run(session: Session, run_id: str) -> RunRecord:
    run = RunRepository(session).get(run_id)
    if run is None:
        raise ResourceNotFoundError("run", run_id)
    return run


def list_run_events(session: Session, run_id: str) -> list[EventRecord]:
    get_run(session, run_id)
    return RunRepository(session).events(run_id)
