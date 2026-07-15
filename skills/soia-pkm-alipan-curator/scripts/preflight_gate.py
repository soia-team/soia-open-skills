#!/usr/bin/env python3
"""Fail-closed execution gate for curator preflight reports.

``validate_preflight_gate`` is the pure policy function: callers provide the
already-loaded manifest/report and current hashes, and it performs no I/O.
``verify_preflight_gate`` is the small filesystem adapter intended for an
executor immediately before its first remote write.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_drive_id(drive_id: str) -> str:
    """Return the report-safe digest for one execution drive ID."""

    return hashlib.sha256(drive_id.encode("utf-8")).hexdigest()


def resolve_run_member(run_dir: Path, value: object, label: str) -> Path:
    """Resolve a manifest member while rejecting absolute and escaping paths."""

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


def _relative_member(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} must stay inside the run directory")
    return value


def registered_plan_paths(manifest: Mapping[str, object]) -> list[str]:
    batches = manifest.get("batches")
    if not isinstance(batches, list):
        raise ValueError("run.batches must be an array")
    plans: list[str] = []
    for index, batch in enumerate(batches):
        if not isinstance(batch, Mapping):
            raise ValueError(f"run.batches[{index}] must be an object")
        plan = _relative_member(batch.get("plan"), f"run.batches[{index}].plan")
        plans.append(plan)
    return plans


def registered_preflight_report(manifest: Mapping[str, object]) -> str:
    files = manifest.get("files")
    if not isinstance(files, Mapping) or not str(files.get("preflight_report", "")).strip():
        raise ValueError("run.files.preflight_report is not registered")
    return _relative_member(files["preflight_report"], "run.files.preflight_report")


def registered_preflight_report_path(run_dir: Path, manifest: Mapping[str, object]) -> Path:
    return resolve_run_member(
        run_dir,
        registered_preflight_report(manifest),
        "run.files.preflight_report",
    )


def registered_cleanup_evidence(manifest: Mapping[str, object]) -> str | None:
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("run.files must be an object")
    value = files.get("empty_cleanup_evidence")
    if value in (None, ""):
        return None
    return _relative_member(value, "run.files.empty_cleanup_evidence")


def validate_preflight_gate(
    *,
    manifest: Mapping[str, object],
    report_path: str,
    report: Mapping[str, object],
    current_hashes: Mapping[str, str],
    executor_plan_path: str | None = None,
    drive_id: str | None = None,
) -> dict:
    """Purely validate one report against the current manifest and plan hashes.

    The function reads and writes no files.  ``current_hashes`` must contain
    ``run.json``, every registered plan, and registered cleanup evidence.
    When supplied by an executor, ``drive_id`` must hash to the report's
    ``drive_id_sha256`` value.
    """

    violations: list[dict] = []
    try:
        registered_report = registered_preflight_report(manifest)
    except ValueError as error:
        detail = str(error)
        kind = (
            "preflight_report_not_registered"
            if "not registered" in detail
            else "preflight_report_path_outside_run"
        )
        violations.append({"kind": kind, "detail": detail})
        registered_report = None

    try:
        actual_report = _relative_member(report_path, "preflight report path")
    except ValueError as error:
        violations.append({"kind": "preflight_report_path_outside_run", "detail": str(error)})
        actual_report = None
    if registered_report is not None and actual_report is not None and actual_report != registered_report:
        violations.append({
            "kind": "preflight_report_not_registered",
            "registered": registered_report,
            "actual": actual_report,
        })

    if report.get("status") != "passed":
        violations.append({
            "kind": "preflight_report_not_passed",
            "actual": report.get("status"),
        })
    if report.get("schema_version") != 1:
        violations.append({
            "kind": "preflight_report_stale",
            "reason": "unsupported_schema_version",
            "actual": report.get("schema_version"),
        })

    try:
        plans = registered_plan_paths(manifest)
    except ValueError as error:
        violations.append({"kind": "preflight_manifest_invalid", "detail": str(error)})
        plans = []
    try:
        cleanup_evidence = registered_cleanup_evidence(manifest)
    except ValueError as error:
        violations.append({"kind": "preflight_manifest_invalid", "detail": str(error)})
        cleanup_evidence = None
    expected_keys = {"run.json", *plans}
    if cleanup_evidence is not None:
        expected_keys.add(cleanup_evidence)
    report_hashes = report.get("hashes")
    if not isinstance(report_hashes, Mapping):
        report_hashes = {}
        violations.append({
            "kind": "preflight_report_stale",
            "reason": "hashes_missing_or_invalid",
        })
    else:
        actual_keys = {str(key) for key in report_hashes}
        if actual_keys != expected_keys:
            violations.append({
                "kind": "preflight_report_stale",
                "reason": "registered_hash_set_changed",
                "missing": sorted(expected_keys - actual_keys),
                "unexpected": sorted(actual_keys - expected_keys),
            })
        invalid_hashes = sorted(
            str(key)
            for key, value in report_hashes.items()
            if not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value.lower())
        )
        if invalid_hashes:
            violations.append({
                "kind": "preflight_report_stale",
                "reason": "invalid_sha256",
                "hashes": invalid_hashes,
            })

    if executor_plan_path is not None:
        try:
            executor_plan = _relative_member(executor_plan_path, "executor plan path")
        except ValueError as error:
            violations.append({"kind": "executor_plan_not_registered", "detail": str(error)})
            executor_plan = None
        if executor_plan is not None and executor_plan not in plans:
            violations.append({
                "kind": "executor_plan_not_registered",
                "plan": executor_plan,
            })

    execution_drive_hash_matched = None
    if drive_id is not None:
        if not isinstance(drive_id, str) or not drive_id.strip():
            violations.append({"kind": "preflight_execution_drive_invalid"})
            execution_drive_hash_matched = False
        else:
            expected_drive_hash = report.get("drive_id_sha256")
            actual_drive_hash = sha256_drive_id(drive_id)
            valid_reported_drive_hash = (
                isinstance(expected_drive_hash, str)
                and len(expected_drive_hash) == 64
                and all(character in "0123456789abcdef" for character in expected_drive_hash.lower())
            )
            execution_drive_hash_matched = (
                valid_reported_drive_hash
                and expected_drive_hash == actual_drive_hash
            )
            if not valid_reported_drive_hash:
                violations.append({
                    "kind": "preflight_report_stale",
                    "reason": "drive_id_hash_missing_or_invalid",
                })
            elif not execution_drive_hash_matched:
                violations.append({
                    "kind": "preflight_execution_drive_changed",
                    "expected": expected_drive_hash,
                    "actual": actual_drive_hash,
                })

    current_manifest_hash = current_hashes.get("run.json")
    report_manifest_hash = report_hashes.get("run.json")
    manifest_hash_matched = (
        "run.json" in current_hashes
        and "run.json" in report_hashes
        and current_manifest_hash == report_manifest_hash
    )
    if "run.json" in current_hashes and "run.json" in report_hashes and not manifest_hash_matched:
        violations.append({
            "kind": "preflight_manifest_changed",
            "expected": report_manifest_hash,
            "actual": current_manifest_hash,
        })

    matched_plans = 0
    for plan in plans:
        current = current_hashes.get(plan)
        recorded = report_hashes.get(plan)
        if plan not in current_hashes:
            violations.append({
                "kind": "preflight_plan_hash_missing",
                "plan": plan,
                "source": "current",
            })
        if plan not in report_hashes:
            violations.append({
                "kind": "preflight_plan_hash_missing",
                "plan": plan,
                "source": "report",
            })
        if plan not in current_hashes or plan not in report_hashes:
            continue
        if current != recorded:
            violations.append({
                "kind": "preflight_plan_changed",
                "plan": plan,
                "expected": recorded,
                "actual": current,
            })
        else:
            matched_plans += 1

    cleanup_evidence_hash_matched = None
    if cleanup_evidence is not None:
        current = current_hashes.get(cleanup_evidence)
        recorded = report_hashes.get(cleanup_evidence)
        cleanup_evidence_hash_matched = (
            cleanup_evidence in current_hashes
            and cleanup_evidence in report_hashes
            and current == recorded
        )
        if cleanup_evidence not in current_hashes or cleanup_evidence not in report_hashes:
            violations.append({
                "kind": "preflight_report_stale",
                "reason": "cleanup_evidence_hash_missing",
                "path": cleanup_evidence,
            })
        if (
            cleanup_evidence in current_hashes
            and cleanup_evidence in report_hashes
            and not cleanup_evidence_hash_matched
        ):
            violations.append({
                "kind": "preflight_cleanup_evidence_changed",
                "path": cleanup_evidence,
                "expected": recorded,
                "actual": current,
            })

    checked = {
        "registered_plans": len(plans),
        "matched_plans": matched_plans,
        "execution_drive_hash_matched": execution_drive_hash_matched,
        "manifest_hash_matched": manifest_hash_matched,
        "cleanup_evidence_hash_matched": cleanup_evidence_hash_matched,
    }
    return {
        "status": "passed" if not violations else "failed",
        "checked": checked,
        "violations": violations,
    }


def _failed(kind: str, **details: object) -> dict:
    return {
        "status": "failed",
        "checked": {},
        "violations": [{"kind": kind, **details}],
    }


def verify_preflight_gate(
    run_dir: Path,
    *,
    plan_path: Path | None = None,
    drive_id: str | None = None,
) -> dict:
    """Load current run evidence and fail closed for executor integration."""

    run_dir = Path(run_dir)
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        return _failed("run_manifest_missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return _failed("preflight_manifest_invalid", detail=str(error))
    if not isinstance(manifest, dict):
        return _failed("preflight_manifest_invalid", detail="run.json must contain an object")

    try:
        report_path = registered_preflight_report_path(run_dir, manifest)
    except ValueError as error:
        detail = str(error)
        kind = (
            "preflight_report_not_registered"
            if "not registered" in detail
            else "preflight_report_path_outside_run"
        )
        return _failed(kind, detail=detail)
    if not report_path.is_file():
        return _failed(
            "preflight_report_missing",
            path=str(manifest["files"]["preflight_report"]),
        )
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return _failed("preflight_report_invalid", detail=str(error))
    if not isinstance(report, dict):
        return _failed("preflight_report_invalid", detail="preflight report must contain an object")

    executor_plan_member = None
    try:
        current_hashes = {"run.json": sha256_file(manifest_path)}
        resolved_executor_plan = plan_path.resolve() if plan_path is not None else None
        for index, plan in enumerate(registered_plan_paths(manifest)):
            registered_plan_path = resolve_run_member(run_dir, plan, f"run.batches[{index}].plan")
            if not registered_plan_path.is_file():
                return _failed("preflight_plan_missing", plan=plan)
            current_hashes[plan] = sha256_file(registered_plan_path)
            if resolved_executor_plan == registered_plan_path:
                executor_plan_member = plan
        cleanup_evidence = registered_cleanup_evidence(manifest)
        if cleanup_evidence is not None:
            evidence_path = resolve_run_member(
                run_dir,
                cleanup_evidence,
                "run.files.empty_cleanup_evidence",
            )
            if not evidence_path.is_file():
                return _failed("preflight_cleanup_evidence_missing", path=cleanup_evidence)
            current_hashes[cleanup_evidence] = sha256_file(evidence_path)
    except (OSError, ValueError) as error:
        return _failed("preflight_manifest_invalid", detail=str(error))
    if plan_path is not None and executor_plan_member is None:
        executor_plan_member = "__unregistered_executor_plan__"

    return validate_preflight_gate(
        manifest=manifest,
        report_path=registered_preflight_report(manifest),
        report=report,
        current_hashes=current_hashes,
        executor_plan_path=executor_plan_member,
        drive_id=drive_id,
    )
