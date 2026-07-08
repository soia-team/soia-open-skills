#!/usr/bin/env python3
"""Locate an optional skill config without hardcoded user paths."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


CONFIG_NAMES = ("config.yml", "config.yaml", "config.json")
ENV_NAME = "YOUR_SKILL_CONFIG"
CONFIG_DIR = "your-skill-name"


def candidate_paths(cwd: Path) -> list[Path]:
    paths: list[Path] = []
    env_path = os.environ.get(ENV_NAME)
    if env_path:
        paths.append(Path(env_path).expanduser())

    config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    for name in CONFIG_NAMES:
        paths.append(config_home / CONFIG_DIR / name)

    cur = cwd.resolve()
    for parent in (cur, *cur.parents):
        for name in CONFIG_NAMES:
            paths.append(parent / ".soia" / CONFIG_DIR / name)

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            deduped.append(path)
            seen.add(key)
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate optional skill config.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Directory used for local config discovery.")
    args = parser.parse_args()

    candidates = candidate_paths(Path(args.cwd).expanduser())
    found = next((path for path in candidates if path.is_file()), None)
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
        print(f"No config found. Set {ENV_NAME} or create ~/.config/{CONFIG_DIR}/config.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
