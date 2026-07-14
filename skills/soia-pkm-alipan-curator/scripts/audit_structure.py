#!/usr/bin/env python3
"""Audit numbering, navigation guides, series chunking, and review manifests."""

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


def direct_files(rows: list[dict], parent: str) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("dir") is not True
        and normalize_cloud_path(str(row.get("path", ""))) == parent
    ]


def index_scan(rows: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    directories_by_parent: dict[str, list[dict]] = {}
    files_by_parent: dict[str, list[dict]] = {}
    for row in rows:
        parent = normalize_cloud_path(str(row.get("path", "")))
        target = directories_by_parent if row.get("dir") is True else files_by_parent
        target.setdefault(parent, []).append(row)
    return directories_by_parent, files_by_parent


def path_is_within(path: str, root: str) -> bool:
    normalized_path = normalize_cloud_path(path)
    normalized_root = normalize_cloud_path(root)
    return normalized_root == "/" or (
        normalized_path == normalized_root or normalized_path.startswith(normalized_root + "/")
    )


def validate_contract(contract: dict) -> None:
    if not isinstance(contract, dict):
        raise ValueError("contract must be a JSON object")
    for key in (
        "numbered_layers",
        "guide_layers",
        "required_guides",
        "required_artifacts",
        "resource_maps",
        "chunk_layers",
        "flat_series_discovery",
    ):
        value = contract.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"contract.{key} must be an array")
        for index, rule in enumerate(value):
            if not isinstance(rule, dict):
                raise ValueError(f"contract.{key}[{index}] must be an object")
    for key in ("numbered_layers", "guide_layers", "required_guides", "chunk_layers"):
        for index, rule in enumerate(contract.get(key, [])):
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
        if not isinstance(rule.get("file_pattern"), str) or not rule["file_pattern"].strip():
            raise ValueError(
                f"contract.guide_layers[{index}].file_pattern is required and must be non-empty"
            )
        min_bytes = rule.get("min_bytes", 1)
        if isinstance(min_bytes, bool) or not isinstance(min_bytes, int) or min_bytes <= 0:
            raise ValueError(f"contract.guide_layers[{index}].min_bytes must be a positive integer")
        if "allow_empty" in rule and not isinstance(rule["allow_empty"], bool):
            raise ValueError(f"contract.guide_layers[{index}].allow_empty must be a boolean")
    for index, rule in enumerate(contract.get("required_guides", [])):
        if not str(rule.get("guide_name", "")).strip():
            raise ValueError(f"contract.required_guides[{index}].guide_name is required")
        if not isinstance(rule.get("file_pattern"), str) or not rule["file_pattern"].strip():
            raise ValueError(
                f"contract.required_guides[{index}].file_pattern is required and must be non-empty"
            )
        min_bytes = rule.get("min_bytes", 1)
        if isinstance(min_bytes, bool) or not isinstance(min_bytes, int) or min_bytes <= 0:
            raise ValueError(
                f"contract.required_guides[{index}].min_bytes must be a positive integer"
            )
    for index, rule in enumerate(contract.get("required_artifacts", [])):
        if not str(rule.get("path", "")).strip():
            raise ValueError(f"contract.required_artifacts[{index}].path is required")
        size = rule.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError(
                f"contract.required_artifacts[{index}].size must be a positive integer"
            )
        sha1 = rule.get("sha1")
        if not isinstance(sha1, str) or re.fullmatch(r"[0-9A-Fa-f]{40}", sha1) is None:
            raise ValueError(
                f"contract.required_artifacts[{index}].sha1 must be 40 hexadecimal characters"
            )
        if "id" in rule and (
            not isinstance(rule["id"], str) or not rule["id"].strip()
        ):
            raise ValueError(
                f"contract.required_artifacts[{index}].id must be a non-empty string"
            )
    for index, rule in enumerate(contract.get("resource_maps", [])):
        for field in ("path", "url_prefix"):
            if not isinstance(rule.get(field), str) or not rule[field].strip():
                raise ValueError(
                    f"contract.resource_maps[{index}].{field} is required and must be non-empty"
                )
        required_ids = rule.get("required_ids")
        if not isinstance(required_ids, list) or not required_ids:
            raise ValueError(
                f"contract.resource_maps[{index}].required_ids must be a non-empty array"
            )
        for target_index, target in enumerate(required_ids):
            if not isinstance(target, str) or not target.strip():
                raise ValueError(
                    f"contract.resource_maps[{index}].required_ids[{target_index}] "
                    "must be a non-empty string"
                )
        if len(set(required_ids)) != len(required_ids):
            raise ValueError(f"contract.resource_maps[{index}].required_ids must be unique")
        min_links = rule.get("min_links", len(required_ids))
        if (
            isinstance(min_links, bool)
            or not isinstance(min_links, int)
            or min_links < len(required_ids)
        ):
            raise ValueError(
                f"contract.resource_maps[{index}].min_links must be an integer "
                "not smaller than required_ids"
            )
    for index, rule in enumerate(contract.get("chunk_layers", [])):
        if not str(rule.get("child_pattern", "")).strip():
            raise ValueError(f"contract.chunk_layers[{index}].child_pattern is required")
        if "count_pattern" in rule and (
            not isinstance(rule["count_pattern"], str) or not rule["count_pattern"].strip()
        ):
            raise ValueError(
                f"contract.chunk_layers[{index}].count_pattern must be a non-empty string"
            )
        max_items = rule.get("max_items")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0:
            raise ValueError(f"contract.chunk_layers[{index}].max_items must be a positive integer")
        if not isinstance(rule.get("exclude", []), list):
            raise ValueError(f"contract.chunk_layers[{index}].exclude must be an array")
    for index, rule in enumerate(contract.get("flat_series_discovery", [])):
        if not str(rule.get("root", "")).strip():
            raise ValueError(f"contract.flat_series_discovery[{index}].root is required")
        max_items = rule.get("max_items")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0:
            raise ValueError(
                f"contract.flat_series_discovery[{index}].max_items must be a positive integer"
            )
        for field in ("path_pattern", "file_pattern"):
            if field in rule and (
                not isinstance(rule[field], str) or not rule[field].strip()
            ):
                raise ValueError(
                    f"contract.flat_series_discovery[{index}].{field} must be a non-empty string"
                )
        exclude_patterns = rule.get("exclude_path_patterns", [])
        if not isinstance(exclude_patterns, list):
            raise ValueError(
                f"contract.flat_series_discovery[{index}].exclude_path_patterns must be an array"
            )
        for pattern_index, pattern in enumerate(exclude_patterns):
            if not isinstance(pattern, str) or not pattern.strip():
                raise ValueError(
                    "contract.flat_series_discovery"
                    f"[{index}].exclude_path_patterns[{pattern_index}] must be a non-empty string"
                )
        if "allow_empty" in rule and not isinstance(rule["allow_empty"], bool):
            raise ValueError(
                f"contract.flat_series_discovery[{index}].allow_empty must be a boolean"
            )
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
    directories_by_parent, files_by_parent = index_scan(rows)
    for index, rule in enumerate(rules):
        parent = normalize_cloud_path(str(rule.get("parent", "")))
        child_pattern_text = str(rule.get("child_pattern", ""))
        child_pattern = re.compile(child_pattern_text)
        guide_name = str(rule.get("guide_name", ""))
        file_pattern_text = str(rule.get("file_pattern", ""))
        file_pattern = re.compile(file_pattern_text) if file_pattern_text else None
        min_bytes = int(rule.get("min_bytes", 1))
        rule_checked = 0
        for child in directories_by_parent.get(parent, []):
            child_name = str(child.get("name", ""))
            if child_name == guide_name:
                continue
            if not child_pattern.search(child_name):
                continue
            checked += 1
            rule_checked += 1
            child_path = normalize_cloud_path(f"{parent}/{child_name}")
            guides = [
                row
                for row in directories_by_parent.get(child_path, [])
                if str(row.get("name", "")) == guide_name
            ]
            if not guides:
                violations.append({
                    "kind": "missing_guide",
                    "rule": index,
                    "parent": child_path,
                    "guide_name": guide_name,
                    "id": child.get("id"),
                })
                continue
            if len(guides) > 1:
                violations.append({
                    "kind": "duplicate_guide_directory",
                    "rule": index,
                    "parent": child_path,
                    "guide_name": guide_name,
                    "count": len(guides),
                })
            if file_pattern is not None:
                guide_path = normalize_cloud_path(f"{child_path}/{guide_name}")
                named_files = [
                    row
                    for row in files_by_parent.get(guide_path, [])
                    if file_pattern.search(str(row.get("name", "")))
                ]
                if not named_files:
                    violations.append({
                        "kind": "missing_guide_file",
                        "rule": index,
                        "parent": child_path,
                        "guide_name": guide_name,
                        "file_pattern": file_pattern_text,
                    })
                elif not any(int(row.get("size") or 0) >= min_bytes for row in named_files):
                    violations.append({
                        "kind": "guide_file_too_small",
                        "rule": index,
                        "parent": child_path,
                        "guide_name": guide_name,
                        "file_pattern": file_pattern_text,
                        "min_bytes": min_bytes,
                    })
        if rule_checked == 0 and not rule.get("allow_empty", False):
            violations.append({
                "kind": "guide_scope_has_no_matching_children",
                "rule": index,
                "parent": parent,
                "child_pattern": child_pattern_text,
                "hint": "fix the scope or set allow_empty=true only after confirming it is empty",
            })
    return checked, violations


