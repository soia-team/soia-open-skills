#!/usr/bin/env python3
"""Merge classifier rows, class targets and controller overrides into a standard TSV map."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path, PurePosixPath


def cloud_path(*parts: str) -> str:
    return "/" + "/".join(
        piece for part in parts if part for piece in str(part).split("/") if piece
    )


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_inventory(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            item_id = str(row.get("id", ""))
            if item_id in result:
                raise ValueError(f"duplicate inventory id: {item_id}")
            result[item_id] = row
    return result


def as_parent_and_name(target: str, source_name: str) -> tuple[str, str]:
    normalized = cloud_path(target)
    suffix = PurePosixPath(normalized).suffix
    if suffix and suffix.lower() == PurePosixPath(source_name).suffix.lower():
        return str(PurePosixPath(normalized).parent), PurePosixPath(normalized).name
    return normalized, source_name


def build_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    classified = read_tsv(args.classification)
    targets = {
        row[args.class_name_column].strip(): row[args.class_target_column].strip()
        for row in read_tsv(args.class_targets)
    }
    overrides = {
        row[args.id_column].strip(): row
        for row in read_tsv(args.overrides)
    } if args.overrides else {}
    inventory = read_inventory(args.inventory)
    seen: set[str] = set()
    output: list[dict[str, str]] = []

    for line_number, row in enumerate(classified, 2):
        item_id = str(row.get(args.id_column, "")).strip()
        source_name = str(row.get(args.name_column, "")).strip()
        class_name = str(row.get(args.class_column, "")).strip()
        if not item_id or not source_name or not class_name:
            raise ValueError(f"classification row {line_number}: missing id/name/class")
        if item_id in seen:
            raise ValueError(f"classification row {line_number}: duplicate id {item_id}")
        seen.add(item_id)
        item = inventory.get(item_id)
        if item is None:
            raise ValueError(f"classification row {line_number}: id absent from inventory {item_id}")
        if str(item.get("name", "")) != source_name:
            raise ValueError(
                f"classification row {line_number}: source name mismatch: "
                f"mapping={source_name}, inventory={item.get('name', '')}"
            )

        override = overrides.get(item_id)
        if override:
            target_value = str(override.get(args.override_target_column, "")).strip()
            status = str(override.get(args.override_status_column, "")).strip() or "controller-override"
        else:
            target_value = targets.get(class_name, "")
            status = "classified-" + (str(row.get(args.confidence_column, "")).strip() or "unknown")
        if not target_value:
            raise ValueError(f"classification row {line_number}: no target for class {class_name}")
        target_parent, normalized_name = as_parent_and_name(target_value, source_name)
        output.append({
            "file_id": item_id,
            "source_path": cloud_path(str(item.get("path", "")), source_name),
            "target_parent": target_parent,
            "normalized_name": normalized_name,
            "status": status,
        })

    if args.expected_rows is not None and len(output) != args.expected_rows:
        raise ValueError(f"expected {args.expected_rows} rows, got {len(output)}")
    unknown_overrides = sorted(set(overrides) - seen)
    if unknown_overrides:
        raise ValueError(f"override ids absent from classification: {unknown_overrides}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--class-targets", type=Path, required=True)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int)
    parser.add_argument("--id-column", default="file_id")
    parser.add_argument("--name-column", default="file_name")
    parser.add_argument("--class-column", default="agent_class")
    parser.add_argument("--confidence-column", default="confidence")
    parser.add_argument("--class-name-column", default="class_name")
    parser.add_argument("--class-target-column", default="target_parent")
    parser.add_argument("--override-target-column", default="proposed_target")
    parser.add_argument("--override-status-column", default="decision_state")
    args = parser.parse_args()
    try:
        rows = build_rows(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["file_id", "source_path", "target_parent", "normalized_name", "status"],
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"rows": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
