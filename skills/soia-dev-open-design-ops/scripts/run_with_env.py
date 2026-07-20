#!/usr/bin/env python3
"""Run an allowlisted Open Design pnpm/Corepack command with private config."""

from __future__ import annotations

import os
import subprocess
import sys

from open_design_env import load_private_env


PNPM_EXECUTABLES = frozenset({"pnpm", "pnpm.cmd"})
COREPACK_EXECUTABLES = frozenset({"corepack", "corepack.cmd"})
TOOLS_DEV_ACTIONS = frozenset({"start", "run", "restart", "status", "logs", "check", "stop"})


def _allowed_pnpm_args(args: list[str]) -> bool:
    if args == ["install"] or args == ["--version"]:
        return True
    if len(args) >= 2 and args[0] == "tools-dev" and args[1] in TOOLS_DEV_ACTIONS:
        return True
    return args == ["--filter", "@open-design/daemon", "build"]


def is_allowed_command(command: list[str]) -> bool:
    if not command:
        return False
    executable, args = command[0], command[1:]
    if executable in PNPM_EXECUTABLES:
        return _allowed_pnpm_args(args)
    if executable in COREPACK_EXECUTABLES:
        if args == ["enable"] or args == ["pnpm", "--version"]:
            return True
        return len(args) > 1 and args[0] == "pnpm" and _allowed_pnpm_args(args[1:])
    return False


def main(argv: list[str] | None = None) -> int:
    command = sys.argv[1:] if argv is None else argv
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        print("usage: run_with_env.py [--] pnpm|corepack <allowed-args>", file=sys.stderr)
        return 2
    if not is_allowed_command(command):
        print("error: command is not in the Open Design allowlist.", file=sys.stderr)
        return 2

    load_private_env(required=False)
    home = os.environ.get("OPEN_DESIGN_HOME", "").strip()
    if not home or not os.path.isdir(home):
        print("error: OPEN_DESIGN_HOME is not a directory.", file=sys.stderr)
        return 2
    try:
        result = subprocess.run(command, check=False, shell=False, cwd=home)
    except OSError:
        print("error: could not start the allowed Open Design command.", file=sys.stderr)
        return 127
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
