import time


def wait(client, run_id, status):
    for _ in range(200):
        run = client.get(f'/api/v1/runs/{run_id}').json()
        if run['status'] == status:
            return run
        time.sleep(.01)
    raise AssertionError(run)


def launch(client, tools, input):
    agent = client.post('/api/v1/agents', json={
        'name': 'tools', 'instructions': 'use tools', 'tools': tools,
        'max_steps': 30,
    }).json()
    run = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': input}).json()
    response = client.post(f"/api/v1/runs/{run['id']}/start")
    assert response.status_code == 202, response.text
    return run['id']


def test_calculator_tool_continues_with_durable_observation(client):
    catalog = client.get('/api/v1/tools')
    assert catalog.status_code == 200
    assert 'calculator@1' in [tool['key'] for tool in catalog.json()]
    run_id = launch(client, ['calculator@1'], '{"forge_script":[{"name":"calculator","arguments":{"expression":"2+3*4"}}]}')
    wait(client, run_id, 'completed')
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    completed = next(e for e in events if e['type'] == 'tool.completed')
    assert completed['payload']['output'] == {'value': 14}
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    assert steps[-2]['input']['messages'][-1]['role'] == 'tool'
    assert '14' in steps[-2]['input']['messages'][-1]['text']
    planner_ids = {step['id'] for step in steps if step['kind'] == 'planner'}
    assert all(e['payload']['step_id'] in planner_ids for e in events if e['type'] == 'planner.started')


def test_catalog_has_typed_openapi_contract(client):
    schema = client.get('/openapi.json').json()
    items = schema['paths']['/api/v1/tools']['get']['responses']['200']['content']['application/json']['schema']['items']
    assert items['$ref'].endswith('/ToolResponse')


def test_write_approval_survives_restart_and_produces_artifact(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from forge.api.app import create_app
    from forge.config import Settings
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        run_id = launch(client, ['calculator@1', 'filesystem_write@1'], '{"forge_script":[{"name":"calculator","arguments":{"expression":"2+2"}},{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        assert not (tmp_path / 'workspaces' / run_id / 'answer.txt').exists()
    with TestClient(create_app(settings)) as client:
        assert client.get(f'/api/v1/runs/{run_id}').json()['status'] == 'waiting_for_approval'
        response = client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True})
        assert response.status_code == 200, response.text
        wait(client, run_id, 'completed')
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 409
        artifacts = client.get(f'/api/v1/runs/{run_id}/artifacts').json()
        assert len(artifacts) == 1
        assert client.get(f"/api/v1/runs/{run_id}/artifacts/{artifacts[0]['id']}").content == b'4'
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
        assert len([e for e in events if e['type'] == 'tool.completed' and e['payload']['tool_name'] == 'calculator']) == 1


def test_current_time_returns_utc_observation(client):
    from datetime import datetime
    run_id = launch(client, ['current_time@1'], '{"forge_script":[{"name":"current_time","arguments":{}}]}')
    wait(client, run_id, 'completed')
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    output = next(e['payload']['output'] for e in events if e['type'] == 'tool.completed')
    assert datetime.fromisoformat(output['utc']).utcoffset().total_seconds() == 0


def test_enabled_tools_are_visible_in_planner_instructions(client):
    run_id = launch(client, ['calculator@1'], '{"forge_script":[{"name":"calculator","arguments":{"expression":"1+1"}}]}')
    wait(client, run_id, 'completed')
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    assert 'No tools are available' not in steps[0]['input']['instructions']
    assert 'calculator' in steps[0]['input']['instructions']


def test_rejecting_approval_returns_observation_and_no_artifact(client):
    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': False}).status_code == 200
    wait(client, run_id, 'completed')
    assert client.get(f'/api/v1/runs/{run_id}/artifacts').json() == []
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    assert next(e for e in events if e['type'] == 'tool.denied')['payload']['output'] == {'error': 'approval_rejected'}


def test_cancelling_pending_approval_prevents_resolution(client):
    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    assert client.post(f'/api/v1/runs/{run_id}/cancel').json()['status'] == 'cancelled'
    assert client.get(f'/api/v1/runs/{run_id}/steps').json()[-1]['status'] == 'cancelled'
    assert client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]['status'] == 'cancelled'
    assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 409


def test_expired_checkpoint_never_executes_approved_write(client):
    from sqlalchemy.orm import Session

    from forge.adapters.sqlite.models import RunCheckpointRecord
    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    with Session(client.app.state.database.engine) as session:
        checkpoint = session.get(RunCheckpointRecord, run_id)
        checkpoint.payload = {**checkpoint.payload, 'remaining_seconds': 0}
        session.commit()
    assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
    wait(client, run_id, 'failed')
    assert client.get(f'/api/v1/runs/{run_id}/artifacts').json() == []
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    failure = next(e for e in events if e['type'] == 'tool.failed')
    assert failure['payload']['tool_version'] == '1'


