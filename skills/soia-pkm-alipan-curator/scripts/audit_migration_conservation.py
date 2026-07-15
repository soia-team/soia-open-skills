#!/usr/bin/env python3
"""Audit that a registered cross-root migration conserved scanned entities.

The audit is intentionally offline: it reads a run bundle's initial scan,
registered action plans/results, and one or more fresh final scans.  It never
calls a drive CLI or assumes a particular cloud root or drive ID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


MISSING_AUTHORIZATION_OPS = {"delete", "remove", "trash"}
MIGRATION_OPS = {"mv", "rename"}
OPERATION_IDENTITY_FIELDS = ("action_id", "op", "from", "to", "file_id")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def read_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append((line_number, value))
    return rows


def resolve_member(run_dir: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    member = Path(value)
    if member.is_absolute() or ".." in member.parts:
        raise ValueError(f"{label} must stay inside the run directory")
    root = run_dir.resolve()
    resolved = (run_dir / member).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"{label} escapes the run directory")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def operation_identity_value(value: object) -> str | None:
    """Normalize a ledger identity value without inferring a missing field."""
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def operation_identity_mismatches(action: dict[str, Any], result: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    """Return every identity component where a result cannot close its action.

    ``action_id`` alone is intentionally insufficient: a stale or reused ledger
    row must not be allowed to verify a different operation on the same ID.
    Missing optional fields compare as ``None``; an unexpected value in a
    result is therefore just as unsafe as omitting a required one.
    """
    mismatches: dict[str, dict[str, str | None]] = {}
    for field in OPERATION_IDENTITY_FIELDS:
        expected = operation_identity_value(action.get(field))
        actual = operation_identity_value(result.get(field))
        if expected != actual:
            mismatches[field] = {"expected": expected, "actual": actual}
    return mismatches


def normalize_path(value: object) -> str:
    text = str(value or "").strip()
    return "/" + str(PurePosixPath("/" + text.lstrip("/"))).lstrip("/")


def full_path(row: dict[str, Any]) -> str:
    name = str(row.get("name", "")).strip("/")
    parent = normalize_path(row.get("path", ""))
    return normalize_path(f"{parent}/{name}")


def target_path(action: dict[str, Any]) -> str | None:
    """Return the final entity path implied by a verified migration action."""
    op = str(action.get("op", "")).strip()
    if op == "rename":
        if not str(action.get("to", "")).strip():
            return None
        return normalize_path(action.get("to", ""))
    if op == "mv":
        if not str(action.get("from", "")).strip() or not str(action.get("to", "")).strip():
            return None
        source_name = PurePosixPath(normalize_path(action.get("from", ""))).name
        return normalize_path(f"{action.get('to', '')}/{source_name}")
    return None


def scan_index(
    scan_name: str,
    rows: list[tuple[int, dict[str, Any]]],
    violations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Index a complete file-level scan and report unsafe scan forms."""
    indexed: dict[str, dict[str, Any]] = {}
    for line, row in rows:
        if "agg_files" in row or "agg_size" in row:
            violations.append({
                "kind": "aggregate_scan_row",
                "scan": scan_name,
                "line": line,
                "path": full_path(row),
            })
        file_id = str(row.get("id", "")).strip()
        if not file_id:
            violations.append({
                "kind": "scan_row_missing_file_id",
                "scan": scan_name,
                "line": line,
                "path": full_path(row),
            })
            continue
        previous = indexed.get(file_id)
        if previous is not None:
            violations.append({
                "kind": "duplicate_physical_row",
                "scan": scan_name,
                "file_id": file_id,
                "line": line,
                "first_line": previous["line"],
                "path": full_path(row),
                "first_path": previous["path"],
            })
            continue
        indexed[file_id] = {"row": row, "line": line, "path": full_path(row), "scan": scan_name}
    return indexed


