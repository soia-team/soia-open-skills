#!/usr/bin/env python3
"""Check NotebookLM CLI/auth using a config-dir default, without reading secrets."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def default_home() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return config_home / "soia-pkm" / "notebooklm"


def run_command(cmd: list[str], env: dict[str, str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "returncode": 127,
            "stdout": "",
            "stderr": f"command not found: {cmd[0]}",
        }
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def maybe_json(text: str) -> object | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def sanitize_auth_check(value: object | None) -> object | None:
    if not isinstance(value, dict):
        return value
    details = value.get("details")
    safe_details: dict[str, Any] = {}
    if isinstance(details, dict):
        for key in ("storage_path", "auth_source", "error", "csrf_length", "session_id_length"):
            if key in details:
                safe_details[key] = details[key]
    return {
        "status": value.get("status"),
        "checks": value.get("checks"),
        "details": safe_details,
    }


def chrome_processes() -> list[str]:
    if sys.platform == "darwin":
        cmd = ["pgrep", "-fl", "Google Chrome|Chromium|Brave Browser|Microsoft Edge"]
    else:
        cmd = ["pgrep", "-fl", "chrome|chromium|brave|edge"]
    proc = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check NotebookLM CLI and auth with a SOIA-friendly NOTEBOOKLM_HOME."
    )
    parser.add_argument("--home", help="NotebookLM home directory. Defaults to NOTEBOOKLM_HOME or ~/.config/soia-pkm/notebooklm.")
    parser.add_argument("--profile", help="NotebookLM profile name to export as NOTEBOOKLM_PROFILE.")
    parser.add_argument("--ensure-home", action="store_true", help="Create the home directory with user-only permissions.")
    parser.add_argument("--skip-auth-test", action="store_true", help="Skip network auth check.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    args = parser.parse_args()

    home = Path(args.home or os.environ.get("NOTEBOOKLM_HOME") or default_home()).expanduser().resolve()
    env = os.environ.copy()
    env["NOTEBOOKLM_HOME"] = str(home)
    if args.profile:
        env["NOTEBOOKLM_PROFILE"] = args.profile

    if args.ensure_home:
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            home.chmod(0o700)
        except OSError:
            pass

    notebooklm = shutil.which("notebooklm")
    result: dict[str, Any] = {
        "notebooklm_command": notebooklm,
        "home": str(home),
        "home_exists": home.is_dir(),
        "profile": args.profile or os.environ.get("NOTEBOOKLM_PROFILE") or "default",
        "chrome_running": bool(chrome_processes()),
        "auth_check": None,
        "login_commands": {
            "managed_browser": f'NOTEBOOKLM_HOME="{home}" notebooklm login',
            "current_chrome_requires_explicit_cookie_consent": (
                f'NOTEBOOKLM_HOME="{home}" notebooklm login --browser-cookies '
                "'chrome::<profile>'"
            ),
        },
    }

    if notebooklm:
        version = run_command(["notebooklm", "--version"], env)
        result["version"] = version["stdout"] or version["stderr"]
        if not args.skip_auth_test:
            auth = run_command(["notebooklm", "auth", "check", "--test", "--json"], env)
            parsed = maybe_json(auth["stdout"])
            result["auth_check"] = {
                "ok": auth["ok"],
                "returncode": auth["returncode"],
                "json": sanitize_auth_check(parsed),
                "stderr": auth["stderr"],
            }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"NotebookLM command: {notebooklm or 'not found'}")
        print(f"NOTEBOOKLM_HOME: {home}")
        print(f"Home exists: {result['home_exists']}")
        if result.get("version"):
            print(f"Version: {result['version']}")
        auth = result.get("auth_check")
        if isinstance(auth, dict):
            print(f"Auth ok: {auth['ok']}")
            if auth["stderr"]:
                print(f"Auth stderr: {auth['stderr']}")
        print("Login command:")
        print(f"  {result['login_commands']['managed_browser']}")
    return 0 if notebooklm and (args.skip_auth_test or (result.get("auth_check") or {}).get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
