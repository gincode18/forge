import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.adapters.sqlite.models import ArtifactRecord, RunRecord, StepRecord
from forge.adapters.sqlite.repositories import RunRepository
from forge.api.app import create_app
from forge.config import Settings
from forge.domain.runs import RunStatus
from forge.domain.steps import StepKind, StepStatus


def old_run(client: TestClient, status=RunStatus.COMPLETED):
    agent = client.post('/api/v1/agents', json={'name': 'Retention', 'instructions': 'Keep.'}).json()
    run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'private input'}).json()['id']
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        run = runs.get(run_id)
        runs.transition(run, RunStatus.RUNNING, 'run.started')
        step = runs.create_step(run_id=run_id, kind=StepKind.MODEL, input={'instructions': 'private instructions', 'input': 'private input'}, status=StepStatus.COMPLETED)
        step.output = {'text': 'private output', 'usage': {'input_tokens': 2, 'output_tokens': 3, 'total_tokens': 5}, 'latency_ms': 7}
        runs.append_event(run_id, 'model.completed', {'step_id': step.id, **step.output})
        if status == RunStatus.COMPLETED:
            runs.transition(run, status, 'run.completed', {'result': 'private output'})
        run.updated_at = datetime.now(UTC) - timedelta(days=40)
        session.commit()
    return run_id


def test_retention_defaults_preserve_everything(client):
    from forge.application.retention import apply_retention
    run_id = old_run(client)
    result = apply_retention(client.app.state.database, Settings(_env_file=None, data_dir=client.app.state.settings.data_dir))
    assert result['events_compacted'] == 0
    assert client.get(f'/api/v1/runs/{run_id}').json()['input'] == 'private input'


def test_event_retention_preserves_envelopes_metrics_and_sequence(client):
    from forge.application.retention import apply_retention
    run_id = old_run(client)
    before = client.get(f'/api/v1/runs/{run_id}/events').json()
    settings = Settings(_env_file=None, data_dir=client.app.state.settings.data_dir, event_retention_days=30)
    result = apply_retention(client.app.state.database, settings)
    after = client.get(f'/api/v1/runs/{run_id}/events').json()
    assert result['events_compacted'] == 2
    assert [e['id'] for e in before] == [e['id'] for e in after]
    assert [e['sequence'] for e in before] == [e['sequence'] for e in after]
    completed = next(e for e in after if e['type'] == 'model.completed')
    assert completed['payload']['usage']['total_tokens'] == 5
    assert completed['payload']['retained'] is False
    assert 'private output' not in str(after)
    assert apply_retention(client.app.state.database, settings)['events_compacted'] == 0


def test_message_retention_skips_active_runs_and_preserves_metrics(client):
    from forge.application.retention import apply_retention
    terminal = old_run(client)
    active = old_run(client, RunStatus.RUNNING)
    settings = Settings(_env_file=None, data_dir=client.app.state.settings.data_dir, message_retention_days=30)
    apply_retention(client.app.state.database, settings)
    assert client.get(f'/api/v1/runs/{terminal}').json()['input'] == '[expired by retention]'
    assert client.get(f'/api/v1/runs/{active}').json()['input'] == 'private input'
    with Session(client.app.state.database.engine) as session:
        step = session.scalar(select(StepRecord).where(StepRecord.run_id == terminal))
        assert step.output['usage']['total_tokens'] == 5
        assert step.input == {'retained': False, 'reason': 'retention_expired'}
        assert 'private' not in str(step.output)
        assert session.get(RunRecord, active).status == 'running'


def test_message_retention_removes_builtin_tool_content_from_step_history(client):
    from forge.application.retention import EXPIRED, apply_retention
    from forge.domain.tools import ReadOutput, SubprocessOutput

    run_id = old_run(client)
    outputs = [
        ('filesystem_read', {'path': 'private.txt'},
         ReadOutput(content='private file content').model_dump()),
        ('subprocess', {'argv': ['/usr/bin/false']},
         SubprocessOutput(stdout='private stdout', stderr='private stderr', returncode=1).model_dump()),
        ('subprocess', {'argv': ['/usr/bin/false']}, {'error': 'tool_execution_failed'}),
    ]
    with Session(client.app.state.database.engine) as session:
        runs = RunRepository(session)
        for index, (name, arguments, output) in enumerate(outputs):
            failed = 'error' in output
            step = runs.create_step(
                run_id=run_id, kind=StepKind.TOOL,
                input={'name': name, 'arguments': arguments, 'call_id': f'call-{index}'},
                status=StepStatus.FAILED if failed else StepStatus.COMPLETED,
            )
            step.output = output
            if failed:
                step.error = {'type': 'ToolExecutionError', 'code': output['error'], 'message': output['error']}
            step.started_at = datetime.now(UTC) - timedelta(days=40, seconds=1)
            step.finished_at = datetime.now(UTC) - timedelta(days=40)
            runs.append_event(run_id, 'tool.failed' if failed else 'tool.completed', {
                'step_id': step.id, 'tool_name': name, 'tool_version': '1',
                'call_id': f'call-{index}', 'output': output, 'duration_ms': 7,
            })
        session.commit()

    before = client.get(f'/api/v1/runs/{run_id}/steps').json()
    settings = Settings(_env_file=None, data_dir=client.app.state.settings.data_dir, message_retention_days=30)
    apply_retention(client.app.state.database, settings)
    after = client.get(f'/api/v1/runs/{run_id}/steps').json()
    assert [step['output'] for step in after[1:]] == [
        EXPIRED, {'returncode': 1, **EXPIRED}, {'error': 'tool_execution_failed'},
    ]
    for original, compacted in zip(before, after, strict=True):
        assert compacted['input'] == EXPIRED
        assert {key: value for key, value in compacted.items() if key not in ('input', 'output')} == {
            key: value for key, value in original.items() if key not in ('input', 'output')
        }
    assert after[0]['output'] == {**EXPIRED, 'usage': before[0]['output']['usage'], 'latency_ms': 7}
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    tool_events = [event for event in events if event['type'] in ('tool.completed', 'tool.failed')]
    assert all(event['payload']['duration_ms'] == 7 for event in tool_events)
    assert [event['payload']['call_id'] for event in tool_events] == ['call-0', 'call-1', 'call-2']
    assert tool_events[-1]['payload']['output'] == {'error': 'tool_execution_failed'}
    assert 'private' not in str(after) + str(events)
    assert apply_retention(client.app.state.database, settings)['messages_compacted'] == 0


