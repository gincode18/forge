import asyncio
import json

import pytest

from forge.domain.tools import ToolContext
from forge.runtime.tools import ToolRegistry, scoped_path


@pytest.mark.parametrize('path', ['../escape', '/absolute', 'nested/../../escape'])
def test_workspace_rejects_traversal(tmp_path, path):
    with pytest.raises(ValueError):
        scoped_path(tmp_path, path)


def test_workspace_rejects_symlink_components(tmp_path):
    (tmp_path / 'link').symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        scoped_path(tmp_path, 'link/escape')


def test_workspace_rejects_symlinked_ancestor(tmp_path):
    actual = tmp_path / 'actual'
    actual.mkdir()
    (tmp_path / 'alias').symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError):
        scoped_path(tmp_path / 'alias' / 'workspace', 'file')


def test_workspace_rejects_special_files_without_opening_them(tmp_path):
    import os
    os.mkfifo(tmp_path / 'fifo')
    with pytest.raises(ValueError):
        scoped_path(tmp_path, 'fifo')


def test_write_rejects_hardlinks_before_mutating_outside_file(tmp_path):
    import os
    external = tmp_path / 'outside.txt'
    external.write_text('original')
    root = tmp_path / 'workspace'
    root.mkdir()
    os.link(external, root / 'linked.txt')
    tool = ToolRegistry().get('filesystem_write@1')
    with pytest.raises(ValueError):
        asyncio.run(tool.execute(tool.input_model.model_validate({'path': 'linked.txt', 'content': 'overwrite'}), ToolContext('test', root)))
    assert external.read_text() == 'original'


def test_engine_rejects_workspace_symlink_before_creating_run_directory(client, tmp_path):
    from forge.runtime.engine import execute_fake_run
    from forge.runtime.fake import FakeProvider
    from forge.runtime.react import ReActPlanner

    outside = tmp_path / 'outside'
    outside.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(outside, target_is_directory=True)
    agent = client.post('/api/v1/agents', json={'name': 'unsafe workspace', 'instructions': 'test'}).json()
    run_id = client.post('/api/v1/runs', json={'agent_id': agent['id'], 'input': 'test'}).json()['id']
    with pytest.raises(ValueError, match='unsafe workspace'):
        asyncio.run(execute_fake_run(client.app.state.database, run_id, FakeProvider(), ReActPlanner(),
                                     workspace_root=alias / 'new-workspaces'))
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize('tool_key', ['filesystem_read@1', 'filesystem_write@1'])
@pytest.mark.parametrize('component', ['file', 'parent'])
def test_filesystem_rejects_symlink_swap_after_validation(tmp_path, monkeypatch, tool_key, component):
    import forge.runtime.tools as tools_module

    workspace = tmp_path / 'workspace'
    outside = tmp_path / 'outside'
    (workspace / 'nested').mkdir(parents=True)
    outside.mkdir()
    target = workspace / 'nested' / 'answer.txt'
    target.write_text('inside')
    external = outside / 'answer.txt'
    external.write_text('outside')
    original = tools_module.scoped_path

    def swap(root, value):
        path = original(root, value)
        if component == 'file':
            target.unlink()
            target.symlink_to(external)
        else:
            (workspace / 'nested').rename(workspace / 'original')
            (workspace / 'nested').symlink_to(outside, target_is_directory=True)
        return path

    monkeypatch.setattr(tools_module, 'scoped_path', swap)
    tool = ToolRegistry().get(tool_key)
    assert tool is not None
    values = {'path': 'nested/answer.txt'}
    if tool_key == 'filesystem_write@1':
        values['content'] = 'overwrite'
    with pytest.raises((ValueError, OSError)):
        asyncio.run(tool.execute(tool.input_model.model_validate(values), ToolContext('test', workspace)))
    assert external.read_text() == 'outside'


@pytest.mark.parametrize('tool_key', ['filesystem_read@1', 'filesystem_write@1'])
def test_filesystem_rejects_hardlink_swap_on_opened_inode(tmp_path, monkeypatch, tool_key):
    import os

    import forge.runtime.tools as tools_module

    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    target = workspace / 'answer.txt'
    target.write_text('inside')
    external = tmp_path / 'outside.txt'
    external.write_text('outside')
    original = tools_module.scoped_path

    def swap(root, value):
        path = original(root, value)
        target.unlink()
        os.link(external, target)
        return path

    monkeypatch.setattr(tools_module, 'scoped_path', swap)
    tool = ToolRegistry().get(tool_key)
    assert tool is not None
    values = {'path': 'answer.txt'}
    if tool_key == 'filesystem_write@1':
        values['content'] = 'overwrite'
    with pytest.raises(ValueError, match='hardlinks'):
        asyncio.run(tool.execute(tool.input_model.model_validate(values), ToolContext('test', workspace)))
    assert external.read_text() == 'outside'


def test_descriptor_write_creates_nested_parents_and_truncates_valid_file(tmp_path):
    tool = ToolRegistry().get('filesystem_write@1')
    assert tool is not None
    context = ToolContext('test', tmp_path)
    for content in ['long original', 'short']:
        arguments = tool.input_model.model_validate({'path': 'new/nested/answer.txt', 'content': content})
        result = asyncio.run(tool.execute(arguments, context))
        assert result.size_bytes == len(content.encode())
        assert (tmp_path / 'new/nested/answer.txt').read_text() == content


@pytest.mark.parametrize('tools', [[], ['calculator@999'], ['calculator'], ['unknown@1']])
def test_disabled_unknown_and_mismatched_versions_are_denied(client, tools):
    from tests.integration.test_tools_phase_four import launch, wait
    run_id = launch(client, tools, json.dumps({'forge_script': [{'name': 'calculator', 'arguments': {'expression': '2+2'}}]}))
    wait(client, run_id, 'completed')
    events = client.get(f'/api/v1/runs/{run_id}/events').json()
    assert any(e['type'] == 'tool.denied' for e in events)
    assert not any(e['type'] == 'tool.started' for e in events)
