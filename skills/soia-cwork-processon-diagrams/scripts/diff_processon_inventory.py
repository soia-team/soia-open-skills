#!/usr/bin/env python3
"""Compare two complete ProcessOn inventory checkpoints without remote APIs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


DELTA_SCHEMA_VERSION = 1


class InventoryDeltaError(RuntimeError):
    """Raised when a snapshot comparison would produce unsafe conclusions."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def safe_posix_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InventoryDeltaError(f"{label} must be a non-empty path")
    normalized = value.replace("\\", "/").strip("/")
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise InventoryDeltaError(f"unsafe {label}: {value!r}")
    return "/".join(parts)


def load_object(path: Path, label: str) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink():
        raise InventoryDeltaError(f"refusing symlink {label}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InventoryDeltaError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InventoryDeltaError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise InventoryDeltaError(f"{label} must be a JSON object")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = path.expanduser()
    if path.is_symlink():
        raise InventoryDeltaError(f"refusing symlink output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_complete_checkpoint(checkpoint: dict[str, Any], label: str) -> dict[str, Any]:
    required = {
        "schema_version",
        "source_url",
        "root_path",
        "discovered_paths",
        "visited_paths",
        "blocked_paths",
        "directories",
    }
    missing = sorted(required - set(checkpoint))
    if missing:
        raise InventoryDeltaError(f"{label} checkpoint missing fields: {', '.join(missing)}")
    if not isinstance(checkpoint["discovered_paths"], list):
        raise InventoryDeltaError(f"{label} discovered_paths must be a list")
    if not isinstance(checkpoint["visited_paths"], list):
        raise InventoryDeltaError(f"{label} visited_paths must be a list")
    if not isinstance(checkpoint["blocked_paths"], dict):
        raise InventoryDeltaError(f"{label} blocked_paths must be an object")
    if not isinstance(checkpoint["directories"], dict):
        raise InventoryDeltaError(f"{label} directories must be an object")

    discovered = {
        safe_posix_path(path, f"{label} discovered path")
        for path in checkpoint["discovered_paths"]
    }
    visited = {
        safe_posix_path(path, f"{label} visited path")
        for path in checkpoint["visited_paths"]
    }
    blocked = {
        safe_posix_path(path, f"{label} blocked path")
        for path in checkpoint["blocked_paths"]
    }
    pending = sorted(discovered - visited - blocked)
    if pending or blocked:
        raise InventoryDeltaError(
            f"{label} checkpoint is incomplete; pending={len(pending)}, blocked={len(blocked)}"
        )
    return {
        "root_path": safe_posix_path(checkpoint["root_path"], f"{label} root path"),
        "source_url": str(checkpoint["source_url"]),
        "directory_count": len(checkpoint["directories"]),
    }


def entry_locator(directory: str, entry: dict[str, Any]) -> tuple[str, str]:
    remote_id = str(entry.get("remote_id") or entry.get("id") or "").strip()
    if remote_id:
        return ("remote_id", f"id:{remote_id}")
    title = str(entry.get("title", "")).strip()
    if not title:
        raise InventoryDeltaError(f"file title is empty: {directory}")
    kind = str(entry.get("type", "unknown")).strip().lower() or "unknown"
    owner = str(entry.get("owner") or "").strip()
    source_url = str(entry.get("source_url") or entry.get("url") or "").strip()
    return ("fallback", "fallback:" + "\x1f".join((directory, title, kind, owner, source_url)))


def normalize_entry(directory: str, entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise InventoryDeltaError(f"file entry must be an object: {directory}")
    identity_kind, identity = entry_locator(directory, entry)
    title = str(entry.get("title", "")).strip()
    return {
        "identity": identity,
        "identity_kind": identity_kind,
        "source_directory": directory,
        "source_path": f"{directory}/{title}",
        "title": title,
        "type": str(entry.get("type", "unknown")).strip().lower() or "unknown",
        "owner": str(entry.get("owner") or "").strip(),
        "remote_updated_at": str(entry.get("remote_updated_at") or "").strip(),
        "remote_id": str(entry.get("remote_id") or entry.get("id") or "").strip(),
        "source_url": str(entry.get("source_url") or entry.get("url") or "").strip(),
    }


def flatten_entries(
    checkpoint: dict[str, Any], label: str
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw_directory, raw_snapshot in checkpoint["directories"].items():
        directory = safe_posix_path(raw_directory, f"{label} directory path")
        if not isinstance(raw_snapshot, dict):
            raise InventoryDeltaError(f"{label} directory snapshot must be an object: {directory}")
        files = raw_snapshot.get("files", [])
        if not isinstance(files, list):
            raise InventoryDeltaError(f"{label} files must be a list: {directory}")
        for raw_entry in files:
            entry = normalize_entry(directory, raw_entry)
            identity = entry["identity"]
            grouped.setdefault(identity, []).append(entry)

    entries: dict[str, dict[str, Any]] = {}
    ambiguous: list[dict[str, Any]] = []
    for identity, matches in grouped.items():
        if len(matches) == 1:
            entries[identity] = matches[0]
            continue
        if matches[0]["identity_kind"] == "remote_id":
            raise InventoryDeltaError(
                f"{label} checkpoint has duplicate stable remote identity: {identity}"
            )
        ambiguous.append(
            {
                "identity": identity,
                "reason": "duplicate_fallback_identity",
                "entries": matches,
            }
        )
    return entries, ambiguous


def changed_entry(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any] | None:
    kinds: list[str] = []
    if previous["identity_kind"] == "remote_id" and previous["source_directory"] != current["source_directory"]:
        kinds.append("moved")
    if previous["identity_kind"] == "remote_id" and previous["title"] != current["title"]:
        kinds.append("renamed")
    if any(
        previous[field] != current[field]
        for field in ("type", "owner", "remote_updated_at", "source_url")
    ):
        kinds.append("updated")
    if not kinds:
        return None
    return {
        "identity": current["identity"],
        "change_kinds": kinds,
        "previous": previous,
        "current": current,
    }


def compare_checkpoints(
    previous_path: Path,
    previous_checkpoint: dict[str, Any],
    current_path: Path,
    current_checkpoint: dict[str, Any],
) -> dict[str, Any]:
    previous_meta = validate_complete_checkpoint(previous_checkpoint, "previous")
    current_meta = validate_complete_checkpoint(current_checkpoint, "current")
    if previous_meta["source_url"] != current_meta["source_url"]:
        raise InventoryDeltaError("previous and current checkpoints have different source_url values")
    if previous_meta["root_path"] != current_meta["root_path"]:
        raise InventoryDeltaError("previous and current checkpoints have different root_path values")

    previous_entries, previous_ambiguous = flatten_entries(previous_checkpoint, "previous")
    current_entries, current_ambiguous = flatten_entries(current_checkpoint, "current")
    previous_ids = set(previous_entries)
    current_ids = set(current_entries)
    shared_ids = sorted(previous_ids & current_ids)
    changes = [
        change
        for identity in shared_ids
        if (change := changed_entry(previous_entries[identity], current_entries[identity]))
        is not None
    ]
    added = [current_entries[identity] for identity in sorted(current_ids - previous_ids)]
    removed_candidates = [
        previous_entries[identity] for identity in sorted(previous_ids - current_ids)
    ]
    moved = sum("moved" in entry["change_kinds"] for entry in changes)
    renamed = sum("renamed" in entry["change_kinds"] for entry in changes)
    updated = sum("updated" in entry["change_kinds"] for entry in changes)
    unchanged = len(shared_ids) - len(changes)
    return {
        "schema_version": DELTA_SCHEMA_VERSION,
        "delta_type": "processon-inventory-snapshot-diff",
        "generated_at": utc_now(),
        "status": (
            "complete_with_ambiguous_entries"
            if previous_ambiguous or current_ambiguous
            else "complete"
        ),
        "scope": {
            "source": "processon",
            "source_url": current_meta["source_url"],
            "root_path": current_meta["root_path"],
        },
        "previous": {
            "checkpoint_path": str(previous_path.resolve()),
            "checkpoint_sha256": sha256_bytes(previous_path.read_bytes()),
            **previous_meta,
        },
        "current": {
            "checkpoint_path": str(current_path.resolve()),
            "checkpoint_sha256": sha256_bytes(current_path.read_bytes()),
            **current_meta,
        },
        "counts": {
            "previous_total": len(previous_entries) + sum(
                len(item["entries"]) for item in previous_ambiguous
            ),
            "current_total": len(current_entries) + sum(
                len(item["entries"]) for item in current_ambiguous
            ),
            "previous_tracked": len(previous_entries),
            "current_tracked": len(current_entries),
            "previous_ambiguous": sum(
                len(item["entries"]) for item in previous_ambiguous
            ),
            "current_ambiguous": sum(
                len(item["entries"]) for item in current_ambiguous
            ),
            "added": len(added),
            "changed": len(changes),
            "moved": moved,
            "renamed": renamed,
            "updated": updated,
            "removed_candidates": len(removed_candidates),
            "unchanged": unchanged,
        },
        "added": added,
        "changed": changes,
        "removed_candidates": removed_candidates,
        "ambiguous_entries": {
            "previous": previous_ambiguous,
            "current": current_ambiguous,
        },
        "notes": [
            "This is a comparison of two complete local snapshots, not a ProcessOn event/API delta.",
            "A removal is a candidate only after both snapshots completed with no blocked paths.",
            "Moves and renames are asserted only for entries carrying a stable remote_id/id; fallback identities become add/remove candidates.",
            "Duplicate fallback identities are isolated from delta conclusions; assign a stable remote_id/id before treating them as added, removed, moved, or renamed.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, required=True, help="previous complete checkpoint")
    parser.add_argument("--current", type=Path, required=True, help="current complete checkpoint")
    parser.add_argument("--output", type=Path, required=True, help="delta JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    previous = load_object(args.previous, "previous checkpoint")
    current = load_object(args.current, "current checkpoint")
    report = compare_checkpoints(args.previous, previous, args.current, current)
    atomic_write_json(args.output, report)
    print(json.dumps({"status": "written", "output": str(args.output), "counts": report["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InventoryDeltaError as exc:
        raise SystemExit(f"error: {exc}")
