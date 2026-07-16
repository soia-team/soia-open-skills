#!/usr/bin/env python3
"""Fresh cloud-state preflight for every registered reclassification batch.

This command is read-only. It lists the exact source/destination parents used
by ``run.json.batches`` and replays all actions in manifest order. Any missing
source, wrong file_id, destination collision, or parent-order defect blocks the
entire run before the first cloud write.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import audit_run_bundle
import preflight_gate


RUNNER_ENV = "SOIA_ALIPAN_RUNNER"
RECLASS_OPS = {"mkdir", "mv", "rename"}
CLEANUP_OPS = {"delete", "remove", "trash"}
CLEANUP_EVIDENCE_VERIFIED_STATUSES = frozenset({
    "removed_to_recycle_bin_verified",
    "removed_to_recycle_bin_and_absence_verified",
    "removed_to_recycle_bin_and_parent_verified_empty",
})
CLEANUP_ACTION_ERROR = (
    "删除动作应登记在 cleanup_batches，由原子层在用户授权+空壳验证后执行，不进入重分类恢复/重放"
)


def alipan_runner_path() -> Path | None:
    """Locate the atomic skill's private-env runner without user paths."""

    override = os.environ.get(RUNNER_ENV)
    candidate = Path(override).expanduser() if override else (
        Path(__file__).resolve().parents[2] / "soia-pkm-alipan-drive-ops" / "scripts" / "run_with_env.py"
    )
    return candidate if candidate.is_file() else None


def require_alipan_runner() -> Path:
    runner = alipan_runner_path()
    if runner is None:
        raise FileNotFoundError(
            "aliyunpan environment runner unavailable; set SOIA_ALIPAN_RUNNER "
            "or install the adjacent soia-pkm-alipan-drive-ops skill"
        )
    return runner


def run_aliyunpan_ll(runner: Path, drive_id: str, path: str, timeout: int) -> subprocess.CompletedProcess:
    """Run one read-only listing through the private-env runner, never bare."""

    args = [
        sys.executable,
        str(runner),
        "--",
        "aliyunpan",
        "ll",
        "--driveId",
        drive_id,
        path,
    ]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "RUNNER_TIMEOUT")
    except OSError:
        return subprocess.CompletedProcess(args, 255, "", "RUNNER_EXECUTION_FAILED")


def normalize(path: str) -> str:
    value = "/" + "/".join(part for part in str(path).split("/") if part)
    return posixpath.normpath(value)


def within(path: str, root: str) -> bool:
    path = normalize(path)
    root = normalize(root)
    return path == root or path.startswith(root + "/")


def parent_name(path: str) -> tuple[str, str]:
    value = normalize(path)
    return posixpath.dirname(value) or "/", posixpath.basename(value)


def destination(action: dict) -> str:
    if action["op"] == "mkdir":
        return normalize(action["to"])
    if action["op"] == "mv":
        return normalize(action["to"] + "/" + posixpath.basename(normalize(action["from"])))
    return normalize(action["to"])


def sha256_file(path: Path) -> str:
    return preflight_gate.sha256_file(path)


def parse_ll(output: str) -> tuple[str, list[dict]]:
    if output.startswith("指定目录不存在:"):
        return "missing", []
    if "当前目录" not in output:
        raise ValueError("missing current-directory marker")
    entries: list[dict] = []
    names: set[str] = set()
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("当前目录") or line.startswith("----"):
            continue
        if "总:" in line and "文件总数" in line:
            continue
        parts = line.split(None, 9)
        if not parts or parts[0] == "#":
            continue
        try:
            int(parts[0])
        except ValueError:
            continue
        if len(parts) < 10:
            raise ValueError(f"malformed ll row: {line[:160]}")
        raw_name = parts[9]
        is_dir = raw_name.endswith("/")
        name = raw_name[:-1] if is_dir else raw_name
        if name in names:
            raise ValueError(f"duplicate exact name in listing: {name}")
        names.add(name)
        entries.append({
            "id": parts[1],
            "name": name,
            "dir": is_dir,
            "size": None if is_dir else int(parts[4]) if parts[4].isdigit() else None,
            "sha1": None if parts[3] == "-" else parts[3],
        })
    return "exists", entries