def audit_required_guides(rows: list[dict], rules: list[dict]) -> tuple[int, list[dict]]:
    """Audit explicit guide locations, including the scan root itself.

    ``guide_layers`` expands over matching child categories. ``required_guides`` is for
    parents that must be checked directly and would otherwise be skipped, such as a
    learning-library root. A required guide must contain at least one matching file.
    """
    checked = 0
    violations: list[dict] = []
    directories_by_parent, files_by_parent = index_scan(rows)
    for index, rule in enumerate(rules):
        checked += 1
        parent = normalize_cloud_path(str(rule.get("parent", "")))
        guide_name = str(rule.get("guide_name", ""))
        file_pattern_text = str(rule.get("file_pattern", ".+"))
        file_pattern = re.compile(file_pattern_text)
        min_bytes = int(rule.get("min_bytes", 1))
        guides = [
            row
            for row in directories_by_parent.get(parent, [])
            if str(row.get("name", "")) == guide_name
        ]
        if not guides:
            violations.append({
                "kind": "missing_required_guide",
                "rule": index,
                "parent": parent,
                "guide_name": guide_name,
            })
            continue
        if len(guides) > 1:
            violations.append({
                "kind": "duplicate_required_guide_directory",
                "rule": index,
                "parent": parent,
                "guide_name": guide_name,
                "count": len(guides),
            })
        guide_path = normalize_cloud_path(f"{parent}/{guide_name}")
        named_files = [
            row
            for row in files_by_parent.get(guide_path, [])
            if file_pattern.search(str(row.get("name", "")))
        ]
        if not named_files:
            violations.append({
                "kind": "missing_required_guide_file",
                "rule": index,
                "parent": parent,
                "guide_name": guide_name,
                "file_pattern": file_pattern_text,
                "id": guides[0].get("id"),
            })
        elif not any(int(row.get("size") or 0) >= min_bytes for row in named_files):
            violations.append({
                "kind": "required_guide_file_too_small",
                "rule": index,
                "parent": parent,
                "guide_name": guide_name,
                "file_pattern": file_pattern_text,
                "min_bytes": min_bytes,
                "id": guides[0].get("id"),
            })
    return checked, violations


