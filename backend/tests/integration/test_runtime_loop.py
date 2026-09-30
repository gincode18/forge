"""Offline runtime acceptance tests against committed SQLite traces."""
import asyncio

from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FinalPlanner
from forge.runtime.ports import (
    ContinueAction,
    ModelDelta,
    ModelMessage,
    ModelResult,
    ModelUsage,
)


def new_run(client, **config):
    agent = client.post('/api/v1/agents', json={
        'name': 'Runtime', 'instructions': 'Be clear.', **config,
    })
    assert agent.status_code == 201, agent.text
    response = client.post('/api/v1/runs', json={
        'agent_id': agent.json()['id'], 'input': 'Hello',
    })
    assert response.status_code == 201, response.text
    return response.json()['id']


def trace(client, run_id, resource):
    return client.get(f'/api/v1/runs/{run_id}/{resource}').json()


Delta = ModelDelta


def test_stream_commits_first_delta_before_final_and_closes(client):
    run_id = new_run(client)
    closed = []

    class StreamingProvider:
        async def stream(self, **kwargs):
            try:
                yield Delta('Hello')
                with client.app.state.database.engine.connect() as connection:
                    from sqlalchemy import text
                    assert connection.execute(text(
                        "SELECT count(*) FROM events WHERE type = 'model.delta'"
                    )).scalar_one() == 1
                yield Delta(' world')
                yield ModelResult('Hello world', 'fake', 'test', latency_ms=12.5)
            finally:
                closed.append(True)

        async def complete(self, **kwargs):
            raise AssertionError('must stream')

    asyncio.run(execute_fake_run(
        client.app.state.database, run_id, StreamingProvider(), FinalPlanner(),
    ))
    events = trace(client, run_id, 'events')
    assert ''.join(e['payload']['text'] for e in events if e['type'] == 'model.delta') == 'Hello world'
    output = trace(client, run_id, 'steps')[0]['output']
    assert output['text'] == 'Hello world'
    assert output['usage'] is None
    assert output['latency_ms'] == 12.5
    assert next(e for e in events if e['type'] == 'model.completed')['payload']['latency_ms'] == 12.5
    assert closed == [True]


def test_continue_runs_another_model_turn_with_history(client):
    run_id = new_run(client)
    seen = []

    class Turns:
        async def stream(self, *, instructions, input, messages=(), max_output_tokens=2048):
            seen.append(messages)
            yield ModelResult('thinking' if not messages else 'done', 'fake', 'test')

    class Planning:
        def decide(self, response):
            from forge.runtime.ports import FinalAction
            return ContinueAction('Keep going') if response == 'thinking' else FinalAction(response)

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Turns(), Planning()))
    assert seen == [(), (ModelMessage('assistant', 'thinking'), ModelMessage('user', 'Keep going'))]
    assert [s['kind'] for s in trace(client, run_id, 'steps')] == ['model', 'planner', 'model', 'planner']
    assert trace(client, run_id, 'events')[-1]['payload']['result'] == 'done'


def test_default_supervisor_uses_react_and_prepares_prompt(client):
    from forge.runtime.fake import FakeProvider
    from forge.runtime.react import ReActPlanner
    assert isinstance(client.app.state.supervisor.planner, ReActPlanner)
    provider = FakeProvider({'Hello': '{"action":"continue","text":"reason"}'})
    run_id = new_run(client, max_steps=4)
    asyncio.run(execute_fake_run(client.app.state.database, run_id, provider, ReActPlanner()))
    assert len(trace(client, run_id, 'steps')) == 4
    assert trace(client, run_id, 'steps')[0]['input']['instructions'] != 'Be clear.'
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'max_steps'


def test_tool_action_fails_without_execution(client):
    from forge.runtime.fake import FakeProvider
    from forge.runtime.react import ReActPlanner
    run_id = new_run(client)
    asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider({
        'Hello': '{"action":"tool","name":"shell","arguments":{"command":"touch forbidden"}}',
    }), ReActPlanner()))
    assert client.get(f'/api/v1/runs/{run_id}').json()['status'] == 'failed'
    steps = trace(client, run_id, 'steps')
    assert steps[-1]['output']['action'] == 'tool'
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'tool_disabled'


def test_stream_coalesces_many_chunks_with_bounded_events(client):
    run_id = new_run(client)
    text = 'x' * 300000

    class Chunks:
        async def stream(self, **kwargs):
            for offset in range(0, len(text), 100):
                yield ModelDelta(text[offset:offset + 100])
            yield ModelResult(text, 'fake', 'test')

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Chunks(), FinalPlanner()))
    deltas = [e for e in trace(client, run_id, 'events') if e['type'] == 'model.delta']
    assert 1 < len(deltas) <= 128
    assert ''.join(e['payload']['text'] for e in deltas) == text
    assert trace(client, run_id, 'steps')[0]['output']['text'] == text


