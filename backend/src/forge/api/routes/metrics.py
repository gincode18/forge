"""Run metrics queries; never execute work from HTTP handlers."""
from fastapi import APIRouter
from pydantic import BaseModel

from forge.api.dependencies import SessionDependency
from forge.application.metrics import run_metrics

router = APIRouter(prefix='/runs', tags=['runs'])


class RunMetricsResponse(BaseModel):
    run_id: str
    duration_ms: float | None
    model_duration_ms: float | None
    model_calls: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None
    retries: int
    failures: int
    tools: dict[str, int]


@router.get('/{run_id}/metrics', response_model=RunMetricsResponse)
def metrics(run_id: str, session: SessionDependency):
    return run_metrics(session, run_id)
