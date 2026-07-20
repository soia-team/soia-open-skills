#!/usr/bin/env python3
"""Offline environment check for an Open Design source checkout."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any

from open_design_env import load_private_env


REQUIRED_REPO_FILES = (
    "package.json",
    "QUICKSTART.md",
    "apps/daemon/src/routes/static-resource.ts",
    "design-systems/_schema/AGENTS.md",
)


def executable_version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip() or completed.stderr.strip()
    return value.splitlines()[0] if value else None


def major_version(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(?:^|[^0-9])(\d+)(?:\.|$)", value)
    return int(match.group(1)) if match else None


def check_environment() -> dict[str, Any]:
    load_private_env(required=False)
    missing: list[str] = []
    suggestions: list[str] = []
    checks: dict[str, Any] = {}

    node = shutil.which("node")
    checks["node"] = {"found": bool(node), "version": None, "compatible": False}
    if not node:
        missing.append("node")
        suggestions.append("Install Node.js 24.x, then run corepack enable.")
    else:
        version = executable_version(node)
        compatible = major_version(version) == 24
        checks["node"].update(version=version, compatible=compatible)
        if not compatible:
            missing.append("node_24")
            suggestions.append("Select Node.js 24.x before running Open Design.")

    pnpm = shutil.which("pnpm")
    checks["pnpm"] = {"found": bool(pnpm), "version": None, "compatible": False}
    if not pnpm:
        missing.append("pnpm")
        suggestions.append("Run corepack enable, then corepack pnpm --version.")
    else:
        version = executable_version(pnpm)
        compatible = bool(version and version.startswith("10.33."))
        checks["pnpm"].update(version=version, compatible=compatible)
        if not compatible:
            missing.append("pnpm_10_33")
            suggestions.append("Use the checkout's Corepack-pinned pnpm 10.33.x.")

    home = os.environ.get("OPEN_DESIGN_HOME", "").strip()
    home_exists = bool(home and os.path.isdir(home))
    checks["open_design_home"] = {"configured": bool(home), "is_directory": home_exists}
    if not home:
        missing.append("OPEN_DESIGN_HOME")
        suggestions.append("Set OPEN_DESIGN_HOME in the private skill config.")
    elif not home_exists:
        missing.append("open_design_checkout")
        suggestions.append("Point OPEN_DESIGN_HOME at an existing Open Design checkout.")

    repo_files: dict[str, bool] = {}
    if home_exists:
        for relative in REQUIRED_REPO_FILES:
            present = os.path.isfile(os.path.join(home, *relative.split("/")))
            repo_files[relative] = present
            if not present:
                missing.append(f"repo_file:{relative}")
        if any(not present for present in repo_files.values()):
            suggestions.append("Use a complete Open Design source checkout.")
    checks["repository"] = repo_files

    return {
        "status": "ok" if not missing else "error",
        "missing": missing,
        "checks": checks,
        "suggestions": suggestions,
    }


def main() -> int:
    result = check_environment()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
