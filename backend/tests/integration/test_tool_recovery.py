"""Crash boundaries at approval dispatch must not replay side effects."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_tools_phase_four import launch, wait

from forge.adapters.sqlite.models import RunCheckpointRecord
from forge.api.app import create_app
from forge.application.approvals import resolve_approval
from forge.config import Settings
from forge.runtime.tools import FilesystemWrite


def test_resolved_approval_before_dispatch_survives_restart(tmp_path, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        # Crash window: decision committed, but supervisor has not dispatched it.
        resolve_approval(client.app.state.database, approval['id'], True)
    with TestClient(create_app(settings)) as client:
        wait(client, run_id, 'completed')
        artifacts = client.get(f'/api/v1/runs/{run_id}/artifacts').json()
        assert len(artifacts) == 1
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
        assert len([e for e in events if e['type'] == 'tool.started']) == 1


def test_started_approved_tool_is_interrupted_not_replayed(tmp_path, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        resolve_approval(client.app.state.database, approval['id'], True)
        with Session(client.app.state.database.engine) as session:
            checkpoint = session.get(RunCheckpointRecord, run_id)
            checkpoint.payload = {**checkpoint.payload, 'execution_started': True}
            session.commit()
    with TestClient(create_app(settings)) as client:
        assert client.get(f'/api/v1/runs/{run_id}').json()['status'] == 'interrupted'
        assert client.get(f'/api/v1/runs/{run_id}/artifacts').json() == []
        assert not (tmp_path / 'workspaces' / run_id / 'answer.txt').exists()


def test_dispatch_marks_checkpoint_before_side_effect(client, monkeypatch):
    observed = []
    original = FilesystemWrite.execute

    async def inspect(self, arguments, context):
        with Session(client.app.state.database.engine) as session:
            checkpoint = session.get(RunCheckpointRecord, context.run_id)
            observed.append(checkpoint.payload.get('execution_started'))
        return await original(self, arguments, context)

    monkeypatch.setattr(FilesystemWrite, 'execute', inspect)
    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
    wait(client, run_id, 'completed')
    assert observed == [True]
