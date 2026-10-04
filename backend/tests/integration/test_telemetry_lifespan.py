import time

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from forge.api.app import create_app
from forge.config import Settings


def test_application_owns_and_drains_sdk_provider(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path))
    exporter = InMemorySpanExporter()
    with TestClient(app) as client:
        handle = app.state.telemetry
        assert handle.closed is False
        handle.provider.add_span_processor(SimpleSpanProcessor(exporter))
        agent = client.post('/api/v1/agents', json={'name': 'Trace lifecycle', 'instructions': 'Answer.'}).json()
        run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'Hello'}).json()['id']
        assert client.post(f'/api/v1/runs/{run_id}/start').status_code == 202
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if client.get(f'/api/v1/runs/{run_id}').json()['status'] == 'completed':
                break
            time.sleep(0.01)
        spans = exporter.get_finished_spans()
        assert {span.name for span in spans} == {'forge.model', 'forge.planner'}
        steps = client.get(f'/api/v1/runs/{run_id}/steps').json()
        by_step = {step['id']: step for step in steps}
        for span in spans:
            step = by_step[span.attributes['step_id']]
            assert f'{span.context.trace_id:032x}' == step['trace_id']
            assert f'{span.context.span_id:016x}' == step['span_id']
    assert handle.closed is True


def test_approval_pause_and_resume_never_reuse_exported_span_identity(client):
    exporter = InMemorySpanExporter()
    client.app.state.telemetry.provider.add_span_processor(SimpleSpanProcessor(exporter))
    agent = client.post('/api/v1/agents', json={'name': 'Approval telemetry', 'instructions': 'Write.', 'tools': ['filesystem_write@1']}).json()
    run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}'}).json()['id']
    client.post(f'/api/v1/runs/{run_id}/start')

    def wait(status):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if client.get(f'/api/v1/runs/{run_id}').json()['status'] == status:
                return
            time.sleep(0.01)
        raise AssertionError(status)

    wait('waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={'approved': True})
    wait('completed')
    spans = exporter.get_finished_spans()
    identities = [(span.context.trace_id, span.context.span_id) for span in spans]
    assert len(identities) == len(set(identities))
    tool = next(span for span in spans if span.name == 'forge.tool' and span.attributes['outcome'] == 'completed')
    step = next(step for step in client.get(f'/api/v1/runs/{run_id}/steps').json() if step['kind'] == 'tool')
    assert f'{tool.context.span_id:016x}' == step['span_id']


def test_concurrent_applications_export_only_their_own_runtime_spans(tmp_path):
    first_exporter = InMemorySpanExporter()
    second_exporter = InMemorySpanExporter()
    with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path / 'first'))) as first:
        first.app.state.telemetry.provider.add_span_processor(SimpleSpanProcessor(first_exporter))
        with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path / 'second'))) as second:
            second.app.state.telemetry.provider.add_span_processor(SimpleSpanProcessor(second_exporter))
            agent = first.post('/api/v1/agents', json={'name': 'Owned spans', 'instructions': 'Answer.'}).json()
            run_id = first.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'Hello'}).json()['id']
            first.post(f'/api/v1/runs/{run_id}/start')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if first.get(f'/api/v1/runs/{run_id}').json()['status'] == 'completed':
                    break
                time.sleep(0.01)
            assert len(first_exporter.get_finished_spans()) == 2
            assert second_exporter.get_finished_spans() == ()