def test_cumulative_token_budget_stops_before_planner(client):
    run_id = new_run(client, max_tokens=9)
    calls = []

    class Tokens:
        async def stream(self, **kwargs):
            calls.append(kwargs['max_output_tokens'])
            yield ModelResult('next', 'fake', 'test', usage=ModelUsage(3, 2, 5))

    class Planning:
        def decide(self, response):
            return ContinueAction('again')

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Tokens(), Planning()))
    assert calls == [9, 4]
    assert [s['kind'] for s in trace(client, run_id, 'steps')] == ['model', 'planner', 'model']
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'max_tokens'
    assert trace(client, run_id, 'steps')[-1]['output']['usage']['total_tokens'] == 5


def test_estimated_cost_is_persisted_and_cumulative_budget_enforced(client):
    run_id = new_run(client, max_cost_usd=0.00001,
                     input_cost_per_million=1, output_cost_per_million=2)
    class Priced:
        async def stream(self, **kwargs):
            yield ModelResult('next', 'fake', 'test', usage=ModelUsage(3, 2, 5),
                              latency_ms=9, request_id='safe', metadata={'mode': 'offline'})
    class Planning:
        def decide(self, response):
            return ContinueAction('again')
    asyncio.run(execute_fake_run(client.app.state.database, run_id, Priced(), Planning()))
    steps = trace(client, run_id, 'steps')
    assert len(steps) == 3
    assert steps[0]['output']['cost_usd'] == 0.000007
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'max_cost_usd'
    completed = [e for e in trace(client, run_id, 'events') if e['type'] == 'model.completed']
    assert completed[-1]['payload']['total_cost_usd'] == 0.000014
    assert completed[-1]['payload']['total_tokens'] == 10


def test_unknown_usage_cannot_bypass_enabled_budget(client):
    run_id = new_run(client, max_tokens=100)
    class Unknown:
        async def complete(self, **kwargs):
            return ModelResult('done', 'fake', 'test', latency_ms=5)
    asyncio.run(execute_fake_run(client.app.state.database, run_id, Unknown(), FinalPlanner()))
    assert client.get(f'/api/v1/runs/{run_id}').json()['status'] == 'failed'
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'usage_unavailable'
    assert trace(client, run_id, 'steps')[0]['output']['latency_ms'] == 5


def test_model_output_cap_rejects_overlong_final(client):
    run_id = new_run(client, max_output_tokens=2)
    class Overlong:
        async def stream(self, **kwargs):
            assert kwargs['max_output_tokens'] == 2
            yield ModelResult('partial', 'fake', 'test', usage=ModelUsage(3, 3, 6))
    asyncio.run(execute_fake_run(client.app.state.database, run_id, Overlong(), FinalPlanner()))
    assert client.get(f'/api/v1/runs/{run_id}').json()['status'] == 'failed'
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'max_output_tokens'
    assert len(trace(client, run_id, 'steps')) == 1


def test_version_deadline_applies_to_direct_execution(client):
    import pytest
    run_id = new_run(client, timeout_seconds=0.02)
    closed = []
    class Waiting:
        async def stream(self, **kwargs):
            try:
                yield ModelDelta('first')
                await asyncio.Event().wait()
            finally:
                closed.append(True)
    with pytest.raises(TimeoutError):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Waiting(), FinalPlanner(),
                                    timeout_seconds=0.05))
    assert closed == [True]
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'timeout'
    assert trace(client, run_id, 'steps')[0]['error']['type'] == 'TimeoutError'
    step = trace(client, run_id, 'steps')[0]
    from datetime import datetime
    assert (datetime.fromisoformat(step['finished_at']) -
            datetime.fromisoformat(step['started_at'])).total_seconds() < 0.045


def test_retry_preserves_failed_attempt_and_does_not_complete_partial_output(client):
    from forge.runtime.ports import ProviderError
    run_id = new_run(client, max_retries=1)
    calls = []
    closed = []
    class Flaky:
        async def stream(self, **kwargs):
            calls.append(kwargs)
            try:
                if len(calls) == 1:
                    yield ModelDelta('discarded partial')
                    raise ProviderError('fake', 'unavailable', 'Temporary failure', retryable=True)
                yield ModelDelta('success')
                yield ModelResult('success', 'fake', 'test', usage=ModelUsage(2, 1, 3))
            finally:
                closed.append(True)
    asyncio.run(execute_fake_run(client.app.state.database, run_id, Flaky(), FinalPlanner()))
    assert len(calls) == 2
    assert closed == [True, True]
    steps = trace(client, run_id, 'steps')
    assert [(s['status'], s['attempt']) for s in steps] == [('failed', 1), ('completed', 2), ('completed', 1)]
    assert steps[0]['output'] is None
    events = trace(client, run_id, 'events')
    retry = next(e for e in events if e['type'] == 'model.retry')
    assert retry['payload']['code'] == 'unavailable'
    assert retry['payload']['attempt'] == 2
    assert events[-1]['payload']['result'] == 'success'
    deltas = [e for e in events if e['type'] == 'model.delta']
    assert deltas[0]['payload']['step_id'] != deltas[1]['payload']['step_id']