def matching_file_rows(rows: list[dict], target: str) -> list[dict]:
    normalized_target = normalize_cloud_path(target)
    target_path = PurePosixPath(normalized_target)
    parent = normalize_cloud_path(str(target_path.parent))
    name = target_path.name
    return [
        row
        for row in rows
        if row.get("dir") is not True
        and normalize_cloud_path(str(row.get("path", ""))) == parent
        and str(row.get("name", "")) == name
    ]


def audit_required_artifacts(rows: list[dict], rules: list[dict]) -> tuple[int, list[dict]]:
    """Verify critical cloud files by exact path, byte size, SHA1, and optional file id."""
    violations: list[dict] = []
    for index, rule in enumerate(rules):
        target = normalize_cloud_path(str(rule.get("path", "")))
        matches = matching_file_rows(rows, target)
        if not matches:
            violations.append({
                "kind": "required_artifact_missing",
                "rule": index,
                "path": target,
            })
            continue
        if len(matches) > 1:
            violations.append({
                "kind": "required_artifact_duplicate_path",
                "rule": index,
                "path": target,
                "count": len(matches),
            })
            continue
        row = matches[0]
        actual_size = int(row.get("size") or 0)
        expected_size = int(rule["size"])
        if actual_size != expected_size:
            violations.append({
                "kind": "required_artifact_size_mismatch",
                "rule": index,
                "path": target,
                "expected": expected_size,
                "actual": actual_size,
            })
        actual_sha1 = str(row.get("sha1") or "").upper()
        expected_sha1 = str(rule["sha1"]).upper()
        if actual_sha1 != expected_sha1:
            violations.append({
                "kind": "required_artifact_sha1_mismatch",
                "rule": index,
                "path": target,
                "expected": expected_sha1,
                "actual": actual_sha1 or None,
            })
        if "id" in rule and str(row.get("id") or "") != str(rule["id"]):
            violations.append({
                "kind": "required_artifact_id_mismatch",
                "rule": index,
                "path": target,
                "expected": str(rule["id"]),
                "actual": str(row.get("id") or "") or None,
            })
    return len(rules), violations


