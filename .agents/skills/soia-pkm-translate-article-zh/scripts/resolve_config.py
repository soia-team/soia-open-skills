#!/usr/bin/env python3
"""Locate the optional soia-pkm-translate-article-zh config without hardcoded user paths.

This script only does the mechanical work of finding and (if possible)
parsing config.yml — it never applies target_language / audience / style /
glossary itself. The calling agent reads the resolved config content and
applies it during the actual translation workflow described in SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

OVERRIDE_CONFIG_NAME = "SOIA_PKM_TRANSLATE_ARTICLE_ZH_CONFIG_FILE"
# Older spelling accepted as a compatibility alias; new docs should prefer
# SOIA_PKM_TRANSLATE_ARTICLE_ZH_CONFIG_FILE.
OVERRIDE_ENV_NAME = "SOIA_PKM_TRANSLATE_ENV_FILE"
CONFIG_NAMES = ("config.yml", "config.yaml", "config.json")
DEFAULT_CONFIG_DIR = "~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-translate-article-zh"


def candidate_paths() -> list[Path]:
    paths: list[Path] = []

    override_config = os.environ.get(OVERRIDE_CONFIG_NAME)
    if override_config:
        paths.append(Path(override_config).expanduser())

    override_env = os.environ.get(OVERRIDE_ENV_NAME)
    if override_env:
        paths.append(Path(override_env).expanduser())

    config_home = Path(DEFAULT_CONFIG_DIR).expanduser()
    for name in CONFIG_NAMES:
        paths.append(config_home / name)

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
        return None, "YAML config found, but PyYAML is not installed; read the file as plain text instead."

    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh), None


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate the optional soia-pkm-translate-article-zh config.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result.")
    args = parser.parse_args()

    candidates = candidate_paths()
    found = next((path for path in candidates if path.is_file()), None)

    result: dict[str, object] = {
        "found": bool(found),
        "path": str(found) if found else None,
        "candidates": [str(path) for path in candidates],
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
            print("No soia-pkm-translate-article-zh config found; using built-in defaults (target_language=zh-CN, mode=normal).")
            print(f"Set {OVERRIDE_CONFIG_NAME} or create {DEFAULT_CONFIG_DIR}/config.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