def final_scan_members(manifest: dict[str, Any]) -> list[str]:
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("run.files must be an object")
    plural = files.get("final_scans")
    if plural is not None:
        if not isinstance(plural, list) or not plural:
            raise ValueError("run.files.final_scans must be a non-empty array")
        if any(not isinstance(item, str) or not item.strip() for item in plural):
            raise ValueError("run.files.final_scans must contain non-empty relative paths")
        return plural
    singular = files.get("final_scan")
    if not isinstance(singular, str) or not singular.strip():
        raise ValueError("run.files.final_scan or run.files.final_scans is required")
    return [singular]


def registered_batches(
    run_dir: Path, manifest: dict[str, Any]
) -> list[tuple[int, Path, Path, list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]]]]:
    batches = manifest.get("batches")
    if not isinstance(batches, list):
        raise ValueError("run.batches must be an array")
    result = []
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict):
            raise ValueError(f"run.batches[{index}] must be an object")
        plan = resolve_member(run_dir, batch.get("plan"), f"run.batches[{index}].plan")
        ledger = resolve_member(run_dir, batch.get("result"), f"run.batches[{index}].result")
        if not plan.is_file():
            raise ValueError(f"run.batches[{index}].plan does not exist: {plan}")
        if not ledger.is_file():
            raise ValueError(f"run.batches[{index}].result does not exist: {ledger}")
        result.append((index, plan, ledger, read_jsonl(plan), read_jsonl(ledger)))
    return result


def conservation_input_hashes(run_dir: Path, manifest: dict[str, Any]) -> dict[str, str]:
    """Hash exactly the registered evidence consumed by this conservation audit."""
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        raise ValueError(f"run manifest does not exist: {manifest_path}")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("run.files must be an object")

    members: list[tuple[str, Path]] = [("run.json", manifest_path)]
    initial_member = files.get("initial_scan")
    initial_path = resolve_member(run_dir, initial_member, "run.files.initial_scan")
    if not initial_path.is_file():
        raise ValueError(f"run.files.initial_scan does not exist: {initial_path}")
    members.append((str(initial_member), initial_path))

    for scan_member in final_scan_members(manifest):
        scan_path = resolve_member(run_dir, scan_member, "run.files.final_scans")
        if not scan_path.is_file():
            raise ValueError(f"registered final scan does not exist: {scan_path}")
        members.append((scan_member, scan_path))

    batches = manifest.get("batches")
    if not isinstance(batches, list):
        raise ValueError("run.batches must be an array")
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict):
            raise ValueError(f"run.batches[{index}] must be an object")
        for member_key in ("plan", "result"):
            member = batch.get(member_key)
            path = resolve_member(run_dir, member, f"run.batches[{index}].{member_key}")
            if not path.is_file():
                raise ValueError(f"run.batches[{index}].{member_key} does not exist: {path}")
            members.append((str(member), path))

    return {member: sha256_file(path) for member, path in members}


