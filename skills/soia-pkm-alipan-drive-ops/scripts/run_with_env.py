#!/usr/bin/env python3
"""Run a command with this skill's optional private environment loaded."""

from __future__ import annotations

import subprocess
import sys

from alipan_env import load_private_env


ALLOWED_EXECUTABLES = frozenset({"aliyunpan", "aliyunpan.exe"})


def is_allowed_command(command: list[str]) -> bool:
    """Return whether *command* starts with an allowed aliyunpan executable.

    Only the documented bare executable names are accepted for normal PATH
    lookup.  A caller-supplied path, including an absolute path, could name an
    arbitrary program that would inherit this wrapper's private environment.
    """
    if not command:
        return False

    return command[0] in ALLOWED_EXECUTABLES


def main(argv: list[str] | None = None) -> int:
    command = sys.argv[1:] if argv is None else argv

    if command[:1] == ["--"]:
        command = command[1:]

    if not command:
        print("usage: run_with_env.py [--] aliyunpan [ARG ...]", file=sys.stderr)
        return 2

    if not is_allowed_command(command):
        print("error: run_with_env.py only runs the aliyunpan executable.", file=sys.stderr)
        return 2

    load_private_env(required=False)
    try:
        result = subprocess.run(command, check=False, shell=False)
    except OSError:
        # Do not include exception details: command lines can contain private
        # values and this wrapper must never echo them to stderr.
        print("error: could not start aliyunpan.", file=sys.stderr)
        return 127
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
