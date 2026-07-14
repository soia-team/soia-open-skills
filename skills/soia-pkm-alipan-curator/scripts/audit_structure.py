#!/usr/bin/env python3
"""Audit numbered business layers, navigation-guide closure, and review manifests."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath


def normalize_cloud_path(value: str) -> str:
    path = "/" + str(PurePosixPath("/" + value.strip().lstrip("/"))).lstrip("/")
    return path.rstrip("/") or "/"


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")
            rows.append(value)
    return rows


def child_dirs(rows: list[dict], parent: str) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("dir") is True and normalize_cloud_path(str(row.get("path", ""))) == parent
    ]


def validate_contract(contract: dict) -> None:
    if not isinstance(contract, dict):
        raise ValueError("contract must be a JSON object")
    for key in ("numbered_layers", "guide_layers"):
        value = contract.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"contract.{key} must be an array")
        for index, rule in enumerate(value):
            if not isinstance(rule, dict):
                raise ValueError(f"contract.{key}[{index}] must be an object")
            if not str(rule.get("parent", "")).strip():
                raise ValueError(f"contract.{key}[{index}].parent is required")
    for index, rule in enumerate(contract.get("numbered_layers", [])):
        if not str(rule.get("pattern", "")).strip():
            raise ValueError(f"contract.numbered_layers[{index}].pattern is required")
        if not isinstance(rule.get("exclude", []), list):
            raise ValueError(f"contract.numbered_layers[{index}].exclude must be an array")
    for index, rule in enumerate(contract.get("guide_layers", [])):
        if not str(rule.get("child_pattern", "")).strip():
            raise ValueError(f"contract.guide_layers[{index}].child_pattern is required")
        if not str(rule.get("guide_name", "")).strip():
            raise ValueError(f"contract.guide_layers[{index}].guide_name is required")
    if "review_root" in contract and not isinstance(contract["review_root"], str):
        raise ValueError("contract.review_root must be a string")


def audit_numbering(rows: list[dict], rules: list[dict]) -> tuple[int, list[dict]]:
    checked = 0
    violations: list[dict] = []
    for index, rule in enumerate(rules):
        parent = normalize_cloud_path(str(rule.get("parent", "")))
        pattern_text = str(rule.get("pattern", ""))
        pattern = re.compile(pattern_text)
        excludes = {str(item) for item in rule.get("exclude", [])}
        children = child_dirs(rows, parent)
        checked += len(children)
        for row in children:
            name = str(row.get("name", ""))
            if name in excludes or pattern.search(name):
                continue
            violations.append({
                "kind": "unnumbered_directory",
                "rule": index,
                "parent": parent,
                "name": name,
                "id": row.get("id"),
                "expected_pattern": pattern_text,
            })
    return checked, violations


def audit_guides(rows: list[dict], rules: list[dict]) -> tuple[int, list[dict]]:
    checked = 0
    violations: list[dict] = []
    for index, rule in enumerate(rules):
        parent = normalize_cloud_path(str(rule.get("parent", "")))
        child_pattern_text = str(rule.get("child_pattern", ""))
        child_pattern = re.compile(child_pattern_text)
        guide_name = str(rule.get("guide_name", ""))
        for child in child_dirs(rows, parent):
            child_name = str(child.get("name", ""))
            if not child_pattern.search(child_name):
                continue
            checked += 1
            child_path = normalize_cloud_path(f"{parent}/{child_name}")
            present = any(
                row.get("dir") is True
                and normalize_cloud_path(str(row.get("path", ""))) == child_path
                and str(row.get("name", "")) == guide_name
                for row in rows
            )
            if not present:
                violations.append({
                    "kind": "missing_guide",
                    "rule": index,
                    "parent": child_path,
                    "guide_name": guide_name,
                    "id": child.get("id"),
                })
    return checked, violations


def scan_contains_file(rows: list[dict], target: str) -> bool:
    normalized_target = normalize_cloud_path(target)
    target_path = PurePosixPath(normalized_target)
    parent = normalize_cloud_path(str(target_path.parent))
    name = target_path.name
    return any(
        row.get("dir") is not True
        and normalize_cloud_path(str(row.get("path", ""))) == parent
        and str(row.get("name", "")) == name
        for row in rows
    )


def audit_unclear_manifest(
    manifest_rows: list[dict],
    review_root: str | None,
    final: bool,
    scan_rows: list[dict] | None = None,
) -> tuple[int, list[dict]]:
    if not manifest_rows:
        return 0, []
    violations: list[dict] = []
    normalized_root = normalize_cloud_path(review_root) if review_root else None
    for index, row in enumerate(manifest_rows, 1):
        source = str(row.get("source", "")).strip()
        reason = str(row.get("reason", "")).strip()
        target = str(row.get("target", "")).strip()
        status = str(row.get("status", "")).strip()
        if not source or not reason or not target:
            violations.append({
                "kind": "invalid_unclear_row",
                "row": index,
                "reason": "source, reason, and target are required",
            })
            continue
        normalized_target = normalize_cloud_path(target)
        if normalized_root and not (
            normalized_target == normalized_root or normalized_target.startswith(normalized_root + "/")
        ):
            violations.append({
                "kind": "unclear_outside_review_root",
                "row": index,
                "target": normalized_target,
                "review_root": normalized_root,
            })
        if final and status != "verified":
            violations.append({
                "kind": "unclear_not_verified",
                "row": index,
                "status": status,
            })
        if final and scan_rows is not None and not scan_contains_file(scan_rows, target):
            violations.append({
                "kind": "unclear_target_missing",
                "row": index,
                "target": normalized_target,
            })
    return len(manifest_rows), violations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit structure contracts against an Aliyun Drive scan JSONL."
    )
    parser.add_argument("--scan", required=True, type=Path, help="scan JSONL")
    parser.add_argument("--contract", required=True, type=Path, help="audit contract JSON")
    parser.add_argument("--unclear", type=Path, help="optional unclear-item manifest JSONL")
    parser.add_argument(
        "--final",
        action="store_true",
        help="require every unclear manifest row to have status=verified",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    validate_contract(contract)
    rows = read_jsonl(args.scan)
    unclear_rows = read_jsonl(args.unclear) if args.unclear else []

    numbered_checked, numbering = audit_numbering(rows, contract.get("numbered_layers", []))
    guides_checked, guides = audit_guides(rows, contract.get("guide_layers", []))
    unclear_checked, unclear = audit_unclear_manifest(
        unclear_rows, contract.get("review_root"), args.final, rows
    )
    violations = numbering + guides + unclear
    result = {
        "status": "passed" if not violations else "failed",
        "scan_rows": len(rows),
        "checked": {
            "numbered_directories": numbered_checked,
            "guide_parents": guides_checked,
            "unclear_items": unclear_checked,
        },
        "violations": violations,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, re.error) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
