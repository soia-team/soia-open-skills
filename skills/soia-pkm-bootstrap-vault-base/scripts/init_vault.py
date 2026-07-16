#!/usr/bin/env python3
"""Initialize an AI-native Markdown knowledge base from a JSON/YAML config.

The script is intentionally configuration-driven: the open-source skill should
not assume every user wants the same folder names, log locations, templates, or
AI adapter files.
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).with_name("default_config.json")


def read_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"config not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("YAML config requires PyYAML; use JSON for zero-dependency setup") from exc
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"config root must be an object: {path}")
    return data


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def file_entries(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [{"path": path, "content": content} for path, content in value.items()]
    if isinstance(value, list):
        entries: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict) or "path" not in item:
                raise ValueError("files entries must be objects with a path field")
            entries.append(item)
        return entries
    raise ValueError("files must be a list or object")


def merge_file_entries(base: list[dict[str, Any]], override: Any) -> list[dict[str, Any]]:
    by_path = {entry["path"]: deepcopy(entry) for entry in base}

    if override is None:
        return list(by_path.values())

    if isinstance(override, list) or isinstance(override, dict) and "path" in override:
        for entry in file_entries(override if isinstance(override, list) else [override]):
            by_path[entry["path"]] = deepcopy(entry)
        return list(by_path.values())

    if isinstance(override, dict):
        for path in override.get("remove", []):
            by_path.pop(path, None)
        for entry in file_entries(override.get("add")):
            by_path[entry["path"]] = deepcopy(entry)
        for entry in file_entries(override.get("replace")):
            by_path[entry["path"]] = deepcopy(entry)
        return list(by_path.values())

    raise ValueError("files override must be a list or object")


def merge_directories(base: list[str], override: Any) -> list[str]:
    if override is None:
        return unique(list(base))
    if isinstance(override, list):
        return unique([str(item) for item in override])
    if not isinstance(override, dict):
        raise ValueError("directories must be a list or object")
    if "replace" in override:
        dirs = [str(item) for item in override["replace"]]
    else:
        dirs = list(base)
    remove = {str(item) for item in override.get("remove", [])}
    dirs = [item for item in dirs if item not in remove]
    dirs.extend(str(item) for item in override.get("add", []))
    return unique(dirs)


def merge_config(default: dict[str, Any], custom: dict[str, Any] | None) -> dict[str, Any]:
    if not custom:
        return deepcopy(default)

    extends_default = custom.get("extends_default", True)
    cfg = deepcopy(default) if extends_default else {"directories": [], "files": []}

    cfg["directories"] = merge_directories(cfg.get("directories", []), custom.get("directories"))
    cfg["files"] = merge_file_entries(file_entries(cfg.get("files")), custom.get("files"))

    for key, value in custom.items():
        if key not in {"schema_version", "extends_default", "directories", "files"}:
            cfg[key] = deepcopy(value)
    return cfg


def render_content(raw: Any) -> str:
    if isinstance(raw, list):
        return "\n".join(str(line) for line in raw) + "\n"
    if isinstance(raw, str):
        return raw
    raise ValueError("file content must be a string or list of lines")


def is_obsidian_path(relative_path: str) -> bool:
    """Return whether a configured path belongs to Obsidian-only output."""
    parts = Path(relative_path).parts
    return ".obsidian" in parts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", nargs="?", help="目标 vault 路径")
    parser.add_argument(
        "--config",
        help="JSON/YAML 配置文件；默认使用 scripts/default_config.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已存在的种子文件；默认只创建不存在的文件",
    )
    parser.add_argument(
        "--print-default-config",
        action="store_true",
        help="打印默认 JSON 配置后退出，方便复制后改成自己的结构",
    )
    parser.add_argument(
        "--no-obsidian",
        action="store_true",
        help="跳过配置中 .obsidian/** 的目录和文件；默认行为保持不变",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    default_cfg = read_config(DEFAULT_CONFIG)

    if args.print_default_config:
        print(json.dumps(default_cfg, ensure_ascii=False, indent=2))
        return 0

    if not args.vault:
        raise ValueError("missing target vault path")

    custom_cfg = read_config(Path(args.config).expanduser()) if args.config else None
    cfg = merge_config(default_cfg, custom_cfg)
    vault = Path(args.vault).expanduser().resolve()

    directories = [str(item) for item in cfg.get("directories", [])]
    files = file_entries(cfg.get("files"))
    if args.no_obsidian:
        directories = [rel for rel in directories if not is_obsidian_path(rel)]
        files = [entry for entry in files if not is_obsidian_path(str(entry["path"]))]

    created_dirs = 0
    for rel in directories:
        path = vault / rel
        if not path.exists():
            created_dirs += 1
        path.mkdir(parents=True, exist_ok=True)

    created_files = skipped_files = overwritten_files = 0
    for entry in files:
        rel = str(entry["path"])
        path = vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        exists = path.exists()
        if exists and not args.force:
            skipped_files += 1
            continue
        path.write_text(render_content(entry.get("content", "")), encoding="utf-8")
        if exists:
            overwritten_files += 1
        else:
            created_files += 1

    print(f"✅ vault 骨架已建于：{vault}")
    print(f"   配置：{Path(args.config).expanduser() if args.config else DEFAULT_CONFIG}")
    print(f"   目录：新建 {created_dirs} / 共 {len(directories)}")
    print(
        "   种子文件："
        f"新建 {created_files}，覆盖 {overwritten_files}，已存在跳过 {skipped_files}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"❌ init_vault failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
