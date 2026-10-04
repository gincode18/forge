"""Read-only aggregate metrics from normalized steps and committed events."""
import math
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from forge.adapters.sqlite.repositories import RunRepository
from forge.application.errors import ResourceNotFoundError
from forge.domain.runs import TERMINAL_RUN_STATUSES


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def elapsed(start: datetime | None, end: datetime | None):
    if start is None or end is None:
        return None
    start = start.replace(tzinfo=UTC) if start.tzinfo is None else start
    end = end.replace(tzinfo=UTC) if end.tzinfo is None else end
    return number((end - start).total_seconds() * 1000)


def run_metrics(session: Session, run_id: str) -> dict:
    runs = RunRepository(session)
    run = runs.get(run_id)
    if run is None:
        raise ResourceNotFoundError('run', run_id)
    steps = runs.steps(run_id)
    models = [step for step in steps if step.kind == 'model']
    events = runs.events(run_id)
    start = next((event.created_at for event in events if event.type == 'run.started'), None)
    end = next((event.created_at for event in reversed(events) if event.type == f'run.{run.status}'), None)

    def total(values):
        return sum(values) if values and all(value is not None for value in values) else None

    def usage(key):
        return total([number(((step.output or {}).get('usage') or {}).get(key)) for step in models])

    tools = {step.id: step.status for step in steps if step.kind == 'tool'}
    for event in events:
        if event.type in ('tool.completed', 'tool.denied', 'tool.failed'):
            tools[event.payload.get('step_id', event.id)] = event.type.partition('.')[2]
    model_duration = total([elapsed(step.started_at, step.finished_at) for step in models])
    terminal = run.status in {status.value for status in TERMINAL_RUN_STATUSES}
    return {
        'run_id': run_id,
        'duration_ms': elapsed(start, end) if terminal else None,
        'model_duration_ms': model_duration,
        'model_calls': len(models),
        'input_tokens': usage('input_tokens'),
        'output_tokens': usage('output_tokens'),
        'total_tokens': usage('total_tokens'),
        'cost_usd': total([number((step.output or {}).get('cost_usd')) for step in models]),
        'retries': sum(step.attempt > 1 for step in models),
        'failures': sum(step.status == 'failed' and tools.get(step.id) != 'denied' for step in steps),
        'tools': {status: sum(value == status for value in tools.values()) for status in ('completed', 'denied', 'failed')},
    }
