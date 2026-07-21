#!/usr/bin/env python3
"""Fail-closed, local-only audit for a catalog publication run manifest.

The manifest is a run-bundle member and records one catalog release.  It must
declare release metadata, local and remote artifacts, a complete remote
inventory, and the consumer files checked for retired ``file_id`` references.
No network calls are made: remote facts are accepted only as local evidence
that can be cross-checked against the declared publication artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


SHA1_RE = re.compile(r"[0-9a-fA-F]{40}")
COPY_SUFFIX_RE = re.compile(r" \(\d+\)(?=(?:\.[^/]+)?$)")
RELEASE_FIELDS = (
    "catalog_release_id",
    "index_updated_at",
    "snapshot_at",
    "catalog_schema_version",
    "source_fingerprint",
)


def failure(kind: str, **details: object) -> dict[str, object]:
    return {"kind": kind, **details}


def resolve_member(run_dir: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty relative path")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must stay inside the run bundle")
    root = run_dir.resolve()
    resolved = (run_dir / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("path escapes the run bundle")
    return resolved


def normalize_remote_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("remote path must be a non-empty string")
    path = "/" + str(PurePosixPath("/" + value.strip().lstrip("/"))).lstrip("/")
    return path.rstrip("/") or "/"


def non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_timestamp(value: object) -> bool:
    if not non_empty_string(value):
        return False
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def parsed_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_violations(
    item: object,
    *,
    side: str,
    index: int,
) -> tuple[dict[str, Any] | None, list[dict[str, object]]]:
    """Validate the common publication artifact contract without coercion."""

    violations: list[dict[str, object]] = []
    if not isinstance(item, dict):
        return None, [failure("invalid_artifact", side=side, index=index, detail="must be an object")]
    record = dict(item)
    for field in ("logical_name", "path", "file_id", "role"):
        if not non_empty_string(record.get(field)):
            violations.append(failure("invalid_artifact_field", side=side, index=index, field=field))
    size = record.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        violations.append(failure("invalid_artifact_field", side=side, index=index, field="size"))
    if not isinstance(record.get("sha1"), str) or SHA1_RE.fullmatch(record["sha1"]) is None:
        violations.append(failure("invalid_artifact_field", side=side, index=index, field="sha1"))
    role = record.get("role")
    if role not in {"catalog_entry", "partition_detail"}:
        violations.append(failure("invalid_artifact_role", side=side, index=index, role=role))
    if role == "partition_detail" and not non_empty_string(record.get("partition")):
        violations.append(failure("invalid_artifact_field", side=side, index=index, field="partition"))
    if role == "catalog_entry" and "partition" in record:
        violations.append(failure("catalog_entry_must_not_have_partition", side=side, index=index))
    try:
        if side == "local" and non_empty_string(record.get("path")):
            candidate = Path(str(record["path"]))
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError("path must stay inside the run bundle")
        elif side == "remote" and non_empty_string(record.get("path")):
            record["path"] = normalize_remote_path(record["path"])
    except ValueError as error:
        violations.append(failure("invalid_artifact_path", side=side, index=index, detail=str(error)))
    return (record if not violations else None), violations


def artifact_key(record: dict[str, Any]) -> tuple[object, ...]:
    return (
        record["file_id"],
        record["size"],
        str(record["sha1"]).lower(),
        record["role"],
        record.get("partition"),
    )


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    return value


def audit_release_fields(manifest: dict[str, Any], violations: list[dict[str, object]]) -> None:
    for field in RELEASE_FIELDS:
        if not non_empty_string(manifest.get(field)):
            violations.append(failure("missing_release_field", field=field))
    for field in ("index_updated_at", "snapshot_at"):
        if field in manifest and not valid_timestamp(manifest[field]):
            violations.append(failure("timestamp_missing_timezone", field=field, value=manifest[field]))
    if valid_timestamp(manifest.get("index_updated_at")) and valid_timestamp(manifest.get("snapshot_at")):
        if parsed_timestamp(str(manifest["snapshot_at"])) > parsed_timestamp(str(manifest["index_updated_at"])):
            violations.append(failure("snapshot_after_index_update"))


def artifact_search_text(path: Path) -> str:
    """Return searchable textual content for Markdown/text or XLSX artifacts."""

    if path.suffix.lower() != ".xlsx":
        return path.read_text(encoding="utf-8")
    chunks: list[str] = []
    with zipfile.ZipFile(path) as workbook:
        for name in workbook.namelist():
            if name.endswith((".xml", ".rels")):
                chunks.append(workbook.read(name).decode("utf-8", errors="replace"))
    return "\n".join(chunks)


def validate_embedded_release_metadata(
    path: Path,
    manifest: dict[str, Any],
    *,
    logical_name: str,
) -> list[dict[str, object]]:
    try:
        text = artifact_search_text(path)
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        return [failure("artifact_release_metadata_unreadable", logical_name=logical_name, detail=str(error))]
    missing = [field for field in RELEASE_FIELDS if str(manifest.get(field, "")) not in text]
    return [failure("artifact_release_metadata_missing", logical_name=logical_name, fields=missing)] if missing else []


def validate_expected_partitions(manifest: dict[str, Any], violations: list[dict[str, object]]) -> list[str]:
    values = manifest.get("expected_partitions")
    if not isinstance(values, list) or not values:
        violations.append(failure("invalid_expected_partitions"))
        return []
    if any(not non_empty_string(value) for value in values):
        violations.append(failure("invalid_expected_partitions"))
        return []
    partitions = [str(value) for value in values]
    if len(set(partitions)) != len(partitions):
        violations.append(failure("duplicate_expected_partition"))
    return partitions


def validate_artifacts(
    run_dir: Path,
    manifest: dict[str, Any],
    expected_partitions: list[str],
    checked: dict[str, int],
    violations: list[dict[str, object]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    configured = manifest.get("artifacts")
    if not isinstance(configured, dict):
        violations.append(failure("invalid_artifacts"))
        return [], []
    parsed: dict[str, list[dict[str, Any]]] = {"local": [], "remote": []}
    for side in ("local", "remote"):
        values = configured.get(side)
        if not isinstance(values, list) or not values:
            violations.append(failure("invalid_artifact_collection", side=side))
            continue
        seen_names: set[str] = set()
        for index, item in enumerate(values):
            record, item_violations = artifact_violations(item, side=side, index=index)
            violations.extend(item_violations)
            if record is None:
                continue
            logical_name = str(record["logical_name"])
            if logical_name in seen_names:
                violations.append(failure("duplicate_logical_name", side=side, logical_name=logical_name))
                continue
            seen_names.add(logical_name)
            if side == "local":
                try:
                    local_path = resolve_member(run_dir, item["path"])
                except ValueError as error:
                    violations.append(failure("local_artifact_path_outside_run_bundle", logical_name=logical_name, detail=str(error)))
                    continue
                if not local_path.is_file():
                    violations.append(failure("local_artifact_missing", logical_name=logical_name, path=item["path"]))
                    continue
                try:
                    actual_size = local_path.stat().st_size
                    actual_sha1 = file_sha1(local_path)
                except OSError as error:
                    violations.append(failure(
                        "local_artifact_unreadable", logical_name=logical_name, detail=str(error)
                    ))
                    continue
                checked["local_artifacts"] += 1
                if actual_size != record["size"] or actual_sha1.lower() != str(record["sha1"]).lower():
                    violations.append(failure(
                        "local_artifact_metadata_mismatch",
                        logical_name=logical_name,
                        expected={"size": record["size"], "sha1": record["sha1"]},
                        actual={"size": actual_size, "sha1": actual_sha1},
                    ))
                metadata_violations = validate_embedded_release_metadata(
                    local_path,
                    manifest,
                    logical_name=logical_name,
                )
                violations.extend(metadata_violations)
                if not metadata_violations:
                    checked["artifacts_with_release_metadata"] += 1
            parsed[side].append(record)

    local_by_name = {str(item["logical_name"]): item for item in parsed["local"]}
    remote_by_name = {str(item["logical_name"]): item for item in parsed["remote"]}
    for logical_name in sorted(set(local_by_name) | set(remote_by_name)):
        local = local_by_name.get(logical_name)
        remote = remote_by_name.get(logical_name)
        if local is None or remote is None or artifact_key(local) != artifact_key(remote):
            violations.append(failure("local_remote_artifact_mismatch", logical_name=logical_name))
        else:
            checked["local_remote_artifact_pairs"] += 1

    expected = set(expected_partitions)
    for side, records in parsed.items():
        entries = [item for item in records if item["role"] == "catalog_entry"]
        if len(entries) != 1:
            violations.append(failure("catalog_entry_coverage_invalid", side=side, actual=len(entries)))
        details: dict[str, list[dict[str, Any]]] = {}
        for item in records:
            if item["role"] == "partition_detail":
                details.setdefault(str(item.get("partition")), []).append(item)
        for partition in expected:
            if len(details.get(partition, [])) != 1:
                violations.append(failure("missing_partition_detail", side=side, partition=partition))
            else:
                checked["partition_details"] += 1
        for partition in sorted(set(details) - expected):
            violations.append(failure("unexpected_partition_detail", side=side, partition=partition))
    checked["expected_partitions"] = len(expected_partitions)
    return parsed["local"], parsed["remote"]


def validate_remote_inventory(
    manifest: dict[str, Any],
    remote_artifacts: list[dict[str, Any]],
    checked: dict[str, int],
    violations: list[dict[str, object]],
) -> None:
    inventory = manifest.get("remote_inventory")
    if not isinstance(inventory, list) or not inventory:
        violations.append(failure("invalid_remote_inventory"))
        return
    records: list[dict[str, Any]] = []
    path_ids: set[tuple[str, str]] = set()
    names: dict[str, list[str]] = {}
    for index, item in enumerate(inventory):
        record, item_violations = artifact_violations(item, side="remote", index=index)
        violations.extend(item_violations)
        if record is None:
            continue
        key = (str(record["path"]), str(record["file_id"]))
        if key in path_ids:
            violations.append(failure("duplicate_remote_inventory_entry", path=record["path"], file_id=record["file_id"]))
        path_ids.add(key)
        name = PurePosixPath(str(record["path"])).name
        normalized_name = COPY_SUFFIX_RE.sub("", name)
        names.setdefault(normalized_name, []).append(str(record["path"]))
        if COPY_SUFFIX_RE.search(name):
            violations.append(failure("remote_duplicate_name_suffix", path=record["path"], name=name))
        records.append(record)
    for name, paths in names.items():
        if len(paths) > 1:
            violations.append(failure("remote_name_not_unique", name=name, paths=paths))
    inventory_keys = {(item["path"],) + artifact_key(item) for item in records}
    for artifact in remote_artifacts:
        key = (artifact["path"],) + artifact_key(artifact)
        if key not in inventory_keys:
            violations.append(failure("remote_artifact_not_in_inventory", logical_name=artifact["logical_name"], path=artifact["path"]))
        else:
            checked["remote_artifacts"] += 1


def validate_consumers(
    run_dir: Path,
    manifest: dict[str, Any],
    checked: dict[str, int],
    violations: list[dict[str, object]],
) -> None:
    consumers = manifest.get("consumer_audits")
    if not isinstance(consumers, list) or not consumers:
        violations.append(failure("invalid_consumer_audits"))
        return
    seen_paths: set[str] = set()
    for index, item in enumerate(consumers):
        if not isinstance(item, dict):
            violations.append(failure("invalid_consumer_audit", index=index))
            continue
        try:
            consumer_path = resolve_member(run_dir, item.get("path"))
        except ValueError as error:
            violations.append(failure("consumer_path_outside_run_bundle", index=index, detail=str(error)))
            continue
        configured_path = str(item["path"])
        if configured_path in seen_paths:
            violations.append(failure("duplicate_consumer_path", path=configured_path))
            continue
        seen_paths.add(configured_path)
        old_ids = item.get("old_file_ids")
        if not isinstance(old_ids, list) or any(not non_empty_string(value) for value in old_ids):
            violations.append(failure("invalid_consumer_old_file_ids", path=configured_path))
            continue
        if len(set(old_ids)) != len(old_ids):
            violations.append(failure("duplicate_consumer_old_file_id", path=configured_path))
            continue
        if item.get("old_file_id_references") != 0:
            violations.append(failure("consumer_old_file_id_references_not_zero", path=configured_path, actual=item.get("old_file_id_references")))
            continue
        if not consumer_path.is_file():
            violations.append(failure("consumer_file_missing", path=configured_path))
            continue
        try:
            text = consumer_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            violations.append(failure("consumer_file_unreadable", path=configured_path, detail=str(error)))
            continue
        actual = sum(text.count(str(old_id)) for old_id in old_ids)
        checked["consumer_files"] += 1
        checked["consumer_old_file_id_references"] += actual
        if actual != 0:
            violations.append(failure("consumer_old_file_id_references_not_zero", path=configured_path, actual=actual))
        missing_metadata = [field for field in RELEASE_FIELDS if str(manifest.get(field, "")) not in text]
        if missing_metadata:
            violations.append(failure(
                "consumer_release_metadata_missing",
                path=configured_path,
                fields=missing_metadata,
            ))
        else:
            checked["consumer_files_with_release_metadata"] += 1


def audit_catalog_publication(run_dir: Path, manifest_member: str, *, final: bool = False) -> dict[str, object]:
    """Audit one declared catalog publication without contacting a remote service."""

    checked = {
        "local_artifacts": 0,
        "remote_artifacts": 0,
        "local_remote_artifact_pairs": 0,
        "expected_partitions": 0,
        "partition_details": 0,
        "consumer_files": 0,
        "consumer_old_file_id_references": 0,
        "artifacts_with_release_metadata": 0,
        "consumer_files_with_release_metadata": 0,
    }
    violations: list[dict[str, object]] = []
    try:
        manifest_path = resolve_member(run_dir, manifest_member)
    except ValueError as error:
        return {"status": "failed", "checked": checked, "violations": [failure("manifest_path_outside_run_bundle", detail=str(error))]}
    if not manifest_path.is_file():
        return {"status": "failed", "checked": checked, "violations": [failure("publication_manifest_missing", path=manifest_member)]}
    try:
        manifest = load_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return {"status": "failed", "checked": checked, "violations": [failure("invalid_publication_manifest", detail=str(error))]}

    audit_release_fields(manifest, violations)
    if final and manifest.get("publication_status") != "passed":
        violations.append(failure("publication_status_not_passed", actual=manifest.get("publication_status")))
    if final and manifest.get("idempotence_status") != "unchanged":
        violations.append(failure("idempotence_status_not_unchanged", actual=manifest.get("idempotence_status")))
    expected_partitions = validate_expected_partitions(manifest, violations)
    _, remote_artifacts = validate_artifacts(run_dir, manifest, expected_partitions, checked, violations)
    validate_remote_inventory(manifest, remote_artifacts, checked, violations)
    validate_consumers(run_dir, manifest, checked, violations)
    return {"status": "passed" if not violations else "failed", "checked": checked, "violations": violations}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a local catalog publication manifest")
    parser.add_argument("--run-dir", required=True, type=Path, help="run bundle containing the manifest")
    parser.add_argument("--manifest", default="catalog-publication.json", help="relative manifest path inside --run-dir")
    parser.add_argument("--final", action="store_true", help="require publication_status=passed")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = audit_catalog_publication(args.run_dir, args.manifest, final=args.final)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
