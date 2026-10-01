import pytest
from sqlalchemy.orm import Session

from forge.adapters.sqlite.repositories import RunRepository


def test_tool_policy_trace_rejects_untyped_decisions(client):
    agent = client.post('/api/v1/agents', json={'name': 'trace', 'instructions': 'test'}).json()
    run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'hi'}).json()['id']
    with Session(client.app.state.database.engine) as session, pytest.raises(ValueError):
        RunRepository(session).append_event(run_id, 'tool.policy', {
            'step_id': 'step', 'tool_name': 'calculator', 'tool_version': '1',
            'call_id': None, 'decision': 'silently_execute', 'reason': 'invalid',
        })