def test_retry_exhaustion_records_every_attempt_and_safe_reason(client):
    import pytest

    from forge.runtime.ports import ProviderError
    run_id = new_run(client, max_retries=1)
    calls = []
    class Unavailable:
        async def stream(self, **kwargs):
            calls.append(True)
            raise ProviderError('fake', 'unavailable', 'Temporarily unavailable', retryable=True)
            yield
    with pytest.raises(ProviderError):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Unavailable(), FinalPlanner()))
    assert len(calls) == 2
    assert [s['attempt'] for s in trace(client, run_id, 'steps')] == [1, 2]
    assert all(s['status'] == 'failed' for s in trace(client, run_id, 'steps'))
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'retry_exhausted'


def test_failed_attempt_with_unknown_usage_cannot_retry_past_budget(client):
    import pytest

    from forge.runtime.ports import ProviderError
    run_id = new_run(client, max_tokens=100, max_retries=2)
    calls = []
    class Flaky:
        async def stream(self, **kwargs):
            calls.append(True)
            yield ModelDelta('partial')
            raise ProviderError('fake', 'unavailable', 'Temporary', retryable=True)
    with pytest.raises(ProviderError):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Flaky(), FinalPlanner()))
    assert len(calls) == 1
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'usage_unavailable'
    assert not any(e['type'] == 'model.retry' for e in trace(client, run_id, 'events'))


def test_arbitrary_provider_errors_are_not_persisted_or_logged(client, monkeypatch, caplog):
    import json
    import logging

    from forge.runtime.supervisor import logger
    secret = 'SYNTHETIC-raw-SDK-key-never-real'
    run_id = new_run(client)
    class Broken:
        async def complete(self, **kwargs):
            raise RuntimeError(secret)
    monkeypatch.setattr(logger, 'disabled', False)
    monkeypatch.setattr(logger, 'propagate', True)
    caplog.set_level(logging.ERROR, logger=logger.name)
    # _execute expects a claimed run.
    from sqlalchemy.orm import Session

    from forge.adapters.sqlite.repositories import RunRepository
    from forge.domain.runs import RunStatus
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        runs.transition(runs.get(run_id), RunStatus.RUNNING, 'run.started')
        session.commit()
    asyncio.run(client.app.state.supervisor._execute(run_id, Broken()))
    assert secret not in json.dumps(trace(client, run_id, 'steps'))
    assert secret not in json.dumps(trace(client, run_id, 'events'))
    assert secret not in caplog.text
    assert trace(client, run_id, 'steps')[0]['error']['message'] == 'run execution failed'


def test_native_tool_call_cannot_be_mistaken_for_final_text(client):
    from forge.runtime.ports import ToolCall
    run_id = new_run(client)
    class Native:
        async def stream(self, **kwargs):
            yield ModelResult('I will do it', 'fake', 'test', tool_calls=(ToolCall('shell', {}),))
    asyncio.run(execute_fake_run(client.app.state.database, run_id, Native(), FinalPlanner()))
    assert client.get(f'/api/v1/runs/{run_id}').json()['status'] == 'failed'
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'tool_disabled'
    assert trace(client, run_id, 'steps')[-1]['output']['action'] == 'tool'


def test_stream_rejects_multiple_final_results_and_closes(client):
    import pytest
    run_id = new_run(client)
    closed = []
    class Invalid:
        async def stream(self, **kwargs):
            try:
                yield ModelResult('one', 'fake', 'test')
                yield ModelResult('two', 'fake', 'test')
            finally:
                closed.append(True)
    with pytest.raises(ValueError, match='after final result'):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Invalid(), FinalPlanner()))
    assert closed == [True]
    assert trace(client, run_id, 'steps')[0]['status'] == 'failed'
    assert trace(client, run_id, 'steps')[0]['output'] is None


def test_retry_checks_step_budget_before_backoff(client):
    from forge.runtime.ports import ProviderError
    run_id = new_run(client, max_steps=1, timeout_seconds=1)
    calls = []
    class Fails:
        async def stream(self, **kwargs):
            calls.append(True)
            raise ProviderError('fake', 'unavailable', 'Temporary', retryable=True)
            yield
    asyncio.run(execute_fake_run(client.app.state.database, run_id, Fails(), FinalPlanner()))
    assert len(calls) == 1
    assert trace(client, run_id, 'events')[-1]['payload']['reason'] == 'max_steps'
    assert not any(e['type'] == 'model.retry' for e in trace(client, run_id, 'events'))
