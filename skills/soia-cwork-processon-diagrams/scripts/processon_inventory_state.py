#!/usr/bin/env python3
"""Persist resumable ProcessOn directory inventory checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
SKILL_NAME = "soia-cwork-processon-diagrams"
RUN_SUBDIRECTORIES = (
    "inventory",
    "inventory/batches",
    "analysis",
    "artifacts",
    "handoff",
    "verification",
)


class InventoryStateError(RuntimeError):
    """Raised when an inventory checkpoint is unsafe or invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_path(value: str) -> str:
    parts = [part.strip() for part in value.replace("\\", "/").split("/")]
    normalized = "/".join(part for part in parts if part)
    if not normalized or normalized in {".", ".."}:
        raise InventoryStateError(f"invalid inventory path: {value!r}")
    if any(part in {".", ".."} for part in normalized.split("/")):
        raise InventoryStateError(f"relative path segments are not allowed: {value!r}")
    return normalized


def new_state(*, root_path: str, source_url: str, now: str | None = None) -> dict[str, Any]:
    timestamp = now or utc_now()
    root = normalize_path(root_path)
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "processon",
        "source_url": source_url,
        "root_path": root,
        "created_at": timestamp,
        "updated_at": timestamp,
        "discovered_paths": [root],
        "visited_paths": [],
        "blocked_paths": {},
        "directories": {},
        "applied_batches": [],
    }


def validate_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != SCHEMA_VERSION:
        raise InventoryStateError("unsupported inventory state schema_version")
    for key in (
        "root_path",
        "discovered_paths",
        "visited_paths",
        "blocked_paths",
        "directories",
        "applied_batches",
    ):
        if key not in state:
            raise InventoryStateError(f"missing state field: {key}")
    if not isinstance(state["discovered_paths"], list):
        raise InventoryStateError("discovered_paths must be a list")
    if not isinstance(state["visited_paths"], list):
        raise InventoryStateError("visited_paths must be a list")
    if not isinstance(state["blocked_paths"], dict):
        raise InventoryStateError("blocked_paths must be an object")
    if not isinstance(state["directories"], dict):
        raise InventoryStateError("directories must be an object")
    if not isinstance(state["applied_batches"], list):
        raise InventoryStateError("applied_batches must be a list")


