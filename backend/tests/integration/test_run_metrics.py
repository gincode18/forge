import asyncio

from sqlalchemy.orm import Session

from forge.adapters.sqlite.repositories import RunRepository
from forge.domain.steps import StepKind, StepStatus
from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FakeProvider, FinalPlanner


def make_run(client):
    agent = client.post('/api/v1/agents', json={'name': 'Metrics', 'instructions': 'Answer.'}).json()
    return client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'Hello'}).json()['id']


def test_metrics_aggregate_actual_run_and_preserve_unknown_cost(client):
    run_id = make_run(client)
    asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider({'Hello': 'Hi'}), FinalPlanner()))
    response = client.get(f'/api/v1/runs/{run_id}/metrics')
    assert response.status_code == 200
    metrics = response.json()
    assert metrics['model_calls'] == 1
    assert metrics['total_tokens'] > 0
    assert metrics['cost_usd'] is None
    assert metrics['duration_ms'] >= 0
    assert metrics['model_duration_ms'] >= 0
    assert metrics['retries'] == 0
    assert metrics['failures'] == 0
    assert client.get('/api/v1/runs/missing/metrics').status_code == 404


def test_metrics_unknown_usage_and_failed_attempts_are_not_zero(client):
    run_id = make_run(client)
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        failed = runs.create_step(run_id=run_id, kind=StepKind.MODEL, input={}, status=StepStatus.FAILED)
        failed.output = {'usage': None}
        successful = runs.create_step(run_id=run_id, kind=StepKind.MODEL, input={}, status=StepStatus.COMPLETED, attempt=2)
        successful.output = {'usage': {'input_tokens': 2, 'output_tokens': 3, 'total_tokens': 5}, 'cost_usd': 0.1}
        session.commit()
    metrics = client.get(f'/api/v1/runs/{run_id}/metrics').json()
    assert metrics['total_tokens'] is None
    assert metrics['cost_usd'] is None
    assert metrics['model_duration_ms'] is None
    assert metrics['duration_ms'] is None
    assert metrics['retries'] == 1
    assert metrics['failures'] == 1


def test_denied_tools_are_not_reported_as_execution_failures(client):
    agent = client.post('/api/v1/agents', json={'name': 'Denied metrics', 'instructions': 'Answer.'}).json()
    run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': '{"forge_script":[{"name":"calculator","arguments":{"expression":"2+2"}}]}'}).json()['id']
    asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider(), FinalPlanner()))
    metrics = client.get(f'/api/v1/runs/{run_id}/metrics').json()
    assert metrics['tools'] == {'completed': 0, 'denied': 1, 'failed': 0}
    assert metrics['failures'] == 0
