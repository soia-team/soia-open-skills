#!/usr/bin/env python3
"""Audit a curator run bundle before a large partition is declared complete."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import audit_migration_conservation
import preflight_gate


FINAL_FILES = (
    "initial_scan",
    "initial_errors",
    "content_audit",
    "structure_contract",
    "final_scan",
    "final_errors",
    "structure_audit",
    "ai_review",
    "receipt",
)

REQUIRED_AI_CHECKS = {
    "focus-target-coverage",
    "classification-axis",
    "semantic-name-match",
    "long-series",
    "numbering-guides",
    "consumer-links",
    "count-conservation",
}


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def read_jsonl(path: Path) -> list[dict]:
    return [value for _, value in read_jsonl_with_lines(path)]


def read_jsonl_with_lines(path: Path) -> list[tuple[int, dict]]:
    """Read JSONL rows while retaining their physical line numbers."""

    rows: list[tuple[int, dict]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            rows.append((line_number, value))
    return rows


def _plan_location(
    batch_index: int,
    batch: dict,
    plan_path: object,
    line_number: int,
    *,
    batch_group: str = "batches",
) -> dict:
    """Return stable manifest/plan coordinates for an action row."""

    location = {
        "batch": batch_index,
        "plan": str(plan_path),
        "line": line_number,
    }
    if str(batch.get("name", "")).strip():
        location["batch_name"] = str(batch["name"])
    if batch_group != "batches":
        location["batch_group"] = batch_group
    return location


def _append_plan_action_id_violations(
    violations: list[dict],
    seen_action_ids: dict[str, dict],
    batch_index: int,
    batch: dict,
    plan_value: object,
    plan_entries: list[tuple[int, dict]],
    *,
    batch_group: str = "batches",
) -> list[str]:
    """Validate one registered plan and return its normalized action IDs."""

    plan_ids: list[str] = []
    for line_number, item in plan_entries:
        action_id = str(item.get("action_id", "")).strip()
        plan_ids.append(action_id)
        location = _plan_location(
            batch_index,
            batch,
            plan_value,
            line_number,
            batch_group=batch_group,
        )
        if not action_id:
            # Keep the historical violation kind for missing/empty IDs.
            violations.append({
                "kind": "invalid_or_duplicate_plan_action_id",
                **location,
            })
            continue
        first_seen = seen_action_ids.get(action_id)
        if first_seen is not None:
            violations.append({
                "kind": "duplicate_plan_action_id",
                "action_id": action_id,
                **location,
                "first_seen": first_seen,
            })
            continue
        seen_action_ids[action_id] = location
    return plan_ids


def resolve_member(run_dir: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} must stay inside the run directory")
    resolved_root = run_dir.resolve()
    resolved = (run_dir / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"{label} escapes the run directory")
    return resolved


def scan_full_path(row: dict) -> str:
    parent = "/" + str(row.get("path", "")).strip().strip("/")
    name = str(row.get("name", "")).strip("/")
    return (parent.rstrip("/") + "/" + name).replace("//", "/")


def find_scan_target(rows: list[dict], target_id: str, target_path: str) -> bool:
    normalized_path = "/" + target_path.strip().strip("/")
    return any(
        (target_id and str(row.get("id", "")) == target_id)
        or (target_path and scan_full_path(row) == normalized_path)
        for row in rows
    )


def collect_final_scan_rows(
    run_dir: Path,
    manifest: dict,
    paths: dict[str, Path],
    violations: list[dict],
) -> list[dict]:
    """Merge every registered final scan, honoring the plural-first contract.

    ``run.files`` may register the terminal scan either as the legacy singular
    ``final_scan`` member or as a non-empty ``final_scans`` array; the plural
    form wins when both are present, mirroring
    ``audit_migration_conservation.final_scan_members``.
    """
    configured_files = manifest.get("files", {})
    if "final_scans" not in configured_files:
        # Singular-only contract: keep the historical single-file behavior.
        path = paths.get("final_scan")
        return read_jsonl(path) if path is not None and path.is_file() else []
    try:
        members = audit_migration_conservation.final_scan_members(manifest)
    except ValueError as error:
        violations.append({"kind": "invalid_final_scan_declaration", "detail": str(error)})
        return []
    rows: list[dict] = []
    for index, member in enumerate(members):
        label = f"final_scans[{index}]"
        try:
            member_path = resolve_member(run_dir, member, f"run.files.{label}")
        except ValueError as error:
            violations.append({"kind": "invalid_run_file_path", "file": label, "detail": str(error)})
            continue
        if not member_path.is_file():
            violations.append({"kind": "run_file_missing", "file": label, "path": member})
            continue
        rows.extend(read_jsonl(member_path))
    return rows


def batch_groups(manifest: dict) -> list[tuple[str, list[dict]]]:
    """Return normal batches plus the optional cleanup batch collection."""
    batches = manifest.get("batches", [])
    if not isinstance(batches, list):
        raise ValueError("run.batches must be an array")
    cleanup_batches = manifest.get("cleanup_batches", [])
    if not isinstance(cleanup_batches, list):
        raise ValueError("run.cleanup_batches must be an array")
    return [("batches", batches), ("cleanup_batches", cleanup_batches)]


def strict_authorized_missing_targets(
    run_dir: Path,
    manifest: dict,
    initial_rows: list[dict],
) -> tuple[set[tuple[str, str]], list[dict]]:
    """Read current ledgers to decide final-scan missing-target exemptions.

    The passing conservation report is deliberately not an input here: report
    summaries are derived evidence and cannot grant a destructive exemption.
    """
    try:
        batches = audit_migration_conservation.registered_batches(run_dir, manifest)
    except (OSError, ValueError):
        # The ordinary batch validation below will report the malformed or
        # missing evidence.  It must never become a reason to waive a target.
        return set(), []
    initial_paths = audit_migration_conservation.scan_paths_by_file_id(initial_rows)
    authorization_violations: list[dict] = []
    authorizations = audit_migration_conservation.load_cleanup_authorizations(
        run_dir,
        manifest,
        authorization_violations,
    )
    authorized_ids = audit_migration_conservation.collect_strict_authorized_missing_ids(
        batches,
        initial_paths,
        authorizations,
        authorization_violations,
    )
    return {
        (file_id, path)
        for file_id, path in initial_paths.items()
        if file_id in authorized_ids
    }, authorization_violations


def append_migration_conservation_violations(
    violations: list[dict],
    run_dir: Path,
    manifest: dict,
) -> str:
    """Require a current, registered, passing migration conservation report."""
    configured_files = manifest.get("files")
    if not isinstance(configured_files, dict) or "migration_conservation" not in configured_files:
        violations.append({"kind": "migration_conservation_report_not_registered"})
        return "not_registered"
    try:
        report_path = resolve_member(
            run_dir,
            configured_files["migration_conservation"],
            "run.files.migration_conservation",
        )
    except ValueError as error:
        violations.append({
            "kind": "migration_conservation_report_path_invalid",
            "detail": str(error),
        })
        return "invalid_path"
    if not report_path.is_file():
        violations.append({
            "kind": "migration_conservation_report_missing",
            "path": str(configured_files["migration_conservation"]),
        })
        return "missing"
    try:
        report = read_json(report_path)
    except ValueError as error:
        violations.append({"kind": "migration_conservation_report_invalid", "detail": str(error)})
        return "invalid"

    if report.get("status") != "passed":
        violations.append({
            "kind": "migration_conservation_report_not_passed",
            "actual": report.get("status"),
        })
    checked = report.get("checked")
    has_process_debt = (
        isinstance(configured_files, dict)
        and configured_files.get("cleanup_process_debt") not in (None, "")
    )
    structural_process_debt = checked.get("structural_process_debt") if isinstance(checked, dict) else None
    if has_process_debt and structural_process_debt != "passed":
        violations.append({
            "kind": "cleanup_process_debt_blocks_final_complete",
            "actual": structural_process_debt,
            "entries": checked.get("process_debt_entries") if isinstance(checked, dict) else None,
        })

    try:
        current_hashes = audit_migration_conservation.conservation_input_hashes(run_dir, manifest)
    except (OSError, ValueError) as error:
        violations.append({
            "kind": "migration_conservation_report_hashes_unavailable",
            "detail": str(error),
        })
        return "failed"

    recorded_hashes = report.get("hashes")
    if not isinstance(recorded_hashes, dict):
        violations.append({"kind": "migration_conservation_report_hashes_missing_or_invalid"})
        return "failed"

    expected_members = set(current_hashes)
    reported_members = {str(member) for member in recorded_hashes}
    if expected_members != reported_members:
        violations.append({
            "kind": "migration_conservation_report_hash_set_mismatch",
            "missing": sorted(expected_members - reported_members),
            "unexpected": sorted(reported_members - expected_members),
        })

    for member in sorted(expected_members & reported_members):
        expected = current_hashes[member]
        actual = recorded_hashes.get(member)
        if actual != expected:
            violations.append({
                "kind": "migration_conservation_report_hash_mismatch",
                "member": member,
                "expected": expected,
                "actual": actual,
            })
    return "passed" if report.get("status") == "passed" and not any(
        violation["kind"].startswith("migration_conservation_report_hash")
        for violation in violations
    ) else "failed"


def audit_bundle(run_dir: Path, *, final: bool, require_preflight: bool | None = None) -> dict:
    violations: list[dict] = []
    if require_preflight is None:
        require_preflight = not final
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        return {"status": "failed", "checked": {}, "violations": [{"kind": "run_manifest_missing"}]}
    manifest = read_json(manifest_path)

    try:
        audit_migration_conservation.validate_cleanup_result_paths(manifest)
    except ValueError as error:
        violations.append({"kind": "invalid_cleanup_result_path", "detail": str(error)})

    preflight_result = None
    if require_preflight:
        preflight_result = preflight_gate.verify_preflight_gate(run_dir)
        violations.extend(preflight_result.get("violations", []))

    if manifest.get("schema_version") != 1:
        violations.append({"kind": "unsupported_schema_version", "actual": manifest.get("schema_version")})
    if not str(manifest.get("run_id", "")).strip():
        violations.append({"kind": "run_id_missing"})
    partition = manifest.get("partition")
    if not isinstance(partition, dict) or not str(partition.get("path", "")).strip():
        violations.append({"kind": "partition_missing"})
    if final and manifest.get("status") != "completed":
        violations.append({"kind": "run_not_completed", "actual": manifest.get("status")})

    configured_files = manifest.get("files", {})
    if not isinstance(configured_files, dict):
        raise ValueError("run.files must be an object")
    required_files = FINAL_FILES if final else ("initial_scan", "initial_errors", "content_audit")
    paths: dict[str, Path] = {}
    for key in required_files:
        if key == "final_scan" and "final_scans" in configured_files:
            # Plural registration takes precedence; validated by
            # collect_final_scan_rows below.
            continue
        if key not in configured_files:
            violations.append({"kind": "run_file_not_declared", "file": key})
            continue
        try:
            path = resolve_member(run_dir, configured_files[key], f"run.files.{key}")
        except ValueError as error:
            violations.append({"kind": "invalid_run_file_path", "file": key, "detail": str(error)})
            continue
        paths[key] = path
        if not path.is_file():
            violations.append({"kind": "run_file_missing", "file": key, "path": str(configured_files[key])})

    initial_rows = read_jsonl(paths["initial_scan"]) if paths.get("initial_scan", Path()).is_file() else []
    audit_rows = read_jsonl(paths["content_audit"]) if paths.get("content_audit", Path()).is_file() else []
    final_rows = collect_final_scan_rows(run_dir, manifest, paths, violations) if final else []
    if not initial_rows:
        violations.append({"kind": "initial_scan_empty"})
    if not audit_rows:
        violations.append({"kind": "content_audit_empty"})
    if final and not final_rows:
        violations.append({"kind": "final_scan_empty"})
    if any("agg_files" in row for row in final_rows):
        violations.append({"kind": "final_scan_contains_aggregate_rows"})

    configured_batch_groups = batch_groups(manifest)
    batches = configured_batch_groups[0][1]
    cleanup_batches = configured_batch_groups[1][1]
    prospective_authorizations: dict[tuple[str, str, str, str], tuple[int, dict]] = {}
    if not final and cleanup_batches:
        authorization_violations: list[dict] = []
        prospective_authorizations = audit_migration_conservation.load_cleanup_authorizations(
            run_dir,
            manifest,
            authorization_violations,
        )
        violations.extend(authorization_violations)
    authorized_missing_targets: set[tuple[str, str]] = set()
    if final:
        authorized_missing_targets, authorization_violations = strict_authorized_missing_targets(
            run_dir,
            manifest,
            initial_rows,
        )
        violations.extend(authorization_violations)

    error_keys = ("initial_errors", "final_errors") if final else ("initial_errors",)
    for key in error_keys:
        path = paths.get(key)
        if path and path.is_file() and path.read_text(encoding="utf-8").strip():
            violations.append({"kind": "scan_errors_present", "file": key})

    focus_targets = manifest.get("focus_targets", [])
    if not isinstance(focus_targets, list) or not focus_targets:
        violations.append({"kind": "focus_targets_missing"})
        focus_targets = []
    audit_by_id = {str(row.get("target_id", "")): row for row in audit_rows if row.get("target_id")}
    seen_ids: set[str] = set()
    for index, target in enumerate(focus_targets):
        if not isinstance(target, dict):
            violations.append({"kind": "invalid_focus_target", "index": index})
            continue
        target_id = str(target.get("id", "")).strip()
        target_path = str(target.get("path", "")).strip()
        if not target_id or not target_path:
            violations.append({"kind": "incomplete_focus_target", "index": index})
            continue
        if target_id in seen_ids:
            violations.append({"kind": "duplicate_focus_target", "id": target_id})
        seen_ids.add(target_id)
        if not find_scan_target(initial_rows, target_id, target_path):
            violations.append({"kind": "focus_target_missing_from_initial_scan", "id": target_id, "path": target_path})
        record = audit_by_id.get(target_id)
        if record is None:
            violations.append({"kind": "focus_target_not_content_audited", "id": target_id, "path": target_path})
        else:
            if record.get("status") not in {"reviewed", "unclear"}:
                violations.append({"kind": "invalid_content_audit_status", "id": target_id})
            evidence = record.get("evidence")
            min_evidence = target.get("min_evidence", 1)
            if isinstance(min_evidence, bool) or not isinstance(min_evidence, int) or min_evidence <= 0:
                violations.append({"kind": "invalid_min_evidence", "id": target_id})
                min_evidence = 1
            if not isinstance(evidence, list) or len(evidence) < min_evidence:
                violations.append({"kind": "insufficient_content_evidence", "id": target_id, "required": min_evidence})
            else:
                for evidence_index, item in enumerate(evidence):
                    if not isinstance(item, dict) or any(not str(item.get(field, "")).strip() for field in ("method", "source", "finding")):
                        violations.append({"kind": "invalid_content_evidence", "id": target_id, "index": evidence_index})
            if not str(record.get("recommendation", "")).strip():
                violations.append({"kind": "content_recommendation_missing", "id": target_id})
            if record.get("confidence") not in {"high", "medium", "low"}:
                violations.append({"kind": "content_confidence_missing_or_invalid", "id": target_id})
            if final and record.get("status") == "unclear" and (
                record.get("disposition") != "archived" or not str(record.get("target", "")).strip()
            ):
                violations.append({"kind": "unclear_focus_target_not_archived", "id": target_id})
        if (
            final
            and (target_id, audit_migration_conservation.normalize_path(target_path)) not in authorized_missing_targets
            and not find_scan_target(final_rows, target_id, target_path)
        ):
            violations.append({"kind": "focus_target_missing_from_final_scan", "id": target_id, "path": target_path})

    planned_actions = 0
    verified_actions = 0
    seen_action_ids: dict[str, dict] = {}
    for batch_group, group_batches in configured_batch_groups:
        for index, batch in enumerate(group_batches):
            if not isinstance(batch, dict):
                violation = {"kind": "invalid_batch", "index": index}
                if batch_group != "batches":
                    violation["batch_group"] = batch_group
                violations.append(violation)
                continue
            label = f"run.{batch_group}[{index}]"
            try:
                plan_path = resolve_member(run_dir, batch.get("plan"), f"{label}.plan")
                result_path = resolve_member(run_dir, batch.get("result"), f"{label}.result")
            except ValueError as error:
                violation = {"kind": "invalid_batch_path", "index": index, "detail": str(error)}
                if batch_group != "batches":
                    violation["batch_group"] = batch_group
                violations.append(violation)
                continue
            if not plan_path.is_file() or (final and not result_path.is_file()):
                violation = {"kind": "batch_file_missing", "index": index}
                if batch_group != "batches":
                    violation["batch_group"] = batch_group
                violations.append(violation)
                continue
            plan_entries = read_jsonl_with_lines(plan_path)
            plans = [value for _, value in plan_entries]
            result_entries = read_jsonl_with_lines(result_path) if result_path.is_file() else []
            _append_plan_action_id_violations(
                violations,
                seen_action_ids,
                index,
                batch,
                batch.get("plan"),
                plan_entries,
                batch_group=batch_group,
            )
            result_by_id = audit_migration_conservation.latest_results_by_action_id(result_entries)
            planned_actions += len(plans)
            for line, action in plan_entries:
                action_id = str(action.get("action_id", "")).strip()
                if not action_id:
                    continue
                op = str(action.get("op", "")).strip()
                operation_violation = audit_migration_conservation.batch_operation_violation_kind(
                    batch_group,
                    op,
                )
                if operation_violation:
                    violation = {
                        "kind": operation_violation,
                        "batch": index,
                        "action_id": action_id,
                        "op": op,
                    }
                    if batch_group != "batches":
                        violation["batch_group"] = batch_group
                    violations.append(violation)
                if batch_group == "cleanup_batches" and not final:
                    authorization_problems, _ = (
                        audit_migration_conservation.cleanup_authorization_binding_problems(
                            action,
                            prospective_authorizations,
                        )
                    )
                    if authorization_problems:
                        violations.append({
                            "kind": "invalid_cleanup_authorization_binding",
                            "batch": index,
                            "batch_group": batch_group,
                            "action_id": action_id,
                            "plan": str(batch.get("plan")),
                            "plan_line": line,
                            "problems": sorted(set(authorization_problems)),
                        })
                if not final:
                    continue
                result_entry = result_by_id.get(action_id)
                if result_entry is None:
                    violation = {"kind": "action_result_missing", "batch": index, "action_id": action_id}
                    if batch_group != "batches":
                        violation["batch_group"] = batch_group
                    violations.append(violation)
                    continue
                ledger_line, result = result_entry
                status = result.get("status")
                if status == "verified":
                    identity_mismatches = audit_migration_conservation.operation_identity_mismatches(action, result)
                    if identity_mismatches:
                        violation = {
                            "kind": "verified_ledger_operation_identity_mismatch",
                            "batch": index,
                            "action_id": action_id,
                            "plan": str(batch.get("plan")),
                            "plan_line": line,
                            "ledger": str(batch.get("result")),
                            "ledger_line": ledger_line,
                            "mismatches": identity_mismatches,
                        }
                        if batch_group != "batches":
                            violation["batch_group"] = batch_group
                        violations.append(violation)
                    else:
                        verified_actions += 1
                elif status == "skipped" and str(result.get("reason", "")).strip():
                    pass
                else:
                    violation = {"kind": "action_not_closed", "batch": index, "action_id": action_id, "status": status}
                    if batch_group != "batches":
                        violation["batch_group"] = batch_group
                    violations.append(violation)

    if final and paths.get("structure_audit", Path()).is_file():
        report = read_json(paths["structure_audit"])
        if report.get("status") != "passed" or report.get("violations") not in ([], None):
            violations.append({"kind": "structure_audit_not_passed"})
    if final and paths.get("ai_review", Path()).is_file():
        review = read_json(paths["ai_review"])
        checks = review.get("checks")
        if review.get("status") != "passed" or not isinstance(checks, list) or not checks:
            violations.append({"kind": "ai_review_not_passed"})
        elif any(not isinstance(item, dict) or item.get("status") != "passed" or not str(item.get("evidence", "")).strip() for item in checks):
            violations.append({"kind": "ai_review_check_incomplete"})
        else:
            check_names = {str(item.get("name", "")).strip() for item in checks}
            missing_checks = sorted(REQUIRED_AI_CHECKS - check_names)
            if missing_checks:
                violations.append({"kind": "ai_review_required_checks_missing", "checks": missing_checks})
        if review.get("unresolved") not in ([], None):
            violations.append({"kind": "ai_review_has_unresolved_items"})
    if final and paths.get("receipt", Path()).is_file() and not paths["receipt"].read_text(encoding="utf-8").strip():
        violations.append({"kind": "receipt_empty"})

    migration_conservation_status = None
    if final:
        migration_conservation_status = append_migration_conservation_violations(
            violations,
            run_dir,
            manifest,
        )

    checked = {
        "initial_scan_rows": len(initial_rows),
        "final_scan_rows": len(final_rows),
        "focus_targets": len(focus_targets),
        "content_audit_rows": len(audit_rows),
        "batches": len(batches),
        "cleanup_batches": len(cleanup_batches),
        "planned_actions": planned_actions,
        "verified_actions": verified_actions,
        "preflight_gate": preflight_result["status"] if preflight_result is not None else "not_required",
    }
    if final:
        checked["migration_conservation_report"] = migration_conservation_status
    return {"status": "passed" if not violations else "failed", "checked": checked, "violations": violations}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--final", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = audit_bundle(args.run_dir, final=args.final)
    except (OSError, ValueError) as error:
        result = {"status": "failed", "checked": {}, "violations": [{"kind": "invalid_run_bundle", "detail": str(error)}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
