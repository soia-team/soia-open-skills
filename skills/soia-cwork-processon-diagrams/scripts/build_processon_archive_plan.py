#!/usr/bin/env python3
"""Build or verify a resumable ProcessOn artifact archive plan from a checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


PLAN_SCHEMA_VERSION = 1
KNOWN_TYPES = {"flowchart", "mindmap", "unknown"}
DEFAULT_EXPORTS = {
    "flowchart": {
        "primary_format": "vsdx",
        "primary_menu": "VISIO文件",
        "fallback_formats": ["pos"],
        "selection_rule": "prefer: 导出全部画布 (.vsdx); fallback: VISIO文件",
    },
    "mindmap": {
        "primary_format": "xmind",
        "primary_menu": "Xmind文件",
        "fallback_formats": ["pos"],
        "selection_rule": "Xmind文件",
    },
    "unknown": {
        "primary_format": None,
        "primary_menu": None,
        "fallback_formats": [],
        "selection_rule": "人工确认图表类型后再选择格式",
    },
}


class PlanError(RuntimeError):
    """Raised when a checkpoint or archive plan is unsafe or inconsistent."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = path.expanduser()
    if path.is_symlink():
        raise PlanError(f"refusing symlink output: {path}")
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


def load_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise PlanError(f"refusing symlink {label}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanError(f"invalid {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlanError(f"{label} must be a JSON object")
    return payload


def safe_posix_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{label} must be a non-empty path")
    normalized = value.replace("\\", "/").strip("/")
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise PlanError(f"unsafe {label}: {value!r}")
    return "/".join(parts)


def validate_checkpoint(checkpoint: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "root_path",
        "source_url",
        "directories",
        "discovered_paths",
        "visited_paths",
        "blocked_paths",
    }
    missing = sorted(required - set(checkpoint))
    if missing:
        raise PlanError(f"checkpoint missing fields: {', '.join(missing)}")
    if not isinstance(checkpoint["directories"], dict):
        raise PlanError("checkpoint directories must be an object")
    if not isinstance(checkpoint["discovered_paths"], list) or not isinstance(
        checkpoint["visited_paths"], list
    ):
        raise PlanError("checkpoint discovered_paths and visited_paths must be lists")
    if not isinstance(checkpoint["blocked_paths"], dict):
        raise PlanError("checkpoint blocked_paths must be an object")


def item_id(directory: str, entry: dict[str, Any]) -> str:
    stable_locator = {
        "directory": directory,
        "title": str(entry.get("title", "")).strip(),
        "type": str(entry.get("type", "unknown")),
        "remote_id": entry.get("remote_id") or entry.get("id") or "",
        "source_url": entry.get("source_url") or entry.get("url") or "",
        "owner": entry.get("owner") or "",
        "remote_updated_at": entry.get("remote_updated_at") or "",
    }
    return sha256_bytes(canonical_json(stable_locator))


def count_same_titles(entries: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for entry in entries:
        key = (entry["source_directory"], entry["title"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_plan(checkpoint_path: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    validate_checkpoint(checkpoint)
    discovered = {
        safe_posix_path(path, "discovered path") for path in checkpoint["discovered_paths"]
    }
    visited = {
        safe_posix_path(path, "visited path") for path in checkpoint["visited_paths"]
    }
    blocked = {
        safe_posix_path(path, "blocked path") for path in checkpoint["blocked_paths"]
    }
    pending = sorted(discovered - visited - blocked)

    entries: list[dict[str, Any]] = []
    confirmation: list[str] = []
    type_counts = {kind: 0 for kind in sorted(KNOWN_TYPES)}

    for directory in sorted(checkpoint["directories"]):
        directory_path = safe_posix_path(directory, "directory path")
        raw_directory = checkpoint["directories"][directory]
        if not isinstance(raw_directory, dict):
            raise PlanError(f"directory entry must be an object: {directory}")
        files = raw_directory.get("files", [])
        if not isinstance(files, list):
            raise PlanError(f"files must be a list: {directory}")
        for raw_entry in files:
            if not isinstance(raw_entry, dict):
                raise PlanError(f"file entry must be an object: {directory}")
            title = str(raw_entry.get("title", "")).strip()
            if not title:
                raise PlanError(f"file title is empty: {directory}")
            kind = str(raw_entry.get("type", "unknown")).strip().lower() or "unknown"
            if kind not in KNOWN_TYPES:
                kind = "unknown"
            policy = DEFAULT_EXPORTS[kind]
            artifact_id = item_id(directory_path, raw_entry)
            item = {
                "artifact_id": artifact_id,
                "source_directory": directory_path,
                "source_path": f"{directory_path}/{title}",
                "title": title,
                "type": kind,
                "owner": raw_entry.get("owner", ""),
                "remote_updated_at": raw_entry.get("remote_updated_at", ""),
                "remote_id": raw_entry.get("remote_id") or raw_entry.get("id") or "",
                "source_url": raw_entry.get("source_url") or raw_entry.get("url") or "",
                "primary_format": policy["primary_format"],
                "primary_menu": policy["primary_menu"],
                "fallback_formats": policy["fallback_formats"],
                "selection_rule": policy["selection_rule"],
                "confirmation_required": kind == "unknown",
                "status": "pending_confirmation" if kind == "unknown" else "planned",
            }
            entries.append(item)
            type_counts[kind] += 1
            if kind == "unknown":
                confirmation.append(artifact_id)

    title_counts = count_same_titles(entries)
    collision_risk_count = 0
    for entry in entries:
        key = (entry["source_directory"], entry["title"])
        if title_counts[key] > 1:
            entry["collision_risk"] = (
                "same title in one directory; preserve artifact_id and never overwrite"
            )
            collision_risk_count += 1
        else:
            entry["collision_risk"] = "none_detected"

    checkpoint_bytes = checkpoint_path.read_bytes()
    inventory_complete = not pending and not blocked
    known_ready = inventory_complete
    full_archive_ready = inventory_complete and not confirmation
    if not inventory_complete:
        archive_status = "inventory_incomplete"
    elif confirmation:
        archive_status = "known_ready_pending_confirmation"
    else:
        archive_status = "ready"
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_type": "processon-artifact-archive",
        "generated_at": now(),
        "checkpoint_path": str(checkpoint_path.resolve()),
        "checkpoint_sha256": sha256_bytes(checkpoint_bytes),
        "source": checkpoint.get("source", "processon"),
        "source_url": checkpoint["source_url"],
        "root_path": checkpoint["root_path"],
        "inventory_complete": inventory_complete,
        "ready_for_known_artifacts": known_ready,
        "ready_for_archive": full_archive_ready,
        "archive_status": archive_status,
        "pending_inventory_paths": pending,
        "blocked_inventory_paths": sorted(blocked),
        "type_counts": type_counts,
        "collision_risk_count": collision_risk_count,
        "counts": {
            "total": len(entries),
            "flowchart": type_counts["flowchart"],
            "mindmap": type_counts["mindmap"],
            "unknown": type_counts["unknown"],
            "pending_confirmation": len(confirmation),
        },
        "confirmation_queue": confirmation,
        "entries": entries,
    }


def verify_plan(plan_path: Path, checkpoint_path: Path) -> dict[str, Any]:
    plan = load_object(plan_path, "archive plan")
    checkpoint = load_object(checkpoint_path, "checkpoint")
    validate_checkpoint(checkpoint)
    current = build_plan(checkpoint_path, checkpoint)
    expected = {entry["artifact_id"] for entry in current["entries"]}
    actual = {entry.get("artifact_id") for entry in plan.get("entries", [])}
    entry_content_match = plan.get("entries") == current.get("entries")
    stage_flags_match = all(
        plan.get(field) == current.get(field)
        for field in (
            "inventory_complete",
            "ready_for_known_artifacts",
            "ready_for_archive",
            "archive_status",
            "pending_inventory_paths",
            "blocked_inventory_paths",
        )
    )
    return {
        "status": "passed"
        if plan.get("checkpoint_sha256") == current["checkpoint_sha256"]
        and actual == expected
        and entry_content_match
        and stage_flags_match
        else "failed",
        "plan_checkpoint_sha256": plan.get("checkpoint_sha256", ""),
        "current_checkpoint_sha256": current["checkpoint_sha256"],
        "missing_artifact_count": len(expected - actual),
        "stale_artifact_count": len(actual - expected),
        "entry_content_match": entry_content_match,
        "stage_flags_match": stage_flags_match,
        "plan_ready_for_known_artifacts": bool(plan.get("ready_for_known_artifacts")),
        "current_ready_for_known_artifacts": bool(
            current.get("ready_for_known_artifacts")
        ),
        "plan_ready_for_archive": bool(plan.get("ready_for_archive")),
        "current_ready_for_archive": bool(current.get("ready_for_archive")),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="build an archive plan from checkpoint")
    build.add_argument("--checkpoint", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify", help="verify a plan against the current checkpoint")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--checkpoint", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        checkpoint = load_object(args.checkpoint, "checkpoint")
        plan = build_plan(args.checkpoint, checkpoint)
        atomic_write_json(args.output, plan)
        print(
            json.dumps(
                {
                    "status": "written",
                    "output": str(args.output),
                    "counts": plan["counts"],
                    "archive_status": plan["archive_status"],
                    "ready_for_known_artifacts": plan["ready_for_known_artifacts"],
                    "ready_for_archive": plan["ready_for_archive"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    result = verify_plan(args.plan, args.checkpoint)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PlanError as exc:
        print(f"error: {exc}")
        raise SystemExit(2)
