#!/usr/bin/env python3
"""Maintain a resumable, auditable ProcessOn artifact archive queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


STATE_SCHEMA_VERSION = 1
KNOWN_TYPES = {"flowchart", "mindmap"}
NUMBERED_DOWNLOAD_SUFFIX = re.compile(r" \(\d+\)$")


class ArchiveStateError(RuntimeError):
    """Raised when an archive queue or artifact cannot be trusted."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_evidence_file(path: Path) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink():
        raise ArchiveStateError(f"refusing symlink evidence file: {path}")
    if not path.is_file():
        raise ArchiveStateError(f"evidence file not found: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise ArchiveStateError(f"evidence file is empty: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": size,
        "sha256": sha256_file(path),
    }


def archive_evidence_file(progress_path: Path, artifact_id: str, source: Path) -> dict[str, Any]:
    source_inspection = inspect_evidence_file(source)
    artifact_key = hashlib.sha256(artifact_id.encode("utf-8")).hexdigest()[:16]
    evidence_dir = progress_path.expanduser().parent / "evidence" / artifact_key
    evidence_dir.mkdir(parents=True, exist_ok=True)
    destination = evidence_dir / f"{source_inspection['sha256'][:12]}--{source.expanduser().name}"
    if destination.is_symlink():
        raise ArchiveStateError(f"refusing symlink evidence destination: {destination}")
    if destination.exists():
        destination_inspection = inspect_evidence_file(destination)
        if (
            destination_inspection["sha256"] != source_inspection["sha256"]
            or destination_inspection["bytes"] != source_inspection["bytes"]
        ):
            raise ArchiveStateError(f"evidence destination collision: {destination}")
    else:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=evidence_dir
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as output, source.expanduser().open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temporary, 0o600)
            if sha256_file(temporary) != source_inspection["sha256"]:
                raise ArchiveStateError("evidence SHA-256 mismatch after copy")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    os.chmod(destination, 0o600)
    return {
        "source": source_inspection["path"],
        "archived_path": str(destination.resolve()),
        "bytes": source_inspection["bytes"],
        "sha256": source_inspection["sha256"],
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink():
        raise ArchiveStateError(f"refusing symlink {label}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArchiveStateError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ArchiveStateError(f"invalid {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArchiveStateError(f"{label} must be a JSON object")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = path.expanduser()
    if path.is_symlink():
        raise ArchiveStateError(f"refusing symlink progress file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def exclusive_state_lock(progress_path: Path) -> Iterator[None]:
    lock_path = progress_path.with_name(f".{progress_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ArchiveStateError(
            f"archive progress is already locked: {lock_path}; "
            "confirm no writer is active before removing a stale lock"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "created_at": now()}))
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def validate_plan(plan: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "plan_type",
        "archive_status",
        "ready_for_known_artifacts",
        "entries",
        "counts",
    }
    missing = sorted(required - set(plan))
    if missing:
        raise ArchiveStateError(f"archive plan missing fields: {', '.join(missing)}")
    if plan.get("plan_type") != "processon-artifact-archive":
        raise ArchiveStateError("unsupported archive plan type")
    if not plan.get("ready_for_known_artifacts"):
        raise ArchiveStateError("archive plan is not ready for known artifacts")
    if not isinstance(plan.get("entries"), list):
        raise ArchiveStateError("archive plan entries must be a list")
    seen: set[str] = set()
    for entry in plan["entries"]:
        if not isinstance(entry, dict):
            raise ArchiveStateError("archive plan entry must be an object")
        artifact_id = entry.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ArchiveStateError("archive plan entry has no artifact_id")
        if artifact_id in seen:
            raise ArchiveStateError(f"duplicate artifact_id in archive plan: {artifact_id}")
        seen.add(artifact_id)


def plan_fingerprint(plan_path: Path) -> str:
    if plan_path.is_symlink():
        raise ArchiveStateError(f"refusing symlink archive plan: {plan_path}")
    try:
        return sha256_file(plan_path)
    except FileNotFoundError as exc:
        raise ArchiveStateError(f"archive plan not found: {plan_path}") from exc


def plan_entries(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["artifact_id"]: entry for entry in plan["entries"]}


def unknown_queue(plan: dict[str, Any]) -> list[dict[str, Any]]:
    fields = ("artifact_id", "source_path", "title", "owner", "remote_updated_at", "status")
    return [
        {field: entry.get(field, "") for field in fields}
        for entry in plan["entries"]
        if entry.get("type") == "unknown" or entry.get("confirmation_required")
    ]


def identifiers(items: list[dict[str, Any]], label: str) -> list[str]:
    result: list[str] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("artifact_id"), str):
            raise ArchiveStateError(f"invalid {label} entry")
        result.append(item["artifact_id"])
    if len(result) != len(set(result)):
        raise ArchiveStateError(f"duplicate artifact_id in {label}")
    return result


def recompute_counts(state: dict[str, Any], plan: dict[str, Any]) -> dict[str, int]:
    known = [entry for entry in plan["entries"] if entry.get("type") in KNOWN_TYPES]
    unknown = [entry for entry in plan["entries"] if entry.get("type") not in KNOWN_TYPES]
    completed_ids = set(identifiers(state.get("completed", []), "completed"))
    failed_ids = set(identifiers(state.get("failed", []), "failed"))
    blocked_ids = set(identifiers(state.get("blocked", []), "blocked"))
    known_ids = {entry["artifact_id"] for entry in known}
    for label, values in (("completed", completed_ids), ("failed", failed_ids), ("blocked", blocked_ids)):
        foreign = values - known_ids
        if foreign:
            raise ArchiveStateError(f"{label} contains unknown or unconfirmed artifacts: {sorted(foreign)}")
    return {
        "planned_known": len(known),
        "unknown_pending_confirmation": len(unknown),
        "completed": len(completed_ids),
        "failed": len(failed_ids),
        "blocked": len(blocked_ids),
        "remaining_known": len(known_ids - completed_ids),
    }


def state_status(counts: dict[str, int]) -> str:
    if counts["remaining_known"]:
        return "asset_archive_running"
    if counts["unknown_pending_confirmation"]:
        return "known_artifacts_completed_pending_confirmation"
    return "asset_archive_completed"


def normalize_state(state: dict[str, Any], plan_path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ArchiveStateError("unsupported archive progress schema_version")
    if state.get("progress_type") != "processon-artifact-archive":
        raise ArchiveStateError("unsupported archive progress type")
    current_fingerprint = plan_fingerprint(plan_path)
    recorded = state.get("plan", {}).get("sha256")
    if recorded and recorded != current_fingerprint:
        raise ArchiveStateError("archive plan changed; do not merge progress across plan fingerprints")
    state.setdefault("created_at", now())
    state.setdefault("completed", [])
    state.setdefault("failed", [])
    state.setdefault("blocked", [])
    identifiers(state["completed"], "completed")
    identifiers(state["failed"], "failed")
    identifiers(state["blocked"], "blocked")
    state["plan"] = {
        "path": str(plan_path.resolve()),
        "sha256": current_fingerprint,
        "archive_status": plan["archive_status"],
    }
    state["unknown_pending_confirmation"] = unknown_queue(plan)
    state["counts"] = recompute_counts(state, plan)
    state["status"] = state_status(state["counts"])
    state["updated_at"] = now()
    return state


def initialize_state(plan_path: Path, progress_path: Path) -> dict[str, Any]:
    plan = load_json(plan_path, "archive plan")
    validate_plan(plan)
    with exclusive_state_lock(progress_path):
        if progress_path.exists():
            state = load_json(progress_path, "archive progress")
        else:
            state = {
                "schema_version": STATE_SCHEMA_VERSION,
                "progress_type": "processon-artifact-archive",
                "created_at": now(),
                "completed": [],
                "failed": [],
                "blocked": [],
            }
        normalize_state(state, plan_path, plan)
        atomic_write_json(progress_path, state)
    return state


def get_plan_item(plan: dict[str, Any], artifact_id: str) -> dict[str, Any]:
    item = plan_entries(plan).get(artifact_id)
    if item is None:
        raise ArchiveStateError(f"artifact_id is not in archive plan: {artifact_id}")
    if item.get("type") not in KNOWN_TYPES or item.get("confirmation_required"):
        raise ArchiveStateError(f"artifact requires type confirmation before archive: {artifact_id}")
    return item


def inspect_artifact(path: Path, actual_format: str) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink() or not path.is_file():
        raise ArchiveStateError(f"artifact must be a regular non-symlink file: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise ArchiveStateError(f"artifact is empty: {path}")
    suffix = path.suffix.lower().lstrip(".")
    if actual_format.lower() != suffix:
        raise ArchiveStateError(
            f"actual format does not match file extension: {actual_format!r} != {suffix!r}"
        )
    inspection: dict[str, Any] = {
        "kind": suffix,
        "bytes": size,
        "sha256": sha256_file(path),
    }
    if suffix == "vsdx":
        try:
            with zipfile.ZipFile(path) as package:
                names = package.namelist()
        except zipfile.BadZipFile as exc:
            raise ArchiveStateError(f"invalid VSDX package: {path}") from exc
        if "visio/document.xml" not in names:
            raise ArchiveStateError(f"VSDX package is missing visio/document.xml: {path}")
        inspection.update(
            {
                "kind": "visio-vsdx",
                "package_entries": len(names),
                "page_part_count": sum(
                    name.startswith("visio/pages/page")
                    and name.endswith(".xml")
                    and name.removeprefix("visio/pages/page").removesuffix(".xml").isdigit()
                    for name in names
                ),
            }
        )
    elif suffix == "xmind":
        try:
            with zipfile.ZipFile(path) as package:
                names = package.namelist()
        except zipfile.BadZipFile as exc:
            raise ArchiveStateError(f"invalid XMind package: {path}") from exc
        if not {"content.json", "content.xml"}.intersection(names):
            raise ArchiveStateError(f"XMind package has no content.json or content.xml: {path}")
        inspection.update({"kind": "xmind", "package_entries": len(names)})
    return inspection


def is_unsafe_flat_numbered_download(path: Path) -> bool:
    """Return true for browser-renamed files in the personal flat Downloads root."""

    resolved = path.expanduser().resolve(strict=False)
    downloads_root = (Path.home() / "Downloads").resolve(strict=False)
    return resolved.parent == downloads_root and bool(NUMBERED_DOWNLOAD_SUFFIX.search(resolved.stem))


def validate_finalizer_manifest(
    manifest_path: Path, destination: Path, inspection: dict[str, Any]
) -> dict[str, Any]:
    manifest = load_json(manifest_path, "finalizer manifest")
    manifest_destination = Path(str(manifest.get("destination", ""))).expanduser()
    if manifest_destination.resolve() != destination.expanduser().resolve():
        raise ArchiveStateError("finalizer manifest destination does not match archived artifact")
    manifest_inspection = manifest.get("inspection", {})
    if manifest_inspection.get("sha256") != inspection["sha256"]:
        raise ArchiveStateError("finalizer manifest SHA-256 does not match archived artifact")
    if manifest_inspection.get("bytes") != inspection["bytes"]:
        raise ArchiveStateError("finalizer manifest size does not match archived artifact")
    return manifest


def record_completed(
    plan_path: Path,
    progress_path: Path,
    artifact_id: str,
    download_source: Path,
    destination: Path,
    manifest_path: Path,
    requested_format: str | None,
    actual_format: str,
    download_event: str,
) -> tuple[dict[str, Any], str]:
    if is_unsafe_flat_numbered_download(download_source):
        raise ArchiveStateError(
            "refusing a numbered file from the flat personal Downloads directory; "
            "redownload it into an artifact_id-scoped managed staging directory"
        )
    plan = load_json(plan_path, "archive plan")
    validate_plan(plan)
    item = get_plan_item(plan, artifact_id)
    inspection = inspect_artifact(destination, actual_format)
    manifest = validate_finalizer_manifest(manifest_path, destination, inspection)
    manifest_source = Path(str(manifest.get("source", ""))).expanduser()
    if manifest_source.resolve() != download_source.expanduser().resolve():
        raise ArchiveStateError("finalizer manifest source does not match browser download")
    if download_source.expanduser().exists():
        source_inspection = inspect_artifact(download_source, actual_format)
        if source_inspection["sha256"] != inspection["sha256"]:
            raise ArchiveStateError("browser download SHA-256 does not match archived artifact")
    elif manifest.get("operation") != "move":
        raise ArchiveStateError("browser download is missing and finalizer manifest is not a move")
    with exclusive_state_lock(progress_path):
        state = load_json(progress_path, "archive progress")
        normalize_state(state, plan_path, plan)
        existing = next(
            (entry for entry in state["completed"] if entry["artifact_id"] == artifact_id), None
        )
        if existing:
            if (
                existing.get("sha256") == inspection["sha256"]
                and Path(existing.get("archive_destination", "")).resolve() == destination.resolve()
            ):
                return state, "already_completed"
            raise ArchiveStateError("artifact_id was already completed with different evidence")
        record = {
            "artifact_id": artifact_id,
            "source_path": item.get("source_path", ""),
            "requested_format": requested_format or item.get("primary_format") or actual_format,
            "actual_format": actual_format,
            "download_source": str(download_source.expanduser().resolve()),
            "archive_destination": str(destination.expanduser().resolve()),
            "manifest": str(manifest_path.expanduser().resolve()),
            "sha256": inspection["sha256"],
            "bytes": inspection["bytes"],
            "inspection": {
                key: value for key, value in inspection.items() if key not in {"sha256", "bytes"}
            },
            "download_event": download_event,
            "completed_at": now(),
        }
        state["completed"].append(record)
        state["failed"] = [entry for entry in state["failed"] if entry["artifact_id"] != artifact_id]
        state["blocked"] = [entry for entry in state["blocked"] if entry["artifact_id"] != artifact_id]
        normalize_state(state, plan_path, plan)
        atomic_write_json(progress_path, state)
    return state, "completed"


def mark_outcome(
    plan_path: Path,
    progress_path: Path,
    artifact_id: str,
    outcome: str,
    reason: str,
    evidence_files: list[Path] | None = None,
) -> dict[str, Any]:
    if outcome not in {"failed", "blocked"}:
        raise ArchiveStateError("outcome must be failed or blocked")
    if not reason.strip():
        raise ArchiveStateError("reason must not be empty")
    plan = load_json(plan_path, "archive plan")
    validate_plan(plan)
    item = get_plan_item(plan, artifact_id)
    with exclusive_state_lock(progress_path):
        state = load_json(progress_path, "archive progress")
        normalize_state(state, plan_path, plan)
        if artifact_id in set(identifiers(state["completed"], "completed")):
            raise ArchiveStateError("completed artifact cannot be marked failed or blocked")
        prior_evidence: list[dict[str, Any]] = []
        for prior_outcome in ("failed", "blocked"):
            for prior_entry in state[prior_outcome]:
                if prior_entry["artifact_id"] == artifact_id:
                    prior_evidence = prior_entry.get("evidence_files", [])
                    break
        evidence_records = [
            archive_evidence_file(progress_path, artifact_id, evidence_file)
            for evidence_file in (evidence_files or [])
        ]
        other = "blocked" if outcome == "failed" else "failed"
        state[other] = [entry for entry in state[other] if entry["artifact_id"] != artifact_id]
        record = {
            "artifact_id": artifact_id,
            "source_path": item.get("source_path", ""),
            "reason": reason.strip(),
            "updated_at": now(),
        }
        if evidence_records or prior_evidence:
            record["evidence_files"] = evidence_records or prior_evidence
        replaced = False
        for index, entry in enumerate(state[outcome]):
            if entry["artifact_id"] == artifact_id:
                state[outcome][index] = record
                replaced = True
                break
        if not replaced:
            state[outcome].append(record)
        normalize_state(state, plan_path, plan)
        atomic_write_json(progress_path, state)
    return state


def next_items(
    plan: dict[str, Any],
    state: dict[str, Any],
    limit: int,
    item_type: str | None,
    include_failed: bool,
    include_blocked: bool,
) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ArchiveStateError("limit must be positive")
    completed = set(identifiers(state.get("completed", []), "completed"))
    failed = set(identifiers(state.get("failed", []), "failed"))
    blocked = set(identifiers(state.get("blocked", []), "blocked"))
    result: list[dict[str, Any]] = []
    fields = (
        "artifact_id",
        "source_directory",
        "source_path",
        "title",
        "type",
        "primary_format",
        "primary_menu",
        "selection_rule",
    )
    for entry in plan["entries"]:
        artifact_id = entry["artifact_id"]
        if entry.get("type") not in KNOWN_TYPES or artifact_id in completed:
            continue
        if item_type and entry.get("type") != item_type:
            continue
        if artifact_id in failed and not include_failed:
            continue
        if artifact_id in blocked and not include_blocked:
            continue
        candidate = {field: entry.get(field) for field in fields}
        if artifact_id in failed:
            candidate["prior_outcome"] = "failed"
        elif artifact_id in blocked:
            candidate["prior_outcome"] = "blocked"
        else:
            candidate["prior_outcome"] = "pending"
        result.append(candidate)
        if len(result) >= limit:
            break
    return result


def audit_state(plan_path: Path, progress_path: Path) -> dict[str, Any]:
    plan = load_json(plan_path, "archive plan")
    validate_plan(plan)
    state = load_json(progress_path, "archive progress")
    errors: list[str] = []
    try:
        expected_fingerprint = plan_fingerprint(plan_path)
        if state.get("plan", {}).get("sha256") != expected_fingerprint:
            errors.append("archive plan fingerprint mismatch")
        expected_counts = recompute_counts(state, plan)
        if state.get("counts") != expected_counts:
            errors.append("archive progress counts do not match completed/failed/blocked evidence")
        expected_unknown = {entry["artifact_id"] for entry in unknown_queue(plan)}
        actual_unknown = set(identifiers(state.get("unknown_pending_confirmation", []), "unknown"))
        if actual_unknown != expected_unknown:
            errors.append("unknown confirmation queue does not match archive plan")
        for outcome in ("failed", "blocked"):
            for entry in state.get(outcome, []):
                for evidence in entry.get("evidence_files", []):
                    try:
                        if not isinstance(evidence, dict):
                            raise ArchiveStateError("evidence record must be an object")
                        inspection = inspect_evidence_file(Path(evidence.get("archived_path", "")))
                        if inspection["sha256"] != evidence.get("sha256"):
                            errors.append(f"evidence SHA-256 mismatch: {entry['artifact_id']}")
                        if inspection["bytes"] != evidence.get("bytes"):
                            errors.append(f"evidence size mismatch: {entry['artifact_id']}")
                    except ArchiveStateError as exc:
                        errors.append(f"invalid {outcome} evidence for {entry['artifact_id']}: {exc}")
        for entry in state.get("completed", []):
            destination = Path(entry.get("archive_destination", ""))
            actual_format = str(entry.get("actual_format", ""))
            inspection = inspect_artifact(destination, actual_format)
            if inspection["sha256"] != entry.get("sha256"):
                errors.append(f"SHA-256 mismatch: {entry['artifact_id']}")
            if inspection["bytes"] != entry.get("bytes"):
                errors.append(f"size mismatch: {entry['artifact_id']}")
            manifest_path = Path(entry.get("manifest", ""))
            validate_finalizer_manifest(manifest_path, destination, inspection)
    except ArchiveStateError as exc:
        errors.append(str(exc))
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "status": "passed" if not errors else "failed",
        "plan_sha256": plan_fingerprint(plan_path),
        "progress_path": str(progress_path.expanduser().resolve()),
        "counts": state.get("counts", {}),
        "errors": errors,
    }


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_parser = subcommands.add_parser("init", help="create or safely resume archive progress")
    init_parser.add_argument("--plan", type=Path, required=True)
    init_parser.add_argument("--progress", type=Path, required=True)

    status_parser = subcommands.add_parser("status", help="show persisted archive progress")
    status_parser.add_argument("--progress", type=Path, required=True)

    next_parser = subcommands.add_parser("next", help="return the next actionable plan entries")
    next_parser.add_argument("--plan", type=Path, required=True)
    next_parser.add_argument("--progress", type=Path, required=True)
    next_parser.add_argument("--limit", type=int, default=10)
    next_parser.add_argument("--type", choices=sorted(KNOWN_TYPES))
    next_parser.add_argument("--include-failed", action="store_true")
    next_parser.add_argument("--include-blocked", action="store_true")

    record_parser = subcommands.add_parser("record", help="record one verified archived artifact")
    record_parser.add_argument("--plan", type=Path, required=True)
    record_parser.add_argument("--progress", type=Path, required=True)
    record_parser.add_argument("--artifact-id", required=True)
    record_parser.add_argument("--download-source", type=Path, required=True)
    record_parser.add_argument("--destination", type=Path, required=True)
    record_parser.add_argument("--manifest", type=Path, required=True)
    record_parser.add_argument("--requested-format")
    record_parser.add_argument("--actual-format", required=True)
    record_parser.add_argument(
        "--download-event", default="observed", choices=["observed", "not_observed_verified_file"]
    )

    mark_parser = subcommands.add_parser("mark", help="persist a failed or blocked artifact")
    mark_parser.add_argument("--plan", type=Path, required=True)
    mark_parser.add_argument("--progress", type=Path, required=True)
    mark_parser.add_argument("--artifact-id", required=True)
    mark_parser.add_argument("--outcome", choices=["failed", "blocked"], required=True)
    mark_parser.add_argument("--reason", required=True)
    mark_parser.add_argument(
        "--evidence-file",
        type=Path,
        action="append",
        default=[],
        help="copy one diagnostic file into the run evidence directory; repeatable",
    )

    audit_parser = subcommands.add_parser("audit", help="replay archived artifact evidence")
    audit_parser.add_argument("--plan", type=Path, required=True)
    audit_parser.add_argument("--progress", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            print_json(initialize_state(args.plan, args.progress))
        elif args.command == "status":
            print_json(load_json(args.progress, "archive progress"))
        elif args.command == "next":
            plan = load_json(args.plan, "archive plan")
            validate_plan(plan)
            state = load_json(args.progress, "archive progress")
            normalize_state(state, args.plan, plan)
            print_json(
                {
                    "status": state["status"],
                    "counts": state["counts"],
                    "items": next_items(
                        plan,
                        state,
                        args.limit,
                        args.type,
                        args.include_failed,
                        args.include_blocked,
                    ),
                }
            )
        elif args.command == "record":
            state, outcome = record_completed(
                args.plan,
                args.progress,
                args.artifact_id,
                args.download_source,
                args.destination,
                args.manifest,
                args.requested_format,
                args.actual_format,
                args.download_event,
            )
            print_json({"status": outcome, "counts": state["counts"]})
        elif args.command == "mark":
            state = mark_outcome(
                args.plan,
                args.progress,
                args.artifact_id,
                args.outcome,
                args.reason,
                args.evidence_file,
            )
            print_json({"status": args.outcome, "counts": state["counts"]})
        elif args.command == "audit":
            result = audit_state(args.plan, args.progress)
            print_json(result)
            return 0 if result["status"] == "passed" else 1
        return 0
    except ArchiveStateError as exc:
        parser = build_parser()
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
