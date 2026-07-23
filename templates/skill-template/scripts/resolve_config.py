#!/usr/bin/env python3
"""Locate an optional v2 skill config, with read-only v1 compatibility."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from collections.abc import Mapping
from pathlib import Path


CONFIG_NAMES = ("config.yml", "config.yaml", "config.json")
ENV_NAME = "YOUR_SKILL_CONFIG_FILE"
SKILL_TYPE = "your-skill-type"
SKILL_NAME = "your-skill-name"
LEGACY_REPOSITORIES = ("soia-open-skills", "soia-open-env-skills")
_WARNED_LEGACY_PATHS: set[Path] = set()


def config_root(env: Mapping[str, str], home: Path) -> Path:
    configured = env.get("SOIA_SKILLS_CONFIG_HOME")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        return Path(env.get("APPDATA", home / "AppData" / "Roaming")) / "soia-skills"
    return Path(env.get("XDG_CONFIG_HOME", home / ".config")) / "soia-skills"


def legacy_skill_types(skill_name: str, declared_type: str) -> tuple[str, ...]:
    values = [declared_type]
    parts = skill_name.split("-")
    if len(parts) >= 2 and parts[0] == "soia" and parts[1]:
        domain = parts[1]
        values.extend((domain if domain == "cwork" else f"soia-{domain}", f"soia-{domain}" if domain == "cwork" else domain))
    return tuple(dict.fromkeys(values))


def candidate_paths(
    cwd: Path,
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> list[Path]:
    del cwd  # Reserved for source-compatible callers; configs are user-owned.
    values = os.environ if env is None else env
    user_home = Path.home() if home is None else home
    paths: list[Path] = []
    env_path = values.get(ENV_NAME)
    if env_path:
        paths.append(Path(env_path).expanduser())

    root = config_root(values, user_home)
    for name in CONFIG_NAMES:
        paths.append(root / SKILL_NAME / name)
    for repository in LEGACY_REPOSITORIES:
        for skill_type in legacy_skill_types(SKILL_NAME, SKILL_TYPE):
            for name in CONFIG_NAMES:
                paths.append(root / repository / skill_type / SKILL_NAME / name)

    return list(dict.fromkeys(paths))


def warn_legacy_config(found: Path, current: Path) -> None:
    if found in _WARNED_LEGACY_PATHS:
        return
    _WARNED_LEGACY_PATHS.add(found)
    print(
        "SOIA storage schema v1 config fallback in use; migrate when convenient: "
        f"mkdir -p {shlex.quote(str(current.parent))} && "
        f"mv {shlex.quote(str(found))} {shlex.quote(str(current))}",
        file=sys.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate optional skill config.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Reserved for source-compatible local discovery.")
    args = parser.parse_args()

    candidates = candidate_paths(Path(args.cwd).expanduser())
    found_index = next((index for index, path in enumerate(candidates) if path.is_file()), None)
    found = candidates[found_index] if found_index is not None else None
    explicit = bool(os.environ.get(ENV_NAME))
    v2_count = len(CONFIG_NAMES) + (1 if explicit else 0)
    if found is not None and found_index is not None and found_index >= v2_count:
        current = next(path for path in candidates if path.name == CONFIG_NAMES[0] and path.parent.name == SKILL_NAME)
        warn_legacy_config(found, current)
    result: dict[str, object] = {
        "found": bool(found),
        "path": str(found) if found else None,
        "candidates": [str(path) for path in candidates],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif found:
        print(f"Config: {found}")
    else:
        print(
            "No config found. Set "
            f"{ENV_NAME} or create ~/.config/soia-skills/{SKILL_NAME}/config.yml"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
