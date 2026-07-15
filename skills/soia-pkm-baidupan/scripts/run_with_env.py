#!/usr/bin/env python3
"""Run bdpan or baidupan-cli with the selected private config loaded."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from baidupan_env import ALLOWED_BINARIES, configured_binary, load_private_env


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--"]:
        args = args[1:]
    try:
        load_private_env(required=False)
        binary = configured_binary()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args[:1] == ["--binary"]:
        if len(args) < 2 or args[1] not in ALLOWED_BINARIES:
            print("error: --binary must be bdpan or baidupan-cli", file=sys.stderr)
            return 2
        binary = args[1]
        args = args[2:]
    if args[:1] == ["--"]:
        args = args[1:]
    if not args:
        print("usage: run_with_env.py [--binary bdpan|baidupan-cli] -- COMMAND [ARG ...]", file=sys.stderr)
        return 2
    if binary == "bdpan" and args[0] == "login":
        print("error: official bdpan login must use the upstream baidu-drive login.sh", file=sys.stderr)
        return 2

    command = [binary, *args]
    try:
        return subprocess.run(command, check=False, shell=False).returncode
    except OSError:
        print(f"error: could not start {Path(binary).name}.", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
