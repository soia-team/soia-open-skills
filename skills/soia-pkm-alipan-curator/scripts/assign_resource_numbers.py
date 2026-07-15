#!/usr/bin/env python3
"""Assign stable fixed-width numbers to reviewed resource-directory mappings.

The script is deliberately map-first: it updates reviewed TSV decisions before
action plans are regenerated. Files are never numbered, technical descendants
are outside the mapping boundary, and existing numbered directory names are
reserved across every supplied map.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"missing TSV header: {path}")
        return list(reader.fieldnames), list(reader)


def read_inventory(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                raise ValueError(f"{path}:{line_number}: missing id")
            if item_id in result:
                raise ValueError(f"{path}:{line_number}: duplicate id {item_id}")
            result[item_id] = item
    return result


def required(row: dict[str, str], column: str, source: Path, row_number: int) -> str:
    value = str(row.get(column, "")).strip()
    if not value:
        raise ValueError(f"{source}:{row_number}: missing {column}")
    return value


def excluded(parent: str, roots: list[str]) -> bool:
    return any(parent == root.rstrip("/") for root in roots)


def assign_numbers(
    inventory: dict[str, dict],
    editable: list[tuple[Path, list[str], list[dict[str, str]]]],
    reserves: list[tuple[Path, list[dict[str, str]]]],
    *,
    id_column: str,
    target_column: str,
    name_column: str,
    reserve_id_column: str,
    reserve_target_column: str,
    reserve_name_column: str,
    exclude_targets: list[str],
    width: int,
    start: int,
    step: int,
) -> dict:
    numbered = re.compile(rf"^(\d{{{width}}})_")
    occupied: dict[str, set[int]] = defaultdict(set)
    final_paths: dict[tuple[str, str], str] = {}

    def reserve_rows(path: Path, rows: list[dict[str, str]], iid: str, target: str, name: str) -> None:
        for row_number, row in enumerate(rows, 2):
            item_id = required(row, iid, path, row_number)
            item = inventory.get(item_id)
            if item is None:
                raise ValueError(f"{path}:{row_number}: id absent from inventory: {item_id}")
            if not item.get("dir"):
                continue
            parent = required(row, target, path, row_number).rstrip("/")
            if parent.startswith("<"):
                continue
            value = required(row, name, path, row_number)
            match = numbered.match(value)
            if match:
                occupied[parent].add(int(match.group(1)))

    for path, _, rows in editable:
        reserve_rows(path, rows, id_column, target_column, name_column)
    for path, rows in reserves:
        reserve_rows(path, rows, reserve_id_column, reserve_target_column, reserve_name_column)

    changed = 0
    assignments: list[dict[str, str | int]] = []
    for path, _, rows in editable:
        for row_number, row in enumerate(rows, 2):
            item_id = required(row, id_column, path, row_number)
            item = inventory[item_id]
            parent = required(row, target_column, path, row_number).rstrip("/")
            name = required(row, name_column, path, row_number)
            if (
                item.get("dir")
                and not parent.startswith("<")
                and not numbered.match(name)
                and not excluded(parent, exclude_targets)
            ):
                number = start
                while number in occupied[parent]:
                    number += step
                if number >= 10 ** width:
                    raise ValueError(f"number width exhausted under {parent}")
                row[name_column] = f"{number:0{width}d}_{name}"
                occupied[parent].add(number)
                changed += 1
                assignments.append({
                    "file_id": item_id,
                    "target_parent": parent,
                    "number": number,
                    "name": row[name_column],
                })

            key = (parent, row[name_column])
            previous = final_paths.get(key)
            if previous and previous != item_id:
                raise ValueError(f"target collision {parent}/{row[name_column]}: {previous}, {item_id}")
            final_paths[key] = item_id

    return {"changed": changed, "assignments": assignments}


def _temporary_path(path: Path) -> tuple[int, Path]:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    return descriptor, Path(name)


def _remove_temporary(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _write_tsv_temporary(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> Path:
    descriptor, temporary = _temporary_path(path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        _remove_temporary(temporary)
        raise
    return temporary


def _write_bytes_temporary(path: Path, contents: bytes) -> Path:
    descriptor, temporary = _temporary_path(path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        _remove_temporary(temporary)
        raise
    return temporary


def _restore_original(path: Path, contents: bytes) -> None:
    temporary = _write_bytes_temporary(path, contents)
    try:
        os.replace(temporary, path)
    finally:
        _remove_temporary(temporary)


def write_tsvs_transactionally(
    outputs: list[tuple[Path, list[str], list[dict[str, str]]]],
) -> None:
    """Replace every output only after all replacement files are ready.

    Replacing multiple filesystem paths cannot be a single atomic operation.
    Keeping the original bytes lets us restore every target if a later replace
    fails, which prevents a partially updated set of reviewed maps.
    """
    originals = [(path, path.read_bytes()) for path, _, _ in outputs]
    prepared: list[tuple[Path, Path]] = []
    try:
        for path, fieldnames, rows in outputs:
            prepared.append((path, _write_tsv_temporary(path, fieldnames, rows)))
    except BaseException:
        for _, temporary in prepared:
            _remove_temporary(temporary)
        raise

    try:
        for path, temporary in prepared:
            os.replace(temporary, path)
    except OSError as replace_error:
        rollback_error: OSError | None = None
        for path, contents in originals:
            try:
                _restore_original(path, contents)
            except OSError as error:
                rollback_error = error
        if rollback_error is not None:
            raise OSError(
                f"{replace_error}; rollback also failed: {rollback_error}"
            ) from replace_error
        raise
    finally:
        for _, temporary in prepared:
            _remove_temporary(temporary)


def write_tsv_atomic(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """Keep the single-file writer API while using the shared transaction path."""
    write_tsvs_transactionally([(path, fieldnames, rows)])


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign fixed-width numbers to mapped resource directories.")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--reserve-input", type=Path, action="append", default=[])
    parser.add_argument("--id-column", default="file_id")
    parser.add_argument("--target-column", default="target_parent")
    parser.add_argument("--name-column", default="normalized_name")
    parser.add_argument("--reserve-id-column", default="file_id")
    parser.add_argument("--reserve-target-column", default="final_target")
    parser.add_argument("--reserve-name-column", default="final_name")
    parser.add_argument("--exclude-target", action="append", default=[])
    parser.add_argument("--width", type=int, default=3)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--step", type=int, default=1)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    try:
        if not args.in_place:
            raise ValueError("--in-place is required; reviewed maps are updated atomically")
        if args.width < 1 or args.start < 0 or args.step < 1:
            raise ValueError("width must be >=1, start >=0, and step >=1")
        inventory = read_inventory(args.inventory)
        editable = [(path, *read_tsv(path)) for path in args.input]
        reserves = [(path, read_tsv(path)[1]) for path in args.reserve_input]
        report = assign_numbers(
            inventory,
            editable,
            reserves,
            id_column=args.id_column,
            target_column=args.target_column,
            name_column=args.name_column,
            reserve_id_column=args.reserve_id_column,
            reserve_target_column=args.reserve_target_column,
            reserve_name_column=args.reserve_name_column,
            exclude_targets=args.exclude_target,
            width=args.width,
            start=args.start,
            step=args.step,
        )
        write_tsvs_transactionally(editable)
    except (OSError, ValueError, json.JSONDecodeError, csv.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
