#!/usr/bin/env python3
"""Build a dry-run JSONL plan for splitting flat media series into chunks.

The input is the file-level JSONL emitted by ``scan_drive.py`` and a portable
rules JSON document.  This script never invokes a cloud-drive client.  It
only emits ``mkdir`` and ``mv`` actions for a later, independently reviewed
executor.

Rules use this shape::

    {
      "series": [{
        "parent": "/<series-parent>",
        "max_items": 20,
        "primary_pattern": "(?i)\\.mp4$",
        "group_prefix_step": 10,
        "episode_pattern": "(?P<episode>\\d+)",
        "sidecar_patterns": ["(?i)\\.(srt|vtt)$"],
        "protect": ["^README\\.txt$"],
        "protected_dir": "配套资料",
        "direct_file_policy": "leave"
      }]
    }

``protect`` entries are regular expressions matched against the direct
file's name or full cloud path.  ``sidecar_patterns`` and ``primary_pattern``
are likewise regular expressions.  A sidecar follows a primary with the same
episode, or the same filename stem when no episode association is available.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 1


class InputError(ValueError):
    """A scan or rules input cannot be safely planned."""


def normalize_cloud_path(value: str) -> str:
    """Normalize separators without changing characters inside a name."""

    if not isinstance(value, str) or not value.strip():
        raise InputError("cloud paths must be non-empty strings")
    if "\x00" in value:
        raise InputError("cloud paths cannot contain NUL")
    return str(PurePosixPath("/" + value.lstrip("/"))).rstrip("/") or "/"


def child_path(parent: str, name: str) -> str:
    if not isinstance(name, str) or not name or "/" in name:
        raise InputError(f"scan entry has an invalid name: {name!r}")
    return normalize_cloud_path(posixpath.join(parent, name))


def natural_sort_key(value: str) -> tuple[tuple[int, Any], ...]:
    """Sort embedded numbers numerically while preserving name spelling."""

    pieces = re.split(r"(\d+)", value.casefold())
    key: list[tuple[int, Any]] = []
    for piece in pieces:
        if piece.isdigit():
            key.append((1, int(piece)))
        else:
            key.append((0, piece))
    return tuple(key)


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
                value = json.loads(raw)
            except json.JSONDecodeError as error:
                raise InputError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(value, dict):
                raise InputError(f"{path}:{line_number}: each JSONL row must be an object")
            rows.append(value)
    return rows


def validate_scan(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows, 1):
        if "agg_files" in row:
            raise InputError(f"scan row {index} contains forbidden agg_files")
        if not isinstance(row.get("path"), str) or not isinstance(row.get("name"), str):
            raise InputError(f"scan row {index} must contain string path and name")
        if row.get("dir") not in (True, False):
            raise InputError(f"scan row {index} dir must be boolean")
        normalize_cloud_path(row["path"])
        if not row["name"] or "/" in row["name"]:
            raise InputError(f"scan row {index} has an invalid name")


def _as_pattern_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise InputError(f"rules.{field} must be a list of non-empty strings")
    return value


def _validate_protected_dir(value: Any, series_index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(
            f"series[{series_index}].protected_dir must be a non-empty relative directory name"
        )
    if value != value.strip() or "\x00" in value or "/" in value or "\\" in value or value in {".", ".."}:
        raise InputError(
            f"series[{series_index}].protected_dir must be one trimmed safe name without path separators"
        )
    return value


def load_rules(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InputError(f"cannot read rules {path}: {error}") from error
    if isinstance(raw, list):
        series = raw
    elif isinstance(raw, dict) and isinstance(raw.get("series"), list):
        series = raw["series"]
    else:
        raise InputError("rules must be an object with a series array, or a series array")
    if not series:
        raise InputError("rules.series must not be empty")

    compiled: list[dict[str, Any]] = []
    seen_parents: set[str] = set()
    for index, item in enumerate(series, 1):
        if not isinstance(item, dict):
            raise InputError(f"series[{index}] must be an object")
        for field in ("parent", "primary_pattern"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise InputError(f"series[{index}].{field} is required")
        parent = normalize_cloud_path(item["parent"])
        if parent in seen_parents:
            raise InputError(f"duplicate series parent: {parent}")
        seen_parents.add(parent)
        max_items = item.get("max_items")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0:
            raise InputError(f"series[{index}].max_items must be a positive integer")
        step = item.get("group_prefix_step", 10)
        if isinstance(step, bool) or not isinstance(step, int) or step <= 0:
            raise InputError(f"series[{index}].group_prefix_step must be a positive integer")
        direct_policy = item.get("direct_file_policy", "fail")
        if direct_policy not in {"fail", "leave", "error"}:
            raise InputError(
                f"series[{index}].direct_file_policy must be 'leave' or the default 'fail'"
            )
        try:
            primary_pattern = re.compile(item["primary_pattern"])
            episode_pattern = re.compile(item["episode_pattern"]) if item.get("episode_pattern") else None
            sidecar_patterns = [re.compile(pattern) for pattern in _as_pattern_list(item.get("sidecar_patterns"), "sidecar_patterns")]
            protect_patterns = [re.compile(pattern) for pattern in _as_pattern_list(item.get("protect"), "protect")]
        except re.error as error:
            raise InputError(f"series[{index}] contains an invalid regular expression: {error}") from error
        if episode_pattern is not None and "episode" not in episode_pattern.groupindex:
            raise InputError(f"series[{index}].episode_pattern must contain named group episode")
        protected_dir = None
        if "protected_dir" in item:
            protected_dir = _validate_protected_dir(item["protected_dir"], index)
        compiled.append({
            "index": index,
            "parent": parent,
            "max_items": max_items,
            "group_prefix_step": step,
            "primary_pattern": primary_pattern,
            "episode_pattern": episode_pattern,
            "sidecar_patterns": sidecar_patterns,
            "protect_patterns": protect_patterns,
            "protected_dir": protected_dir,
            "direct_file_policy": "leave" if direct_policy == "leave" else "fail",
        })
    return compiled


def _matches(patterns: list[re.Pattern[str]], name: str, path: str) -> bool:
    return any(pattern.search(name) or pattern.search(path) for pattern in patterns)


def _stem(name: str) -> str:
    return posixpath.splitext(name)[0]


def _episode(pattern: re.Pattern[str] | None, name: str) -> str | None:
    if pattern is None:
        return None
    match = pattern.search(name)
    return match.group("episode") if match else None


def _display_value(value: str) -> str:
    """Keep the real label but prevent it from becoming a path component."""

    value = value.replace("/", "-").replace("\\", "-")
    if re.fullmatch(r"[\d\s]+", value):
        return re.sub(r"\s+", "", value)
    return value


def _group_suffix(group: dict[str, Any], use_episode: bool) -> str:
    if use_episode:
        first = _display_value(str(group["units"][0]["key"]))
        last = _display_value(str(group["units"][-1]["key"]))
    else:
        width = max(3, len(str(group["last_order"])))
        first = f"{group['first_order']:0{width}d}"
        last = f"{group['last_order']:0{width}d}"
    return first if first == last else f"{first}-{last}"


def _episodes_are_natural_numbers(units: list[dict[str, Any]]) -> bool:
    """Return true when every episode key is a numeric/compound numeric label."""

    return bool(units) and all(
        re.fullmatch(r"[\d\s._-]+", str(unit["key"])) is not None
        for unit in units
    )


def _parent_matches(rows: list[dict[str, Any]], parent: str) -> bool:
    if any(normalize_cloud_path(str(row.get("path", ""))) == parent for row in rows):
        return True
    target = PurePosixPath(parent)
    target_parent = normalize_cloud_path(str(target.parent))
    return any(
        row.get("dir") is True
        and normalize_cloud_path(str(row.get("path", ""))) == target_parent
        and row.get("name") == target.name
        for row in rows
    )


def _scan_entity_paths(rows: list[dict[str, Any]]) -> set[str]:
    """Return paths represented by the file-level scan's parent/name rows."""

    return {
        child_path(normalize_cloud_path(str(row["path"])), str(row["name"]))
        for row in rows
    }


