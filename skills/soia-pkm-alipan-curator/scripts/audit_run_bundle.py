#!/usr/bin/env python3
"""Audit a curator run bundle before a large partition is declared complete."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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


def _plan_location(batch_index: int, batch: dict, plan_path: object, line_number: int) -> dict:
    """Return stable manifest/plan coordinates for an action row."""

    location = {
        "batch": batch_index,
        "plan": str(plan_path),
        "line": line_number,
    }
    if str(batch.get("name", "")).strip():
        location["batch_name"] = str(batch["name"])
    return location


def _append_plan_action_id_violations(
    violations: list[dict],
    seen_action_ids: dict[str, dict],
    batch_index: int,
    batch: dict,
    plan_value: object,
    plan_entries: list[tuple[int, dict]],
) -> list[str]:
    """Validate one registered plan and return its normalized action IDs."""

    plan_ids: list[str] = []
    for line_number, item in plan_entries:
        action_id = str(item.get("action_id", "")).strip()
        plan_ids.append(action_id)
        location = _plan_location(batch_index, batch, plan_value, line_number)
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


def audit_bundle(run_dir: Path, *, final: bool) -> dict:
    violations: list[dict] = []
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        return {"status": "failed", "checked": {}, "violations": [{"kind": "run_manifest_missing"}]}
    manifest = read_json(manifest_path)

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
    final_rows = read_jsonl(paths["final_scan"]) if paths.get("final_scan", Path()).is_file() else []
    if not initial_rows:
        violations.append({"kind": "initial_scan_empty"})
    if not audit_rows:
        violations.append({"kind": "content_audit_empty"})
    if final and not final_rows:
        violations.append({"kind": "final_scan_empty"})
    if any("agg_files" in row for row in final_rows):
        violations.append({"kind": "final_scan_contains_aggregate_rows"})

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
        if final and not find_scan_target(final_rows, target_id, target_path):
            violations.append({"kind": "focus_target_missing_from_final_scan", "id": target_id, "path": target_path})

    planned_actions = 0
    verified_actions = 0
    batches = manifest.get("batches", [])
    if not isinstance(batches, list):
        raise ValueError("run.batches must be an array")
    seen_action_ids: dict[str, dict] = {}
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict):
            violations.append({"kind": "invalid_batch", "index": index})
            continue
        try:
            plan_path = resolve_member(run_dir, batch.get("plan"), f"run.batches[{index}].plan")
            result_path = resolve_member(run_dir, batch.get("result"), f"run.batches[{index}].result")
        except ValueError as error:
            violations.append({"kind": "invalid_batch_path", "index": index, "detail": str(error)})
            continue
        if not plan_path.is_file() or (final and not result_path.is_file()):
            violations.append({"kind": "batch_file_missing", "index": index})
            continue
        plan_entries = read_jsonl_with_lines(plan_path)
        plans = [value for _, value in plan_entries]
        results = read_jsonl(result_path) if result_path.is_file() else []
        plan_ids = _append_plan_action_id_violations(
            violations,
            seen_action_ids,
            index,
            batch,
            batch.get("plan"),
            plan_entries,
        )
        result_by_id = {str(item.get("action_id", "")): item for item in results}
        planned_actions += len(plans)
        if not final:
            continue
        for action_id in plan_ids:
            result = result_by_id.get(action_id)
            if result is None:
                violations.append({"kind": "action_result_missing", "batch": index, "action_id": action_id})
                continue
            status = result.get("status")
            if status == "verified":
                verified_actions += 1
            elif status == "skipped" and str(result.get("reason", "")).strip():
                pass
            else:
                violations.append({"kind": "action_not_closed", "batch": index, "action_id": action_id, "status": status})

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

    checked = {
        "initial_scan_rows": len(initial_rows),
        "final_scan_rows": len(final_rows),
        "focus_targets": len(focus_targets),
        "content_audit_rows": len(audit_rows),
        "batches": len(batches),
        "planned_actions": planned_actions,
        "verified_actions": verified_actions,
    }
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
