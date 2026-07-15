#!/usr/bin/env python3
"""Build a deterministic reclassification plan from a reviewed TSV map.

This script only writes a JSONL plan. It never calls aliyunpan or changes cloud state.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path, PurePosixPath


def cloud_path(*parts: str) -> str:
    cleaned: list[str] = []
    for part in parts:
        if part:
            cleaned.extend(piece for piece in str(part).split("/") if piece)
    return "/" + "/".join(cleaned)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_inventory(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            item_id = str(row.get("id", "")).strip()
            if not item_id:
                raise ValueError(f"inventory line {line_number} has no id")
            if item_id in rows:
                raise ValueError(f"duplicate inventory id: {item_id}")
            rows[item_id] = row
    return rows


def inventory_full_path(row: dict) -> str:
    return cloud_path(str(row.get("path", "")), str(row.get("name", "")))


def within(path: str, root: str) -> bool:
    normalized_path = cloud_path(path)
    normalized_root = cloud_path(root)
    return normalized_path == normalized_root or normalized_path.startswith(normalized_root + "/")


def required(row: dict[str, str], column: str, row_number: int) -> str:
    value = str(row.get(column, "")).strip()
    if not value:
        raise ValueError(f"mapping row {row_number}: missing {column}")
    return value


def build_plan(args: argparse.Namespace) -> tuple[list[dict], dict]:
    rows = read_tsv(args.input)
    inventory = read_inventory(args.inventory) if args.inventory else {}
    skip_target = re.compile(args.skip_target_regex)
    selected: list[dict] = []
    seen_ids: set[str] = set()
    final_paths: dict[str, str] = {}

    for row_number, row in enumerate(rows, 2):
        item_id = required(row, args.id_column, row_number)
        if item_id in seen_ids:
            raise ValueError(f"mapping row {row_number}: duplicate file_id {item_id}")
        seen_ids.add(item_id)

        target_value = required(row, args.target_column, row_number)
        if skip_target.search(target_value):
            continue
        target_parent = (
            cloud_path(target_value)
            if target_value.startswith("/")
            else cloud_path(args.target_base, target_value)
        )
        if args.include_target_prefix and not any(
            within(target_parent, prefix) for prefix in args.include_target_prefix
        ):
            continue

        inventory_item = inventory.get(item_id) if inventory else None
        if args.source_from_inventory:
            if inventory_item is None:
                raise ValueError(
                    f"mapping row {row_number}: --source-from-inventory requires id in inventory: {item_id}"
                )
            source_path = inventory_full_path(inventory_item)
            mapped_name = str(row.get(args.source_name_column, "")).strip()
            if mapped_name and mapped_name != str(inventory_item.get("name", "")):
                raise ValueError(
                    f"mapping row {row_number}: source name mismatch for {item_id}: "
                    f"mapping={mapped_name}, inventory={inventory_item.get('name', '')}"
                )
        else:
            source_path_value = str(row.get(args.source_path_column, "")).strip()
            if source_path_value:
                source_path = cloud_path(source_path_value)
            else:
                source_name = required(row, args.source_name_column, row_number)
                source_group = str(row.get(args.source_group_column, "")).strip()
                source_path = cloud_path(args.source_base, source_group, source_name)

        normalized_name = (
            str(row.get(args.name_column, "")).strip() if args.name_column else ""
        ) or PurePosixPath(source_path).name
        if "/" in normalized_name:
            raise ValueError(
                f"mapping row {row_number}: normalized name must be one component: {normalized_name}"
            )
        final_path = cloud_path(target_parent, normalized_name)
        previous = final_paths.get(final_path)
        if previous and previous != item_id:
            raise ValueError(
                f"mapping row {row_number}: target collision {final_path}: {previous}, {item_id}"
            )
        final_paths[final_path] = item_id

        if inventory:
            if inventory_item is None:
                raise ValueError(f"mapping row {row_number}: id absent from inventory: {item_id}")
            actual = inventory_full_path(inventory_item)
            if actual != source_path:
                raise ValueError(
                    f"mapping row {row_number}: source mismatch for {item_id}: "
                    f"mapping={source_path}, inventory={actual}"
                )

        if source_path != final_path:
            selected.append({
                "file_id": item_id,
                "source": source_path,
                "target_parent": target_parent,
                "normalized_name": normalized_name,
                "row_number": row_number,
            })

    actions: list[dict] = []
    target_parents = sorted(
        {item["target_parent"] for item in selected},
        key=lambda value: (value.count("/"), value),
    )
    mkdir_actions = []
    if not getattr(args, "no_mkdir", False):
        for index, target_parent in enumerate(target_parents, 1):
            mkdir_actions.append({
                "action_id": f"{args.action_prefix}-MK{index:04d}",
                "op": "mkdir",
                "to": target_parent,
                "reason": "create mapped target directory",
            })
    actions.extend(mkdir_actions)

    move_index = 0
    rename_index = 0
    for item in selected:
        source_parent = str(PurePosixPath(item["source"]).parent)
        moved_path = cloud_path(item["target_parent"], PurePosixPath(item["source"]).name)
        if source_parent != item["target_parent"]:
            move_index += 1
            actions.append({
                "action_id": f"{args.action_prefix}-MV{move_index:04d}",
                "op": "mv",
                "from": item["source"],
                "to": item["target_parent"],
                "file_id": item["file_id"],
                "reason": f"apply reviewed TSV mapping row {item['row_number']}",
            })
        else:
            moved_path = item["source"]

        final_path = cloud_path(item["target_parent"], item["normalized_name"])
        if moved_path != final_path:
            rename_index += 1
            actions.append({
                "action_id": f"{args.action_prefix}-RN{rename_index:04d}",
                "op": "rename",
                "from": moved_path,
                "to": final_path,
                "file_id": item["file_id"],
                "reason": f"apply reviewed normalized name from TSV row {item['row_number']}",
            })

    return actions, {
        "mapping_rows": len(rows),
        "selected_items": len(selected),
        "mkdir_actions": len(mkdir_actions),
        "move_actions": move_index,
        "rename_actions": rename_index,
        "total_actions": len(actions),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a reviewed TSV classification map into a dry-run-first JSONL plan."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--source-base", default="/")
    parser.add_argument(
        "--source-from-inventory",
        action="store_true",
        help="derive each source path from inventory file_id; also verify source_name when present",
    )
    parser.add_argument("--target-base", default="/")
    parser.add_argument(
        "--include-target-prefix",
        action="append",
        default=[],
        help="only emit mappings whose target is inside this cloud prefix; repeatable",
    )
    parser.add_argument(
        "--no-mkdir",
        action="store_true",
        help="omit mkdir actions while keeping move and rename actions",
    )
    parser.add_argument("--source-path-column", default="source_path")
    parser.add_argument("--source-name-column", default="source_name")
    parser.add_argument("--source-group-column", default="source_group")
    parser.add_argument("--target-column", default="target_parent")
    parser.add_argument("--name-column", default="normalized_name")
    parser.add_argument("--id-column", default="file_id")
    parser.add_argument("--skip-target-regex", default=r"^<")
    parser.add_argument("--action-prefix", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        actions, summary = build_plan(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            for action in actions:
                handle.write(json.dumps(action, ensure_ascii=False, separators=(",", ":")) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
