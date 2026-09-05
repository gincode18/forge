"""Queued run and persisted event endpoints."""

from fastapi import APIRouter, status

from forge.api.dependencies import SessionDependency
from forge.api.schemas import CreateRunRequest, EventResponse, RunResponse, StepResponse
from forge.application.runs import (
    create_run,
    get_run,
    list_run_events,
    list_run_steps,
    list_runs,
)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def post_run(request: CreateRunRequest, session: SessionDependency) -> RunResponse:
    run = create_run(session, **request.model_dump())
    return RunResponse.model_validate(run)


@router.get("", response_model=list[RunResponse])
def get_runs(session: SessionDependency) -> list[RunResponse]:
    return [RunResponse.model_validate(run) for run in list_runs(session)]


@router.get("/{run_id}", response_model=RunResponse)
def get_run_by_id(run_id: str, session: SessionDependency) -> RunResponse:
    return RunResponse.model_validate(get_run(session, run_id))


@router.get("/{run_id}/events", response_model=list[EventResponse])
def get_events(run_id: str, session: SessionDependency) -> list[EventResponse]:
    return [
        EventResponse.model_validate(event) for event in list_run_events(session, run_id)
    ]


@router.get("/{run_id}/steps", response_model=list[StepResponse])
def get_steps(run_id: str, session: SessionDependency) -> list[StepResponse]:
    return [
        StepResponse.model_validate(step) for step in list_run_steps(session, run_id)
    ]
