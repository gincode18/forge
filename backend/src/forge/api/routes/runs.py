"""Queued run and persisted event endpoints."""

import asyncio

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from forge.adapters.sqlite.repositories import RunRepository
from forge.api.dependencies import SessionDependency
from forge.api.schemas import CreateRunRequest, EventResponse, RunResponse, StepResponse
from forge.application.errors import ResourceNotFoundError
from forge.application.runs import (
    create_run,
    get_run,
    list_run_events,
    list_run_steps,
    list_runs,
)
from forge.domain.runs import TERMINAL_RUN_STATUSES, InvalidRunTransition, RunStatus

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def post_run(
    request: CreateRunRequest, session: SessionDependency, http_request: Request
) -> RunResponse:
    run = create_run(session, **request.model_dump(), request_id=http_request.state.request_id)
    return RunResponse.model_validate(run)


@router.post("/{run_id}/start", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_run(run_id: str, request: Request) -> RunResponse:
    try:
        run = request.app.state.supervisor.start(run_id)
    except InvalidRunTransition:
        raise
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return RunResponse.model_validate(run)


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(run_id: str, request: Request) -> RunResponse:
    return RunResponse.model_validate(request.app.state.supervisor.cancel(run_id))


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


@router.get("/{run_id}/stream")
async def stream_events(
    run_id: str, request: Request, last_event_id: str | None = Header(default=None),
    since: int = Query(default=0, ge=0),
) -> StreamingResponse:
    try:
        cursor = int(last_event_id) if last_event_id is not None else since
        if cursor < 0 or (last_event_id is not None and str(cursor) != last_event_id):
            raise ValueError
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Last-Event-ID must be a nonnegative sequence") from error

    database = request.app.state.database
    with Session(database.engine) as session:
        if RunRepository(session).get(run_id) is None:
            raise ResourceNotFoundError("run", run_id)

    async def generate():
        nonlocal cursor
        while True:
            # Re-query after each wakeup; there is no snapshot/subscription gap.
            with Session(database.engine) as session:
                runs = RunRepository(session)
                run = runs.get(run_id)
                terminal = run is None or RunStatus(run.status) in TERMINAL_RUN_STATUSES
                events = runs.events_after(run_id, cursor)
                frames = [EventResponse.model_validate(event) for event in events]
            for event in frames:
                cursor = event.sequence
                yield f"id: {cursor}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"
            if terminal:
                return
            await asyncio.sleep(0.05)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/{run_id}/steps", response_model=list[StepResponse])
def get_steps(run_id: str, session: SessionDependency) -> list[StepResponse]:
    return [
        StepResponse.model_validate(step) for step in list_run_steps(session, run_id)
    ]
