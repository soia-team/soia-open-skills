#!/usr/bin/env python3
"""Run the official bdpan device-code login compatibility path.

This exists for bdpan versions where the upstream login.sh authorization URL
flow fails but ``bdpan login --device-code`` is available. It deliberately
accepts no shell arguments and never reads or prints the bdpan config file.

The official CLI also has its own first-run disclaimer prompt. The agent has
already obtained the user's approval to start this login flow, so the wrapper
passes ``--accept-disclaimer`` and leaves only the browser/App authorization
step to the customer. The customer must not be asked to type ``y`` in a
terminal.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from baidupan_env import configured_binary, load_private_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run official bdpan device-code login after the upstream login URL flow fails"
    )
    parser.parse_args(argv)
    load_private_env(required=False)
    binary = configured_binary()
    if binary != "bdpan":
        print("error: device-code compatibility login requires the official bdpan provider", file=sys.stderr)
        return 2
    if shutil.which(binary) is None:
        print(f"error: could not find {binary}; install the official baidu-drive Skill first", file=sys.stderr)
        return 127

    try:
        return subprocess.run(
            [binary, "login", "--device-code", "--accept-disclaimer"],
            check=False,
        ).returncode
    except OSError as exc:
        print(f"error: could not start {Path(binary).name}: {exc}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