def test_native_multiple_calls_resume_remaining_batch_after_restart(tmp_path, monkeypatch):
    import json

    from fastapi.testclient import TestClient

    from forge.api.app import create_app
    from forge.config import Settings
    from forge.runtime.ports import ModelResult, ToolCall
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = Settings(_env_file=None, data_dir=tmp_path)
    calls = [
        {'name': 'calculator', 'arguments': {'expression': '7*6'}},
        {'name': 'filesystem_write', 'arguments': {'path': 'answer.txt', 'content': '42'}},
        {'name': 'filesystem_read', 'arguments': {'path': 'answer.txt'}},
    ]
    class Batch:
        async def stream(self, **kwargs):
            yield ModelResult('', 'fake', 'batch', tool_calls=tuple(ToolCall(**call, id=f'c{i}') for i, call in enumerate(calls)))
    with TestClient(create_app(settings)) as client:
        client.app.state.supervisor.provider = Batch()
        run_id = launch(client, ['calculator@1', 'filesystem_write@1', 'filesystem_read@1'], json.dumps({'forge_script': calls}))
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    with TestClient(create_app(settings)) as client:
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
        wait(client, run_id, 'completed')
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
        outputs = [e['payload'] for e in events if e['type'] == 'tool.completed']
        assert [o['tool_name'] for o in outputs] == ['calculator', 'filesystem_write', 'filesystem_read']
        assert outputs[-1]['output'] == {'content': '42'}


def test_resolving_pause_ignores_finished_task_waiting_for_cleanup(client):
    import asyncio
    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    async def finished():
        old_task = asyncio.get_running_loop().create_future()
        old_task.set_result(None)
        return old_task
    old_task = client.portal.call(finished)
    client.app.state.supervisor.tasks[run_id] = old_task
    response = client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True})
    assert response.status_code == 200, response.text
    wait(client, run_id, 'completed')


def test_unavailable_provider_does_not_consume_pending_approval(tmp_path, monkeypatch):
    import asyncio

    from fastapi.testclient import TestClient

    from forge.api.app import create_app
    from forge.config import Settings
    from forge.runtime.engine import execute_fake_run
    from forge.runtime.fake import FakeProvider
    from forge.runtime.react import ReActPlanner
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path)), raise_server_exceptions=False) as client:
        agent = client.post('/api/v1/agents', json={'name': 'approval', 'provider': 'gemini', 'instructions': 'tools', 'tools': ['filesystem_write@1']}).json()
        run = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}'}).json()
        asyncio.run(execute_fake_run(client.app.state.database, run['id'], FakeProvider(), ReActPlanner()))
        approval = client.get(f"/api/v1/runs/{run['id']}/approvals").json()[0]
        response = client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True})
        assert response.status_code == 422
        assert client.get(f"/api/v1/runs/{run['id']}/approvals").json()[0]['status'] == 'pending'
        assert client.get(f"/api/v1/runs/{run['id']}").json()['status'] == 'waiting_for_approval'


def test_approved_subprocess_output_limit_is_durable_observation(tmp_path, monkeypatch):
    import json
    import sys

    from fastapi.testclient import TestClient

    from forge.api.app import create_app
    from forge.config import Settings
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    argv = [sys.executable, '-c', 'print("x"*100000)']
    settings = Settings(_env_file=None, data_dir=tmp_path, subprocess_allowlist=[argv])
    with TestClient(create_app(settings)) as client:
        run_id = launch(client, ['subprocess@1'], json.dumps({'forge_script': [{'name': 'subprocess', 'arguments': {'argv': argv}}]}))
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
        wait(client, run_id, 'completed')
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
        event = next(e for e in events if e['type'] == 'tool.failed')
        assert event['payload']['output'] == {'error': 'output_limit'}
        steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
        assert next(s for s in steps if s['kind'] == 'tool')['error']['code'] == 'output_limit'


def test_subprocess_shares_remaining_run_deadline(tmp_path, monkeypatch):
    import json
    import sys

    from fastapi.testclient import TestClient

    from forge.api.app import create_app
    from forge.config import Settings
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    argv = [sys.executable, '-c', 'import time; time.sleep(10)']
    with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path, subprocess_allowlist=[argv]))) as client:
        agent = client.post('/api/v1/agents', json={'name': 'deadline', 'instructions': 'tools', 'tools': ['subprocess@1'], 'timeout_seconds': .2}).json()
        run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': json.dumps({'forge_script': [{'name': 'subprocess', 'arguments': {'argv': argv}}]})}).json()['id']
        assert client.post(f'/api/v1/runs/{run_id}/start').status_code == 202
        wait(client, run_id, 'waiting_for_approval')
        approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
        assert client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True}).status_code == 200
        wait(client, run_id, 'failed')
        events = client.get(f'/api/v1/runs/{run_id}/events').json()
        event = next(e for e in events if e['type'] == 'tool.failed')
        assert event['payload']['output'] == {'error': 'timeout'}
        assert events[-1]['payload']['reason'] == 'timeout'


def test_tool_storage_failure_closes_active_step_with_valid_trace(client, monkeypatch):
    from forge.adapters.sqlite.repositories import RunRepository
    original = RunRepository.append_event
    def fail_completion(self, run_id, type, payload):
        if type == 'tool.completed':
            raise RuntimeError('synthetic storage failure')
        return original(self, run_id, type, payload)
    monkeypatch.setattr(RunRepository, 'append_event', fail_completion)
    run_id = launch(client, ['calculator@1'], '{"forge_script":[{"name":"calculator","arguments":{"expression":"1+1"}}]}')
    wait(client, run_id, 'failed')
    steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
    assert steps[-1]['status'] == 'failed'
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    assert events[-2]['type'] == 'tool.failed'
    assert events[-2]['payload']['output']['error'] == 'run_execution_stopped'