def _base_report(rows: list[dict[str, Any]], rules: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "failed",
        "complete": False,
        "plan_generated": False,
        "scan_rows": len(rows),
        "series_count": len(rules),
        "actions": 0,
        "errors": [],
        "unresolved": [],
        "protected": [],
        "planned_protected": [],
        "series": [],
    }


def build_plan(rows: list[dict[str, Any]], rules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Return ``(actions, report, can_write_plan)`` without filesystem writes."""

    validate_scan(rows)
    report = _base_report(rows, rules)
    actions: list[dict[str, Any]] = []
    mkdir_actions: list[dict[str, Any]] = []
    move_actions: list[dict[str, Any]] = []
    any_leave = False
    target_conflict = False
    existing_paths = _scan_entity_paths(rows) if any(rule["protected_dir"] is not None for rule in rules) else set()

    for rule in rules:
        parent = rule["parent"]
        series_report: dict[str, Any] = {
            "parent": parent,
            "primary_count": 0,
            "groups": [],
            "unresolved": [],
            "protected": [],
            "planned_protected": [],
        }
        report["series"].append(series_report)
        if not _parent_matches(rows, parent):
            report["errors"].append({"kind": "rule_parent_not_in_scan", "parent": parent})
            continue

        direct = [
            row for row in rows
            if row.get("dir") is not True
            and normalize_cloud_path(str(row.get("path", ""))) == parent
        ]
        direct.sort(key=lambda row: natural_sort_key(str(row["name"])))
        primary: list[dict[str, Any]] = []
        sidecars: list[dict[str, Any]] = []
        protected_rows: list[dict[str, Any]] = []
        for row in direct:
            name = str(row["name"])
            path = child_path(parent, name)
            if _matches(rule["protect_patterns"], name, path):
                protected = {"path": path, "name": name, "reason": "matched protect rule"}
                series_report["protected"].append(protected)
                report["protected"].append({"parent": parent, **protected})
                protected_rows.append(row)
            elif rule["primary_pattern"].search(name) or rule["primary_pattern"].search(path):
                primary.append(row)
            elif _matches(rule["sidecar_patterns"], name, path):
                sidecars.append(row)
            else:
                unresolved = {
                    "parent": parent,
                    "path": path,
                    "name": name,
                    "reason": "direct file matches neither primary_pattern nor sidecar_patterns",
                    "policy": rule["direct_file_policy"],
                }
                series_report["unresolved"].append(unresolved)
                report["unresolved"].append(unresolved)

        series_report["primary_count"] = len(primary)
        if not primary:
            report["errors"].append({"kind": "no_primary_files", "parent": parent})
            continue

        episode_pattern = rule["episode_pattern"]
        primary_by_stem: dict[str, list[dict[str, Any]]] = defaultdict(list)
        primary_by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
        missing_episode: list[str] = []
        for row in primary:
            primary_by_stem[_stem(str(row["name"]))].append(row)
            episode = _episode(episode_pattern, str(row["name"]))
            if episode_pattern is not None and episode is None:
                missing_episode.append(str(row["name"]))
            elif episode is not None:
                primary_by_episode[episode].append(row)
        if missing_episode:
            report["errors"].append({
                "kind": "primary_missing_episode",
                "parent": parent,
                "names": missing_episode,
            })

        for row in sidecars:
            name = str(row["name"])
            path = child_path(parent, name)
            episode = _episode(episode_pattern, name)
            key: str | None = None
            if episode is not None and episode in primary_by_episode:
                key = f"episode:{episode}"
            else:
                matches = primary_by_stem.get(_stem(name), [])
                if len(matches) == 1:
                    key = f"stem:{_stem(name)}"
                elif episode is not None and episode in primary_by_episode:
                    key = f"episode:{episode}"
            if key is None:
                unresolved = {
                    "parent": parent,
                    "path": path,
                    "name": name,
                    "reason": "sidecar cannot be associated by episode or stem",
                    "policy": rule["direct_file_policy"],
                }
                series_report["unresolved"].append(unresolved)
                report["unresolved"].append(unresolved)
        if series_report["unresolved"] and rule["direct_file_policy"] == "fail":
            report["errors"].append({
                "kind": "unresolved_direct_files",
                "parent": parent,
                "count": len(series_report["unresolved"]),
                "hint": "set direct_file_policy=leave only when leaving these files is intentional",
            })
        elif series_report["unresolved"]:
            any_leave = True

        protected_target = None
        if protected_rows and rule["protected_dir"] is not None:
            protected_target = child_path(parent, rule["protected_dir"])
            if protected_target in existing_paths:
                report["errors"].append({
                    "kind": "existing_target_conflict",
                    "parent": parent,
                    "target": protected_target,
                    "reason": "scan already contains an entity at the protected directory target",
                })
                target_conflict = True
            else:
                mkdir_action = {
                    "action_id": f"S{rule['index']:02d}-PD-MK",
                    "op": "mkdir",
                    "to": protected_target,
                    "reason": f"create protected companion directory {rule['protected_dir']} for {parent}",
                    "series_parent": parent,
                    "protected_dir": rule["protected_dir"],
                }
                mkdir_actions.append(mkdir_action)
                for move_index, row in enumerate(protected_rows, 1):
                    path = child_path(parent, str(row["name"]))
                    planned = {
                        "parent": parent,
                        "path": path,
                        "name": str(row["name"]),
                        "to": protected_target,
                        "reason": "matched protect rule and assigned to protected_dir",
                        "action_id": f"S{rule['index']:02d}-PD-M{move_index:03d}",
                    }
                    series_report["planned_protected"].append(planned)
                    report["planned_protected"].append(planned)
                    move_actions.append({
                        "action_id": planned["action_id"],
                        "op": "mv",
                        "from": path,
                        "to": protected_target,
                        "reason": f"move protected file {row['name']} into {rule['protected_dir']}",
                        "series_parent": parent,
                        "protected_dir": rule["protected_dir"],
                    })

        if len(primary) <= rule["max_items"]:
            continue
        if missing_episode:
            continue

        units: list[dict[str, Any]] = []
        if episode_pattern is not None:
            unit_by_key: dict[str, dict[str, Any]] = {}
            for order, row in enumerate(primary, 1):
                episode = _episode(episode_pattern, str(row["name"]))
                assert episode is not None
                unit = unit_by_key.get(episode)
                if unit is None:
                    unit = {"key": episode, "primary": [], "first_order": order}
                    unit_by_key[episode] = unit
                    units.append(unit)
                unit["primary"].append(row)
            for unit in units:
                if len(unit["primary"]) > rule["max_items"]:
                    report["errors"].append({
                        "kind": "episode_exceeds_chunk_limit",
                        "parent": parent,
                        "episode": unit["key"],
                        "primary_count": len(unit["primary"]),
                        "max_items": rule["max_items"],
                    })
            for index, unit in enumerate(units, 1):
                unit["last_order"] = unit["first_order"] + len(unit["primary"]) - 1
            if _episodes_are_natural_numbers(units):
                units.sort(key=lambda unit: natural_sort_key(re.sub(r"\s+", "", str(unit["key"]))))
        else:
            for offset in range(0, len(primary), rule["max_items"]):
                part = primary[offset:offset + rule["max_items"]]
                units.append({
                    "key": None,
                    "primary": part,
                    "first_order": offset + 1,
                    "last_order": offset + len(part),
                })

        groups: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for unit in units:
            if len(unit["primary"]) > rule["max_items"]:
                continue
            if current is None or len(current["primary"]) + len(unit["primary"]) > rule["max_items"]:
                current = {"units": [], "primary": [], "first_order": unit["first_order"]}
                groups.append(current)
            current["units"].append(unit)
            current["primary"].extend(unit["primary"])
            current["last_order"] = unit["last_order"]

        episode_to_group: dict[str, int] = {}
        stem_to_group: dict[str, int] = {}
        prefix_width = max(
            2,
            len(str(len(groups) * rule["group_prefix_step"])),
        )
        for group_index, group in enumerate(groups):
            prefix = (group_index + 1) * rule["group_prefix_step"]
            group_name = f"{prefix:0{prefix_width}d}_{_group_suffix(group, episode_pattern is not None)}"
            target = child_path(parent, group_name)
            group["name"] = group_name
            group["target"] = target
            if rule["protected_dir"] is not None:
                if group_name == rule["protected_dir"]:
                    report["errors"].append({
                        "kind": "protected_dir_conflicts_with_group",
                        "parent": parent,
                        "protected_dir": rule["protected_dir"],
                        "group": group_name,
                    })
                    target_conflict = True
                elif target in existing_paths:
                    report["errors"].append({
                        "kind": "existing_target_conflict",
                        "parent": parent,
                        "target": target,
                        "group": group_name,
                        "reason": "scan already contains an entity at the generated group target",
                    })
                    target_conflict = True
            for unit in group["units"]:
                if unit["key"] is not None:
                    episode_to_group[unit["key"]] = group_index
                for row in unit["primary"]:
                    stem_to_group[_stem(str(row["name"]))] = group_index
            series_report["groups"].append({
                "name": group_name,
                "path": target,
                "primary_count": len(group["primary"]),
                "first_order": group["first_order"],
                "last_order": group["last_order"],
            })

        for group in groups:
            group_index = groups.index(group)
            prefix = (group_index + 1) * rule["group_prefix_step"]
            action_id = f"S{rule['index']:02d}-G{prefix:02d}-MK"
            mkdir_actions.append({
                "action_id": action_id,
                "op": "mkdir",
                "to": group["target"],
                "reason": f"create ordered series group {group['name']} for {parent}",
                "series_parent": parent,
                "group": group["name"],
            })
            move_rows: list[dict[str, Any]] = list(group["primary"])
            for row in sidecars:
                name = str(row["name"])
                episode = _episode(episode_pattern, name)
                group_for_sidecar = episode_to_group.get(episode) if episode is not None else None
                if group_for_sidecar is None:
                    group_for_sidecar = stem_to_group.get(_stem(name))
                if group_for_sidecar == group_index:
                    move_rows.append(row)
            move_rows.sort(key=lambda row: natural_sort_key(str(row["name"])))
            for move_index, row in enumerate(move_rows, 1):
                path = child_path(parent, str(row["name"]))
                if any(item.get("path") == path for item in series_report["protected"]):
                    continue
                move_actions.append({
                    "action_id": f"S{rule['index']:02d}-G{prefix:02d}-M{move_index:03d}",
                    "op": "mv",
                    "from": path,
                    "to": group["target"],
                    "reason": f"move {row['name']} into ordered group {group['name']}",
                    "series_parent": parent,
                    "group": group["name"],
                })

    actions = [] if target_conflict else mkdir_actions + move_actions
    hard_errors = bool(report["errors"])
    report["actions"] = len(actions)
    report["plan_generated"] = not hard_errors
    planned_protected_paths = {item["path"] for item in report["planned_protected"]}
    unplanned_protected = [
        item for item in report["protected"] if item["path"] not in planned_protected_paths
    ]
    report["complete"] = not hard_errors and not report["unresolved"] and not unplanned_protected
    if hard_errors:
        report["status"] = "failed"
    elif unplanned_protected:
        report["status"] = "planned_with_protected"
    elif any_leave:
        report["status"] = "planned_with_unresolved"
    else:
        report["status"] = "planned"
    return actions, report, not hard_errors


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan safe long-series chunk moves from a scan JSONL.")
    parser.add_argument("--scan", required=True, type=Path, help="file-level scan JSONL")
    parser.add_argument("--rules", required=True, type=Path, help="portable series rules JSON")
    parser.add_argument("--out-plan", required=True, type=Path, help="JSONL action plan")
    parser.add_argument("--out-report", required=True, type=Path, help="JSON report")
    parser.add_argument("--force", action="store_true", help="overwrite existing output files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.out_plan.resolve() == args.out_report.resolve():
        print("--out-plan and --out-report must be different files", file=sys.stderr)
        return 2
    existing = [path for path in (args.out_plan, args.out_report) if path.exists()]
    if existing and not args.force:
        names = ", ".join(str(path) for path in existing)
        print(f"refusing to overwrite existing output: {names}; pass --force", file=sys.stderr)
        return 2
    try:
        rows = read_jsonl(args.scan)
        rules = load_rules(args.rules)
        actions, report, can_write = build_plan(rows, rules)
    except InputError as error:
        failure = {
            "schema_version": SCHEMA_VERSION,
            "status": "failed",
            "complete": False,
            "plan_generated": False,
            "actions": 0,
            "errors": [{"kind": "input_error", "message": str(error)}],
        }
        try:
            write_report(args.out_report, failure)
        except OSError:
            pass
        print(str(error), file=sys.stderr)
        return 2
    if can_write:
        write_jsonl(args.out_plan, actions)
    write_report(args.out_report, report)
    if not can_write:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
