#!/usr/bin/env python3
"""Start, stop, inspect, and health-check the local Open Design daemon."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from open_design_env import load_private_env


SKILL_NAME = "soia-dev-open-design-ops"
DEFAULT_DAEMON_PORT = 7456


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


def daemon_port() -> int:
    raw = os.environ.get("OPEN_DESIGN_DAEMON_PORT", str(DEFAULT_DAEMON_PORT))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("OPEN_DESIGN_DAEMON_PORT must be an integer.") from exc
    if not 1 <= value <= 65535:
        raise ValueError("OPEN_DESIGN_DAEMON_PORT must be between 1 and 65535.")
    return value


def daemon_url() -> str:
    configured = os.environ.get("OPEN_DESIGN_DAEMON_URL", "").strip()
    url = configured.rstrip("/") if configured else f"http://127.0.0.1:{daemon_port()}"
    return validate_daemon_url(url)


def validate_daemon_url(url: str) -> str:
    url = url.rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("Open Design daemon URL must use a loopback host.")
    return url


def state_dir() -> Path:
    configured = os.environ.get("OPEN_DESIGN_STATE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / SKILL_NAME / "state"
    state_root = Path(os.environ["XDG_STATE_HOME"]).expanduser() if os.environ.get("XDG_STATE_HOME") else Path.home() / ".local" / "state"
    return state_root / SKILL_NAME


def pid_file() -> Path:
    return state_dir() / "daemon.json"


def log_file() -> Path:
    return state_dir() / "daemon.log"


def health_request(base_url: str, timeout: float = 3.0) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/skills",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"reachable": False, "error": type(exc).__name__}

    skills = payload.get("skills") if isinstance(payload, dict) else None
    if status != 200 or not isinstance(skills, list):
        return {"reachable": False, "error": "invalid_skills_response", "http_status": status}
    return {"reachable": True, "http_status": status, "skills_count": len(skills)}


def read_pid_metadata() -> dict[str, Any] | None:
    try:
        payload = json.loads(pid_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def recorded_process_matches(pid: int) -> bool:
    """Fail closed before signaling a potentially reused POSIX PID."""
    if not process_is_alive(pid):
        return False
    if os.name == "nt":
        # Windows does not expose a command line through a portable stdlib API.
        # The private state file remains the ownership boundary on that platform.
        return True
    try:
        completed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    command = completed.stdout.strip()
    return completed.returncode == 0 and "tools-dev" in command and "run web" in command


def start(wait_seconds: float) -> int:
    base_url = daemon_url()
    existing_health = health_request(base_url)
    if existing_health["reachable"]:
        emit({"status": "already_running", "url": base_url, "health": existing_health})
        return 0

    home = os.environ.get("OPEN_DESIGN_HOME", "").strip()
    if not home or not os.path.isdir(home) or not os.path.isfile(os.path.join(home, "QUICKSTART.md")):
        emit({"status": "error", "error": "invalid_open_design_home"})
        return 1
    pnpm = shutil.which("pnpm")
    if not pnpm:
        emit({"status": "error", "error": "pnpm_not_found"})
        return 1

    metadata = read_pid_metadata()
    recorded_pid = metadata.get("pid") if metadata else None
    if isinstance(recorded_pid, int) and process_is_alive(recorded_pid):
        emit({"status": "error", "error": "recorded_process_alive_but_unhealthy", "pid": recorded_pid})
        return 1

    output_dir = state_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [pnpm, "tools-dev", "run", "web", "--daemon-port", str(daemon_port())]
    web_port = os.environ.get("OPEN_DESIGN_WEB_PORT", "").strip()
    if web_port:
        try:
            parsed_web_port = int(web_port)
        except ValueError:
            emit({"status": "error", "error": "invalid_web_port"})
            return 1
        if not 1 <= parsed_web_port <= 65535:
            emit({"status": "error", "error": "invalid_web_port"})
            return 1
        command.extend(["--web-port", str(parsed_web_port)])

    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) if os.name == "nt" else 0
    try:
        with log_file().open("ab") as log_handle:
            process = subprocess.Popen(
                command,
                cwd=home,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                shell=False,
                start_new_session=os.name != "nt",
                creationflags=creationflags,
            )
    except OSError:
        emit({"status": "error", "error": "could_not_start_tools_dev"})
        return 1

    try:
        pid_file().write_text(
            json.dumps({"pid": process.pid, "open_design_home": home, "url": base_url}),
            encoding="utf-8",
        )
    except OSError:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        emit({"status": "error", "error": "could_not_record_managed_pid"})
        return 1

    deadline = time.monotonic() + max(0.0, wait_seconds)
    health = health_request(base_url)
    while not health["reachable"] and time.monotonic() < deadline and process.poll() is None:
        time.sleep(0.5)
        health = health_request(base_url)

    status = "running" if health["reachable"] else "starting"
    if process.poll() is not None and not health["reachable"]:
        status = "error"
    emit(
        {
            "status": status,
            "pid": process.pid,
            "url": base_url,
            "health": health,
            "log_path": str(log_file()),
        }
    )
    return 1 if status == "error" else 0


def stop(wait_seconds: float) -> int:
    metadata = read_pid_metadata()
    pid = metadata.get("pid") if metadata else None
    if not isinstance(pid, int):
        emit({"status": "not_managed", "error": "no_recorded_pid"})
        return 1
    if not process_is_alive(pid):
        pid_file().unlink(missing_ok=True)
        emit({"status": "stopped", "pid": pid, "already_exited": True})
        return 0
    if not recorded_process_matches(pid):
        emit({"status": "error", "error": "recorded_pid_identity_mismatch", "pid": pid})
        return 1

    try:
        if os.name != "nt":
            os.killpg(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError:
        emit({"status": "error", "error": "term_failed", "pid": pid})
        return 1

    deadline = time.monotonic() + max(0.0, wait_seconds)
    while process_is_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.2)
    alive = process_is_alive(pid)
    if not alive:
        pid_file().unlink(missing_ok=True)
    emit({"status": "stopping" if alive else "stopped", "pid": pid, "force_kill_used": False})
    return 0 if not alive else 1


def status() -> int:
    base_url = daemon_url()
    metadata = read_pid_metadata()
    pid = metadata.get("pid") if metadata else None
    managed_alive = isinstance(pid, int) and process_is_alive(pid)
    health = health_request(base_url)
    if managed_alive and health["reachable"]:
        state = "running"
    elif health["reachable"]:
        state = "running_external"
    elif managed_alive:
        state = "unhealthy"
    else:
        state = "stopped"
    emit({"status": state, "pid": pid if isinstance(pid, int) else None, "url": base_url, "health": health})
    return 0 if health["reachable"] else 1


def health() -> int:
    base_url = daemon_url()
    result = health_request(base_url)
    emit({"status": "ok" if result["reachable"] else "error", "url": base_url, "health": result})
    return 0 if result["reachable"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop", "status", "health"))
    parser.add_argument("--wait", type=float, default=20.0, help="Maximum startup/stop wait in seconds.")
    args = parser.parse_args(argv)
    load_private_env(required=False)
    try:
        if args.action == "start":
            return start(args.wait)
        if args.action == "stop":
            return stop(args.wait)
        if args.action == "status":
            return status()
        return health()
    except ValueError as exc:
        emit({"status": "error", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
