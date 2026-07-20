#!/usr/bin/env python3
"""Build ``gen_family_nav_xlsx.mjs`` inputs from a fresh drive scan JSONL.

The scan is the file-level format emitted by ``soia-pkm-alipan-drive-ops``'s
``scan_drive.py``.  A guide describes one navigation workbook and selects
independently usable directory units beneath its ``scope_root``:

* ``explicit_roots`` (the default) selects only the declared
  ``resource_roots``;
* ``deepest_leaves`` retains the opt-in automatic leaf selection behavior.

Files, including videos and their sidecars, are evidence for a directory but
are never emitted as individual family-navigation rows.

Guide spec shape::

    {
      "guides": [{
        "id": "language",
        "scope_root": "/Learning/Language",
        "title": "Language · Family navigation",
        "summary": "...",
        "generatedAt": "2026-01-01",
        "partition": "Language",
        "selection_mode": "explicit_roots",
        "guidance": [{"label": "...", "text": "..."}],
        "row_defaults": {
          "category": "Language",
          "audience": "To be confirmed",
          "type": "To be confirmed",
          "usage": "To be confirmed",
          "pace": "To be confirmed"
        },
        "resource_roots": [
          {"path": "/Learning/Language/Complete course", "category": "Courses"}
        ],
        "exclude_paths": ["/Learning/Language/01_先看这里"],
        "exclude_name_patterns": ["^说明(?:-|_).+$"]
      }]
    }

Each guide writes ``<out-dir>/<guide id>.json``.  Output rows retain the
scan-derived ``file_id`` alongside the fields consumed by the workbook
generator, so the direct-link evidence remains reviewable.  The output also
records every excluded directory and the rule that matched it.  Its companion
``<scan>.errors`` sidecar is required by default so an incomplete listing can
never silently turn into a resource leaf.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import posixpath
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


ROW_DEFAULT_FIELDS = ("category", "audience", "type", "usage", "pace")
GUIDE_TEXT_FIELDS = ("id", "title", "summary", "generatedAt", "partition")
GUIDE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
FILE_ID_PATTERN = re.compile(r"[0-9a-f]{40}\Z", re.IGNORECASE)
DEFAULT_EXCLUDE_NAME_PATTERNS = (r"^01_先看这里$",)
DEFAULT_SELECTION_MODE = "explicit_roots"
SELECTION_MODES = ("explicit_roots", "deepest_leaves")
URL_PREFIX_PATTERN = re.compile(
    r"https://(?:www\.)?(?:alipan|aliyundrive)\.com/drive/file/all/backup/\Z",
    re.IGNORECASE,
)
SCAN_LISTING_ERROR_PATTERN = re.compile(
    r"\bLIST_FAIL\s+(?P<path_literal>'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")"
)


class InputError(ValueError):
    """The scan or guide specification cannot safely produce workbook input."""


def normalize_cloud_path(value: Any, field: str) -> str:
    """Return a normalized absolute cloud path without accepting traversal."""

    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} must be a non-empty string")
    if "\x00" in value:
        raise InputError(f"{field} must not contain NUL")
    parts = value.split("/")
    if any(part in {".", ".."} for part in parts):
        raise InputError(f"{field} must not contain . or .. path segments")
    return str(PurePosixPath("/" + value.lstrip("/"))).rstrip("/") or "/"


def child_path(parent: str, name: Any, field: str) -> str:
    if not isinstance(name, str) or not name or "/" in name or "\x00" in name:
        raise InputError(f"{field} must be a non-empty name without path separators")
    return normalize_cloud_path(posixpath.join(parent, name), field)


def path_is_within(path: str, root: str) -> bool:
    return root == "/" or path == root or path.startswith(root + "/")


def strict_descendant(path: str, root: str) -> bool:
    return path != root and path_is_within(path, root)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as error:
        raise InputError(f"cannot read scan {path}: {error}") from error
    with handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as error:
                raise InputError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(row, dict):
                raise InputError(f"{path}:{line_number}: each JSONL row must be an object")
            rows.append(row)
    if not rows:
        raise InputError("scan must contain at least one row")
    return rows


def parse_failed_listing_path(raw: str, line_number: int, sidecar: Path) -> str:
    """Return the failed listing path recorded by ``scan_drive.py``."""

    match = SCAN_LISTING_ERROR_PATTERN.search(raw)
    if match is None:
        raise InputError(
            f"{sidecar}:{line_number}: unsupported scan error entry; expected LIST_FAIL '<path>'"
        )
    try:
        path = ast.literal_eval(match.group("path_literal"))
    except (SyntaxError, ValueError) as error:
        raise InputError(
            f"{sidecar}:{line_number}: invalid LIST_FAIL path literal"
        ) from error
    return normalize_cloud_path(path, f"{sidecar}:{line_number} LIST_FAIL path")


def load_scan_errors(
    scan: Path,
    explicit_sidecar: Path | None,
    *,
    allow_missing: bool,
    allow_errors: bool,
) -> tuple[dict[str, Any], set[str]]:
    """Validate scan completeness evidence and return its auditable summary.

    A non-empty ``scan_drive.py`` sidecar means that some directory listings
    failed.  Callers must opt in to using the incomplete scan, and the failed
    paths are then withheld from automatic leaf selection.
    """

    sidecar = explicit_sidecar if explicit_sidecar is not None else Path(f"{scan}.errors")
    try:
        contents = sidecar.read_bytes()
    except FileNotFoundError as error:
        if explicit_sidecar is not None:
            raise InputError(f"scan error sidecar is missing: {sidecar}") from error
        if not allow_missing:
            raise InputError(
                f"scan error sidecar is missing: {sidecar}; use --allow-missing-scan-errors "
                "only after independently verifying scan completeness"
            ) from error
        return (
            {
                "sidecar": str(sidecar.resolve()),
                "status": "missing-overridden",
                "override": "allow-missing-scan-errors",
                "error_count": 0,
                "listing_failure_paths": [],
                "sha256": None,
            },
            set(),
        )
    except OSError as error:
        raise InputError(f"cannot read scan error sidecar {sidecar}: {error}") from error

    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InputError(f"scan error sidecar {sidecar} is not UTF-8: {error}") from error
    lines = [(number, line.strip()) for number, line in enumerate(text.splitlines(), 1) if line.strip()]
    failed_paths = {
        parse_failed_listing_path(line, line_number, sidecar) for line_number, line in lines
    }
    error_count = len(lines)
    if error_count and not allow_errors:
        raise InputError(
            f"scan error sidecar {sidecar} contains {error_count} failed listing(s); "
            "refusing incomplete scan (use --allow-scan-errors only after independent review)"
        )
    return (
        {
            "sidecar": str(sidecar.resolve()),
            "status": "errors-overridden" if error_count else "clean",
            "override": "allow-scan-errors" if error_count else None,
            "error_count": error_count,
            "listing_failure_paths": sorted(failed_paths, key=str.casefold),
            "sha256": hashlib.sha256(contents).hexdigest(),
        },
        failed_paths,
    )


def load_guide_spec(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InputError(f"cannot read guide spec {path}: {error}") from error
    if not isinstance(document, dict) or not isinstance(document.get("guides"), list):
        raise InputError("guide spec must be an object with a non-empty guides array")
    guides = document["guides"]
    if not guides:
        raise InputError("guide spec guides must not be empty")

    guide_ids: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, guide in enumerate(guides):
        label = f"guides[{index}]"
        if not isinstance(guide, dict):
            raise InputError(f"{label} must be an object")
        normalized = dict(guide)
        for field in GUIDE_TEXT_FIELDS:
            value = normalized.get(field)
            if not isinstance(value, str) or not value.strip():
                raise InputError(f"{label}.{field} must be a non-empty string")
            normalized[field] = value.strip()
        if GUIDE_ID_PATTERN.fullmatch(normalized["id"]) is None:
            raise InputError(f"{label}.id must contain only ASCII letters, digits, _ or -")
        if normalized["id"] in guide_ids:
            raise InputError(f"duplicate guide id {normalized['id']!r}")
        guide_ids.add(normalized["id"])
        normalized["scope_root"] = normalize_cloud_path(normalized.get("scope_root"), f"{label}.scope_root")

        selection_mode = normalized.get("selection_mode", DEFAULT_SELECTION_MODE)
        if not isinstance(selection_mode, str) or not selection_mode.strip():
            raise InputError(f"{label}.selection_mode must be a non-empty string")
        selection_mode = selection_mode.strip()
        if selection_mode not in SELECTION_MODES:
            allowed_modes = ", ".join(SELECTION_MODES)
            raise InputError(
                f"{label}.selection_mode {selection_mode!r} is unsupported; "
                f"choose one of: {allowed_modes}"
            )
        normalized["selection_mode"] = selection_mode

        guidance = normalized.get("guidance")
        if not isinstance(guidance, list):
            raise InputError(f"{label}.guidance must be an array")
        for guidance_index, item in enumerate(guidance):
            if not isinstance(item, dict):
                raise InputError(f"{label}.guidance[{guidance_index}] must be an object")
            for field in ("label", "text"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise InputError(
                        f"{label}.guidance[{guidance_index}].{field} must be a non-empty string"
                    )

        defaults = normalized.get("row_defaults")
        if not isinstance(defaults, dict):
            raise InputError(f"{label}.row_defaults must be an object")
        for field in ROW_DEFAULT_FIELDS:
            if not isinstance(defaults.get(field), str) or not defaults[field].strip():
                raise InputError(f"{label}.row_defaults.{field} must be a non-empty string")
        normalized["row_defaults"] = {field: defaults[field].strip() for field in ROW_DEFAULT_FIELDS}

        roots = normalized.get("resource_roots", [])
        if not isinstance(roots, list):
            raise InputError(f"{label}.resource_roots must be an array")
        root_paths: set[str] = set()
        validated_roots: list[dict[str, Any]] = []
        for root_index, resource_root in enumerate(roots):
            root_label = f"{label}.resource_roots[{root_index}]"
            if not isinstance(resource_root, dict):
                raise InputError(f"{root_label} must be an object")
            unknown = set(resource_root) - {"path", *ROW_DEFAULT_FIELDS}
            if unknown:
                raise InputError(f"{root_label} has unsupported fields: {', '.join(sorted(unknown))}")
            root = dict(resource_root)
            root["path"] = normalize_cloud_path(root.get("path"), f"{root_label}.path")
            if root["path"] in root_paths:
                raise InputError(f"{root_label}.path is duplicated within this guide")
            root_paths.add(root["path"])
            for field in ROW_DEFAULT_FIELDS:
                if field in root and (not isinstance(root[field], str) or not root[field].strip()):
                    raise InputError(f"{root_label}.{field} must be a non-empty string when provided")
                if field in root:
                    root[field] = root[field].strip()
            validated_roots.append(root)
        normalized["resource_roots"] = validated_roots
        if selection_mode == "explicit_roots" and not validated_roots:
            raise InputError(
                f"{label}.resource_roots must contain at least one directory when "
                "selection_mode is 'explicit_roots'"
            )

        exclude_paths = normalized.get("exclude_paths", [])
        if not isinstance(exclude_paths, list):
            raise InputError(f"{label}.exclude_paths must be an array")
        normalized_exclude_paths: list[str] = []
        seen_exclude_paths: set[str] = set()
        for exclude_index, value in enumerate(exclude_paths):
            exclude_label = f"{label}.exclude_paths[{exclude_index}]"
            excluded_path = normalize_cloud_path(value, exclude_label)
            if not strict_descendant(excluded_path, normalized["scope_root"]):
                raise InputError(
                    f"{exclude_label} must be within scope_root {normalized['scope_root']!r}"
                )
            if excluded_path in seen_exclude_paths:
                raise InputError(f"{exclude_label} is duplicated within this guide")
            seen_exclude_paths.add(excluded_path)
            normalized_exclude_paths.append(excluded_path)
        normalized["exclude_paths"] = normalized_exclude_paths

        exclude_patterns = normalized.get("exclude_name_patterns", [])
        if not isinstance(exclude_patterns, list):
            raise InputError(f"{label}.exclude_name_patterns must be an array")
        configured_patterns: list[dict[str, Any]] = [
            {"pattern": pattern, "source": "default"} for pattern in DEFAULT_EXCLUDE_NAME_PATTERNS
        ]
        seen_patterns = set(DEFAULT_EXCLUDE_NAME_PATTERNS)
        for pattern_index, value in enumerate(exclude_patterns):
            pattern_label = f"{label}.exclude_name_patterns[{pattern_index}]"
            if not isinstance(value, str) or not value:
                raise InputError(f"{pattern_label} must be a non-empty string")
            try:
                re.compile(value)
            except re.error as error:
                raise InputError(f"{pattern_label} is not a valid regular expression: {error}") from error
            if value in seen_patterns:
                continue
            seen_patterns.add(value)
            configured_patterns.append({"pattern": value, "source": "spec"})
        normalized["exclude_name_patterns"] = configured_patterns
        validated.append(normalized)
    return validated


def index_scan(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index directories and reject unsafe scan evidence before selection."""

    directories: dict[str, dict[str, Any]] = {}
    ids: dict[str, str] = {}
    for index, row in enumerate(rows, 1):
        if "agg_files" in row or "agg_size" in row:
            raise InputError(f"scan row {index} is aggregated; use a fresh file-level scan")
        parent = normalize_cloud_path(row.get("path"), f"scan row {index}.path")
        full_path = child_path(parent, row.get("name"), f"scan row {index}.name")
        if row.get("dir") not in (True, False):
            raise InputError(f"scan row {index}.dir must be boolean")
        identifier = row.get("id")
        if isinstance(identifier, str) and identifier.strip():
            identifier = identifier.strip()
            previous = ids.get(identifier)
            if previous is not None:
                raise InputError(
                    f"duplicate file_id {identifier!r} in scan rows for {previous!r} and {full_path!r}"
                )
            ids[identifier] = full_path
        if row["dir"] is True:
            if full_path in directories:
                raise InputError(f"duplicate directory path in scan: {full_path!r}")
            directories[full_path] = {**row, "_path": full_path, "_parent": parent}
    return directories


