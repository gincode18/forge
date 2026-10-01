"""Dependency-free, POSIX local Forge operator CLI."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parser():
    result = argparse.ArgumentParser(prog="forge", description="Forge API + dashboard, without Docker")
    result.add_argument("command", choices=["setup", "dev", "start", "stop", "restart", "status", "logs", "check", "_serve"])
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--api-port", type=int, default=8000)
    result.add_argument("--dashboard-port", type=int, default=3000)
    result.add_argument("--api-url", help="Browser-visible API URL (use for remote access)")
    result.add_argument("--state-dir", default=os.environ.get("FORGE_LOCAL_STATE_DIR", str(ROOT / ".forge-local")))
    result.add_argument("--timeout", type=float, default=60)
    result.add_argument("--offline", action="store_true", help="Ignore dotenv/provider keys; requires FORGE_DATA_DIR")
    result.add_argument("--token", help=argparse.SUPPRESS)
    result.add_argument("--follow", "-f", action="store_true", help="Follow logs until Ctrl-C")
    result.add_argument("--service", choices=["api", "dashboard", "supervisor", "all"], default="all")
    result.add_argument("--lines", type=int, default=40)
    return result


def configuration(args):
    if not (0 < args.api_port < 65536 and 0 < args.dashboard_port < 65536):
        raise ValueError("Ports must be between 1 and 65535")
    if args.api_port == args.dashboard_port:
        raise ValueError("API and dashboard require different ports")
    if args.timeout <= 0:
        raise ValueError("Timeout must be positive")
    host = "localhost" if args.host in ("0.0.0.0", "::") else args.host
    host = f"[{host}]" if ":" in host else host
    return {"root": str(ROOT), "host": args.host, "api_port": args.api_port,
            "dashboard_port": args.dashboard_port,
            "api_url": args.api_url or f"http://{host}:{args.api_port}",
            "api_url_override": args.api_url,
            "dashboard_url": f"http://{host}:{args.dashboard_port}",
            "state_dir": str(Path(args.state_dir).expanduser().resolve()),
            "timeout": args.timeout, "offline": args.offline}


def service_environment(config):
    env = os.environ.copy()
    if config["offline"]:
        if not env.get("FORGE_DATA_DIR"):
            raise ValueError("--offline requires an isolated FORGE_DATA_DIR")
        for name in list(env):
            if name.endswith("API_KEY") or name in ("FORGE_DATABASE_URL", "GOOGLE_APPLICATION_CREDENTIALS"):
                env.pop(name)
        env["GEMINI_API_KEY"] = ""
        env["FORGE_DATABASE_URL"] = ""
    env["NEXT_PUBLIC_FORGE_API_URL"] = config["api_url"]
    origins = [config["dashboard_url"],
               f"http://localhost:{config['dashboard_port']}",
               f"http://127.0.0.1:{config['dashboard_port']}"]
    browser_host = urllib.parse.urlsplit(config["api_url"]).hostname
    if browser_host:
        browser_host = f"[{browser_host}]" if ":" in browser_host else browser_host
        origins.append(f"http://{browser_host}:{config['dashboard_port']}")
    env["FORGE_ALLOWED_ORIGINS"] = json.dumps(list(dict.fromkeys(origins)))
    if env.get("FORGE_DATA_DIR"):
        env["FORGE_DATA_DIR"] = str(Path(env["FORGE_DATA_DIR"]).expanduser().resolve())
    return env


def process_identity(pid):
    """PID plus OS start time and full command, never PID alone."""
    result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "command="],
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def child_running(child):
    """Observe without wait/poll: an unreaped leader prevents PGID reuse."""
    result = subprocess.run(["ps", "-p", str(child.pid), "-o", "stat="],
                            capture_output=True, text=True, check=False)
    status = result.stdout.strip()
    return result.returncode == 0 and bool(status) and not status.startswith("Z")


def read_state(directory):
    try:
        state = json.loads((Path(directory) / "state.json").read_text())
        return state if isinstance(state, dict) else None
    except (OSError, ValueError):
        return None


def owned(state):
    return bool(state and isinstance(state.get("pid"), int)
                and state.get("identity")
                and str(Path(__file__).resolve()) in state["identity"]
                and state.get("config", {}).get("root") == str(ROOT)
                and process_identity(state["pid"]) == state["identity"])


def write_state(directory, state):
    target = directory / "state.json"
    temporary = directory / "state.json.new"
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(target)


def http_ready(url):
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=.7) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def supervise(config, token, probe=http_ready):
    directory = Path(config["state_dir"])
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "supervisor.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Forge is already running; use ./forge status or stop") from error
        children = {}
        handles = []
        stopping = False

        def request_stop(*_):
            nonlocal stopping
            stopping = True

        previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
        state = {"pid": os.getpid(), "identity": process_identity(os.getpid()),
                 "token": token, "phase": "starting", "config": config, "children": {}}
        try:
            write_state(directory, state)
            env = service_environment(config)
            commands = config["commands"]
            for name, command in commands.items():
                if stopping:
                    return 0
                handle = (directory / f"{name}.log").open("ab", buffering=0)
                handles.append(handle)
                children[name] = subprocess.Popen(command, cwd=Path(config["root"]) / ("backend" if name == "api" else "frontend"),
                                                  env=env, stdin=subprocess.DEVNULL,
                                                  stdout=handle, stderr=handle, start_new_session=True)
                state["children"][name] = children[name].pid
                write_state(directory, state)
            deadline = time.monotonic() + config["timeout"]
            ready = set()
            urls = {"api": config["probe_api_url"] if "probe_api_url" in config else config["api_url"] + "/api/v1/health",
                    "dashboard": config["dashboard_url"]}
            while not stopping:
                for name, child in children.items():
                    if not child_running(child):
                        raise RuntimeError(f"{name} exited; see ./forge logs --service {name}")
                if state["phase"] != "ready":
                    ready.update(name for name in children if name not in ready and probe(urls[name]))
                    if len(ready) == len(children):
                        state["phase"] = "ready"
                        write_state(directory, state)
                        print(f"API: {config['api_url']}\nDashboard: {config['dashboard_url']}\nLogs: {directory}", flush=True)
                    elif time.monotonic() >= deadline:
                        raise RuntimeError("Service readiness timed out; see ./forge logs")
                time.sleep(.1)
            return 0
        finally:
            # Only groups created here are signalled. Their leaders are not reaped
            # until cleanup completes, preventing PID reuse even after early exit.
            for child in children.values():
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                groups_alive = False
                for child in children.values():
                    try:
                        os.killpg(child.pid, 0)
                        groups_alive = True
                    except (ProcessLookupError, PermissionError):
                        pass
                if not groups_alive:
                    break
                time.sleep(.05)
            for child in children.values():
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                child.wait()
            for handle in handles:
                handle.close()
            (directory / "state.json").unlink(missing_ok=True)
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def stop(directory):
    state = read_state(directory)
    if not owned(state):
        print("Forge is stopped (no matching supervisor).")
        return 0
    os.kill(state["pid"], signal.SIGTERM)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        current = read_state(directory)
        if not current or current.get("token") != state.get("token") or not owned(current):
            print("Forge stopped.")
            return 0
        time.sleep(.1)
    raise RuntimeError("Supervisor did not stop; inspect supervisor.log (no unsafe force-kill attempted)")


def prerequisites(installed=True):
    for tool, hint in (("uv", "Install uv: https://docs.astral.sh/uv/getting-started/installation/"),
                       ("node", "Install Node.js >=20.9"), ("pnpm", "Install pnpm 10 (corepack enable)")):
        if not shutil.which(tool):
            raise RuntimeError(f"Missing {tool}. {hint}")
    version = subprocess.check_output(["node", "--version"], text=True).strip().lstrip("v")
    if tuple(int(p) for p in version.split(".")[:2]) < (20, 9):
        raise RuntimeError("Node.js >=20.9 is required")
    if installed and (not (ROOT / "backend/.venv/bin/python").is_file()
                      or not (ROOT / "frontend/node_modules/next/package.json").is_file()):
        raise RuntimeError("Dependencies missing. Run ./forge setup first (uv sync + pnpm install).")
    if installed:
        python = subprocess.check_output([str(ROOT / "backend/.venv/bin/python"), "--version"], text=True).strip()
        if tuple(int(p) for p in python.split()[1].split(".")[:2]) < (3, 12):
            raise RuntimeError("Python >=3.12 is required; run uv python install 3.12 and ./forge setup")


def launch_configuration(config):
    prerequisites()
    service_environment(config)  # Fail before launching anything for invalid offline mode.
    for port in (config["api_port"], config["dashboard_port"]):
        try:
            with socket.create_server((config["host"], port)):
                pass
        except OSError as error:
            raise RuntimeError(f"Cannot bind {config['host']}:{port}; stop its owner or choose another port") from error
    config["commands"] = {
        "api": ["uv", "run", "--no-sync", "python", str(ROOT / "scripts/local_api.py"),
                "--host", config["host"], "--api-port", str(config["api_port"])] + (["--offline"] if config["offline"] else []),
        "dashboard": ["pnpm", "dev", "--hostname", config["host"], "--port", str(config["dashboard_port"])],
    }
    host = "127.0.0.1" if config["host"] == "0.0.0.0" else config["host"]
    host = f"[{host}]" if ":" in host else host
    config["probe_api_url"] = f"http://{host}:{config['api_port']}/api/v1/health"
    return config


def start(args, config):
    directory = Path(config["state_dir"])
    if owned(read_state(directory)):
        raise RuntimeError("Forge is already running; use ./forge status or stop")
    launch_configuration(config)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = uuid.uuid4().hex
    command = [sys.executable, str(Path(__file__).resolve()), "_serve", "--token", token,
               "--state-dir", str(directory), "--host", args.host,
               "--api-port", str(args.api_port), "--dashboard-port", str(args.dashboard_port),
               "--timeout", str(args.timeout)]
    if args.api_url:
        command += ["--api-url", args.api_url]
    if args.offline:
        command += ["--offline"]
    with (directory / "supervisor.log").open("ab", buffering=0) as handle:
        child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                 stdout=handle, stderr=handle, start_new_session=True)
    try:
        deadline = time.monotonic() + config["timeout"] + 5
        while time.monotonic() < deadline:
            state = read_state(directory)
            if state and state.get("token") == token and state.get("phase") == "ready" and owned(state):
                print(f"API: {config['api_url']}\nDashboard: {config['dashboard_url']}\nLogs: {directory}")
                return 0
            if child.poll() is not None:
                raise RuntimeError(f"Startup failed; inspect {directory}/supervisor.log and service logs")
            time.sleep(.1)
        raise RuntimeError(f"Startup timed out; inspect {directory}/supervisor.log")
    except BaseException:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=12)
        raise


def logs(args, directory):
    names = ("api", "dashboard", "supervisor") if args.service == "all" else (args.service,)
    handles = []
    try:
        for name in names:
            path = directory / f"{name}.log"
            if not path.exists():
                print(f"{name}: no log yet")
                continue
            handle = path.open(errors="replace")
            handles.append((name, handle))
            print(f"== {name} ==")
            from collections import deque
            print("".join(deque(handle, maxlen=max(0, args.lines))), end="")
        while args.follow:
            for name, handle in handles:
                text = handle.read()
                if text:
                    print(f"[{name}] {text}", end="", flush=True)
            time.sleep(.2)
        return 0
    finally:
        for _, handle in handles:
            handle.close()


def restore_restart_options(args, saved, argv):
    for name in ("host", "api_port", "dashboard_port", "api_url", "timeout", "offline"):
        flag = "--" + name.replace("_", "-")
        if not any(word == flag or word.startswith(flag + "=") for word in argv):
            setattr(args, name, saved.get("api_url_override") if name == "api_url" else saved[name])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    try:
        config = configuration(args)
        directory = Path(config["state_dir"])
        if args.command == "stop":
            return stop(directory)
        if args.command == "status":
            state = read_state(directory)
            if not owned(state):
                print("Forge is stopped.")
                return 1
            print(f"Forge {state['phase']} (supervisor {state['pid']})")
            saved = state["config"]
            healthy = http_ready(saved["probe_api_url"]) and http_ready(saved["dashboard_url"])
            print(f"API: {saved['api_url']}\nDashboard: {saved['dashboard_url']}\nHTTP: {'ready' if healthy else 'unavailable'}")
            return 0 if healthy else 1
        if args.command == "logs":
            return logs(args, directory)
        if args.command == "setup":
            prerequisites(installed=False)
            subprocess.run(["uv", "sync", "--locked"], cwd=ROOT / "backend", check=True)
            subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=ROOT / "frontend", check=True)
            print("Setup complete. Run ./forge dev or ./forge start.")
            return 0
        if args.command == "check":
            prerequisites()
            for cwd, command in [("backend", ["uv", "run", "pytest"]),
                                 ("backend", ["uv", "run", "ruff", "check", ".", "../scripts"]),
                                 ("frontend", ["pnpm", "lint"]), ("frontend", ["pnpm", "build"])]:
                subprocess.run(command, cwd=ROOT / cwd, check=True)
            return 0
        if args.command == "restart":
            state = read_state(directory)
            if owned(state):
                restore_restart_options(args, state["config"], argv)
                config = configuration(args)
            stop(directory)
        if args.command in ("start", "restart"):
            return start(args, config)
        if owned(read_state(directory)):
            raise RuntimeError("Forge is already running; use ./forge stop first")
        return supervise(launch_configuration(config), args.token or uuid.uuid4().hex)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"forge: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