def audit_resource_maps(rules: list[dict], contract_dir: Path) -> tuple[int, list[dict]]:
    """Require actual Markdown cloud links instead of an unverified textual claim."""
    violations: list[dict] = []
    for index, rule in enumerate(rules):
        configured_path = str(rule["path"])
        map_path = Path(configured_path).expanduser()
        if not map_path.is_absolute():
            map_path = contract_dir / map_path
        if not map_path.is_file():
            violations.append({
                "kind": "resource_map_missing",
                "rule": index,
                "path": configured_path,
            })
            continue
        text = map_path.read_text(encoding="utf-8")
        url_prefix = str(rule["url_prefix"])
        cloud_link_pattern = re.compile(
            r"\]\(\s*(" + re.escape(url_prefix) + r"[^)\s]+)"
        )
        cloud_urls = set(cloud_link_pattern.findall(text))
        min_links = int(rule.get("min_links", len(rule["required_ids"])))
        if len(cloud_urls) < min_links:
            violations.append({
                "kind": "resource_map_has_too_few_cloud_links",
                "rule": index,
                "path": configured_path,
                "expected_minimum": min_links,
                "actual_unique_links": len(cloud_urls),
            })
        for target in rule["required_ids"]:
            expected_url = f"{url_prefix}{target}"
            if not any(
                url == expected_url
                or url.startswith(expected_url + "?")
                or url.startswith(expected_url + "#")
                for url in cloud_urls
            ):
                violations.append({
                    "kind": "resource_map_missing_required_link",
                    "rule": index,
                    "path": configured_path,
                    "target": target,
                })
    return len(rules), violations


