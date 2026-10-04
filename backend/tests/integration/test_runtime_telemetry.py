"""Offline SQLite/runtime boundaries exported through the real OTel SDK."""
import asyncio
import hashlib

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from forge.observability.telemetry import configure_telemetry, use_provider
from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FakeProvider, FinalPlanner
from forge.runtime.ports import ModelResult


def new_run(client, **config):
    agent = client.post('/api/v1/agents', json={
        'name': 'Telemetry', 'instructions': 'SYNTHETIC-PROMPT', **config,
    }).json()
    return client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'Hello'}).json()['id']


def events(client, run_id):
    return client.get(f'/api/v1/runs/{run_id}/events').json()


@pytest.fixture
def capture():
    handle = configure_telemetry()
    exporter = InMemorySpanExporter()
    handle.provider.add_span_processor(SimpleSpanProcessor(exporter))
    with use_provider(handle.provider):
        yield exporter
    handle.close()


def test_model_planner_actual_timing_identity_and_safe_attributes(client, capture):
    run_id = new_run(client)

    class Provider:
        async def complete(self, **kwargs):
            assert capture.get_finished_spans() == ()
            await asyncio.sleep(0.005)
            return ModelResult('SYNTHETIC-OUTPUT', 'fake', 'test')

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    spans = capture.get_finished_spans()
    assert [s.name for s in spans] == ['forge.model', 'forge.planner']
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    for span, step in zip(spans, steps, strict=True):
        assert span.context.trace_id == int(hashlib.sha256(run_id.encode()).hexdigest()[:32], 16)
        assert span.context.span_id == int(hashlib.sha256(step['id'].encode()).hexdigest()[:16], 16)
        assert span.attributes['outcome'] == 'completed'
        assert span.attributes['duration_ms'] > 0
        assert 'SYNTHETIC' not in span.to_json()
    assert spans[0].attributes['duration_ms'] >= 5
    completed = next(e for e in events(client, run_id) if e['type'] == 'model.completed')
    assert completed['payload']['duration_ms'] >= 5
    assert completed['payload']['outcome'] == 'completed'


@pytest.mark.parametrize('mode', ['failure', 'timeout', 'retry', 'cancel'])
def test_model_terminal_and_retry_attempts_have_safe_durations(client, capture, mode):
    from forge.runtime.ports import ProviderError

    run_id = new_run(client, max_retries=1, timeout_seconds=0.03 if mode == 'timeout' else 5)
    calls = []

    class Provider:
        async def complete(self, **kwargs):
            calls.append(True)
            await asyncio.sleep(0.002)
            if mode == 'timeout':
                await asyncio.Event().wait()
            if mode == 'cancel':
                raise asyncio.CancelledError('SYNTHETIC-SECRET')
            if mode == 'failure':
                raise RuntimeError('SYNTHETIC-SECRET')
            if len(calls) == 1:
                raise ProviderError('fake', 'unavailable', 'SYNTHETIC-SECRET', retryable=True)
            return ModelResult('done', 'fake', 'test')

    if mode == 'retry':
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    else:
        error = {'failure': RuntimeError, 'timeout': TimeoutError, 'cancel': asyncio.CancelledError}[mode]
        with pytest.raises(error):
            asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    model_spans = [s for s in capture.get_finished_spans() if s.name == 'forge.model']
    assert len(model_spans) == (2 if mode == 'retry' else 1)
    expected = {'failure': 'failed', 'timeout': 'timeout', 'retry': 'failed', 'cancel': 'cancelled'}[mode]
    assert model_spans[0].attributes['outcome'] == expected
    for span in model_spans:
        assert span.attributes['duration_ms'] >= 2
        assert 'SYNTHETIC-SECRET' not in span.to_json()
        assert not span.events
    terminal = [e for e in events(client, run_id) if e['type'] in {'model.failed', 'model.cancelled'}]
    assert terminal
    assert terminal[0]['payload']['duration_ms'] >= 2
    assert terminal[0]['payload']['outcome'] == expected
    assert 'SYNTHETIC-SECRET' not in str(events(client, run_id))


