"""Offline acceptance edges around approvals, snapshots, and artifacts."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_tools_phase_four import launch, wait

from forge.adapters.sqlite.models import ArtifactRecord, RunCheckpointRecord
from forge.api.app import create_app
from forge.application.approvals import resolve_approval
from forge.config import Settings
from forge.domain.runs import InvalidRunTransition
from forge.runtime.ports import ModelResult, ModelUsage, ToolCall


@pytest.mark.parametrize('approved', [True, False])
def test_concurrent_resolution_has_one_durable_winner(client, approved):
    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    barrier = Barrier(2)

    def resolve(value):
        barrier.wait()
        try:
            return resolve_approval(client.app.state.database, approval['id'], value).status
        except InvalidRunTransition:
            return 'conflict'

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(resolve, approved), pool.submit(resolve, not approved)
        outcomes = [a.result(), b.result()]
    assert outcomes.count('conflict') == 1
    client.portal.call(client.app.state.supervisor.start, run_id)
    wait(client, run_id, 'completed')
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    assert len([e for e in events if e['type'] == 'approval.resolved']) == 1
    assert len([e for e in events if e['type'] == 'tool.started']) <= 1


@pytest.mark.parametrize('budget,reason', [({'max_tokens': 10}, 'max_tokens'), ({'max_cost_usd': .00001}, 'max_cost_usd')])
def test_restart_preserves_accounting_and_version_snapshot(tmp_path, monkeypatch, budget, reason):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path)

    class First:
        async def stream(self, **kwargs):
            yield ModelResult('', 'fake', 'test', usage=ModelUsage(4, 4, 8), tool_calls=(ToolCall('filesystem_write', {'path': 'answer.txt', 'content': '4'}, 'write'),))

    class Second:
        async def stream(self, **kwargs):
            assert kwargs['max_output_tokens'] == (2 if reason == 'max_tokens' else 2048)
            yield ModelResult('done', 'fake', 'test', usage=ModelUsage(3, 1, 4))

    config = {'instructions': 'tools', 'tools': ['filesystem_write@1'], 'max_steps': 12,
              'input_cost_per_million': 1, 'output_cost_per_million': 1, **budget}
    with TestClient(create_app(settings)) as client:
        agent = client.post('/api/v1/agents', json={'name': 'snapshot', **config}).json()
        run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'write'}).json()['id']
        client.app.state.supervisor.provider = First()
        assert client.post(f'/api/v1/runs/{run_id}/start').status_code == 202
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        with Session(client.app.state.database.engine) as session:
            checkpoint = session.get(RunCheckpointRecord, run_id)
            assert checkpoint.payload['accounting'] == [8, .000008, True]
            remaining = checkpoint.payload['remaining_seconds']
        assert client.post(f"/api/v1/agents/{agent['id']}/versions", json={**config, 'tools': [], 'max_tokens': 1000, 'max_cost_usd': 1}).status_code == 201
    with TestClient(create_app(settings)) as client:
        client.app.state.supervisor.provider = Second()
        with Session(client.app.state.database.engine) as session:
            assert session.get(RunCheckpointRecord, run_id).payload['remaining_seconds'] == remaining
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
        wait(client, run_id, 'failed')
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
        assert events[-1]['payload']['reason'] == reason
        completed = [e for e in events if e['type'] == 'model.completed']
        assert completed[-1]['payload']['total_tokens'] == 12
        assert completed[-1]['payload']['total_cost_usd'] == pytest.approx(.000012)
        assert len(client.get(f'/api/v1/runs/{run_id}/artifacts').json()) == 1


def test_cancelling_approved_running_tool_closes_step_and_process(tmp_path, monkeypatch):
    import sys
    import time
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    script = 'import time; open("ready", "w").write("ready"); time.sleep(.3); open("escaped.txt", "w").write("alive"); time.sleep(10)'
    argv = [sys.executable, '-c', script]
    settings = Settings(_env_file=None, data_dir=tmp_path, subprocess_allowlist=[argv])
    with TestClient(create_app(settings)) as client:
        run_id = launch(client, ['subprocess@1'], json.dumps({'forge_script': [{'name': 'subprocess', 'arguments': {'argv': argv}}]}))
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
        workspace = tmp_path / 'workspaces' / run_id
        for _ in range(100):
            if (workspace / 'ready').exists():
                break
            time.sleep(.005)
        assert (workspace / 'ready').exists()
        assert client.post(f'/api/v1/runs/{run_id}/cancel').json()['status'] == 'cancelled'
        time.sleep(.4)
        assert not (workspace / 'escaped.txt').exists()
        steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
        assert steps[-1]['status'] == 'cancelled'
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
        assert any(e['type'] == 'tool.cancelled' for e in events)
        assert not any(e['type'] == 'tool.completed' for e in events)
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 409


@pytest.mark.parametrize('component', ['file', 'workspace_ancestor'])
def test_artifact_download_rejects_symlink_swap_after_validation(client, tmp_path, monkeypatch, component):
    import forge.runtime.tools as tools_module

    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True})
    wait(client, run_id, 'completed')
    artifact = client.get(f'/api/v1/runs/{run_id}/artifacts').json()[0]
    root = client.app.state.settings.resolved_data_dir / 'workspaces'
    outside = tmp_path / 'outside'
    (outside / run_id).mkdir(parents=True)
    external = outside / run_id / 'answer.txt'
    external.write_text('never disclose')
    original = tools_module.scoped_path

    def swap(workspace, value):
        path = original(workspace, value)
        if component == 'file':
            path.unlink()
            path.symlink_to(external)
        else:
            root.rename(root.with_name('original-workspaces'))
            root.symlink_to(outside, target_is_directory=True)
        return path

    monkeypatch.setattr(tools_module, 'scoped_path', swap)
    response = client.get(f"/api/v1/runs/{run_id}/artifacts/{artifact['id']}")
    assert response.status_code == 404
    assert b'never disclose' not in response.content


@pytest.mark.parametrize('tamper', ['traversal', 'symlink', 'missing', 'oversize', 'hardlink'])
def test_artifact_download_revalidates_record_and_filesystem(client, tmp_path, tamper):
    run_id = launch(client, ['filesystem_write@1'], json.dumps({'forge_script': [{'name': 'filesystem_write', 'arguments': {'path': 'answer.txt', 'content': '4'}}]}))
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True})
    wait(client, run_id, 'completed')
    artifact = client.get(f'/api/v1/runs/{run_id}/artifacts').json()[0]
    file = client.app.state.settings.resolved_data_dir / 'workspaces' / run_id / 'answer.txt'
    outside = tmp_path / 'outside.txt'
    outside.write_text('never disclose')
    if tamper == 'traversal':
        with Session(client.app.state.database.engine) as session:
            session.get(ArtifactRecord, artifact['id']).path = '../../../outside.txt'
            session.commit()
    elif tamper == 'oversize':
        file.write_bytes(b'x' * 32769)
    else:
        file.unlink()
        if tamper == 'symlink':
            file.symlink_to(outside)
        elif tamper == 'hardlink':
            import os
            os.link(outside, file)
    response = client.get(f"/api/v1/runs/{run_id}/artifacts/{artifact['id']}")
    assert response.status_code == 404
    assert b'never disclose' not in response.content
    other = launch(client, [], 'ordinary')
    wait(client, other, 'completed')
    assert client.get(f"/api/v1/runs/{other}/artifacts/{artifact['id']}").status_code == 404