def load_state(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise InventoryStateError(f"refusing symlink state file: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InventoryStateError(f"state file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InventoryStateError(f"invalid state JSON: {exc}") from exc
    if not isinstance(state, dict):
        raise InventoryStateError("inventory state root must be an object")
    validate_state(state)
    return state


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    original_path = path.expanduser()
    if original_path.is_symlink():
        raise InventoryStateError(f"refusing symlink state file: {original_path}")
    path = original_path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise InventoryStateError(f"refusing symlink state file: {path}")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
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


def atomic_write_text(path: Path, content: str) -> None:
    original_path = path.expanduser()
    if original_path.is_symlink():
        raise InventoryStateError(f"refusing symlink text file: {original_path}")
    path = original_path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise InventoryStateError(f"refusing symlink {label}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InventoryStateError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InventoryStateError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise InventoryStateError(f"{label} root must be an object")
    return payload


def safe_run_file(run_dir: Path, relative: str, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise InventoryStateError(f"{label} path must be a non-empty string")
    if "\\" in relative:
        raise InventoryStateError(f"{label} path must use forward slashes: {relative!r}")
    relative_path = Path(relative)
    if relative_path.is_absolute() or any(part in {".", ".."} for part in relative_path.parts):
        raise InventoryStateError(f"unsafe {label} path: {relative!r}")
    root = run_dir.resolve(strict=False)
    unresolved = root
    for part in relative_path.parts:
        unresolved /= part
        if unresolved.is_symlink():
            raise InventoryStateError(f"refusing symlink {label}: {relative!r}")
    target = unresolved.resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise InventoryStateError(f"{label} escapes run directory: {relative!r}") from exc
    return target


def default_state_root(
    *, environ: dict[str, str] | None = None, home: Path | None = None
) -> Path:
    env = os.environ if environ is None else environ
    user_home = Path.home() if home is None else home
    xdg_state = env.get("XDG_STATE_HOME", "").strip()
    base = Path(xdg_state).expanduser() if xdg_state else user_home / ".local" / "state"
    return (base / SKILL_NAME).resolve(strict=False)


def resolve_run_dir(
    *, run_dir: Path | None, run_id: str | None, state_root: Path | None = None
) -> Path:
    if run_dir is not None:
        candidate = run_dir.expanduser()
    elif run_id:
        safe_run_id = normalize_path(run_id)
        if "/" in safe_run_id:
            raise InventoryStateError("run_id must be one path segment")
        candidate = (state_root or default_state_root()) / "runs" / safe_run_id
    else:
        raise InventoryStateError("provide --run-dir or --run-id")
    if candidate.is_symlink():
        raise InventoryStateError(f"refusing symlink run directory: {candidate}")
    return candidate.resolve(strict=False)


def run_state_path(run_dir: Path) -> Path:
    return run_dir / "inventory" / "checkpoint.json"


def initialize_run_bundle(
    run_dir: Path,
    *,
    root_path: str,
    source_url: str,
    now: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if run_dir.exists() and any(run_dir.iterdir()):
        raise InventoryStateError(f"run directory is not empty: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(run_dir, 0o700)
    for relative in RUN_SUBDIRECTORIES:
        directory = run_dir / relative
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
    timestamp = now or utc_now()
    state = new_state(root_path=root_path, source_url=source_url, now=timestamp)
    atomic_write_json(run_state_path(run_dir), state)
    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_dir.name,
        "created_at": timestamp,
        "updated_at": timestamp,
        "status": "inventory_running",
        "scope": normalize_path(root_path),
        "source_url": source_url,
        "files": {
            "checkpoint": "inventory/checkpoint.json",
            "batches": "inventory/batches",
            "handoff": "handoff",
            "progress": "handoff/progress.md",
            "receipt": "handoff/receipt.md",
            "inventory_audit": None,
            "verification": "verification",
        },
        "execution_chain": [
            "inventory-init",
            "browser-batch",
            "checkpoint-record",
            "gap-audit",
            "content-archive",
        ],
        "batches": [],
        "counts": state_summary(state),
    }
    atomic_write_json(run_dir / "run.json", run)
    write_progress(run_dir, run, state)
    return state, run


def canonical_batch_bytes(batch: dict[str, Any]) -> bytes:
    return (
        json.dumps(batch, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def archive_batch(run_dir: Path, batch: dict[str, Any]) -> tuple[str, Path]:
    payload = canonical_batch_bytes(batch)
    batch_id = hashlib.sha256(payload).hexdigest()
    batch_number = len(list((run_dir / "inventory" / "batches").glob("*.json"))) + 1
    target = run_dir / "inventory" / "batches" / f"{batch_number:04d}-{batch_id[:12]}.json"
    existing = list((run_dir / "inventory" / "batches").glob(f"*-{batch_id[:12]}.json"))
    if existing:
        recorded = json.loads(existing[0].read_text(encoding="utf-8"))
        if canonical_batch_bytes(recorded) != payload:
            raise InventoryStateError(f"batch hash collision: {batch_id}")
        return batch_id, existing[0]
    atomic_write_json(target, batch)
    return batch_id, target


def progress_markdown(run: dict[str, Any], state: dict[str, Any]) -> str:
    summary = state_summary(state)
    lines = [
        "# ProcessOn 盘点进度",
        "",
        f"- run_id: `{run.get('run_id', '')}`",
        f"- status: `{run.get('status', 'inventory_running')}`",
        f"- scope: `{run.get('scope', state['root_path'])}`",
        f"- updated_at: `{run.get('updated_at', state['updated_at'])}`",
        f"- discovered: {summary['discovered_count']}",
        f"- visited: {summary['visited_count']}",
        f"- pending: {summary['pending_count']}",
        f"- blocked: {summary['blocked_count']}",
        f"- files: {summary['file_entry_count']}",
        f"- batches: {summary['applied_batch_count']}",
    ]
    audit_path = run.get("files", {}).get("inventory_audit")
    if audit_path:
        lines.append(f"- latest_audit: `{audit_path}`")
    lines.extend(["", "## 待访问目录", ""])
    lines.extend(
        [f"- `{path}`" for path in summary["pending_paths"]]
        or ["- 无"]
    )
    lines.extend(["", "## 受阻目录", ""])
    lines.extend(
        [f"- `{path}`" for path in summary["blocked_paths"]]
        or ["- 无"]
    )
    return "\n".join(lines) + "\n"


def write_progress(run_dir: Path, run: dict[str, Any], state: dict[str, Any]) -> Path:
    relative = run.get("files", {}).get("progress", "handoff/progress.md")
    target = safe_run_file(run_dir, relative, label="progress")
    atomic_write_text(target, progress_markdown(run, state))
    return target


def update_run_metadata(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    run_path = run_dir / "run.json"
    run = load_json_object(run_path, label="run.json")
    summary = state_summary(state)
    files = run.setdefault("files", {})
    files.setdefault("checkpoint", "inventory/checkpoint.json")
    files.setdefault("batches", "inventory/batches")
    files.setdefault("handoff", "handoff")
    files.setdefault("progress", "handoff/progress.md")
    files.setdefault("receipt", "handoff/receipt.md")
    files.setdefault("inventory_audit", None)
    files.setdefault("verification", "verification")
    run.setdefault(
        "execution_chain",
        [
            "inventory-init",
            "browser-batch",
            "checkpoint-record",
            "gap-audit",
            "content-archive",
        ],
    )
    run["updated_at"] = state["updated_at"]
    run["counts"] = summary
    run["batches"] = list(state["applied_batches"])
    run["status"] = (
        "inventory_ready_for_audit"
        if summary["pending_count"] == 0 and summary["blocked_count"] == 0
        else "inventory_running"
    )
    run["current_stage"] = (
        "gap-audit"
        if run["status"] == "inventory_ready_for_audit"
        else "browser-batch"
    )
    atomic_write_json(run_path, run)
    write_progress(run_dir, run, state)
    return run


def record_run_batch(
    run_dir: Path, batch: dict[str, Any], *, now: str | None = None
) -> tuple[dict[str, Any], bool, Path]:
    state = load_state(run_state_path(run_dir))
    batch_id, archived_path = archive_batch(run_dir, batch)
    already_applied = any(
        entry.get("batch_id") == batch_id for entry in state["applied_batches"]
    )
    artifact_sha256 = sha256_file(archived_path)
    if not already_applied:
        timestamp = now or utc_now()
        apply_batch(state, batch, now=timestamp)
        state["applied_batches"].append(
            {
                "batch_id": batch_id,
                "path": str(archived_path.relative_to(run_dir)),
                "artifact_sha256": artifact_sha256,
                "applied_at": timestamp,
            }
        )
        atomic_write_json(run_state_path(run_dir), state)
    else:
        migrated = False
        for entry in state["applied_batches"]:
            if entry.get("batch_id") == batch_id and not entry.get("artifact_sha256"):
                entry["artifact_sha256"] = artifact_sha256
                migrated = True
        if migrated:
            atomic_write_json(run_state_path(run_dir), state)
    update_run_metadata(run_dir, state)
    return state, already_applied, archived_path


def next_audit_path(run_dir: Path) -> Path:
    verification = safe_run_file(run_dir, "verification", label="verification directory")
    verification.mkdir(parents=True, exist_ok=True)
    os.chmod(verification, 0o700)
    index = 1
    while True:
        candidate = safe_run_file(
            run_dir,
            f"verification/inventory-audit-{index:04d}.json",
            label="inventory audit",
        )
        if not candidate.exists():
            return candidate
        index += 1


def completion_receipt_markdown(run: dict[str, Any]) -> str:
    counts = run["counts"]
    return "\n".join(
        [
            "# ProcessOn 盘点完成回执",
            "",
            f"- run_id: `{run['run_id']}`",
            f"- scope: `{run['scope']}`",
            f"- completed_at: `{run['completed_at']}`",
            f"- discovered: {counts['discovered_count']}",
            f"- visited: {counts['visited_count']}",
            f"- files: {counts['file_entry_count']}",
            f"- batches: {counts['applied_batch_count']}",
            f"- audit: `{run['files']['inventory_audit']}`",
            "- result: checkpoint 已由不可变批次重建并核对，目录差集与受阻项均为 0。",
            "",
        ]
    )


def audit_run_bundle(
    run_dir: Path, *, now: str | None = None
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    timestamp = now or utc_now()
    audit_path = next_audit_path(run_dir)
    violations: list[str] = []
    run: dict[str, Any] | None = None
    state: dict[str, Any] | None = None
    reconstructed: dict[str, Any] | None = None

    try:
        run = load_json_object(run_dir / "run.json", label="run.json")
        state = load_state(run_state_path(run_dir))
        if run.get("schema_version") != SCHEMA_VERSION:
            violations.append("run.json schema_version does not match")
        if run.get("run_id") != run_dir.name:
            violations.append("run.json run_id does not match directory name")
        files = run.get("files")
        if not isinstance(files, dict):
            violations.append("run.json files must be an object")
            files = {}
            run["files"] = files
        files.setdefault("progress", "handoff/progress.md")
        files.setdefault("receipt", "handoff/receipt.md")
        files.setdefault("verification", "verification")
        files.setdefault("inventory_audit", None)
        if files.get("checkpoint") != "inventory/checkpoint.json":
            violations.append("run.json checkpoint path is not canonical")

        reconstructed = new_state(
            root_path=state["root_path"],
            source_url=str(state.get("source_url", "")),
            now=state["created_at"],
        )
        for index, entry in enumerate(state["applied_batches"], start=1):
            if not isinstance(entry, dict):
                violations.append(f"batch index {index} is not an object")
                continue
            try:
                batch_path = safe_run_file(
                    run_dir, str(entry.get("path", "")), label=f"batch {index}"
                )
                batch = load_json_object(batch_path, label=f"batch {index}")
                canonical_hash = hashlib.sha256(canonical_batch_bytes(batch)).hexdigest()
                if canonical_hash != entry.get("batch_id"):
                    violations.append(f"batch {index} canonical SHA-256 mismatch")
                artifact_hash = sha256_file(batch_path)
                if artifact_hash != entry.get("artifact_sha256"):
                    violations.append(f"batch {index} artifact SHA-256 mismatch")
                apply_batch(
                    reconstructed,
                    batch,
                    now=str(entry.get("applied_at", state["updated_at"])),
                )
                reconstructed["applied_batches"].append(dict(entry))
            except (InventoryStateError, OSError, json.JSONDecodeError) as exc:
                violations.append(f"batch {index} cannot be replayed: {exc}")

        if reconstructed != state:
            violations.append("checkpoint cannot be reproduced from archived batches")
        summary = state_summary(state)
        if run.get("counts") != summary:
            violations.append("run.json counts do not match checkpoint")
        if run.get("batches") != state["applied_batches"]:
            violations.append("run.json batch index does not match checkpoint")
    except (InventoryStateError, OSError, json.JSONDecodeError, KeyError) as exc:
        violations.append(str(exc))

    summary = state_summary(state) if state is not None else None
    complete_eligible = bool(
        not violations
        and summary is not None
        and summary["pending_count"] == 0
        and summary["blocked_count"] == 0
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_dir.name,
        "audited_at": timestamp,
        "status": "passed" if not violations else "failed",
        "complete_eligible": complete_eligible,
        "checked": {
            "archived_batches": len(state["applied_batches"]) if state else 0,
            "checkpoint_replay": reconstructed == state if state else False,
            "run_index": bool(
                state is not None
                and run is not None
                and run.get("batches") == state["applied_batches"]
            ),
            "counts": summary,
        },
        "violations": violations,
    }
    atomic_write_json(audit_path, report)

    if run is not None and state is not None:
        run.setdefault("files", {})["inventory_audit"] = str(
            audit_path.relative_to(run_dir.resolve(strict=False))
        )
        run["updated_at"] = timestamp
        if violations:
            run["status"] = "inventory_audit_failed"
            run["current_stage"] = "gap-audit"
        elif complete_eligible:
            run["status"] = "completed"
            run["current_stage"] = "completed"
            run.setdefault("completed_at", timestamp)
        else:
            run["status"] = "inventory_running"
            run["current_stage"] = "browser-batch"
        atomic_write_json(run_dir / "run.json", run)
        write_progress(run_dir, run, state)
        if complete_eligible:
            receipt_path = safe_run_file(
                run_dir, run["files"]["receipt"], label="receipt"
            )
            atomic_write_text(receipt_path, completion_receipt_markdown(run))
    return report, run


def child_path(parent: str, folder: str | dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if isinstance(folder, str):
        name = folder.strip()
        if not name:
            raise InventoryStateError("folder name cannot be empty")
        path = normalize_path(f"{parent}/{name}")
        return path, {"name": name, "path": path}
    if not isinstance(folder, dict):
        raise InventoryStateError("folders must contain strings or objects")
    name = str(folder.get("name", "")).strip()
    supplied_path = str(folder.get("path", "")).strip()
    if supplied_path:
        path = normalize_path(supplied_path)
    elif name:
        path = normalize_path(f"{parent}/{name}")
    else:
        raise InventoryStateError("folder object requires name or path")
    if not path.startswith(f"{parent}/"):
        raise InventoryStateError(f"folder path is not below parent {parent!r}: {path!r}")
    normalized = dict(folder)
    normalized["path"] = path
    normalized.setdefault("name", path.rsplit("/", 1)[-1])
    return path, normalized


def normalize_file(file_entry: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(file_entry, str):
        title = file_entry.strip()
        if not title:
            raise InventoryStateError("file title cannot be empty")
        return {"title": title, "type": "unknown"}
    if not isinstance(file_entry, dict):
        raise InventoryStateError("files must contain strings or objects")
    title = str(file_entry.get("title", "")).strip()
    if not title:
        raise InventoryStateError("file object requires title")
    normalized = dict(file_entry)
    normalized["title"] = title
    normalized.setdefault("type", "unknown")
    return normalized


def file_identity(file_entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(file_entry.get("title", "")),
        str(file_entry.get("type", "unknown")),
        str(file_entry.get("owner", "")),
        str(file_entry.get("remote_updated_at", "")),
    )


def apply_batch(
    state: dict[str, Any], batch: dict[str, Any], *, now: str | None = None
) -> dict[str, Any]:
    validate_state(state)
    directories = batch.get("directories", [])
    blocked = batch.get("blocked", [])
    if not isinstance(directories, list) or not isinstance(blocked, list):
        raise InventoryStateError("batch directories and blocked must be lists")

    discovered = {normalize_path(path) for path in state["discovered_paths"]}
    visited = {normalize_path(path) for path in state["visited_paths"]}
    blocked_paths = dict(state["blocked_paths"])
    directory_map = dict(state["directories"])
    timestamp = now or utc_now()

    for entry in directories:
        if not isinstance(entry, dict):
            raise InventoryStateError("directory entries must be objects")
        path = normalize_path(str(entry.get("path", "")))
        status = str(entry.get("status", "visited"))
        if status not in {"visited", "discovered"}:
            raise InventoryStateError(f"unsupported directory status: {status}")
        discovered.add(path)

        folders: list[dict[str, Any]] = []
        for folder in entry.get("folders", []):
            path_value, normalized_folder = child_path(path, folder)
            discovered.add(path_value)
            folders.append(normalized_folder)

        files = [normalize_file(item) for item in entry.get("files", [])]
        unique_files = {file_identity(item): item for item in files}
        directory_map[path] = {
            "path": path,
            "status": status,
            "captured_at": entry.get("captured_at", timestamp),
            "folders": folders,
            "files": list(unique_files.values()),
        }
        if status == "visited":
            visited.add(path)
            blocked_paths.pop(path, None)

    for entry in blocked:
        if not isinstance(entry, dict):
            raise InventoryStateError("blocked entries must be objects")
        path = normalize_path(str(entry.get("path", "")))
        discovered.add(path)
        blocked_paths[path] = {
            "reason": str(entry.get("reason", "unknown")),
            "captured_at": entry.get("captured_at", timestamp),
        }

    state["discovered_paths"] = sorted(discovered)
    state["visited_paths"] = sorted(visited)
    state["blocked_paths"] = dict(sorted(blocked_paths.items()))
    state["directories"] = dict(sorted(directory_map.items()))
    state["updated_at"] = timestamp
    return state


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    validate_state(state)
    discovered = set(state["discovered_paths"])
    visited = set(state["visited_paths"])
    blocked = set(state["blocked_paths"])
    pending = sorted(discovered - visited - blocked)
    file_entries = sum(
        len(entry.get("files", [])) for entry in state["directories"].values()
    )
    return {
        "schema_version": state["schema_version"],
        "root_path": state["root_path"],
        "discovered_count": len(discovered),
        "visited_count": len(visited),
        "pending_count": len(pending),
        "blocked_count": len(blocked),
        "file_entry_count": file_entries,
        "applied_batch_count": len(state["applied_batches"]),
        "pending_paths": pending,
        "blocked_paths": sorted(blocked),
        "updated_at": state["updated_at"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("init", help="create a new checkpoint")
    initialize_target = initialize.add_mutually_exclusive_group(required=True)
    initialize_target.add_argument("--state", type=Path)
    initialize_target.add_argument("--run-dir", type=Path)
    initialize_target.add_argument("--run-id")
    initialize.add_argument("--state-root", type=Path)
    initialize.add_argument("--root-path", required=True)
    initialize.add_argument("--source-url", required=True)

    record = subparsers.add_parser("record", help="atomically merge one browser batch")
    record_target = record.add_mutually_exclusive_group(required=True)
    record_target.add_argument("--state", type=Path)
    record_target.add_argument("--run-dir", type=Path)
    record.add_argument("--input", type=Path, required=True)

    status = subparsers.add_parser("status", help="show resumable inventory counts")
    status_target = status.add_mutually_exclusive_group(required=True)
    status_target.add_argument("--state", type=Path)
    status_target.add_argument("--run-dir", type=Path)
    status.add_argument("--full", action="store_true", help="include directory data")

    audit = subparsers.add_parser(
        "audit", help="replay immutable batches and verify the run bundle"
    )
    audit.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exit_code = 0
    try:
        if args.command == "init":
            if args.state is not None:
                if args.state.exists():
                    raise InventoryStateError(f"state file already exists: {args.state}")
                state = new_state(root_path=args.root_path, source_url=args.source_url)
                atomic_write_json(args.state, state)
                output = state_summary(state)
            else:
                run_dir = resolve_run_dir(
                    run_dir=args.run_dir,
                    run_id=args.run_id,
                    state_root=args.state_root,
                )
                state, _ = initialize_run_bundle(
                    run_dir, root_path=args.root_path, source_url=args.source_url
                )
                output = {"run_dir": str(run_dir), **state_summary(state)}
        elif args.command == "record":
            batch = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(batch, dict):
                raise InventoryStateError("batch root must be an object")
            if args.run_dir is not None:
                run_dir = resolve_run_dir(run_dir=args.run_dir, run_id=None)
                state, already_applied, archived_path = record_run_batch(run_dir, batch)
                output = {
                    "run_dir": str(run_dir),
                    "batch": str(archived_path.relative_to(run_dir)),
                    "already_applied": already_applied,
                    **state_summary(state),
                }
            else:
                state = load_state(args.state)
                state = apply_batch(state, batch)
                atomic_write_json(args.state, state)
                output = state_summary(state)
        elif args.command == "status":
            state_path = (
                run_state_path(resolve_run_dir(run_dir=args.run_dir, run_id=None))
                if args.run_dir is not None
                else args.state
            )
            state = load_state(state_path)
            output = state if args.full else state_summary(state)
        else:
            run_dir = resolve_run_dir(run_dir=args.run_dir, run_id=None)
            output, _ = audit_run_bundle(run_dir)
            if output["status"] != "passed":
                exit_code = 2
    except (InventoryStateError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
