#!/usr/bin/env python3
"""Check whether a compatible OfficeCLI binary is available."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path


MIN_VERSION = (1, 0, 137)
VERSION_PATTERN = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")


def resolve_binary(env: Mapping[str, str] | None = None) -> str | None:
    values = os.environ if env is None else env
    configured = values.get("OFFICECLI_BIN")
    if configured:
        path = Path(configured).expanduser()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which("officecli")


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = VERSION_PATTERN.search(value)
    if not match:
        return None
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def check_environment(env: Mapping[str, str] | None = None) -> dict[str, object]:
    binary = resolve_binary(env)
    if not binary:
        return {
            "status": "error",
            "available": False,
            "version": None,
            "compatible": False,
            "minimum_version": ".".join(map(str, MIN_VERSION)),
            "suggestions": [
                "Install OfficeCLI from https://github.com/iOfficeAI/OfficeCLI",
                "Or set OFFICECLI_BIN to an executable OfficeCLI binary",
            ],
        }

    try:
        subprocess_env = dict(os.environ if env is None else env)
        subprocess_env["OFFICECLI_SKIP_UPDATE"] = "1"
        completed = subprocess.run(
            [binary, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=subprocess_env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "status": "error",
            "available": True,
            "version": None,
            "compatible": False,
            "error": type(exc).__name__,
            "suggestions": ["Verify that OFFICECLI_BIN points to a runnable binary"],
        }

    raw_version = (completed.stdout or completed.stderr).strip()
    version = parse_version(raw_version)
    compatible = completed.returncode == 0 and version is not None and version >= MIN_VERSION
    return {
        "status": "ok" if compatible else "error",
        "available": completed.returncode == 0,
        "version": ".".join(map(str, version)) if version else raw_version or None,
        "compatible": compatible,
        "minimum_version": ".".join(map(str, MIN_VERSION)),
        "suggestions": [] if compatible else ["Upgrade OfficeCLI before running write operations"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print indented JSON output.")
    args = parser.parse_args()
    result = check_environment()
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
