#!/usr/bin/env python3
"""Locate the optional soia-pkm-transform config without hardcoded user paths."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


CONFIG_NAMES = (
    "transform.yml",
    "transform.yaml",
    "transform.json",
)


def candidate_paths(cwd: Path) -> list[Path]:
    paths: list[Path] = []
    env_path = os.environ.get("SOIA_PKM_TRANSFORM_CONFIG")
    if env_path:
        paths.append(Path(env_path).expanduser())

    config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    for name in CONFIG_NAMES:
        paths.append(config_home / "soia-pkm" / name)

    for name in CONFIG_NAMES:
        paths.append(Path("~/.soia-pkm").expanduser() / name)

    cur = cwd.resolve()
    for parent in (cur, *cur.parents):
        for name in CONFIG_NAMES:
            paths.append(parent / ".soia" / name)

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            deduped.append(path)
            seen.add(key)
    return deduped


def load_if_possible(path: Path) -> tuple[object | None, str | None]:
    if path.suffix == ".json":
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh), None

    try:
        import yaml  # type: ignore
    except Exception:
        return None, "YAML config found, but PyYAML is not installed; agents may still read it as text."

    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh), None


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate soia-pkm-transform config.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Directory used for .soia config discovery.")
    args = parser.parse_args()

    cwd = Path(args.cwd).expanduser()
    candidates = candidate_paths(cwd)
    found = next((p for p in candidates if p.is_file()), None)

    result: dict[str, object] = {
        "found": bool(found),
        "path": str(found) if found else None,
        "candidates": [str(p) for p in candidates],
    }

    if found:
        config, warning = load_if_possible(found)
        if warning:
            result["warning"] = warning
        if config is not None:
            result["config"] = config

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if found:
            print(f"Config: {found}")
            if "warning" in result:
                print(f"Warning: {result['warning']}", file=sys.stderr)
        else:
            print("No soia-pkm-transform config found.")
            print("Set SOIA_PKM_TRANSFORM_CONFIG or create ~/.config/soia-pkm/transform.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