def audit_chunks(rows: list[dict], rules: list[dict]) -> tuple[int, list[dict]]:
    """Check that large flat series are split into bounded, consistently named groups.

    A contracted series may stay flat while its direct file count is within ``max_items``.
    Once matching chunk directories exist, every file must live in one of those chunks and
    each chunk must contain between 1 and ``max_items`` counted items. When
    ``count_pattern`` is present, sidecar files still have to move into chunks but do
    not consume the primary-item limit.
    """
    checked = 0
    violations: list[dict] = []
    for index, rule in enumerate(rules):
        parent = normalize_cloud_path(str(rule.get("parent", "")))
        pattern_text = str(rule.get("child_pattern", ""))
        pattern = re.compile(pattern_text)
        count_pattern_text = str(rule.get("count_pattern", ""))
        count_pattern = re.compile(count_pattern_text) if count_pattern_text else None
        max_items = int(rule.get("max_items", 0))
        excludes = {str(item) for item in rule.get("exclude", [])}
        all_children = child_dirs(rows, parent)
        chunks = [row for row in all_children if pattern.search(str(row.get("name", "")))]
        unexpected_children = [
            row
            for row in all_children
            if not pattern.search(str(row.get("name", "")))
            and str(row.get("name", "")) not in excludes
        ]
        loose_files = direct_files(rows, parent)
        loose_counted = [
            row
            for row in loose_files
            if count_pattern is None or count_pattern.search(str(row.get("name", "")))
        ]

        for child in unexpected_children:
            violations.append({
                "kind": "unexpected_non_chunk_directory",
                "rule": index,
                "parent": parent,
                "name": str(child.get("name", "")),
                "id": child.get("id"),
                "expected_pattern": pattern_text,
            })

        if not chunks:
            checked += 1
            if all_children and not loose_files:
                violations.append({
                    "kind": "missing_chunk_directory",
                    "rule": index,
                    "parent": parent,
                    "child_pattern": pattern_text,
                })
            elif len(loose_counted) > max_items:
                violations.append({
                    "kind": "series_exceeds_chunk_limit",
                    "rule": index,
                    "parent": parent,
                    "item_count": len(loose_counted),
                    "total_files": len(loose_files),
                    "max_items": max_items,
                })
            continue

        checked += len(chunks)
        if loose_files:
            violations.append({
                "kind": "direct_items_outside_chunks",
                "rule": index,
                "parent": parent,
                "item_count": len(loose_files),
                "sample": [str(row.get("name", "")) for row in loose_files[:5]],
            })
        for chunk in chunks:
            chunk_name = str(chunk.get("name", ""))
            chunk_path = normalize_cloud_path(f"{parent}/{chunk_name}")
            chunk_files = direct_files(rows, chunk_path)
            counted_files = [
                row
                for row in chunk_files
                if count_pattern is None or count_pattern.search(str(row.get("name", "")))
            ]
            item_count = len(counted_files)
            if item_count == 0:
                violations.append({
                    "kind": "empty_chunk_directory",
                    "rule": index,
                    "parent": parent,
                    "name": chunk_name,
                    "id": chunk.get("id"),
                })
            elif item_count > max_items:
                violations.append({
                    "kind": "chunk_exceeds_limit",
                    "rule": index,
                    "parent": parent,
                    "name": chunk_name,
                    "id": chunk.get("id"),
                    "item_count": item_count,
                    "total_files": len(chunk_files),
                    "max_items": max_items,
                })
    return checked, violations