@pytest.mark.parametrize('mode', ['success', 'deny', 'failure', 'timeout', 'cancel'])
def test_tool_policy_spans_time_actual_invocation_and_preserve_parent(client, capture, monkeypatch, mode):
    from forge.runtime.ports import ToolCall
    from forge.runtime.tools import Calculator

    run_id = new_run(client, tools=[] if mode == 'deny' else ['calculator@1'])

    async def execute(self, arguments, context):
        assert not any(s.name == 'forge.tool' for s in capture.get_finished_spans())
        assert any(s.name == 'forge.policy' for s in capture.get_finished_spans())
        await asyncio.sleep(0.002)
        if mode == 'timeout':
            await asyncio.Event().wait()
        if mode == 'cancel':
            raise asyncio.CancelledError('SYNTHETIC-SECRET')
        if mode == 'failure':
            raise RuntimeError('SYNTHETIC-SECRET')
        return {'value': 4}

    monkeypatch.setattr(Calculator, 'execute', execute)
    monkeypatch.setattr(Calculator, 'timeout_seconds', 0.02)

    class Provider:
        async def stream(self, **kwargs):
            yield (ModelResult('SYNTHETIC-OUTPUT', 'fake', 'test',
                               tool_calls=(ToolCall('calculator', {'expression': '2+2'}),))
                   if not kwargs['messages'] else ModelResult('done', 'fake', 'test'))

    if mode == 'cancel':
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    else:
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    tool, = [s for s in capture.get_finished_spans() if s.name == 'forge.tool']
    policy, = [s for s in capture.get_finished_spans() if s.name == 'forge.policy']
    assert policy.parent.span_id == tool.context.span_id
    assert policy.context.span_id != tool.context.span_id
    assert policy.attributes['step_id'] == tool.attributes['step_id']
    expected = {'success': 'completed', 'deny': 'deny', 'failure': 'failed', 'timeout': 'timeout', 'cancel': 'cancelled'}[mode]
    assert tool.attributes['outcome'] == expected
    assert 'SYNTHETIC' not in tool.to_json()
    assert 'SYNTHETIC' not in policy.to_json()
    assert not tool.events
    if mode != 'deny':
        assert tool.attributes['duration_ms'] >= 2
    if mode == 'cancel':
        cancelled = next(e for e in events(client, run_id) if e['type'] == 'tool.cancelled')
        assert cancelled['payload']['step_id'] == tool.attributes['step_id']
        assert cancelled['payload']['duration_ms'] >= 2
        assert events(client, run_id)[-1]['type'] == 'run.cancelled'


def test_supervisor_catch_logs_safe_explicit_fields_without_traceback(client, capture, caplog, monkeypatch):
    import logging

    from sqlalchemy.orm import Session

    from forge.adapters.sqlite.repositories import RunRepository
    from forge.domain.runs import RunStatus
    from forge.domain.trace import trace_id_for_run
    from forge.runtime.ports import ProviderError
    from forge.runtime.supervisor import logger

    run_id = new_run(client)
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        runs.transition(runs.get(run_id), RunStatus.RUNNING, 'run.started')
        session.commit()

    class Provider:
        async def complete(self, **kwargs):
            raise ProviderError('fake', 'unavailable', 'SYNTHETIC-SECRET')

    monkeypatch.setattr(logger, 'disabled', False)
    monkeypatch.setattr(logger, 'propagate', True)
    caplog.set_level(logging.ERROR, logger=logger.name)
    asyncio.run(client.app.state.supervisor._execute(run_id, Provider()))
    record, = [r for r in caplog.records if r.name == logger.name]
    assert record.exc_info is None
    assert record.run_id == run_id
    assert record.trace_id == trace_id_for_run(run_id)
    assert record.outcome == 'failed'
    assert record.code == 'unavailable'
    step, = client.get(f'/api/v1/runs/{run_id}/steps').json()
    assert record.step_id == step['id']
    assert record.span_id == hashlib.sha256(step['id'].encode()).hexdigest()[:16]
    assert 'SYNTHETIC' not in caplog.text