def test_artifact_retention_removes_only_recorded_terminal_files(client, tmp_path):
    from forge.application.retention import apply_retention
    run_id = old_run(client)
    root = tmp_path / 'workspaces' / run_id
    root.mkdir(parents=True)
    (root / 'recorded.txt').write_text('expired artifact')
    (root / 'unrecorded.txt').write_text('leave alone')
    outside = tmp_path / 'outside.txt'
    outside.write_text('outside')
    (root / 'unsafe.txt').symlink_to(outside)
    with Session(client.app.state.database.engine) as session:
        session.add_all([ArtifactRecord(id='recorded', run_id=run_id, path='recorded.txt', size_bytes=16, media_type='text/plain'), ArtifactRecord(id='unsafe', run_id=run_id, path='unsafe.txt', size_bytes=7, media_type='text/plain')])
        session.commit()
    settings = Settings(_env_file=None, data_dir=tmp_path, artifact_retention_days=30)
    result = apply_retention(client.app.state.database, settings)
    assert result['artifacts_expired'] == 1
    assert result['artifact_errors'] == 1
    assert not (root / 'recorded.txt').exists()
    assert (root / 'unrecorded.txt').read_text() == 'leave alone'
    assert outside.read_text() == 'outside'
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    assert any(e['type'] == 'artifact.expired' and e['payload']['id'] == 'recorded' for e in events)
    assert apply_retention(client.app.state.database, settings)['artifacts_expired'] == 0


def test_retention_dry_run_and_expired_artifact_api(client, tmp_path):
    from forge.application.retention import apply_retention
    run_id = old_run(client)
    root = tmp_path / 'workspaces' / run_id
    root.mkdir(parents=True)
    (root / 'file.txt').write_text('content')
    with Session(client.app.state.database.engine) as session:
        session.add(ArtifactRecord(id='download', run_id=run_id, path='file.txt', size_bytes=7, media_type='text/plain'))
        session.commit()
    settings = Settings(_env_file=None, data_dir=tmp_path, artifact_retention_days=30, message_retention_days=30)
    preview = apply_retention(client.app.state.database, settings, dry_run=True)
    assert preview['artifacts_expired'] == 1
    assert (root / 'file.txt').exists()
    assert client.get(f'/api/v1/runs/{run_id}').json()['input'] == 'private input'
    apply_retention(client.app.state.database, settings)
    artifacts = client.get(f'/api/v1/runs/{run_id}/artifacts').json()
    assert artifacts[0]['expired'] is True
    assert client.get(f'/api/v1/runs/{run_id}/artifacts/download').status_code == 410


def test_configured_retention_is_applied_at_startup(client):
    run_id = old_run(client)
    settings = Settings(_env_file=None, data_dir=client.app.state.settings.data_dir, message_retention_days=30)
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(f'/api/v1/runs/{run_id}').json()['input'] == '[expired by retention]'


def test_retention_command_previews_by_default_and_requires_apply(client):
    run_id = old_run(client)
    env = {**os.environ, 'FORGE_DATA_DIR': str(client.app.state.settings.data_dir), 'FORGE_MESSAGE_RETENTION_DAYS': '30'}
    command = [sys.executable, '-m', 'forge.application.retention']
    preview = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
    assert json.loads(preview.stdout)['dry_run'] is True
    assert client.get(f'/api/v1/runs/{run_id}').json()['input'] == 'private input'
    applied = subprocess.run([*command, '--apply'], env=env, capture_output=True, text=True, check=True)
    assert json.loads(applied.stdout)['dry_run'] is False
    assert client.get(f'/api/v1/runs/{run_id}').json()['input'] == '[expired by retention]'


def test_overlapping_retention_policies_have_exact_dry_run_counts(client):
    from forge.application.retention import apply_retention
    old_run(client)
    settings = Settings(_env_file=None, data_dir=client.app.state.settings.data_dir,
                        event_retention_days=30, message_retention_days=30)
    preview = apply_retention(client.app.state.database, settings, dry_run=True)
    applied = apply_retention(client.app.state.database, settings)
    assert preview == applied