def audit_flat_series_discovery(
    rows: list[dict],
    rules: list[dict],
    chunk_rules: list[dict] | None = None,
) -> tuple[dict[str, int], list[dict]]:
    """Find oversized direct-file series that were never declared in ``chunk_layers``.

    Discovery is deliberately contract-driven: the caller chooses the scan root, limit,
    optional path/file filters, and explicit semantic-bucket exceptions. It does not
    infer a universal series size or silently exempt a directory by name.
    """
    stats = {
        "matching_parents": 0,
        "skipped_by_chunk": 0,
        "skipped_by_exception": 0,
        "aggregate_rows": 0,
        "violating_parents": 0,
    }
    violations: list[dict] = []
    contracted_limits: dict[str, int] = {}
    for chunk_rule in chunk_rules or []:
        parent = normalize_cloud_path(str(chunk_rule.get("parent", "")))
        limit = int(chunk_rule.get("max_items", 0))
        contracted_limits[parent] = min(limit, contracted_limits.get(parent, limit))
    file_rows = [row for row in rows if row.get("dir") is not True]
    files_by_parent: dict[str, list[dict]] = {}
    for row in file_rows:
        parent = normalize_cloud_path(str(row.get("path", "")))
        files_by_parent.setdefault(parent, []).append(row)
    for index, rule in enumerate(rules):
        root = normalize_cloud_path(str(rule.get("root", "")))
        max_items = int(rule.get("max_items", 0))
        path_pattern_text = str(rule.get("path_pattern", ".*"))
        file_pattern_text = str(rule.get("file_pattern", ".*"))
        path_pattern = re.compile(path_pattern_text)
        file_pattern = re.compile(file_pattern_text)
        exclude_patterns = [
            re.compile(str(value)) for value in rule.get("exclude_path_patterns", [])
        ]
        aggregate_rows = []
        for row in rows:
            if not int(row.get("agg_files") or 0):
                continue
            aggregate_path = normalize_cloud_path(
                f"{normalize_cloud_path(str(row.get('path', '')))}/{row.get('name', '')}"
            )
            if path_is_within(aggregate_path, root) and path_pattern.search(aggregate_path):
                aggregate_rows.append((aggregate_path, int(row.get("agg_files") or 0)))
        if aggregate_rows:
            stats["aggregate_rows"] += len(aggregate_rows)
            violations.append({
                "kind": "aggregate_scan_rows_in_discovery_scope",
                "rule": index,
                "root": root,
                "count": len(aggregate_rows),
                "sample": [
                    {"path": path, "agg_files": count}
                    for path, count in aggregate_rows[:5]
                ],
            })
        parents = sorted(
            parent
            for parent in files_by_parent
            if path_is_within(parent, root)
        )
        scoped_parents = [parent for parent in parents if path_pattern.search(parent)]
        matching_parents_for_rule = 0
        for parent in scoped_parents:
            matches = [
                row
                for row in files_by_parent[parent]
                if file_pattern.search(str(row.get("name", "")))
            ]
            if not matches:
                continue
            matching_parents_for_rule += 1
            stats["matching_parents"] += 1
            if any(pattern.search(parent) for pattern in exclude_patterns):
                stats["skipped_by_exception"] += 1
                continue
            if parent in contracted_limits and contracted_limits[parent] <= max_items:
                stats["skipped_by_chunk"] += 1
                continue
            if len(matches) <= max_items:
                continue
            stats["violating_parents"] += 1
            violations.append({
                "kind": "undeclared_flat_series",
                "rule": index,
                "parent": parent,
                "item_count": len(matches),
                "max_items": max_items,
                "path_pattern": path_pattern_text,
                "file_pattern": file_pattern_text,
                "sample": [str(row.get("name", "")) for row in matches[:5]],
            })
        if not scoped_parents and not rule.get("allow_empty", False):
            violations.append({
                "kind": "discovery_scope_has_no_file_rows",
                "rule": index,
                "root": root,
                "path_pattern": path_pattern_text,
                "hint": "use a complete file-level scan or set allow_empty=true explicitly",
            })
        elif matching_parents_for_rule == 0 and not rule.get("allow_empty", False):
            violations.append({
                "kind": "discovery_scope_has_no_matching_files",
                "rule": index,
                "root": root,
                "path_pattern": path_pattern_text,
                "file_pattern": file_pattern_text,
                "hint": "fix file_pattern or set allow_empty=true only after confirming it is empty",
            })
    return stats, violations