def audit_run(run_dir: Path) -> dict[str, Any]:
    """Return a JSON-serializable conservation report for one registered run."""
    manifest = read_json(run_dir / "run.json")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("run.files must be an object")
    initial_path = resolve_member(run_dir, files.get("initial_scan"), "run.files.initial_scan")
    if not initial_path.is_file():
        raise ValueError(f"run.files.initial_scan does not exist: {initial_path}")

    violations: list[dict[str, Any]] = []
    initial_rows = read_jsonl(initial_path)
    initial = scan_index(str(files["initial_scan"]), initial_rows, violations)
    final: dict[str, dict[str, Any]] = {}
    final_paths = final_scan_members(manifest)
    final_row_count = 0
    for scan_member in final_paths:
        scan_path = resolve_member(run_dir, scan_member, "run.files.final_scans")
        if not scan_path.is_file():
            raise ValueError(f"registered final scan does not exist: {scan_path}")
        rows = read_jsonl(scan_path)
        final_row_count += len(rows)
        indexed = scan_index(scan_member, rows, violations)
        for file_id, entry in indexed.items():
            previous = final.get(file_id)
            if previous is not None:
                violations.append({
                    "kind": "duplicate_physical_row",
                    "scan": scan_member,
                    "file_id": file_id,
                    "line": entry["line"],
                    "first_scan": previous["scan"],
                    "first_line": previous["line"],
                    "path": entry["path"],
                    "first_path": previous["path"],
                })
                continue
            final[file_id] = entry

    batches = registered_batches(run_dir, manifest)
    action_ids: set[str] = set()
    # Only IDs explicitly named by a verified plan action get a path contract.
    # Descendant files of a moved directory are still fingerprint-conserved, but
    # are allowed to inherit their parent directory's path change without a
    # redundant per-file action.
    action_state: dict[str, str | None] = {}
    allowed_missing: set[str] = set()
    planned_ids: set[str] = set()
    closed_actions = 0

    for batch_index, plan_path, ledger_path, plan_rows, ledger_rows in batches:
        latest_results: dict[str, tuple[int, dict[str, Any]]] = {}
        for ledger_line, result in ledger_rows:
            action_id = str(result.get("action_id", "")).strip()
            if action_id:
                latest_results[action_id] = (ledger_line, result)
        plan_action_ids: set[str] = set()
        for line, action in plan_rows:
            action_id = str(action.get("action_id", "")).strip()
            location = {
                "batch": batch_index,
                "plan": str(plan_path.relative_to(run_dir.resolve())),
                "line": line,
            }
            if not action_id:
                violations.append({"kind": "plan_action_id_missing", **location})
                continue
            if action_id in action_ids:
                violations.append({"kind": "duplicate_plan_action_id", "action_id": action_id, **location})
                continue
            action_ids.add(action_id)
            plan_action_ids.add(action_id)
            op = str(action.get("op", "")).strip()
            file_id = str(action.get("file_id", "")).strip()
            if action.get("allow_missing") is True and (
                op not in MISSING_AUTHORIZATION_OPS
                or not file_id
                or not str(action.get("reason", "")).strip()
            ):
                violations.append({
                    "kind": "invalid_missing_authorization",
                    "action_id": action_id,
                    **location,
                })
            if op in MIGRATION_OPS and not file_id:
                violations.append({"kind": "migration_action_missing_file_id", "action_id": action_id, **location})
                continue
            if not file_id:
                result_entry = latest_results.get(action_id)
                if result_entry is not None:
                    ledger_line, result = result_entry
                    if result.get("status") == "verified":
                        identity_mismatches = operation_identity_mismatches(action, result)
                        if identity_mismatches:
                            violations.append({
                                "kind": "verified_ledger_operation_identity_mismatch",
                                "action_id": action_id,
                                "batch": batch_index,
                                "ledger": str(ledger_path.relative_to(run_dir.resolve())),
                                "line": ledger_line,
                                "mismatches": identity_mismatches,
                            })
                continue
            planned_ids.add(file_id)
            if file_id not in initial:
                violations.append({"kind": "planned_file_id_not_in_initial_scan", "action_id": action_id, "file_id": file_id, **location})
            result_entry = latest_results.get(action_id)
            if result_entry is None:
                violations.append({"kind": "migration_action_result_missing", "action_id": action_id, "file_id": file_id, **location})
                continue
            ledger_line, result = result_entry
            status = result.get("status")
            if status == "verified":
                identity_mismatches = operation_identity_mismatches(action, result)
                if identity_mismatches:
                    violations.append({
                        "kind": "verified_ledger_operation_identity_mismatch",
                        "action_id": action_id,
                        "file_id": file_id,
                        "batch": batch_index,
                        "ledger": str(ledger_path.relative_to(run_dir.resolve())),
                        "line": ledger_line,
                        "mismatches": identity_mismatches,
                    })
                    continue
                closed_actions += 1
            elif status == "skipped" and str(result.get("reason", action.get("reason", ""))).strip():
                closed_actions += 1
            else:
                violations.append({
                    "kind": "migration_action_not_closed",
                    "action_id": action_id,
                    "file_id": file_id,
                    "status": status,
                    **location,
                })
                continue
            if status != "verified":
                if op in MIGRATION_OPS:
                    source = str(action.get("from", "")).strip()
                    if not source:
                        violations.append({"kind": "migration_action_invalid_source", "action_id": action_id, **location})
                    else:
                        # A skipped action did not alter cloud state.  Its source
                        # is therefore the only defensible terminal path claim.
                        action_state[file_id] = normalize_path(source)
                continue
            if action.get("allow_missing") is True:
                if op not in MISSING_AUTHORIZATION_OPS or not str(action.get("reason", "")).strip():
                    # The malformed authorization was already reported above.
                    pass
                else:
                    allowed_missing.add(file_id)
                    action_state[file_id] = None
                continue
            expected = target_path(action)
            if op in MIGRATION_OPS and expected is None:
                violations.append({"kind": "migration_action_invalid_target", "action_id": action_id, **location})
            elif expected is not None:
                action_state[file_id] = expected
        for line, result in ledger_rows:
            action_id = str(result.get("action_id", "")).strip()
            if action_id and action_id not in plan_action_ids:
                violations.append({
                    "kind": "ledger_action_not_registered",
                    "batch": batch_index,
                    "ledger": str(ledger_path.relative_to(run_dir.resolve())),
                    "line": line,
                    "action_id": action_id,
                })

    authorized_missing = 0
    for file_id, original in initial.items():
        terminal = final.get(file_id)
        if terminal is None:
            if file_id in allowed_missing:
                authorized_missing += 1
                continue
            violations.append({
                "kind": "initial_entity_missing",
                "file_id": file_id,
                "initial_path": original["path"],
                "planned": file_id in planned_ids,
            })
            continue
        if file_id in allowed_missing:
            violations.append({
                "kind": "authorized_missing_entity_still_present",
                "file_id": file_id,
                "final_path": terminal["path"],
            })
        row = original["row"]
        final_row = terminal["row"]
        if row.get("dir") is not True:
            initial_size, final_size = row.get("size"), final_row.get("size")
            if initial_size is None or final_size is None:
                violations.append({"kind": "file_size_missing", "file_id": file_id})
            elif initial_size != final_size:
                violations.append({
                    "kind": "file_size_mismatch",
                    "file_id": file_id,
                    "initial": initial_size,
                    "final": final_size,
                })
            initial_sha1, final_sha1 = row.get("sha1"), final_row.get("sha1")
            if not isinstance(initial_sha1, str) or not initial_sha1.strip() or not isinstance(final_sha1, str) or not final_sha1.strip():
                violations.append({"kind": "file_sha1_missing", "file_id": file_id})
            elif initial_sha1.lower() != final_sha1.lower():
                violations.append({
                    "kind": "file_sha1_mismatch",
                    "file_id": file_id,
                    "initial": initial_sha1,
                    "final": final_sha1,
                })
        expected_path = action_state.get(file_id)
        if expected_path is not None and terminal["path"] != expected_path:
            violations.append({
                "kind": "planned_final_path_mismatch",
                "file_id": file_id,
                "expected": expected_path,
                "actual": terminal["path"],
            })

    hashes = conservation_input_hashes(run_dir, manifest)
    return {
        "status": "passed" if not violations else "failed",
        "checked": {
            "initial_scan_rows": len(initial_rows),
            "initial_entities": len(initial),
            "final_scans": len(final_paths),
            "final_scan_rows": final_row_count,
            "final_entities": len(final),
            "registered_batches": len(batches),
            "planned_file_ids": len(planned_ids),
            "closed_migration_actions": closed_actions,
            "authorized_missing": authorized_missing,
            "hashed_inputs": len(hashes),
        },
        "hashes": hashes,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="registered curator run bundle")
    parser.add_argument("--final", action="store_true", help="return non-zero when any conservation violation exists")
    args = parser.parse_args()
    try:
        report = audit_run(args.run_dir)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.final and report["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
