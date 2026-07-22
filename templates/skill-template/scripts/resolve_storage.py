#!/usr/bin/env python3
"""Resolve portable, user-owned storage locations without creating them."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path


CONFIG_NAMES = ("config.yml", "config.yaml", "config.json")
LEGACY_REPO_NAMES = ("soia-open-skills", "soia-open-env-skills")
_WARNED_LEGACY_PATHS: set[Path] = set()


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

    del skill_type  # Kept in the API so generated skills remain source-compatible.
    suffix = Path(skill_name)
    temporary_base = Path(tempfile.gettempdir()) if temp_root is None else temp_root
    return {
        "config": config_base / suffix,
        "state": state_base / suffix,
        "cache": cache_base / suffix,
        "temp": temporary_base / "soia-skills" / suffix,
    }


def _legacy_skill_types(skill_name: str) -> tuple[str, ...]:
    parts = skill_name.split("-")
    if len(parts) < 2 or parts[0] != "soia" or not parts[1]:
        raise ValueError(f"cannot infer legacy skill type from {skill_name!r}")

    domain = parts[1]
    preferred = domain if domain == "cwork" else f"soia-{domain}"
    alternate = f"soia-{domain}" if domain == "cwork" else domain
    return preferred, alternate


def storage_candidates(
    skill_type: str,
    skill_name: str,
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    platform_name: str | None = None,
    temp_root: Path | None = None,
) -> dict[str, list[Path]]:
    """Return v2 first, followed by read-only v1 compatibility roots."""

    v2 = storage_paths(
        skill_type,
        skill_name,
        env=env,
        home=home,
        platform_name=platform_name,
        temp_root=temp_root,
    )
    candidates = {kind: [path] for kind, path in v2.items()}
    for repo_name in LEGACY_REPO_NAMES:
        for legacy_skill_type in _legacy_skill_types(skill_name):
            suffix = Path(repo_name) / legacy_skill_type / skill_name
            for kind, v2_path in v2.items():
                candidates[kind].append(v2_path.parent / suffix)
    return candidates


def _warn_legacy_path(legacy_path: Path, v2_path: Path) -> None:
    if legacy_path in _WARNED_LEGACY_PATHS:
        return
    _WARNED_LEGACY_PATHS.add(legacy_path)
    print(
        "SOIA storage schema v1 fallback in use; migrate when convenient: "
        f"mkdir -p {shlex.quote(str(v2_path.parent))} && "
        f"mv {shlex.quote(str(legacy_path))} {shlex.quote(str(v2_path))}",
        file=sys.stderr,
    )


def resolve_storage_dir(
    kind: str,
    skill_type: str,
    skill_name: str,
    *,
    for_write: bool = False,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    platform_name: str | None = None,
    temp_root: Path | None = None,
) -> Path:
    """Resolve a storage root; v1 roots are eligible only for reads."""

    candidates = storage_candidates(
        skill_type,
        skill_name,
        env=env,
        home=home,
        platform_name=platform_name,
        temp_root=temp_root,
    )
    if kind not in candidates:
        raise ValueError(f"unknown storage kind: {kind}")

    v2_path, *legacy_paths = candidates[kind]
    if for_write or v2_path.exists():
        return v2_path
    for legacy_path in legacy_paths:
        if legacy_path.exists():
            _warn_legacy_path(legacy_path, v2_path)
            return legacy_path
    return v2_path


def resolve_config_file(
    skill_type: str,
    skill_name: str,
    env_name: str | None = None,
    *,
    for_write: bool = False,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    platform_name: str | None = None,
) -> Path:
    """Resolve a skill config file with an explicit env override first."""

    values = os.environ if env is None else env
    if env_name is None:
        env_name = f"{skill_name.upper().replace('-', '_')}_CONFIG_FILE"
    configured = _configured_path(values, env_name)
    if configured is not None:
        return configured

    candidates = storage_candidates(
        skill_type,
        skill_name,
        env=values,
        home=home,
        platform_name=platform_name,
    )["config"]
    v2_dir, *legacy_dirs = candidates
    if for_write:
        return v2_dir / CONFIG_NAMES[0]

    for name in CONFIG_NAMES:
        candidate = v2_dir / name
        if candidate.is_file():
            return candidate
    for legacy_dir in legacy_dirs:
        for name in CONFIG_NAMES:
            candidate = legacy_dir / name
            if candidate.is_file():
                _warn_legacy_path(candidate, v2_dir / name)
                return candidate
    return v2_dir / CONFIG_NAMES[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-type", default="your-skill-type")
    parser.add_argument("--skill-name", default="your-skill-name")
    parser.add_argument("--for-write", action="store_true", help="Return v2 write roots only.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable paths.")
    args = parser.parse_args()

    paths = {
        kind: resolve_storage_dir(
            kind,
            args.skill_type,
            args.skill_name,
            for_write=args.for_write,
        )
        for kind in ("config", "state", "cache", "temp")
    }
    result = {name: str(path) for name, path in paths.items()}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for name, path in result.items():
            print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