def validate_resource_roots(guide: dict[str, Any], directories: dict[str, dict[str, Any]]) -> None:
    scope = guide["scope_root"]
    roots = [item["path"] for item in guide["resource_roots"]]
    for root in roots:
        if not strict_descendant(root, scope):
            raise InputError(
                f"guide {guide['id']!r} resource root {root!r} is outside scope_root {scope!r}"
            )
        if root not in directories:
            raise InputError(f"guide {guide['id']!r} resource root {root!r} is not a scanned directory")
    for position, root in enumerate(roots):
        for other in roots[position + 1 :]:
            if strict_descendant(root, other) or strict_descendant(other, root):
                raise InputError(
                    f"guide {guide['id']!r} resource roots overlap: {root!r} and {other!r}"
                )


def scan_file_id(directory: dict[str, Any], guide_id: str) -> str:
    identifier = directory.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise InputError(f"guide {guide_id!r} selected resource {directory['_path']!r} is missing file_id")
    identifier = identifier.strip()
    if FILE_ID_PATTERN.fullmatch(identifier) is None:
        raise InputError(
            f"guide {guide_id!r} selected resource {directory['_path']!r} has invalid file_id {identifier!r}"
        )
    return identifier


def exclusion_audit(
    guide: dict[str, Any], directories: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return every scoped directory excluded by a configured or default rule."""

    scope = guide["scope_root"]
    scoped_paths = sorted(
        (path for path in directories if strict_descendant(path, scope)), key=str.casefold
    )
    direct_rules: dict[str, list[dict[str, str]]] = {}
    excluded_paths = set(guide["exclude_paths"])
    compiled_patterns = [
        {**item, "regex": re.compile(item["pattern"])} for item in guide["exclude_name_patterns"]
    ]
    for path in scoped_paths:
        rules: list[dict[str, str]] = []
        if path in excluded_paths:
            rules.append({
                "field": "exclude_paths",
                "value": path,
                "source": "spec",
            })
        for item in compiled_patterns:
            if item["regex"].search(directories[path]["name"]):
                rules.append({
                    "field": "exclude_name_patterns",
                    "value": item["pattern"],
                    "source": item["source"],
                })
        if rules:
            direct_rules[path] = rules

    excluded: list[dict[str, Any]] = []
    for path in scoped_paths:
        matched_by: list[dict[str, str]] = []
        ancestor = path
        while strict_descendant(ancestor, scope):
            for rule in direct_rules.get(ancestor, []):
                matched_by.append({**rule, "matched_path": ancestor})
            ancestor = directories[ancestor]["_parent"]
        if matched_by:
            excluded.append(
                {"path": path, "name": directories[path]["name"], "matched_by": matched_by}
            )
    return excluded


def build_guide_input(
    guide: dict[str, Any],
    directories: dict[str, dict[str, Any]],
    url_prefix: str,
    failed_listing_paths: set[str],
    scan_errors: dict[str, Any],
) -> dict[str, Any]:
    """Select resource directories and return one generator-compatible document."""

    validate_resource_roots(guide, directories)
    scope = guide["scope_root"]
    explicit_by_path = {item["path"]: item for item in guide["resource_roots"]}
    explicit_paths = set(explicit_by_path)
    failed_roots = sorted(
        (
            root
            for root in explicit_paths
            if any(
                path_is_within(root, failed_path) or path_is_within(failed_path, root)
                for failed_path in failed_listing_paths
            )
        ),
        key=str.casefold,
    )
    if failed_roots:
        raise InputError(
            f"guide {guide['id']!r} resource root {failed_roots[0]!r} overlaps a failed scan listing"
        )
    excluded_directories = exclusion_audit(guide, directories)
    excluded_paths = {item["path"] for item in excluded_directories}
    conflicting_roots = sorted(explicit_paths & excluded_paths, key=str.casefold)
    if conflicting_roots:
        raise InputError(
            f"guide {guide['id']!r} resource root {conflicting_roots[0]!r} matches an exclusion rule"
        )
    scoped_paths = sorted(
        (path for path in directories if strict_descendant(path, scope)), key=str.casefold
    )
    child_directory_parents = {directory["_parent"] for directory in directories.values()}

    selected_paths = set(explicit_paths)
    if guide["selection_mode"] == "deepest_leaves":
        for path in scoped_paths:
            if path in excluded_paths:
                continue
            if any(path_is_within(path, failed_path) for failed_path in failed_listing_paths):
                continue
            if path in child_directory_parents:
                continue
            if any(strict_descendant(path, root) for root in explicit_paths):
                continue
            selected_paths.add(path)
    if not selected_paths:
        raise InputError(
            f"guide {guide['id']!r} has no directory resource units in {scope!r} after exclusions"
        )

    rows: list[dict[str, str]] = []
    for path in sorted(selected_paths, key=str.casefold):
        directory = directories[path]
        overrides = explicit_by_path.get(path, {})
        metadata = {
            field: overrides.get(field, guide["row_defaults"][field]) for field in ROW_DEFAULT_FIELDS
        }
        file_id = scan_file_id(directory, guide["id"])
        rows.append(
            {
                "category": metadata["category"],
                "name": directory["name"],
                "audience": metadata["audience"],
                "type": metadata["type"],
                "usage": metadata["usage"],
                "pace": metadata["pace"],
                "path": path,
                "url": f"{url_prefix}{file_id}",
                "file_id": file_id,
            }
        )
    return {
        "title": guide["title"],
        "summary": guide["summary"],
        "generatedAt": guide["generatedAt"],
        "partition": guide["partition"],
        "guidance": guide["guidance"],
        "rows": rows,
        "excluded_directories": excluded_directories,
        "scan_errors": scan_errors,
    }


def write_json_atomically(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build gen_family_nav_xlsx.mjs JSON inputs from a fresh scan JSONL."
    )
    parser.add_argument("--scan", required=True, type=Path, help="fresh file-level scan JSONL")
    parser.add_argument(
        "--scan-errors",
        type=Path,
        help="scan error sidecar; defaults to <scan>.errors and must exist when supplied",
    )
    parser.add_argument(
        "--allow-missing-scan-errors",
        action="store_true",
        help="allow a missing default <scan>.errors sidecar after independently verifying completeness",
    )
    parser.add_argument(
        "--allow-scan-errors",
        action="store_true",
        help="allow a non-empty validated sidecar after independent review; failed listings stay excluded",
    )
    parser.add_argument("--guide-spec", required=True, type=Path, help="guide specification JSON")
    parser.add_argument("--out-dir", required=True, type=Path, help="directory for <guide-id>.json outputs")
    parser.add_argument(
        "--url-prefix",
        required=True,
        help="direct-link prefix ending in /drive/file/all/backup/",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if URL_PREFIX_PATTERN.fullmatch(args.url_prefix) is None:
        raise InputError(
            "--url-prefix must be an https://alipan or aliyundrive direct-link prefix ending in "
            "/drive/file/all/backup/"
        )
    scan_errors, failed_listing_paths = load_scan_errors(
        args.scan,
        args.scan_errors,
        allow_missing=args.allow_missing_scan_errors,
        allow_errors=args.allow_scan_errors,
    )
    directories = index_scan(read_jsonl(args.scan))
    guides = load_guide_spec(args.guide_spec)
    outputs = [
        (
            guide["id"],
            build_guide_input(
                guide,
                directories,
                args.url_prefix,
                failed_listing_paths,
                scan_errors,
            ),
        )
        for guide in guides
    ]
    output_dir = args.out_dir.resolve()
    for guide_id, document in outputs:
        write_json_atomically(output_dir / f"{guide_id}.json", document)
    print(
        json.dumps(
            {
                "status": "updated",
                "scan_errors": scan_errors,
                "outputs": [
                    {
                        "guide_id": guide_id,
                        "output": str((output_dir / f"{guide_id}.json")),
                        "rows": len(document["rows"]),
                        "excluded_directories": document["excluded_directories"],
                    }
                    for guide_id, document in outputs
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InputError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