@pytest.mark.parametrize('mode', ['cancel', 'interrupted'])
def test_supervisor_terminal_events_identify_only_active_step_with_duration(client, mode):
    from datetime import timedelta

    from sqlalchemy.orm import Session

    from forge.adapters.sqlite.models import utc_now
    from forge.adapters.sqlite.repositories import RunRepository
    from forge.domain.runs import RunStatus
    from forge.domain.steps import StepKind, StepStatus

    run_id = new_run(client)
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        runs.transition(runs.get(run_id), RunStatus.RUNNING, 'run.started')
        old = runs.create_step(run_id=run_id, kind=StepKind.TOOL, input={}, status=StepStatus.FAILED)
        active = runs.create_step(run_id=run_id, kind=StepKind.MODEL, input={}, status=StepStatus.RUNNING)
        active.started_at = utc_now() - timedelta(milliseconds=20)
        active_id, old_id = active.id, old.id
        session.commit()
    supervisor = client.app.state.supervisor
    if mode == 'cancel':
        supervisor.cancel(run_id)
    else:
        supervisor.recover(resume=False)
    terminal = events(client, run_id)[-1]
    assert terminal['payload']['step_id'] == active_id
    assert terminal['payload']['step_id'] != old_id
    closed = next(e for e in events(client, run_id) if e['type'] == f'model.{"cancelled" if mode == "cancel" else "interrupted"}')
    assert closed['payload']['duration_ms'] >= 20
    assert closed['payload']['outcome'] == ('cancelled' if mode == 'cancel' else 'interrupted')


def test_response_budget_stop_links_model_not_previous_tool(client):
    from forge.runtime.ports import ModelUsage, ToolCall

    run_id = new_run(client, max_tokens=3, tools=['calculator@1'])

    class Provider:
        async def stream(self, **kwargs):
            if not kwargs['messages']:
                yield ModelResult('call', 'fake', 'test', usage=ModelUsage(0, 1, 1),
                                  tool_calls=(ToolCall('calculator', {'expression': '1/0'}),))
            else:
                yield ModelResult('done', 'fake', 'test', usage=ModelUsage(2, 1, 3))

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    failed_tool, = [s for s in steps if s['kind'] == 'tool' and s['status'] == 'failed']
    terminal = events(client, run_id)[-1]
    assert terminal['payload']['step_id'] == steps[-1]['id']
    assert terminal['payload']['step_id'] != failed_tool['id']
    assert terminal['payload']['reason'] == 'max_tokens'


@pytest.mark.parametrize('mode', ['failure', 'timeout'])
def test_synchronous_planner_has_safe_failure_and_real_timing(client, capture, mode):
    import time


    run_id = new_run(client)

    class Planner:
        def decide(self, response):
            time.sleep(0.2 if mode == 'timeout' else 0.025)
            if mode == 'failure':
                raise RuntimeError('SYNTHETIC-SECRET')
            return FinalPlanner().decide(response)

    with pytest.raises(RuntimeError if mode == 'failure' else TimeoutError):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider(), Planner(),
                                    timeout_seconds=0.1 if mode == 'timeout' else 5))
    span, = [s for s in capture.get_finished_spans() if s.name == 'forge.planner']
    assert span.attributes['outcome'] == ('failed' if mode == 'failure' else 'timeout')
    assert span.attributes['duration_ms'] >= 25
    assert 'SYNTHETIC' not in span.to_json()
    event = next(e for e in events(client, run_id) if e['type'] == 'planner.failed')
    assert event['payload']['duration_ms'] >= 25


@pytest.mark.parametrize('kind', ['planner', 'policy'])
def test_synchronous_boundary_cancellation_closes_exact_active_step(client, capture, monkeypatch, kind):
    from forge.runtime.policy import ToolPolicy
    from forge.runtime.ports import ToolCall

    run_id = new_run(client, tools=['calculator@1'])

    def cancel(*args):
        raise asyncio.CancelledError('SYNTHETIC-SECRET')

    class Planner:
        decide = cancel

    class Provider:
        async def complete(self, **kwargs):
            return ModelResult('call', 'fake', 'test',
                               tool_calls=(ToolCall('calculator', {'expression': '2+2'}),)
                               if kind == 'policy' else ())

    if kind == 'policy':
        monkeypatch.setattr(ToolPolicy, 'evaluate', cancel)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), Planner()))
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    assert steps[-1]['status'] == 'cancelled'
    assert events(client, run_id)[-1]['type'] == 'run.cancelled'
    assert events(client, run_id)[-1]['payload']['step_id'] == steps[-1]['id']
    span = next(s for s in capture.get_finished_spans() if s.name == f'forge.{kind}')
    assert span.attributes['outcome'] == 'cancelled'
    assert span.attributes['duration_ms'] > 0
    assert 'SYNTHETIC-SECRET' not in span.to_json()


