"""Terminal diagnosis links real failed boundaries, never unrelated budget steps."""
import asyncio

import pytest

from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FakeProvider, FinalPlanner
from forge.runtime.ports import ProviderError
from forge.runtime.react import ReActPlanner


def create_run(client, **config):
    agent = client.post('/api/v1/agents', json={
        'name': 'Trace diagnosis', 'instructions': 'test', **config,
    }).json()
    return client.post('/api/v1/runs', json={
        'agent_id': agent['id'], 'input': 'demo',
    }).json()['id']


@pytest.mark.parametrize('kind', ['model', 'planner'])
def test_terminal_failure_identifies_its_actual_failed_step(client, kind):
    run_id = create_run(client, max_retries=0)

    class FailedProvider(FakeProvider):
        async def stream(self, **kwargs):
            raise ProviderError('fake', 'unavailable', 'Provider unavailable')
            yield  # pragma: no cover - retain the async iterator contract

    class FailedPlanner:
        def decide(self, response):
            raise ValueError('invalid action')

    provider = FailedProvider() if kind == 'model' else FakeProvider()
    planner = FailedPlanner() if kind == 'planner' else FinalPlanner()
    with pytest.raises((ProviderError, ValueError)):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, provider, planner))
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    failed = next(step for step in steps if step['kind'] == kind and step['status'] == 'failed')
    assert events[-1]['type'] == 'run.failed'
    assert events[-1]['payload']['step_id'] == failed['id']
    assert next(event for event in events if event['type'] == f'{kind}.failed')['payload']['step_id'] == failed['id']


def test_between_step_budget_stop_does_not_claim_a_failed_boundary(client):
    run_id = create_run(client, max_steps=2)
    provider = FakeProvider({'demo': '{"action":"continue","text":"again"}'})
    asyncio.run(execute_fake_run(client.app.state.database, run_id, provider, ReActPlanner()))
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    assert events[-1]['payload'] == {'reason': 'max_steps'}
    assert all(step['status'] == 'completed' for step in client.get(f'/api/v1/runs/{run_id}/steps').json())