def list_directory(
    drive_id: str,
    path: str,
    timeout: int,
    attempts: int,
    runner: Path | None = None,
) -> dict:
    runner = require_alipan_runner() if runner is None else runner
    last: dict = {}
    for attempt in range(1, attempts + 1):
        result = run_aliyunpan_ll(runner, drive_id, path, timeout)
        output = result.stdout or ""
        last = {
            "path": path,
            "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        if result.returncode == 0:
            try:
                state, entries = parse_ll(output)
                return {**last, "state": state, "entries": entries}
            except ValueError as error:
                last["error"] = str(error)
        else:
            last["error"] = (result.stderr or output)[:240]
        if attempt < attempts:
            time.sleep(attempt)
    return {**last, "state": "error", "entries": []}


def load_registered(run_dir: Path, roots: list[str]) -> tuple[dict, list[dict], dict[str, str]]:
    manifest_path = run_dir / "run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actions: list[dict] = []
    hashes = {"run.json": sha256_file(manifest_path)}
    # Every executable plan is immutable at preflight, including cleanup plans.
    # Cleanup result ledgers are intentionally omitted: they are append-only
    # evidence produced by the executor after this report is issued.
    for relative in preflight_gate.registered_plan_paths(manifest):
        plan_path = preflight_gate.resolve_run_member(run_dir, relative, "registered plan")
        if not plan_path.is_file():
            raise ValueError(f"registered plan is missing: {relative}")
        hashes[relative] = sha256_file(plan_path)
    for index, result in enumerate(preflight_gate.registered_cleanup_result_paths(manifest)):
        preflight_gate.resolve_run_member(run_dir, result, f"run.cleanup_batches[{index}].result")
    cleanup_authorizations = preflight_gate.registered_cleanup_authorizations(manifest)
    if cleanup_authorizations is not None:
        authorization_path = preflight_gate.resolve_run_member(
            run_dir,
            cleanup_authorizations,
            "run.files.cleanup_authorizations",
        )
        if not authorization_path.is_file():
            raise ValueError(f"registered cleanup authorizations are missing: {cleanup_authorizations}")
        hashes[cleanup_authorizations] = sha256_file(authorization_path)
    cleanup_evidence = preflight_gate.registered_cleanup_evidence(manifest)
    if cleanup_evidence is not None:
        evidence_path = preflight_gate.resolve_run_member(
            run_dir,
            cleanup_evidence,
            "run.files.empty_cleanup_evidence",
        )
        if not evidence_path.is_file():
            raise ValueError(f"registered empty cleanup evidence is missing: {cleanup_evidence}")
        hashes[cleanup_evidence] = sha256_file(evidence_path)
    seen_ids: set[str] = set()
    for batch_index, batch in enumerate(manifest.get("batches", []), 1):
        relative = str(batch.get("plan", "")).strip()
        plan_path = (run_dir / relative).resolve()
        if run_dir.resolve() not in plan_path.parents:
            raise ValueError(f"batch {batch_index}: plan escapes run dir")
        with plan_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                action = json.loads(line)
                action_id = str(action.get("action_id", "")).strip()
                op = action.get("op")
                if not action_id or action_id in seen_ids:
                    raise ValueError(f"{relative}:{line_number}: invalid/duplicate action_id")
                seen_ids.add(action_id)
                if op in CLEANUP_OPS:
                    raise ValueError(
                        f"{CLEANUP_ACTION_ERROR}（{relative}:{line_number} op={op!r}）"
                    )
                if op not in RECLASS_OPS:
                    raise ValueError(f"{relative}:{line_number}: invalid op {op}")
                for field in (("to",) if op == "mkdir" else ("from", "to")):
                    value = str(action.get(field, ""))
                    if not value.startswith("/") or normalize(value) != value.rstrip("/"):
                        raise ValueError(f"{relative}:{line_number}: noncanonical {field}")
                    if not any(within(value, root) for root in roots):
                        raise ValueError(f"{relative}:{line_number}: {field} outside allowed roots")
                if op != "mkdir" and not str(action.get("file_id", "")).strip():
                    raise ValueError(f"{relative}:{line_number}: missing file_id")
                actions.append({**action, "_batch": batch_index, "_plan": relative, "_line": line_number})
    return manifest, actions, hashes


def operation_key(item: dict) -> tuple:
    """Match the executors' resume identity, including ``file_id``."""

    return item.get("action_id"), item.get("op"), item.get("from"), item.get("to"), item.get("file_id")


def load_resume_state(run_dir: Path, manifest: dict, actions: list[dict]) -> tuple[set[tuple], list[dict]]:
    """Load each batch ledger's latest rows without trusting their claims."""

    registered_by_batch: dict[int, set[tuple]] = {}
    for action in actions:
        registered_by_batch.setdefault(int(action["_batch"]), set()).add(operation_key(action))

    verified: set[tuple] = set()
    violations: list[dict] = []
    for batch_index, batch in enumerate(manifest.get("batches", []), 1):
        relative = batch.get("result") if isinstance(batch, dict) else None
        try:
            result_path = preflight_gate.resolve_run_member(
                run_dir,
                relative,
                f"run.batches[{batch_index - 1}].result",
            )
        except ValueError as error:
            raise ValueError(f"batch {batch_index}: invalid result ledger: {error}") from error
        if not result_path.is_file():
            continue
        latest: dict[tuple, tuple[int, dict]] = {}
        with result_path.open(encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, 1):
                if not raw.strip():
                    continue
                row = json.loads(raw)
                if not isinstance(row, dict):
                    raise ValueError(f"{relative}:{line_number}: ledger row must be an object")
                latest[operation_key(row)] = (line_number, row)
        registered = registered_by_batch.get(batch_index, set())
        for key, (line_number, row) in latest.items():
            if row.get("status") not in {"verified", "completed"}:
                continue
            if key not in registered:
                violations.append({
                    "kind": "verified_ledger_operation_not_registered",
                    "batch": batch_index,
                    "result": str(relative),
                    "line": line_number,
                    "action_id": row.get("action_id"),
                    "file_id": row.get("file_id"),
                })
                continue
            verified.add(key)
    return verified, violations


def load_cleanup_evidence(run_dir: Path, manifest: dict) -> tuple[str | None, list[dict]]:
    relative = preflight_gate.registered_cleanup_evidence(manifest)
    if relative is None:
        return None, []
    evidence_path = preflight_gate.resolve_run_member(
        run_dir,
        relative,
        "run.files.empty_cleanup_evidence",
    )
    if not evidence_path.is_file():
        raise ValueError(f"registered empty cleanup evidence is missing: {relative}")
    rows: list[dict] = []
    with evidence_path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise ValueError(f"{relative}:{line_number}: cleanup evidence must be an object")
            rows.append({**row, "_line": line_number, "_evidence": relative})
    return relative, rows


def required_listing_paths(actions: list[dict]) -> list[str]:
    result: set[str] = set()
    for action in actions:
        if action["op"] == "mkdir":
            result.add(parent_name(action["to"])[0])
        else:
            result.add(parent_name(action["from"])[0])
            target_parent = normalize(action["to"] if action["op"] == "mv" else parent_name(action["to"])[0])
            result.add(target_parent)
    return sorted(result)


def seed_virtual(listings: list[dict]) -> tuple[dict[str, dict], set[str]]:
    entities: dict[str, dict] = {}
    existing_dirs: set[str] = {"/"}
    for listing in listings:
        path = normalize(listing["path"])
        if listing["state"] == "exists":
            existing_dirs.add(path)
            for item in listing["entries"]:
                full = normalize(path + "/" + item["name"])
                previous = entities.get(full)
                if previous and previous["id"] != item["id"]:
                    raise ValueError(f"conflicting live entries for {full}")
                entities[full] = dict(item)
                if item["dir"]:
                    existing_dirs.add(full)
    return entities, existing_dirs


def directory_identity(item: dict | None) -> str | None:
    """Return a fresh-listing directory ID, never a path-only assumption."""

    if not isinstance(item, dict) or item.get("dir") is not True:
        return None
    value = item.get("id")
    return value.strip() if isinstance(value, str) and value.strip() else None


def relocate_entity(
    entities: dict[str, dict],
    directories: set[str],
    source: str,
    target: str,
) -> None:
    """Move one entity and all known descendants in the virtual state."""

    item = entities.pop(source)
    descendant_entities = [path for path in entities if path.startswith(source + "/")]
    descendant_dirs = [path for path in directories if path == source or path.startswith(source + "/")]
    entities[target] = item
    for old in descendant_entities:
        entities[target + old[len(source):]] = entities.pop(old)
    if item["dir"]:
        for old in descendant_dirs:
            directories.remove(old)
            directories.add(target + old[len(source):])


def verified_prefixes(actions: list[dict], verified_keys: set[tuple]) -> tuple[dict[str, list[dict]], list[dict]]:
    """Return contiguous verified prefixes for each planned file-id chain."""

    chains: dict[str, list[dict]] = {}
    for action in actions:
        if action["op"] != "mkdir":
            chains.setdefault(str(action["file_id"]), []).append(action)

    prefixes: dict[str, list[dict]] = {}
    violations: list[dict] = []
    for file_id, chain in chains.items():
        prefix: list[dict] = []
        gap_seen = False
        previous: dict | None = None
        for action in chain:
            is_verified = operation_key(action) in verified_keys
            if previous is not None and destination(previous) != normalize(action["from"]):
                violations.append({
                    "kind": "file_id_chain_disconnected",
                    "file_id": file_id,
                    "previous_action_id": previous["action_id"],
                    "action_id": action["action_id"],
                    "expected_source": destination(previous),
                    "actual_source": normalize(action["from"]),
                })
            if is_verified:
                if gap_seen:
                    violations.append({
                        "kind": "verified_chain_gap",
                        "file_id": file_id,
                        "action_id": action["action_id"],
                    })
                else:
                    prefix.append(action)
            else:
                gap_seen = True
            previous = action
        if prefix:
            prefixes[file_id] = prefix
    return prefixes, violations


def rewind_verified_prefixes(
    actions: list[dict],
    entities: dict[str, dict],
    directories: set[str],
    verified_keys: set[tuple],
) -> tuple[set[tuple], list[dict]]:
    """Prove current terminal states, then rewind them for ordered replay."""

    prefixes, violations = verified_prefixes(actions, verified_keys)
    accepted: set[tuple] = set()
    provisional: set[tuple] = set()
    invalid_file_ids = {
        str(item["file_id"])
        for item in violations
        if item.get("file_id") is not None
    }
    for file_id, prefix in prefixes.items():
        if file_id in invalid_file_ids:
            continue
        terminal = destination(prefix[-1])
        terminal_item = entities.get(terminal)
        if terminal_item is None:
            violations.append({
                "kind": "verified_terminal_missing",
                "file_id": file_id,
                "action_id": prefix[-1]["action_id"],
                "terminal": terminal,
            })
            continue
        if str(terminal_item.get("id", "")) != file_id:
            violations.append({
                "kind": "verified_terminal_id_mismatch",
                "file_id": file_id,
                "action_id": prefix[-1]["action_id"],
                "terminal": terminal,
                "actual": terminal_item.get("id"),
            })
            continue
        provisional.update(operation_key(action) for action in prefix)

    for action in actions:
        if action["op"] != "mkdir" or operation_key(action) not in verified_keys:
            continue
        target = destination(action)
        occupant = entities.get(target)
        if target not in directories:
            violations.append({
                "kind": "verified_mkdir_terminal_missing",
                "action_id": action["action_id"],
                "target": target,
            })
        elif directory_identity(occupant) is None:
            violations.append({
                "kind": "verified_mkdir_terminal_identity_missing",
                "action_id": action["action_id"],
                "target": target,
            })
        else:
            accepted.add(operation_key(action))

    rewound_entities = {path: dict(item) for path, item in entities.items()}
    rewound_directories = set(directories)
    rewound = True
    for action in reversed(actions):
        key = operation_key(action)
        if action["op"] == "mkdir" or key not in provisional:
            continue
        file_id = str(action["file_id"])
        target = destination(action)
        source = normalize(action["from"])
        target_item = rewound_entities.get(target)
        if target_item is None or str(target_item.get("id", "")) != file_id:
            violations.append({
                "kind": "verified_chain_intermediate_missing",
                "file_id": file_id,
                "action_id": action["action_id"],
                "path": target,
                "actual": None if target_item is None else target_item.get("id"),
            })
            rewound = False
            break
        if source in rewound_entities and source != target:
            violations.append({
                "kind": "verified_chain_rewind_collision",
                "file_id": file_id,
                "action_id": action["action_id"],
                "path": source,
                "occupant_id": rewound_entities[source].get("id"),
            })
            rewound = False
            break
        relocate_entity(rewound_entities, rewound_directories, target, source)
    if rewound:
        entities.clear()
        entities.update(rewound_entities)
        directories.clear()
        directories.update(rewound_directories)
        accepted.update(provisional)
    return accepted, violations


def evaluate_cleanup_superseded(
    actions: list[dict],
    entities: dict[str, dict],
    directories: set[str],
    verified_keys: set[tuple],
    evidence_rows: list[dict],
) -> tuple[dict[tuple, dict], list[dict]]:
    """Validate approved empty-directory removals without trusting evidence alone."""

    violations: list[dict] = []
    mkdir_by_path: dict[str, list[dict]] = {}
    for action in actions:
        if action["op"] == "mkdir":
            mkdir_by_path.setdefault(destination(action), []).append(action)

    records: dict[str, dict] = {}
    invalid_paths: set[str] = set()
    seen_file_ids: dict[str, str] = {}

    def violate(kind: str, row: dict, **extra: object) -> None:
        violations.append({
            "kind": kind,
            "evidence": row.get("_evidence"),
            "line": row.get("_line"),
            **extra,
        })

    for row in evidence_rows:
        raw_path = row.get("path")
        if not isinstance(raw_path, str) or not raw_path.startswith("/") or normalize(raw_path) != raw_path.rstrip("/"):
            violate("invalid_cleanup_evidence_path", row, path=raw_path)
            continue
        path = normalize(raw_path)
        if path in records:
            violate("duplicate_cleanup_evidence_path", row, path=path)
            invalid_paths.add(path)
            continue
        records[path] = row
        if path not in mkdir_by_path:
            violate("cleanup_evidence_path_not_registered", row, path=path)
            invalid_paths.add(path)
        elif len(mkdir_by_path[path]) != 1:
            violate("cleanup_evidence_path_ambiguous", row, path=path)
            invalid_paths.add(path)

        file_id = row.get("file_id")
        if not isinstance(file_id, str) or not file_id.strip():
            violate("invalid_cleanup_evidence_file_id", row, path=path)
            invalid_paths.add(path)
        elif file_id in seen_file_ids:
            violate(
                "duplicate_cleanup_evidence_file_id",
                row,
                path=path,
                file_id=file_id,
                first_path=seen_file_ids[file_id],
            )
            invalid_paths.add(path)
            invalid_paths.add(seen_file_ids[file_id])
        else:
            seen_file_ids[file_id] = path

        files = row.get("files")
        if isinstance(files, bool) or not isinstance(files, int) or files != 0:
            violate("cleanup_evidence_not_empty", row, path=path, files=files)
            invalid_paths.add(path)
        dirs = row.get("dirs")
        if isinstance(dirs, bool) or not isinstance(dirs, int) or dirs < 0:
            violate("invalid_cleanup_evidence_dirs", row, path=path, dirs=dirs)
            invalid_paths.add(path)
        if not isinstance(row.get("decision"), str) or not row["decision"].strip():
            violate("cleanup_evidence_decision_missing", row, path=path)
            invalid_paths.add(path)
        status = row.get("status")
        if status not in CLEANUP_EVIDENCE_VERIFIED_STATUSES:
            violate("invalid_cleanup_evidence_status", row, path=path, status=status)
            invalid_paths.add(path)

    for parent_path, parent in records.items():
        descendants = [
            (child_path, child)
            for child_path, child in records.items()
            if child_path != parent_path and within(child_path, parent_path)
        ]
        later_descendants = [
            child_path
            for child_path, child in descendants
            if int(child["_line"]) > int(parent["_line"])
        ]
        if later_descendants:
            violate(
                "cleanup_evidence_parent_removed_before_child",
                parent,
                path=parent_path,
                later_children=sorted(later_descendants),
            )
            invalid_paths.add(parent_path)
        dirs = parent.get("dirs")
        if isinstance(dirs, int) and not isinstance(dirs, bool) and dirs > 0:
            direct_children_before = [
                child_path
                for child_path, child in descendants
                if parent_name(child_path)[0] == parent_path
                and int(child["_line"]) < int(parent["_line"])
            ]
            if len(direct_children_before) != dirs:
                violate(
                    "cleanup_evidence_child_count_mismatch",
                    parent,
                    path=parent_path,
                    expected_dirs=dirs,
                    evidenced_direct_children=len(direct_children_before),
                )
                invalid_paths.add(parent_path)

    superseded: dict[tuple, dict] = {}
    for path, row in records.items():
        if path in invalid_paths or path not in mkdir_by_path or len(mkdir_by_path[path]) != 1:
            continue
        action = mkdir_by_path[path][0]
        key = operation_key(action)
        if key not in verified_keys:
            violate(
                "cleanup_evidence_without_verified_mkdir",
                row,
                path=path,
                action_id=action["action_id"],
            )
            continue
        if path in directories or path in entities:
            violate(
                "cleanup_evidence_target_still_exists",
                row,
                path=path,
                action_id=action["action_id"],
            )
            continue
        superseded[key] = row
    return superseded, violations


def replay(
    actions: list[dict],
    listings: list[dict],
    verified_keys: set[tuple] | None = None,
    cleanup_evidence: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    entities, directories = seed_virtual(listings)
    verified_keys = verified_keys or set()
    superseded, cleanup_violations = evaluate_cleanup_superseded(
        actions,
        entities,
        directories,
        verified_keys,
        cleanup_evidence or [],
    )
    statuses: list[dict] = []
    accepted_verified, violations = rewind_verified_prefixes(
        actions,
        entities,
        directories,
        verified_keys - set(superseded),
    )
    violations = [*cleanup_violations, *violations]

    def block(action: dict, kind: str, **extra: object) -> None:
        violations.append({
            "kind": kind,
            "action_id": action["action_id"],
            "plan": action["_plan"],
            "line": action["_line"],
            **extra,
        })

    first_mkdir_by_target: dict[str, dict] = {}
    for action in actions:
        op = action["op"]
        target = destination(action)
        if op == "mkdir":
            first_mkdir = first_mkdir_by_target.setdefault(target, action)
            if first_mkdir is not action:
                block(
                    action,
                    "duplicate_mkdir_target",
                    target=target,
                    first_action_id=first_mkdir["action_id"],
                )
                continue
            cleanup = superseded.get(operation_key(action))
            if cleanup is not None:
                parent = parent_name(target)[0]
                if parent not in directories:
                    block(
                        action,
                        "superseded_mkdir_parent_missing_or_out_of_order",
                        parent=parent,
                    )
                    continue
                entities[target] = {
                    "id": f"superseded:{cleanup['file_id']}",
                    "name": parent_name(target)[1],
                    "dir": True,
                }
                directories.add(target)
                statuses.append({
                    "action_id": action["action_id"],
                    "status": "superseded",
                    "target": target,
                    "cleanup_file_id": cleanup["file_id"],
                    "cleanup_evidence": cleanup["_evidence"],
                    "cleanup_line": cleanup["_line"],
                })
                continue
            parent = parent_name(target)[0]
            occupant = entities.get(target)
            if occupant and not occupant["dir"]:
                block(action, "mkdir_target_is_file", path=target)
                continue
            already_verified = operation_key(action) in accepted_verified
            if target in directories:
                if already_verified:
                    statuses.append({
                        "action_id": action["action_id"],
                        "status": "already_verified",
                        "target": target,
                        "directory_id": directory_identity(occupant),
                    })
                else:
                    block(
                        action,
                        "mkdir_target_preexists_without_provenance",
                        target=target,
                        directory_id=directory_identity(occupant),
                    )
                continue
            if parent not in directories:
                block(action, "mkdir_parent_missing_or_out_of_order", parent=parent)
                continue
            entities[target] = {"id": f"planned:{action['action_id']}", "name": parent_name(target)[1], "dir": True}
            directories.add(target)
            statuses.append({"action_id": action["action_id"], "status": "ready", "target": target})
            continue

        source = normalize(action["from"])
        item = entities.get(source)
        if item is None:
            block(action, "source_missing", source=source, target=target)
            continue
        expected_id = str(action.get("file_id", ""))
        if item["id"] != expected_id:
            block(action, "source_id_mismatch", source=source, expected=expected_id, actual=item["id"])
            continue
        target_parent = parent_name(target)[0]
        if target_parent not in directories:
            block(action, "target_parent_missing_or_out_of_order", parent=target_parent)
            continue
        if op == "rename" and parent_name(source)[0] != target_parent:
            block(action, "cross_parent_rename", source=source, target=target)
            continue
        if item["dir"] and within(target, source) and target != source:
            block(action, "directory_moved_into_descendant", source=source, target=target)
            continue
        occupant = entities.get(target)
        if occupant is not None and target != source:
            block(action, "destination_collision", target=target, occupant_id=occupant["id"])
            continue

        relocate_entity(entities, directories, source, target)
        statuses.append({
            "action_id": action["action_id"],
            "status": "already_verified" if operation_key(action) in accepted_verified else "ready",
            "source": source,
            "target": target,
            "file_id": expected_id,
        })
    return statuses, violations


def summarize_action_statuses(statuses: list[dict]) -> dict[str, int]:
    already_verified = sum(item.get("status") == "already_verified" for item in statuses)
    superseded = sum(item.get("status") == "superseded" for item in statuses)
    return {
        "ready_actions": len(statuses) - already_verified - superseded,
        "already_verified_actions": already_verified,
        "superseded_actions": superseded,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fresh read-only preflight for registered cloud reclassification plans.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--driveId", required=True)
    parser.add_argument("--allow-root", action="append", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()
    try:
        if args.report.exists():
            raise ValueError(f"refusing to overwrite report: {args.report}")
        roots = [normalize(root) for root in args.allow_root]
        run_audit = audit_run_bundle.audit_bundle(args.run_dir, final=False, require_preflight=False)
        if run_audit.get("status") != "passed":
            raise ValueError("non-final run-bundle audit failed")
        manifest, actions, hashes = load_registered(args.run_dir, roots)
        verified_keys, ledger_violations = load_resume_state(args.run_dir, manifest, actions)
        _, cleanup_evidence = load_cleanup_evidence(args.run_dir, manifest)
        registered_report = preflight_gate.registered_preflight_report_path(args.run_dir, manifest)
        if args.report.resolve() != registered_report:
            raise ValueError(
                "--report must equal run.files.preflight_report inside the run directory"
            )
        runner = require_alipan_runner()
        paths = required_listing_paths(actions)
        listings: list[dict] = []
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 16))) as pool:
            future_paths = {
                pool.submit(
                    list_directory,
                    args.driveId,
                    path,
                    args.timeout,
                    args.attempts,
                    runner,
                ): path
                for path in paths
            }
            for future in as_completed(future_paths):
                listings.append(future.result())
        listings.sort(key=lambda item: item["path"])
        list_errors = [item for item in listings if item["state"] == "error"]
        statuses, replay_violations = (
            replay(actions, listings, verified_keys, cleanup_evidence)
            if not list_errors else ([], [])
        )
        violations = [*ledger_violations, *replay_violations]
        action_counts = summarize_action_statuses(statuses)
        report = {
            "schema_version": 1,
            "status": "passed" if not list_errors and not violations else "failed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "drive_id_sha256": hashlib.sha256(args.driveId.encode("utf-8")).hexdigest(),
            "allowed_roots": roots,
            "hashes": hashes,
            "checked": {
                "registered_actions": len(actions),
                "listing_paths": len(paths),
                **action_counts,
                "listing_errors": len(list_errors),
                "violations": len(violations),
            },
            "listing_errors": [{k: v for k, v in item.items() if k != "entries"} for item in list_errors],
            "violations": violations,
            "actions": statuses,
            "listing_evidence": [
                {k: v for k, v in item.items() if k != "entries"} | {"entry_count": len(item["entries"])}
                for item in listings
            ],
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.report.with_name(args.report.name + ".tmp")
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, args.report)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report["checked"], ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
