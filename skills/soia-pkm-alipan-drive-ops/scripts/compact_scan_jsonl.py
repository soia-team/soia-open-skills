#!/usr/bin/env python3
# @created_by  openai/gpt-5-codex
# @created_at  2026-07-15 11:32:00
# @modified_by openai/gpt-5-codex
# @modified_at 2026-07-15 12:12:00
# @version     0.1.1
# @description Atomically compact duplicate physical rows in scan_drive JSONL output
# @changelog   Make both output modes atomic and reject ambiguous same-path output
"""Compact a ``scan_drive.py`` JSONL file without changing row order.

The first occurrence of every physical row is retained.  In-place replacement
is atomic and creates a backup by default.  Malformed rows abort replacement so
an interrupted or corrupt inventory cannot be silently normalized away.
"""

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from scan_drive import row_identity


def compact(source, destination):
    """Write unique valid rows and return a machine-readable audit summary."""

    seen = set()
    total = unique = duplicates = malformed = 0
    with source.open(encoding="utf-8") as reader, destination.open(
        "w", encoding="utf-8"
    ) as writer:
        for line in reader:
            total += 1
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                malformed += 1
                continue
            if not isinstance(row, dict):
                malformed += 1
                continue
            identity = row_identity(row)
            if identity in seen:
                duplicates += 1
                continue
            seen.add(identity)
            writer.write(json.dumps(row, ensure_ascii=False) + "\n")
            unique += 1
    return {
        "source": str(source),
        "total_rows": total,
        "unique_rows": unique,
        "duplicate_rows": duplicates,
        "malformed_rows": malformed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument(
        "--backup-suffix",
        default=".pre-compact",
        help="In-place backup suffix; pass an empty string to disable the backup",
    )
    args = parser.parse_args()

    if args.in_place == bool(args.output):
        parser.error("choose exactly one of --in-place or --output")
    source = args.input.resolve()
    if not source.is_file():
        parser.error(f"input is not a file: {source}")

    destination = source if args.in_place else args.output.resolve()
    if not args.in_place and destination == source:
        parser.error("use --in-place when input and output are the same path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".compact", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)

    try:
        summary = compact(source, temporary)
        if summary["malformed_rows"]:
            raise SystemExit(
                "refusing replacement because malformed_rows="
                f"{summary['malformed_rows']}"
            )
        if args.in_place:
            if args.backup_suffix:
                backup = source.with_name(source.name + args.backup_suffix)
                shutil.copy2(source, backup)
                summary["backup"] = str(backup)
        os.replace(temporary, destination)
        summary["output"] = str(destination)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    main()
