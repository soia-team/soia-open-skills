#!/usr/bin/env python3
"""Resolve portable, user-owned storage locations without creating them."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path


REPO_NAME = "soia-open-skills"


def _configured_path(env: Mapping[str, str], name: str) -> Path | None:
    value = env.get(name)
    return Path(value).expanduser() if value else None


def storage_paths(
    skill_type: str,
    skill_name: str,
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    platform_name: str | None = None,
    temp_root: Path | None = None,
) -> dict[str, Path]:
    """Return config/state/cache/temp roots for one installed skill."""

    values = os.environ if env is None else env
    user_home = Path.home() if home is None else home
    platform_id = sys.platform if platform_name is None else platform_name
    is_windows = platform_id.startswith("win")
    is_macos = platform_id == "darwin"

    config_base = _configured_path(values, "SOIA_SKILLS_CONFIG_HOME")
    if config_base is None:
        if is_windows:
            config_base = Path(values.get("APPDATA", user_home / "AppData" / "Roaming")) / "soia-skills"
        else:
            config_base = Path(values.get("XDG_CONFIG_HOME", user_home / ".config")) / "soia-skills"

    state_base = _configured_path(values, "SOIA_SKILLS_STATE_HOME")
    if state_base is None:
        if is_windows:
            state_base = Path(values.get("LOCALAPPDATA", user_home / "AppData" / "Local")) / "soia-skills" / "state"
        else:
            state_base = Path(values.get("XDG_STATE_HOME", user_home / ".local" / "state")) / "soia-skills"

    cache_base = _configured_path(values, "SOIA_SKILLS_CACHE_HOME")
    if cache_base is None:
        if is_windows:
            cache_base = Path(values.get("LOCALAPPDATA", user_home / "AppData" / "Local")) / "soia-skills" / "Cache"
        elif is_macos:
            cache_base = user_home / "Library" / "Caches" / "soia-skills"
        else:
            cache_base = Path(values.get("XDG_CACHE_HOME", user_home / ".cache")) / "soia-skills"

    suffix = Path(REPO_NAME) / skill_type / skill_name
    temporary_base = Path(tempfile.gettempdir()) if temp_root is None else temp_root
    return {
        "config": config_base / suffix,
        "state": state_base / suffix,
        "cache": cache_base / suffix,
        "temp": temporary_base / "soia-skills" / suffix,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-type", default="your-skill-type")
    parser.add_argument("--skill-name", default="your-skill-name")
    parser.add_argument("--json", action="store_true", help="Print machine-readable paths.")
    args = parser.parse_args()

    paths = storage_paths(args.skill_type, args.skill_name)
    result = {name: str(path) for name, path in paths.items()}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for name, path in result.items():
            print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
