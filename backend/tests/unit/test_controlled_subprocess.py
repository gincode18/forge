import asyncio
import sys

from forge.domain.tools import ToolContext
from forge.runtime.tools import ToolRegistry


def test_subprocess_requires_exact_argv_and_sanitizes_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-secret-never-forward')
    registry = ToolRegistry()
    tool = registry.get('subprocess@1')
    assert tool is not None
    argv = [sys.executable, '-c', 'import os; print(os.getenv("GEMINI_API_KEY", "absent"))']
    context = ToolContext('test', tmp_path, (tuple(argv),))
    result = asyncio.run(tool.execute(tool.input_model.model_validate({'argv': argv}), context))
    assert result.stdout == 'absent\n'
    assert result.returncode == 0
    import pytest
    with pytest.raises(ValueError):
        asyncio.run(tool.execute(tool.input_model.model_validate({'argv': argv + ['extra']}), context))


def test_subprocess_output_limit_stops_process(tmp_path):
    import pytest
    tool = ToolRegistry().get('subprocess@1')
    tool.max_output_bytes = 1024
    argv = [sys.executable, '-c', 'print("x"*2048)']
    with pytest.raises(ValueError, match='output limit'):
        asyncio.run(tool.execute(tool.input_model.model_validate({'argv': argv}), ToolContext('test', tmp_path, (tuple(argv),))))


def test_subprocess_timeout_is_enforced_without_runtime_wrapper(tmp_path):
    import time

    import pytest
    tool = ToolRegistry().get('subprocess@1')
    tool.timeout_seconds = .03
    argv = [sys.executable, '-c', 'import time; time.sleep(10)']
    async def run():
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(tool.execute(tool.input_model.model_validate({'argv': argv}), ToolContext('test', tmp_path, (tuple(argv),))), .3)
    started = time.monotonic()
    asyncio.run(run())
    assert time.monotonic() - started < .2


def test_cancellation_terminates_descendants(tmp_path):
    tool = ToolRegistry().get('subprocess@1')
    child = 'import time; time.sleep(.3); open("escaped.txt", "w").write("alive")'
    script = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); open("ready", "w").write("ready"); time.sleep(10)'
    argv = [sys.executable, '-c', script]
    async def run():
        task = asyncio.create_task(tool.execute(tool.input_model.model_validate({'argv': argv}), ToolContext('test', tmp_path, (tuple(argv),))))
        for _ in range(100):
            if (tmp_path / 'ready').exists():
                break
            await asyncio.sleep(.005)
        assert (tmp_path / 'ready').exists()
        task.cancel()
        import pytest
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(.4)
    asyncio.run(run())
    assert not (tmp_path / 'escaped.txt').exists()


def test_subprocess_rejects_symlink_workspace(tmp_path):
    import pytest
    actual = tmp_path / 'actual'
    actual.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(actual, target_is_directory=True)
    tool = ToolRegistry().get('subprocess@1')
    argv = [sys.executable, '-c', 'print("safe")']
    with pytest.raises(ValueError):
        asyncio.run(tool.execute(tool.input_model.model_validate({'argv': argv}), ToolContext('test', alias, (tuple(argv),))))


def test_timeout_terminates_descendants_even_after_parent_exits(tmp_path):
    import pytest
    tool = ToolRegistry().get('subprocess@1')
    tool.timeout_seconds = .15
    child = 'import time; time.sleep(.4); open("escaped.txt", "w").write("alive")'
    # Parent exits, but the descendant retains pipes and the process group.
    script = f'import subprocess,sys; subprocess.Popen([sys.executable,"-c",{child!r}]); open("ready", "w").write("ready")'
    argv = [sys.executable, '-c', script]

    async def exercise():
        with pytest.raises(TimeoutError):
            await tool.execute(tool.input_model.model_validate({'argv': argv}), ToolContext('test', tmp_path, (tuple(argv),)))
        assert (tmp_path / 'ready').exists()
        await asyncio.sleep(.45)

    asyncio.run(exercise())
    assert not (tmp_path / 'escaped.txt').exists()


def test_output_cap_terminates_descendants(tmp_path):
    import pytest
    tool = ToolRegistry().get('subprocess@1')
    tool.max_output_bytes = 1024
    child = 'import time; time.sleep(.3); open("escaped.txt", "w").write("alive")'
    script = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); open("ready", "w").write("ready"); print("x"*4096,flush=True); time.sleep(10)'
    argv = [sys.executable, '-c', script]

    async def exercise():
        with pytest.raises(ValueError, match='output limit'):
            await tool.execute(tool.input_model.model_validate({'argv': argv}), ToolContext('test', tmp_path, (tuple(argv),)))
        assert (tmp_path / 'ready').exists()
        await asyncio.sleep(.4)

    asyncio.run(exercise())
    assert not (tmp_path / 'escaped.txt').exists()
