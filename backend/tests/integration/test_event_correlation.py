"""Durable envelopes, semantic causality, and committed metadata-only logs."""
import asyncio
import hashlib

from sqlalchemy.orm import Session

from forge.adapters.sqlite.repositories import RunRepository
from forge.runtime.engine import execute_fake_run
from forge.runtime.fake import FakeProvider, FinalPlanner


def launch(client):
    agent = client.post('/api/v1/agents', json={'name': 'Trace', 'instructions': 'private instruction'}).json()
    return client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'private input'}, headers={'X-Request-ID': 'unchanged-request'}).json()['id']


def test_version_two_envelope_matches_steps_and_semantic_predecessors(client):
    run_id = launch(client)
    asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider(), FinalPlanner()))
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    steps = {s['id']: s for s in client.get(f'/api/v1/runs/{run_id}/steps').json()}
    by_type = {e['type']: e for e in events}
    for event in events:
        assert event['schema_version'] == 2
        assert event['correlation_id'] == run_id
        assert event['trace_id'] == hashlib.sha256(run_id.encode()).hexdigest()[:32]
        if event['step_id']:
            step = steps[event['step_id']]
            assert event['span_id'] == step['span_id'] == hashlib.sha256(step['id'].encode()).hexdigest()[:16]
            assert step['correlation_id'] == run_id
            assert step['trace_id'] == event['trace_id']
        else:
            assert event['span_id'] is None
    assert by_type['run.created']['payload']['request_id']
    assert by_type['run.created']['payload']['request_id'] != run_id
    assert by_type['run.created']['causation_id'] is None
    for child, parent in [('run.started', 'run.created'), ('model.requested', 'run.started'), ('model.completed', 'model.requested'), ('planner.started', 'model.completed'), ('planner.decided', 'planner.started'), ('run.completed', 'planner.decided')]:
        assert by_type[child]['causation_id'] == by_type[parent]['id']
    assert steps[by_type['model.requested']['step_id']]['causation_id'] == by_type['run.started']['id']
    # A chunk is not the causal source of the final model outcome.
    assert by_type['model.completed']['causation_id'] != by_type['model.delta']['id']


def test_tool_approval_causality_survives_restart(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from test_tools_phase_four import launch as launch_tools
    from test_tools_phase_four import wait

    from forge.api.app import create_app
    from forge.config import Settings

    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        run_id = launch_tools(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"private content"}}]}')
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        before = client.get(f'/api/v1/runs/{run_id}/events').json()
    with TestClient(create_app(settings)) as client:
        assert client.get(f'/api/v1/runs/{run_id}/events').json() == before
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
        wait(client, run_id, 'completed')
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
    by_type = {e['type']: e for e in events if e['type'] not in {'model.requested', 'planner.decided'}}
    requested = next(e for e in events if e['type'] == 'tool.requested')
    planner = next(e for e in events if e['type'] == 'planner.decided')
    assert requested['causation_id'] == planner['id']
    for child, parent in [('tool.policy', 'tool.requested'), ('approval.requested', 'tool.policy'), ('approval.resolved', 'approval.requested'), ('tool.started', 'approval.resolved'), ('tool.completed', 'tool.started'), ('artifact.created', 'tool.completed'), ('run.paused', 'approval.requested'), ('run.resumed', 'approval.resolved')]:
        assert by_type[child]['causation_id'] == by_type[parent]['id']
    assert by_type['approval.resolved']['step_id'] == approval['step_id']
    assert by_type['artifact.created']['step_id'] == approval['step_id']
    next_model = [e for e in events if e['type'] == 'model.requested'][-1]
    assert next_model['causation_id'] == by_type['tool.completed']['id']


def test_terminal_failure_uses_explicit_step_not_last_failed_tool(client):
    from forge.domain.steps import StepKind
    run_id = launch(client)
    with Session(client.app.state.database.engine, expire_on_commit=False) as session:
        runs = RunRepository(session)
        tool = runs.create_step(run_id=run_id, kind=StepKind.TOOL, input={})
        model = runs.create_step(run_id=run_id, kind=StepKind.MODEL, input={})
        runs.append_event(run_id, 'model.requested', {'step_id': model.id})
        failed = runs.append_event(run_id, 'model.failed', {'step_id': model.id})
        runs.append_event(run_id, 'tool.failed', {'step_id': tool.id, 'tool_name': 'calculator', 'tool_version': '1', 'call_id': 'other', 'output': {'error': 'private error'}, 'duration_ms': 0})
        terminal = runs.append_event(run_id, 'run.failed', {'step_id': model.id, 'reason': 'error'})
        assert terminal.causation_id == failed.id
        boundary = runs.append_event(run_id, 'run.failed', {'reason': 'max_steps'})
        assert boundary.step_id is None
        assert boundary.causation_id is None or boundary.causation_id != runs.events(run_id)[-3].id
        session.commit()


