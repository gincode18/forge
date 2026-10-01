"""Offline tests for the root operator CLI (real child processes)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load_cli():
    path = ROOT / "scripts/local_cli.py"
    assert path.is_file(), "The local launcher must exist"
    spec = importlib.util.spec_from_file_location("local_cli", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configuration_resolves_root_and_wires_custom_ports(tmp_path):
    cli = load_cli()
    args = cli.parser().parse_args([
        "dev", "--host", "0.0.0.0", "--api-port", "8123",
        "--dashboard-port", "3123", "--state-dir", str(tmp_path),
    ])
    config = cli.configuration(args)
    assert config["root"] == str(ROOT)
    assert config["api_url"] == "http://localhost:8123"
    assert config["dashboard_url"] == "http://localhost:3123"
    env = cli.service_environment(config)
    assert env["NEXT_PUBLIC_FORGE_API_URL"] == config["api_url"]
    assert 'http://localhost:3123' in env["FORGE_ALLOWED_ORIGINS"]
    assert 'http://127.0.0.1:3123' in env["FORGE_ALLOWED_ORIGINS"]


def test_browser_api_hostname_is_allowed_for_remote_dashboard():
    cli = load_cli()
    config = cli.configuration(cli.parser().parse_args([
        'dev', '--host', '0.0.0.0', '--api-url', 'http://forge.local:8123', '--dashboard-port', '3123',
    ]))
    assert 'http://forge.local:3123' in cli.service_environment(config)['FORGE_ALLOWED_ORIGINS']


@pytest.mark.parametrize('shutdown', ['stop', 'interrupt', 'hangup'])
def test_supervisor_stops_real_children_and_rejects_duplicates(tmp_path, shutdown):
    import json
    import signal
    import subprocess
    import sys
    import time

    cli = load_cli()
    config = cli.configuration(cli.parser().parse_args([
        "dev", "--state-dir", str(tmp_path), "--timeout", "3",
    ]))
    config["commands"] = {
        "api": [sys.executable, "-u", "-c", "import time; print('api-ready'); time.sleep(60)"],
        "dashboard": [sys.executable, "-u", "-c", "import time; print('dashboard-ready'); time.sleep(60)"],
    }
    script = (f"import importlib.util,json; s=importlib.util.spec_from_file_location('cli',{str(ROOT / 'scripts/local_cli.py')!r}); "
              f"m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.supervise(json.loads({json.dumps(config)!r}), "
              "'test-token', probe=lambda url: True)")
    child = subprocess.Popen([sys.executable, "-c", script])
    state = None
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = cli.read_state(tmp_path)
            if state and state["phase"] == "ready":
                break
            time.sleep(.05)
        assert state and state["phase"] == "ready"
        with pytest.raises(RuntimeError, match="already running"):
            cli.supervise(config, "duplicate", probe=lambda url: True)
        if shutdown == 'stop':
            assert cli.stop(tmp_path) == 0
        else:
            child.send_signal(signal.SIGINT if shutdown == 'interrupt' else signal.SIGHUP)
        child.wait(timeout=8)
        assert child.returncode == 0
        assert not (tmp_path / "state.json").exists()
        for pid in state["children"].values():
            assert cli.process_identity(pid) is None
        assert "api-ready" in (tmp_path / "api.log").read_text()
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=8)
        # A failing signal test must not leave its test-owned groups behind.
        if state:
            for pid in state['children'].values():
                try:
                    __import__('os').killpg(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass


def test_failed_readiness_cleans_children(tmp_path):
    import sys

    import pytest
    cli = load_cli()
    config = cli.configuration(cli.parser().parse_args([
        "dev", "--state-dir", str(tmp_path), "--timeout", ".2",
    ]))
    config["commands"] = {name: [sys.executable, "-c", "import time; time.sleep(60)"]
                          for name in ("api", "dashboard")}
    with pytest.raises(RuntimeError, match="readiness"):
        cli.supervise(config, "failure", probe=lambda url: False)
    assert not (tmp_path / "state.json").exists()


def test_stale_state_never_kills_unrelated_pid(tmp_path):
    import json
    import os
    cli = load_cli()
    (tmp_path / "state.json").write_text(json.dumps({
        "pid": os.getpid(), "identity": "not-the-same-process", "token": "fake",
    }))
    assert cli.stop(tmp_path) == 0
    assert cli.process_identity(os.getpid()) is not None


def test_matching_pid_is_not_enough_to_claim_unrelated_process():
    import os
    cli = load_cli()
    assert not cli.owned({'pid': os.getpid(), 'identity': cli.process_identity(os.getpid()),
                          'token': 'fake', 'config': {'root': str(ROOT)}})


def test_root_commands_with_real_http_children(tmp_path):
    import os
    import socket
    import subprocess
    import sys
    tools = tmp_path / "bin"
    tools.mkdir()
    fake = "#!" + sys.executable + "\n" + '''
import http.server,sys
if '--version' in sys.argv:
    print('24.0.0'); sys.exit(0)
flag = '--api-port' if '--api-port' in sys.argv else '--port'
port = int(sys.argv[sys.argv.index(flag)+1])
print('lightweight child ready', flush=True)
http.server.HTTPServer(('127.0.0.1',port), type('Handler',(http.server.BaseHTTPRequestHandler,),{
 'do_GET':lambda s: (s.send_response(200),s.end_headers(),s.wfile.write(b'ok')),
})).serve_forever()
'''
    for name in ("uv", "pnpm", "node"):
        (tools / name).write_text(fake)
        (tools / name).chmod(0o755)
    ports = []
    for _ in range(2):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            ports.append(s.getsockname()[1])
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'])
    command = [str(ROOT / "forge")]
    flags = ["--state-dir", str(tmp_path / "state"), "--api-port", str(ports[0]),
             "--dashboard-port", str(ports[1]), "--timeout", "8"]
    def run(action):
        return subprocess.run(command + [action] + flags, cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=25, check=False)
    assert (ROOT / "forge").is_file(), 'Root executable must exist'
    try:
        result = run('start')
        assert result.returncode == 0, result.stderr
        assert 'Dashboard:' in result.stdout
        assert run('start').returncode != 0
        assert run('status').returncode == 0
        assert 'lightweight child ready' in run('logs').stdout
        restarted = subprocess.run(command + ['restart', '--state-dir', str(tmp_path / 'state')],
                                   cwd=tmp_path, env=env, capture_output=True, text=True,
                                   timeout=25, check=False)
        assert restarted.returncode == 0, restarted.stderr
        assert f'http://127.0.0.1:{ports[0]}' in restarted.stdout
    finally:
        assert run('stop').returncode == 0
    assert run('status').returncode == 1


def test_restart_port_override_recomputes_default_browser_url():
    cli = load_cli()
    args = cli.parser().parse_args(['restart', '--api-port', '9001'])
    saved = cli.configuration(cli.parser().parse_args(['start', '--api-port', '8123']))
    cli.restore_restart_options(args, saved, ['restart', '--api-port', '9001'])
    assert cli.configuration(args)['api_url'] == 'http://127.0.0.1:9001'


def test_child_liveness_does_not_reap_group_leader():
    import subprocess
    import sys
    import time
    cli = load_cli()
    child = subprocess.Popen([sys.executable, '-c', 'pass'])
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and cli.child_running(child):
            time.sleep(.05)
        assert not cli.child_running(child)
        assert child.returncode is None, 'Keep the PID reserved until group cleanup'
    finally:
        child.wait(timeout=3)


def test_prerequisites_reject_old_backend_python(monkeypatch, tmp_path):
    import os
    import sys

    import pytest
    cli = load_cli()
    tools = tmp_path / 'bin'
    tools.mkdir()
    for name in ('uv', 'pnpm', 'node'):
        path = tools / name
        path.write_text(f'#!{sys.executable}\nprint("v24.0.0")\n')
        path.chmod(0o755)
    backend_python = tmp_path / 'backend/.venv/bin/python'
    backend_python.parent.mkdir(parents=True)
    backend_python.write_text(f'#!{sys.executable}\nprint("Python 3.11.0")\n')
    backend_python.chmod(0o755)
    next_package = tmp_path / 'frontend/node_modules/next/package.json'
    next_package.parent.mkdir(parents=True)
    next_package.write_text('{}')
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    monkeypatch.setenv('PATH', str(tools) + os.pathsep + os.environ['PATH'])
    with pytest.raises(RuntimeError, match='Python >=3.12'):
        cli.prerequisites()


def test_offline_environment_rejects_missing_data_dir(monkeypatch):
    import pytest
    cli = load_cli()
    config = cli.configuration(cli.parser().parse_args(['dev', '--offline']))
    monkeypatch.delenv('FORGE_DATA_DIR', raising=False)
    with pytest.raises(ValueError, match='FORGE_DATA_DIR'):
        cli.service_environment(config)


def test_offline_environment_clears_ambient_credentials(monkeypatch, tmp_path):
    cli = load_cli()
    config = cli.configuration(cli.parser().parse_args(['dev', '--offline']))
    monkeypatch.setenv('FORGE_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('FORGE_DATABASE_URL', 'sqlite:///developer.db')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-not-a-secret')
    env = cli.service_environment(config)
    assert env['GEMINI_API_KEY'] == ''
    assert env['FORGE_DATABASE_URL'] == ''


def test_offline_api_ignores_dotenv_and_uses_temporary_database(tmp_path):
    import json
    import os
    import socket
    import subprocess
    import sys
    import time
    import urllib.request
    cli = load_cli()
    # Synthetic dotenv, never the developer's file.
    (tmp_path / '.env').write_text('GEMINI_API_KEY=synthetic\nFORGE_DATABASE_URL=sqlite:///wrong.db\n')
    env = dict(os.environ, FORGE_DATA_DIR=str(tmp_path / 'data'), GEMINI_API_KEY='', FORGE_DATABASE_URL='')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    path = ROOT / 'scripts/local_api.py'
    assert path.is_file(), 'API launcher must exist'
    child = subprocess.Popen([sys.executable, str(path), '--offline', '--api-port', str(port)],
                             cwd=tmp_path, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 10
        url = f'http://127.0.0.1:{port}/api/v1/health'
        while time.monotonic() < deadline and child.poll() is None:
            if cli.http_ready(url):
                break
            time.sleep(.1)
        assert cli.http_ready(url)
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/providers') as response:
            data = json.load(response)
        assert 'synthetic' not in json.dumps(data)
        assert (tmp_path / 'data/forge.db').exists()
        assert not (tmp_path / 'wrong.db').exists()
    finally:
        child.terminate()
        child.wait(timeout=10)
