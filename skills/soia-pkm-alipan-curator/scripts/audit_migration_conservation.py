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
import posixpath
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


MISSING_AUTHORIZATION_OPS = {"delete", "remove", "trash"}
MIGRATION_OPS = {"mv", "rename"}
OPERATION_IDENTITY_FIELDS = ("action_id", "op", "from", "to", "file_id")
PROCESS_DEBT_CLASSIFICATIONS = {
    "legacy_process_debt",
    "authorization_unproven_execution",
}
PAYLOAD_CONSERVATION_VIOLATIONS = {
    "aggregate_scan_row",
    "duplicate_physical_row",
    "scan_row_missing_file_id",
    "initial_entity_missing",
    "authorized_missing_original_path_reused",
    "file_size_missing",
    "file_size_mismatch",
    "file_sha1_missing",
    "file_sha1_mismatch",
    "planned_final_path_mismatch",
}
STRICT_ISO8601_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


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


def relative_member(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    member = PurePosixPath(value)
    if member.is_absolute():
        raise ValueError(f"{label} must stay inside the run directory")
    canonical = posixpath.normpath(value)
    if canonical == ".." or canonical.startswith("../"):
        raise ValueError(f"{label} must stay inside the run directory")
    return canonical


def resolve_member(run_dir: Path, value: object, label: str) -> Path:
    member_value = relative_member(value, label)
    member = Path(member_value)
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


def parse_strict_iso8601_timestamp(value: object) -> datetime | None:
    """Parse a timezone-bearing ISO-8601 instant without accepting variants.

    Cleanup authorization and result evidence is an ordering contract, so a
    permissive parser must not silently accept a local or ambiguous time.
    """

    if not isinstance(value, str) or not STRICT_ISO8601_TIMESTAMP.fullmatch(value):
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _registered_file_members(manifest: dict[str, Any]) -> set[str]:
    """Return canonical ``run.files`` members that reserve paths."""

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("run.files must be an object")
    members: set[str] = set()
    for name, value in files.items():
        label = f"run.files.{name}"
        if isinstance(value, str) and value.strip():
            members.add(relative_member(value, label))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                members.add(relative_member(item, f"{label}[{index}]"))
    return members


def validate_cleanup_result_paths(manifest: dict[str, Any]) -> list[str]:
    """Validate cleanup ledgers have one safe, non-aliased result path each.

    A cleanup result is mutable while cleanup executes.  It must therefore
    never overlap run metadata, any plan, authorization/evidence input, or a
    different cleanup ledger; otherwise an append could corrupt an immutable
    input or make two destructive batches share history.
    """

    batches = manifest.get("batches")
    if not isinstance(batches, list):
        raise ValueError("run.batches must be an array")
    cleanup_batches = manifest.get("cleanup_batches", [])
    if not isinstance(cleanup_batches, list):
        raise ValueError("run.cleanup_batches must be an array")
    if not cleanup_batches:
        return []

    reserved = {"run.json", *_registered_file_members(manifest)}
    for group, entries in (("batches", batches), ("cleanup_batches", cleanup_batches)):
        for index, batch in enumerate(entries):
            if not isinstance(batch, dict):
                raise ValueError(f"run.{group}[{index}] must be an object")
            reserved.add(relative_member(batch.get("plan"), f"run.{group}[{index}].plan"))
            if group == "batches":
                reserved.add(relative_member(batch.get("result"), f"run.{group}[{index}].result"))

    results: list[str] = []
    for index, batch in enumerate(cleanup_batches):
        result = relative_member(batch.get("result"), f"run.cleanup_batches[{index}].result")
        if result in reserved:
            raise ValueError(
                f"run.cleanup_batches[{index}].result must not alias immutable/input member: {result}"
            )
        if result in results:
            raise ValueError(
                f"run.cleanup_batches[{index}].result must not be shared by cleanup batches: {result}"
            )
        results.append(result)
    return results


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


def exact_operation_identity_mismatches(
    action: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return raw identity mismatches for strict cleanup authorization."""
    return {
        field: {"expected": action.get(field), "actual": result.get(field)}
        for field in OPERATION_IDENTITY_FIELDS
        if action.get(field) != result.get(field)
    }


def batch_operation_violation_kind(batch_group: str, op: str) -> str | None:
    """Return the contract violation for an action in the wrong batch type."""
    if batch_group == "batches" and op in MISSING_AUTHORIZATION_OPS:
        return "cleanup_action_in_regular_batch"
    if batch_group == "cleanup_batches" and op not in MISSING_AUTHORIZATION_OPS:
        return "non_cleanup_action_in_cleanup_batch"
    return None


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


def registered_batch_declarations(manifest: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    """Return normal and optional cleanup batch declarations in manifest order.

    ``batches`` remains the original required collection.  ``cleanup_batches``
    is deliberately optional so established run bundles keep their old shape;
    when present it uses the same ``plan`` / ``result`` contract.
    """
    batches = manifest.get("batches")
    if not isinstance(batches, list):
        raise ValueError("run.batches must be an array")
    cleanup_batches = manifest.get("cleanup_batches", [])
    if not isinstance(cleanup_batches, list):
        raise ValueError("run.cleanup_batches must be an array")

    declarations: list[tuple[str, int, dict[str, Any]]] = []
    for group, entries in (("batches", batches), ("cleanup_batches", cleanup_batches)):
        for index, batch in enumerate(entries):
            if not isinstance(batch, dict):
                raise ValueError(f"run.{group}[{index}] must be an object")
            declarations.append((group, index, batch))
    return declarations


def registered_batches(
    run_dir: Path, manifest: dict[str, Any]
) -> list[tuple[str, int, Path, Path, list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]]]]:
    """Load every registered normal and cleanup batch.

    The group name keeps cleanup evidence distinct in diagnostics while action
    IDs are intentionally checked in one shared namespace by callers.
    """
    result = []
    for group, index, batch in registered_batch_declarations(manifest):
        label = f"run.{group}[{index}]"
        plan = resolve_member(run_dir, batch.get("plan"), f"{label}.plan")
        ledger = resolve_member(run_dir, batch.get("result"), f"{label}.result")
        if not plan.is_file():
            raise ValueError(f"{label}.plan does not exist: {plan}")
        if not ledger.is_file():
            raise ValueError(f"{label}.result does not exist: {ledger}")
        result.append((group, index, plan, ledger, read_jsonl(plan), read_jsonl(ledger)))
    return result


def latest_results_by_action_id(
    ledger_rows: list[tuple[int, dict[str, Any]]],
) -> dict[str, tuple[int, dict[str, Any]]]:
    """Return the physically latest ledger row for each non-empty action ID."""
    latest: dict[str, tuple[int, dict[str, Any]]] = {}
    for line, result in ledger_rows:
        action_id = str(result.get("action_id", "")).strip()
        if action_id:
            latest[action_id] = (line, result)
    return latest


def scan_paths_by_file_id(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Return unambiguous scan paths keyed by non-empty file ID.

    Duplicate IDs are omitted so ambiguous initial evidence can never authorize
    a destructive missing-entity exemption.
    """
    paths: dict[str, str] = {}
    ambiguous: set[str] = set()
    for row in rows:
        file_id = str(row.get("id", "")).strip()
        if not file_id or file_id in ambiguous:
            continue
        if file_id in paths:
            paths.pop(file_id)
            ambiguous.add(file_id)
            continue
        paths[file_id] = full_path(row)
    return paths


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def cleanup_authorization_key(action: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return the exact immutable authorization binding for one cleanup action."""

    return tuple(
        str(action.get(field, "")).strip()
        for field in ("authorization_ref", "action_id", "file_id", "from")
    )


def load_cleanup_authorizations(
    run_dir: Path,
    manifest: dict[str, Any],
    violations: list[dict[str, Any]] | None = None,
) -> dict[tuple[str, str, str, str], tuple[int, dict[str, Any]]]:
    """Load registered immutable cleanup authorization rows, fail closed.

    A free-form ``authorization_ref`` in a plan is never evidence by itself.
    It has to resolve to exactly one registered JSONL row binding the reference,
    action, file ID, and source path, with an explicit approval decision.
    """

    cleanup_batches = manifest.get("cleanup_batches", [])
    if not isinstance(cleanup_batches, list):
        raise ValueError("run.cleanup_batches must be an array")
    if not cleanup_batches:
        return {}
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("run.files must be an object")
    member = files.get("cleanup_authorizations")
    if not isinstance(member, str) or not member.strip():
        if violations is not None:
            violations.append({"kind": "cleanup_authorizations_not_registered"})
        return {}
    try:
        path = resolve_member(run_dir, member, "run.files.cleanup_authorizations")
    except ValueError as error:
        if violations is not None:
            violations.append({"kind": "cleanup_authorizations_path_invalid", "detail": str(error)})
        return {}
    if not path.is_file():
        if violations is not None:
            violations.append({"kind": "cleanup_authorizations_missing", "path": member})
        return {}

    indexed: dict[tuple[str, str, str, str], tuple[int, dict[str, Any]]] = {}
    for line, authorization in read_jsonl(path):
        key = cleanup_authorization_key(authorization)
        problems: list[str] = []
        for field in ("authorization_ref", "action_id", "file_id", "from", "authorized_at"):
            if not _non_empty_string(authorization.get(field)):
                problems.append(f"authorization_{field}_missing_or_invalid")
        if parse_strict_iso8601_timestamp(authorization.get("authorized_at")) is None:
            problems.append("authorization_authorized_at_missing_or_invalid")
        if authorization.get("decision") != "approved":
            problems.append("authorization_decision_not_approved")
        if problems:
            if violations is not None:
                violations.append({
                    "kind": "invalid_cleanup_authorization",
                    "authorization": str(member),
                    "line": line,
                    "problems": sorted(set(problems)),
                })
            continue
        if key in indexed:
            if violations is not None:
                violations.append({
                    "kind": "duplicate_cleanup_authorization",
                    "authorization": str(member),
                    "line": line,
                    "first_line": indexed[key][0],
                    "authorization_ref": key[0],
                    "action_id": key[1],
                    "file_id": key[2],
                    "from": key[3],
                })
            indexed.pop(key)
            continue
        indexed[key] = (line, authorization)
    return indexed


def cleanup_authorization_binding_problems(
    action: dict[str, Any],
    authorizations: dict[tuple[str, str, str, str], tuple[int, dict[str, Any]]],
) -> tuple[list[str], tuple[int, dict[str, Any]] | None]:
    """Validate that a cleanup plan is bound to one approved authorization.

    This is intentionally independent from cleanup-result validation so the
    non-final audit can fail before the cleanup writer exists or appends a
    ledger row.
    """

    problems = []
    for field in ("authorization_ref", "action_id", "file_id", "from"):
        if not _non_empty_string(action.get(field)):
            problems.append(f"plan_{field}_missing_or_invalid")
    authorization = authorizations.get(cleanup_authorization_key(action))
    if authorization is None:
        problems.append("registered_authorization_missing_or_not_exact")
    return problems, authorization


def load_cleanup_process_debt(
    run_dir: Path,
    manifest: dict[str, Any],
    violations: list[dict[str, Any]] | None = None,
) -> dict[str, tuple[int, dict[str, Any]]]:
    """Load post-hoc cleanup records without turning them into authorization.

    Process-debt records preserve what happened before a prospective
    authorization contract existed.  They may support a payload reconciliation,
    but can never grant ``authorized_missing`` or a passing final-complete
    status.
    """

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("run.files must be an object")
    member = files.get("cleanup_process_debt")
    if member in (None, ""):
        return {}
    try:
        path = resolve_member(run_dir, member, "run.files.cleanup_process_debt")
    except ValueError as error:
        if violations is not None:
            violations.append({"kind": "cleanup_process_debt_path_invalid", "detail": str(error)})
        return {}
    if not path.is_file():
        if violations is not None:
            violations.append({"kind": "cleanup_process_debt_missing", "path": str(member)})
        return {}

    indexed: dict[str, tuple[int, dict[str, Any]]] = {}
    action_ids: set[str] = set()
    row_count = 0
    for line, debt in read_jsonl(path):
        row_count += 1
        problems: list[str] = []
        for field in ("action_id", "file_id", "from", "classification", "recorded_at", "historic_plan", "historic_result"):
            if not _non_empty_string(debt.get(field)):
                problems.append(f"process_debt_{field}_missing_or_invalid")
        if debt.get("classification") not in PROCESS_DEBT_CLASSIFICATIONS:
            problems.append("process_debt_classification_invalid")
        if parse_strict_iso8601_timestamp(debt.get("recorded_at")) is None:
            problems.append("process_debt_recorded_at_missing_or_invalid")
        if debt.get("authorized_at") not in (None, ""):
            problems.append("process_debt_must_not_have_authorized_at")
        for field in ("historic_plan", "historic_result"):
            value = debt.get(field)
            if not _non_empty_string(value):
                continue
            try:
                evidence_path = resolve_member(run_dir, value, f"cleanup process debt {field}")
            except ValueError:
                problems.append(f"process_debt_{field}_path_invalid")
                continue
            if not evidence_path.is_file():
                problems.append(f"process_debt_{field}_missing")

        action_id = str(debt.get("action_id", "")).strip()
        file_id = str(debt.get("file_id", "")).strip()
        if action_id and action_id in action_ids:
            problems.append("duplicate_process_debt_action_id")
        if file_id and file_id in indexed:
            problems.append("duplicate_process_debt_file_id")
        if problems:
            if violations is not None:
                violations.append({
                    "kind": "invalid_cleanup_process_debt",
                    "debt": str(member),
                    "line": line,
                    "problems": sorted(set(problems)),
                })
            continue
        action_ids.add(action_id)
        indexed[file_id] = (line, debt)
    if row_count == 0 and violations is not None:
        violations.append({
            "kind": "invalid_cleanup_process_debt",
            "debt": str(member),
            "problems": ["cleanup_process_debt_empty"],
        })
    return indexed


def collect_reconciled_process_debt_missing_ids(
    debts: dict[str, tuple[int, dict[str, Any]]],
    initial_paths: dict[str, str],
    final: dict[str, dict[str, Any]],
    final_path_owners: dict[str, set[str]],
    violations: list[dict[str, Any]],
) -> set[str]:
    """Reconcile deleted historic payloads while retaining their process debt."""

    reconciled: set[str] = set()
    for file_id, (line, debt) in debts.items():
        action_id = str(debt["action_id"])
        classification = str(debt["classification"])
        expected_path = initial_paths.get(file_id)
        if expected_path is None or debt.get("from") != expected_path:
            violations.append({
                "kind": "cleanup_process_debt_initial_identity_mismatch",
                "action_id": action_id,
                "file_id": file_id,
                "classification": classification,
                "line": line,
                "expected_from": expected_path,
                "actual_from": debt.get("from"),
            })
            continue
        if file_id in final:
            violations.append({
                "kind": "cleanup_process_debt_terminal_entity_present",
                "action_id": action_id,
                "file_id": file_id,
                "classification": classification,
                "line": line,
            })
            continue
        replacement_ids = sorted(final_path_owners.get(expected_path, set()) - {file_id})
        if replacement_ids:
            violations.append({
                "kind": "cleanup_process_debt_original_path_reused",
                "action_id": action_id,
                "file_id": file_id,
                "classification": classification,
                "line": line,
                "original_path": expected_path,
                "replacement_file_ids": replacement_ids,
            })
            continue
        reconciled.add(file_id)
        violations.append({
            "kind": "cleanup_process_debt",
            "action_id": action_id,
            "file_id": file_id,
            "classification": classification,
            "line": line,
            "terminal_conservation": "reconciled_but_not_authorized",
        })
    return reconciled


def collect_strict_authorized_missing_ids(
    batches: list[tuple[str, int, Path, Path, list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]]]],
    initial_paths: dict[str, str],
    authorizations: dict[tuple[str, str, str, str], tuple[int, dict[str, Any]]],
    violations: list[dict[str, Any]] | None = None,
) -> set[str]:
    """Collect IDs backed by complete authorization and deletion evidence.

    This deliberately reads plan/result evidence, never a conservation report
    summary.  The plan must identify the original scanned entity and explicit
    authorization; its latest ledger row must exactly match that operation and
    prove an empty pre-delete shell, recycle-bin removal, and post-delete
    absence.
    """
    authorized: set[str] = set()
    for batch_group, batch_index, plan_path, ledger_path, plan_rows, ledger_rows in batches:
        if batch_group != "cleanup_batches":
            continue
        latest_results = latest_results_by_action_id(ledger_rows)
        for plan_line, action in plan_rows:
            problems: list[str] = []
            for field in ("action_id", "op", "from", "file_id", "reason", "authorization_ref"):
                if not _non_empty_string(action.get(field)):
                    problems.append(f"plan_{field}_missing_or_invalid")

            action_id = action.get("action_id") if isinstance(action.get("action_id"), str) else ""
            file_id = action.get("file_id") if isinstance(action.get("file_id"), str) else ""
            source = action.get("from") if isinstance(action.get("from"), str) else ""
            op = action.get("op") if isinstance(action.get("op"), str) else ""
            authorization_ref = action.get("authorization_ref")
            if op not in MISSING_AUTHORIZATION_OPS:
                problems.append("plan_op_not_cleanup")
            if action.get("allow_missing") is not True:
                problems.append("plan_allow_missing_not_true")

            expected_source = initial_paths.get(file_id)
            if expected_source is None:
                problems.append("plan_file_id_not_in_initial_scan")
            elif source != expected_source:
                problems.append("plan_from_mismatch")
            authorization_problems, authorization_entry = cleanup_authorization_binding_problems(
                action,
                authorizations,
            )
            problems.extend(authorization_problems)

            result_entry = latest_results.get(action_id)
            ledger_line: int | None = None
            identity_mismatches: dict[str, dict[str, Any]] = {}
            if result_entry is None:
                problems.append("latest_result_missing")
            else:
                ledger_line, result = result_entry
                for field in ("action_id", "op", "from", "file_id"):
                    if not _non_empty_string(result.get(field)):
                        problems.append(f"result_{field}_missing_or_invalid")
                identity_mismatches = exact_operation_identity_mismatches(action, result)
                if identity_mismatches:
                    problems.append("result_operation_identity_mismatch")
                if result.get("status") != "verified":
                    problems.append("result_status_not_verified")
                if (
                    not _non_empty_string(authorization_ref)
                    or result.get("authorization_ref") != authorization_ref
                ):
                    problems.append("result_authorization_ref_mismatch")
                result_timestamp = parse_strict_iso8601_timestamp(result.get("ts"))
                if result_timestamp is None:
                    problems.append("result_ts_missing_or_invalid")
                elif authorization_entry is not None:
                    authorized_at = parse_strict_iso8601_timestamp(
                        authorization_entry[1].get("authorized_at")
                    )
                    # ``load_cleanup_authorizations`` only indexes valid rows,
                    # but retain fail-closed behavior if a caller supplied an
                    # inconsistent index directly.
                    if authorized_at is None or result_timestamp < authorized_at:
                        problems.append("result_ts_before_authorized_at")

                verify = result.get("verify")
                if not isinstance(verify, dict):
                    problems.append("result_verify_missing_or_invalid")
                else:
                    predelete = verify.get("predelete")
                    if not isinstance(predelete, dict):
                        problems.extend((
                            "result_predelete_files_not_zero",
                            "result_predelete_dirs_not_zero",
                        ))
                    else:
                        if type(predelete.get("files")) is not int or predelete.get("files") != 0:
                            problems.append("result_predelete_files_not_zero")
                        if type(predelete.get("dirs")) is not int or predelete.get("dirs") != 0:
                            problems.append("result_predelete_dirs_not_zero")
                    recycle_status = verify.get("recycle_bin_status")
                    if (
                        recycle_status != "removed_to_recycle_bin_verified"
                    ):
                        problems.append("result_recycle_bin_status_invalid")
                    if verify.get("postdelete_absence_verified") is not True:
                        problems.append("result_postdelete_absence_not_verified")

            if problems:
                if violations is not None:
                    violation: dict[str, Any] = {
                        "kind": "invalid_cleanup_authorization_evidence",
                        "action_id": action_id,
                        "file_id": file_id,
                        "batch": batch_index,
                        "batch_group": batch_group,
                        "plan": str(plan_path),
                        "plan_line": plan_line,
                        "problems": sorted(set(problems)),
                    }
                    if ledger_line is not None:
                        violation["ledger"] = str(ledger_path)
                        violation["ledger_line"] = ledger_line
                    if identity_mismatches:
                        violation["mismatches"] = identity_mismatches
                    if expected_source is not None and source != expected_source:
                        violation["expected_from"] = expected_source
                        violation["actual_from"] = source
                    violations.append(violation)
                continue
            authorized.add(file_id)
    return authorized


def conservation_input_hashes(run_dir: Path, manifest: dict[str, Any]) -> dict[str, str]:
    """Hash exactly the registered evidence consumed by this conservation audit."""
    validate_cleanup_result_paths(manifest)
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

    for group, index, batch in registered_batch_declarations(manifest):
        plan_member = batch.get("plan")
        plan_label = f"run.{group}[{index}].plan"
        plan_path = resolve_member(run_dir, plan_member, plan_label)
        if not plan_path.is_file():
            raise ValueError(f"{plan_label} does not exist: {plan_path}")
        members.append((str(plan_member), plan_path))

        result_member = batch.get("result")
        result_label = f"run.{group}[{index}].result"
        result_path = resolve_member(run_dir, result_member, result_label)
        if not result_path.is_file():
            raise ValueError(f"{result_label} does not exist: {result_path}")
        members.append((str(result_member), result_path))

    cleanup_batches = manifest.get("cleanup_batches", [])
    if cleanup_batches:
        authorization_member = files.get("cleanup_authorizations")
        if not isinstance(authorization_member, str) or not authorization_member.strip():
            raise ValueError("run.files.cleanup_authorizations is required for cleanup_batches")
        authorization_path = resolve_member(
            run_dir,
            authorization_member,
            "run.files.cleanup_authorizations",
        )
        if not authorization_path.is_file():
            raise ValueError(f"run.files.cleanup_authorizations does not exist: {authorization_path}")
        # Parse it now so malformed immutable evidence is never merely hashed.
        load_cleanup_authorizations(run_dir, manifest)
        members.append((authorization_member, authorization_path))

    process_debt_member = files.get("cleanup_process_debt")
    if process_debt_member not in (None, ""):
        process_debt_path = resolve_member(
            run_dir,
            process_debt_member,
            "run.files.cleanup_process_debt",
        )
        if not process_debt_path.is_file():
            raise ValueError(
                f"run.files.cleanup_process_debt does not exist: {process_debt_path}"
            )
        members.append((str(process_debt_member), process_debt_path))
        # The registry alone is not enough: its historic plan/result pointers
        # are the immutable evidence that keeps a post-hoc record from being
        # silently rewritten into an unexplained terminal deletion.
        for _, debt in load_cleanup_process_debt(run_dir, manifest).values():
            for field in ("historic_plan", "historic_result"):
                member = str(debt[field])
                evidence_path = resolve_member(
                    run_dir,
                    member,
                    f"cleanup process debt {field}",
                )
                if not evidence_path.is_file():
                    raise ValueError(
                        f"cleanup process debt {field} does not exist: {evidence_path}"
                    )
                members.append((member, evidence_path))

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
    initial_paths = scan_paths_by_file_id([row for _, row in initial_rows])
    authorizations = load_cleanup_authorizations(run_dir, manifest, violations)
    process_debts = load_cleanup_process_debt(run_dir, manifest, violations)
    allowed_missing = collect_strict_authorized_missing_ids(
        batches,
        initial_paths,
        authorizations,
        violations,
    )
    planned_ids: set[str] = set()
    closed_actions = 0

    for batch_group, batch_index, plan_path, ledger_path, plan_rows, ledger_rows in batches:
        latest_results = latest_results_by_action_id(ledger_rows)
        plan_action_ids: set[str] = set()
        for line, action in plan_rows:
            action_id = str(action.get("action_id", "")).strip()
            location = {
                "batch": batch_index,
                "plan": str(plan_path.relative_to(run_dir.resolve())),
                "line": line,
            }
            if batch_group != "batches":
                location["batch_group"] = batch_group
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
            operation_violation = batch_operation_violation_kind(batch_group, op)
            if operation_violation:
                violations.append({
                    "kind": operation_violation,
                    "action_id": action_id,
                    "op": op,
                    **location,
                })
            if batch_group == "batches" and action.get("allow_missing") is True and (
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
                if file_id in allowed_missing:
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
                location = {
                    "batch": batch_index,
                    "ledger": str(ledger_path.relative_to(run_dir.resolve())),
                    "line": line,
                }
                if batch_group != "batches":
                    location["batch_group"] = batch_group
                violations.append({
                    "kind": "ledger_action_not_registered",
                    "action_id": action_id,
                    **location,
                })

    # Historical records are evidence of process debt, not executable cleanup
    # actions.  In particular, a later plan must never launder one of these
    # records into a prospective authorization exemption.
    for debt_file_id, (debt_line, debt) in process_debts.items():
        debt_action_id = str(debt["action_id"])
        if debt_action_id in action_ids:
            violations.append({
                "kind": "cleanup_process_debt_action_registered_as_executable",
                "action_id": debt_action_id,
                "file_id": debt_file_id,
                "classification": debt["classification"],
                "line": debt_line,
            })

    authorized_missing = 0
    reconciled_process_debt_missing = 0
    final_path_owners: dict[str, set[str]] = {}
    for terminal_file_id, terminal_entry in final.items():
        final_path_owners.setdefault(terminal_entry["path"], set()).add(terminal_file_id)
    reconciled_process_debt = collect_reconciled_process_debt_missing_ids(
        process_debts,
        initial_paths,
        final,
        final_path_owners,
        violations,
    )
    for file_id, original in initial.items():
        terminal = final.get(file_id)
        if terminal is None:
            if file_id in allowed_missing:
                replacement_ids = sorted(final_path_owners.get(original["path"], set()) - {file_id})
                if replacement_ids:
                    violations.append({
                        "kind": "authorized_missing_original_path_reused",
                        "file_id": file_id,
                        "original_path": original["path"],
                        "replacement_file_ids": replacement_ids,
                    })
                    continue
                authorized_missing += 1
                continue
            if file_id in reconciled_process_debt:
                reconciled_process_debt_missing += 1
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
    payload_violation_count = sum(
        1 for violation in violations
        if violation.get("kind") in PAYLOAD_CONSERVATION_VIOLATIONS
    )
    process_debt_violation_count = sum(
        1 for violation in violations
        if "process_debt" in str(violation.get("kind", ""))
    )
    return {
        "status": "passed" if not violations else "failed",
        "checked": {
            "initial_scan_rows": len(initial_rows),
            "initial_entities": len(initial),
            "final_scans": len(final_paths),
            "final_scan_rows": final_row_count,
            "final_entities": len(final),
            "registered_batches": len(batches),
            "registered_cleanup_batches": sum(1 for group, *_ in batches if group == "cleanup_batches"),
            "planned_file_ids": len(planned_ids),
            "closed_migration_actions": closed_actions,
            "authorized_missing": authorized_missing,
            "process_debt_entries": len(process_debts),
            "process_debt_reconciled_missing": reconciled_process_debt_missing,
            "payload_conservation": "passed" if payload_violation_count == 0 else "failed",
            "structural_process_debt": "passed" if process_debt_violation_count == 0 else "failed",
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