def audit_scan_errors(path: Path | None, *, required: bool = False) -> tuple[int, list[dict]]:
    if path is None:
        if required:
            return 0, [{
                "kind": "scan_error_sidecar_missing",
                "path": None,
            }]
        return 0, []
    if not path.exists():
        if required:
            return 0, [{
                "kind": "scan_error_sidecar_missing",
                "path": str(path),
            }]
        return 0, []
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return 0, []
    return len(lines), [{
        "kind": "scan_errors_present",
        "path": str(path),
        "count": len(lines),
        "sample": lines[:5],
    }]


def scan_contains_target(rows: list[dict], target: str) -> bool:
    """Return whether a file or directory target exists in a scan."""
    normalized_target = normalize_cloud_path(target)
    for row in rows:
        path = normalize_cloud_path(str(row.get("path", "")))
        name = str(row.get("name", "")).strip()
        if name and normalize_cloud_path(f"{path}/{name}") == normalized_target:
            return True
    return False


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
        if final and scan_rows is not None and not scan_contains_target(scan_rows, target):
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
    parser.add_argument(
        "--scan-errors",
        type=Path,
        help="scan error sidecar; explicit paths must exist; --final defaults to <scan>.errors",
    )
    parser.add_argument(
        "--allow-missing-scan-errors",
        action="store_true",
        help="allow --final without a scan error sidecar after independently verifying scan completeness",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    validate_contract(contract)
    rows = read_jsonl(args.scan)
    unclear_rows = read_jsonl(args.unclear) if args.unclear else []
    scan_errors_path = args.scan_errors
    if scan_errors_path is None and args.final:
        automatic_errors = Path(str(args.scan) + ".errors")
        if automatic_errors.exists() or not args.allow_missing_scan_errors:
            scan_errors_path = automatic_errors
    scan_errors_required = args.scan_errors is not None or (
        args.final and not args.allow_missing_scan_errors
    )

    numbered_checked, numbering = audit_numbering(rows, contract.get("numbered_layers", []))
    guides_checked, guides = audit_guides(rows, contract.get("guide_layers", []))
    required_guides_checked, required_guides = audit_required_guides(
        rows, contract.get("required_guides", [])
    )
    required_artifacts_checked, required_artifacts = audit_required_artifacts(
        rows, contract.get("required_artifacts", [])
    )
    resource_maps_checked, resource_maps = audit_resource_maps(
        contract.get("resource_maps", []), args.contract.parent
    )
    chunk_rules = contract.get("chunk_layers", [])
    chunks_checked, chunks = audit_chunks(rows, chunk_rules)
    discovery_stats, discovery = audit_flat_series_discovery(
        rows, contract.get("flat_series_discovery", []), chunk_rules
    )
    unclear_checked, unclear = audit_unclear_manifest(
        unclear_rows, contract.get("review_root"), args.final, rows
    )
    scan_errors_checked, scan_errors = audit_scan_errors(
        scan_errors_path, required=scan_errors_required
    )
    violations = (
        numbering
        + guides
        + required_guides
        + required_artifacts
        + resource_maps
        + chunks
        + discovery
        + unclear
        + scan_errors
    )
    result = {
        "status": "passed" if not violations else "failed",
        "scan_rows": len(rows),
        "checked": {
            "numbered_directories": numbered_checked,
            "guide_parents": guides_checked,
            "required_guides": required_guides_checked,
            "required_artifacts": required_artifacts_checked,
            "resource_maps": resource_maps_checked,
            "chunk_groups": chunks_checked,
            "flat_series_matching_parents": discovery_stats["matching_parents"],
            "flat_series_skipped_by_chunk": discovery_stats["skipped_by_chunk"],
            "flat_series_skipped_by_exception": discovery_stats["skipped_by_exception"],
            "flat_series_aggregate_rows": discovery_stats["aggregate_rows"],
            "flat_series_violating_parents": discovery_stats["violating_parents"],
            "unclear_items": unclear_checked,
            "scan_errors": scan_errors_checked,
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