def test_policy_exception_closes_exact_tool_step_not_successful_planner(client, capture, monkeypatch):
    from forge.runtime.policy import ToolPolicy
    from forge.runtime.ports import ToolCall

    run_id = new_run(client, tools=['calculator@1'])

    def evaluate(*args):
        raise RuntimeError('SYNTHETIC-SECRET')

    monkeypatch.setattr(ToolPolicy, 'evaluate', evaluate)

    class Provider:
        async def complete(self, **kwargs):
            return ModelResult('call', 'fake', 'test', tool_calls=(ToolCall('calculator', {'expression': '2+2'}),))

    with pytest.raises(RuntimeError):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    assert [(s['kind'], s['status']) for s in steps] == [('model', 'completed'), ('planner', 'completed'), ('tool', 'failed')]
    assert events(client, run_id)[-1]['payload']['step_id'] == steps[-1]['id']
    policy, tool = capture.get_finished_spans()[-2:]
    assert policy.name == 'forge.policy'
    assert tool.name == 'forge.tool'
    assert policy.attributes['outcome'] == tool.attributes['outcome'] == 'failed'
    assert 'SYNTHETIC-SECRET' not in str(events(client, run_id))


def test_stream_preview_has_bounded_memory_independent_final_response(client):
    from forge.runtime.ports import ModelDelta

    run_id = new_run(client)
    final = 'x' * (2 * 1024 * 1024)

    class Provider:
        async def stream(self, **kwargs):
            for offset in range(0, len(final), 1024):
                yield ModelDelta(final[offset:offset + 1024])
            yield ModelResult(final, 'fake', 'test')

    asyncio.run(execute_fake_run(client.app.state.database, run_id, Provider(), FinalPlanner()))
    deltas = [e for e in events(client, run_id) if e['type'] == 'model.delta']
    assert len(deltas) <= 128
    assert sum(len(e['payload']['text']) for e in deltas) == 1024 * 1024
    model = client.get(f'/api/v1/runs/{run_id}/steps').json()[0]
    assert model['output']['text'] == final


def test_expired_approval_budget_identifies_pending_step_without_inventing_span(client, capture):
    from uuid import uuid4

    from sqlalchemy.orm import Session

    from forge.adapters.sqlite.models import ApprovalRecord
    from forge.adapters.sqlite.repositories import RunRepository
    from forge.domain.runs import RunStatus
    from forge.domain.steps import StepKind, StepStatus
    from forge.runtime.ports import ToolCall
    from forge.runtime.tool_execution import execute_calls

    run_id = new_run(client, tools=['calculator@1'])
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        runs.transition(runs.get(run_id), RunStatus.RUNNING, 'run.started')
        step = runs.create_step(run_id=run_id, kind=StepKind.TOOL, input={'name': 'calculator'},
                                status=StepStatus.RUNNING)
        approval = ApprovalRecord(id=str(uuid4()), run_id=run_id, step_id=step.id,
                                  tool_name='calculator', tool_version='1', arguments={}, status='approved')
        session.add(approval)
        pending = {'step_id': step.id, 'approval_id': approval.id}
        session.commit()

    async def expired():
        await execute_calls(client.app.state.database, run_id,
                            (ToolCall('calculator', {'expression': '2+2'}),), (), (), None, None,
                            8, asyncio.get_running_loop().time() - 1, [], None, pending)

    asyncio.run(expired())
    terminal = events(client, run_id)[-1]
    assert terminal['payload']['step_id'] == pending['step_id']
    assert terminal['payload']['reason'] == 'timeout'
    assert capture.get_finished_spans() == ()