def test_structured_logs_only_emit_committed_metadata(client, caplog):
    import json
    import logging

    caplog.set_level(logging.INFO, logger='forge.events')
    run_id = launch(client)
    created = client.get(f'/api/v1/runs/{run_id}/events').json()[0]
    assert any(json.loads(record.message)['event_id'] == created['id'] for record in caplog.records if record.name == 'forge.events')
    caplog.clear()
    with Session(client.app.state.database.engine, expire_on_commit=False) as session:
        runs = RunRepository(session)
        rolled_back = runs.append_event(run_id, 'model.delta', {'text': 'DO NOT LOG PRIVATE TEXT'})
        assert not caplog.records
        session.rollback()
        assert not caplog.records
        committed = runs.append_event(run_id, 'run.failed', {'error': 'DO NOT LOG EXCEPTION', 'duration_ms': 12.5})
        assert not caplog.records
        session.commit()
    records = [json.loads(record.message) for record in caplog.records if record.name == 'forge.events']
    assert len(records) == 1
    log = records[0]
    assert log['event_id'] == committed.id
    assert log['event_id'] != rolled_back.id
    assert log['duration_ms'] == 12.5
    assert log['outcome'] == 'failed'
    assert set(log) == {'event_id', 'event_type', 'run_id', 'step_id', 'correlation_id', 'causation_id', 'trace_id', 'span_id', 'outcome', 'duration_ms'}
    assert 'PRIVATE' not in caplog.text and 'EXCEPTION' not in caplog.text


def test_nested_rollback_never_logs_discarded_events(client, caplog):
    import json
    import logging

    run_id = launch(client)
    caplog.set_level(logging.INFO, logger='forge.events')
    caplog.clear()
    with Session(client.app.state.database.engine, expire_on_commit=False) as session:
        runs = RunRepository(session)
        outer = runs.append_event(run_id, 'run.started', {})
        nested = session.begin_nested()
        runs.append_event(run_id, 'model.delta', {'text': 'private'})
        nested.rollback()
        assert not caplog.records
        nested = session.begin_nested()
        inner = runs.append_event(run_id, 'planner.started', {})
        nested.commit()
        assert not caplog.records
        session.commit()
    assert [json.loads(r.message)['event_id'] for r in caplog.records if r.name == 'forge.events'] == [outer.id, inner.id]


def test_artifact_expiry_schema_and_link(client):
    from forge.adapters.sqlite.models import ArtifactRecord
    from forge.api.schemas import ArtifactResponse

    run_id = launch(client)
    with Session(client.app.state.database.engine, expire_on_commit=False) as session:
        artifact = ArtifactRecord(id='artifact', run_id=run_id, path='answer.txt', size_bytes=1, media_type='text/plain')
        session.add(artifact)
        session.flush()
        assert ArtifactResponse.model_validate(artifact).expired is False
        runs = RunRepository(session)
        created = runs.append_event(run_id, 'artifact.created', {'id': artifact.id, 'path': artifact.path})
        expired = runs.append_event(run_id, 'artifact.expired', {'id': artifact.id, 'run_id': run_id, 'path': artifact.path, 'reason': 'retention_expired'})
        assert expired.causation_id == created.id
        session.commit()


def test_explicit_causation_is_validated_and_not_added_to_tool_payload(client):
    import pytest

    from forge.domain.steps import StepKind

    run_id = launch(client)
    other_run = launch(client)
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        source = runs.events(run_id)[0]
        foreign_source = runs.events(other_run)[0]
        step = runs.create_step(run_id=run_id, kind=StepKind.TOOL, input={})
        payload = {'step_id': step.id, 'tool_name': 'calculator', 'tool_version': '1', 'call_id': 'call', 'arguments': {}}
        requested = runs.append_event(run_id, 'tool.requested', payload, causation_id=source.id)
        assert requested.causation_id == source.id
        assert requested.payload == payload
        with pytest.raises(ValueError, match='causation'):
            runs.append_event(run_id, 'unknown', {}, causation_id=foreign_source.id)
        with pytest.raises(ValueError, match='causation'):
            runs.append_event(run_id, 'unknown', {}, causation_id='missing')
        unlinked = runs.append_event(run_id, 'unknown', {})
        assert unlinked.causation_id is None


def test_cancelled_step_and_terminal_have_known_causal_boundaries(client):
    from test_tools_phase_four import launch as launch_tools
    from test_tools_phase_four import wait

    run_id = launch_tools(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"private"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    assert client.post(f'/api/v1/runs/{run_id}/cancel').status_code == 200
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    by_type = {e['type']: e for e in events}
    assert by_type['tool.cancelled']['causation_id'] == by_type['approval.requested']['id']
    assert by_type['run.cancelled']['causation_id'] == by_type['tool.cancelled']['id']
    assert by_type['approval.cancelled']['causation_id'] == by_type['approval.requested']['id']
    assert by_type['run.cancelled']['step_id'] == by_type['tool.cancelled']['step_id']


def test_tool_failure_does_not_invent_execution_from_allow_policy(client):
    from forge.domain.steps import StepKind

    run_id = launch(client)
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        step = runs.create_step(run_id=run_id, kind=StepKind.TOOL, input={})
        boundary = {'step_id': step.id, 'tool_name': 'calculator', 'tool_version': '1', 'call_id': 'call'}
        runs.append_event(run_id, 'tool.policy', {**boundary, 'decision': 'allow', 'reason': 'enabled'})
        failed = runs.append_event(run_id, 'tool.failed', {**boundary, 'output': {'error': 'timeout'}, 'duration_ms': 0})
        assert failed.causation_id is None
        policy = runs.append_event(run_id, 'tool.policy', {**boundary, 'decision': 'deny', 'reason': 'disabled'})
        denied = runs.append_event(run_id, 'tool.denied', {**boundary, 'output': {'error': 'disabled'}, 'duration_ms': 0})
        assert denied.causation_id == policy.id


def test_trace_identity_contract():
    from forge.domain.trace import span_id_for_step, trace_id_for_run
    assert trace_id_for_run('run') == hashlib.sha256(b'run').hexdigest()[:32]
    assert span_id_for_step('step') == hashlib.sha256(b'step').hexdigest()[:16]
