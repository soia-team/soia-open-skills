#!/usr/bin/env python3
"""Materialize a target-partition catalog snapshot from a verified run ledger.

This is deliberately offline.  It starts with a complete, file-level base
scan, replays only the registered ordinary ``run.json.batches`` actions whose
append-only result ledger closes with an exact operation identity and a
``verified``/``completed`` status, then emits the resulting entities below one
explicit target root.  It never invokes a drive client or writes a vault.

``mv`` follows :mod:`apply_reclass`: ``to`` is a destination *directory* and
the source basename is retained.  ``rename`` follows the same executor: its
``to`` is the new full path in the same parent directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import sys
import tempfile
from pathlib import Path
from typing import Any


RECLASS_OPS = {"mkdir", "mv", "rename"}
CLEANUP_OPS = {"delete", "remove", "trash"}
SUCCESS_STATUSES = {"verified", "completed"}


class MaterializationError(ValueError):
    """An input cannot prove a complete, unambiguous materialized state."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise MaterializationError(f"{label} is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise MaterializationError(f"{label} is not valid JSON: {path}: {error.msg}") from error
    if not isinstance(value, dict):
        raise MaterializationError(f"{label} must be a JSON object: {path}")
    return value


def read_jsonl(path: Path, label: str) -> list[tuple[int, dict[str, Any]]]:
    try:
        source = path.open("r", encoding="utf-8")
    except FileNotFoundError as error:
        raise MaterializationError(f"{label} is missing: {path}") from error
    rows: list[tuple[int, dict[str, Any]]] = []
    with source:
        for line_number, raw in enumerate(source, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as error:
                raise MaterializationError(
                    f"{label}:{line_number} is not valid JSON: {error.msg}"
                ) from error
            if not isinstance(value, dict):
                raise MaterializationError(f"{label}:{line_number} must be a JSON object")
            rows.append((line_number, value))
    return rows


def canonical_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value or not value.startswith("/"):
        raise MaterializationError(f"{label} must be a non-empty absolute canonical path")
    normalized = posixpath.normpath(value)
    expected = value.rstrip("/") or "/"
    if normalized != expected:
        raise MaterializationError(f"{label} is not canonical: {value!r}")
    return normalized


def non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise MaterializationError(f"{label} must be a non-empty string")
    return value


def child_path(parent: str, name: str) -> str:
    return posixpath.normpath(posixpath.join(parent, name))


def parent_and_name(path: str) -> tuple[str, str]:
    parent = posixpath.dirname(path) or "/"
    name = posixpath.basename(path)
    if not name:
        raise MaterializationError(f"path has no entity name: {path!r}")
    return parent, name


def path_is_within(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def resolve_run_member(run_dir: Path, value: object, label: str) -> tuple[Path, str]:
    member = non_empty_string(value, label)
    relative = Path(member)
    if relative.is_absolute() or ".." in relative.parts:
        raise MaterializationError(f"{label} must stay inside the run directory")
    root = run_dir.resolve()
    resolved = (run_dir / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise MaterializationError(f"{label} escapes the run directory")
    return resolved, resolved.relative_to(root).as_posix()


def operation_key(action: dict[str, Any]) -> tuple[object, object, object, object, object]:
    """Match the existing executor's identity: action_id/op/from/to/file_id."""

    return (
        action.get("action_id"),
        action.get("op"),
        action.get("from"),
        action.get("to"),
        action.get("file_id"),
    )


def parse_operation(row: dict[str, Any], label: str) -> dict[str, Any]:
    """Validate one plan or ledger operation without inferring absent identity."""

    action_id = non_empty_string(row.get("action_id"), f"{label}.action_id")
    op = row.get("op")
    if op in CLEANUP_OPS:
        raise MaterializationError(
            f"{label}: cleanup op {op!r} is not a normal migration action"
        )
    if op not in RECLASS_OPS:
        raise MaterializationError(f"{label}.op is invalid: {op!r}")

    action: dict[str, Any] = {"action_id": action_id, "op": op}
    if op == "mkdir":
        if row.get("from") is not None:
            raise MaterializationError(f"{label}: mkdir must not have from")
        action["from"] = None
    else:
        action["from"] = canonical_path(row.get("from"), f"{label}.from")

    action["to"] = canonical_path(row.get("to"), f"{label}.to")
    raw_file_id = row.get("file_id")
    if op == "mkdir":
        if raw_file_id is not None:
            action["file_id"] = non_empty_string(raw_file_id, f"{label}.file_id")
        else:
            action["file_id"] = None
    else:
        action["file_id"] = non_empty_string(raw_file_id, f"{label}.file_id")

    if op == "rename":
        source_parent, _ = parent_and_name(action["from"])
        target_parent, _ = parent_and_name(action["to"])
        if source_parent != target_parent:
            raise MaterializationError(f"{label}: rename must remain in the same parent directory")
    return action


def mkdir_file_id(
    action: dict[str, Any],
    result: dict[str, Any],
    label: str,
    directory_identities: dict[str, str],
) -> str:
    """Read the separately verified directory identity required for ``mkdir``.

    Existing plans normally omit ``file_id`` for mkdir because the executor did
    not need it to issue the command.  A snapshot cannot safely invent that
    identity, so an identity-enriched ledger may provide ``created_file_id`` or
    ``verify.directory_id``.  If a plan does carry ``file_id``, the normal
    exact operation-key check already binds it to the result.
    """

    candidates = [
        action.get("file_id"),
        result.get("created_file_id"),
        result.get("directory_id"),
        result.get("verify", {}).get("directory_id") if isinstance(result.get("verify"), dict) else None,
        directory_identities.get(action["to"]),
    ]
    identities = [
        non_empty_string(value, f"{label}.mkdir directory identity")
        for value in candidates
        if value is not None
    ]
    if not identities:
        raise MaterializationError(
            f"{label}: verified mkdir has no directory file_id; refusing to invent an entity"
        )
    if len(set(identities)) != 1:
        raise MaterializationError(f"{label}: mkdir directory identity conflicts across evidence")
    return identities[0]


def load_closed_actions(
    run_dir: Path, manifest: dict[str, Any]
) -> tuple[
    list[tuple[dict[str, Any], dict[str, Any]]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Load only registered normal batches and fail closed on an open ledger."""

    batches = manifest.get("batches")
    if not isinstance(batches, list):
        raise MaterializationError("run.batches must be an array")

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    plan_hashes: list[dict[str, Any]] = []
    ledger_hashes: list[dict[str, Any]] = []
    globally_seen_action_ids: set[str] = set()
    globally_seen_keys: set[tuple[object, object, object, object, object]] = set()

    for batch_index, batch in enumerate(batches, 1):
        if not isinstance(batch, dict):
            raise MaterializationError(f"run.batches[{batch_index - 1}] must be an object")
        plan_path, plan_member = resolve_run_member(
            run_dir, batch.get("plan"), f"run.batches[{batch_index - 1}].plan"
        )
        ledger_path, ledger_member = resolve_run_member(
            run_dir, batch.get("result"), f"run.batches[{batch_index - 1}].result"
        )
        plan_rows = read_jsonl(plan_path, f"plan {plan_member}")
        ledger_rows = read_jsonl(ledger_path, f"result ledger {ledger_member}")

        actions: list[dict[str, Any]] = []
        plan_keys: set[tuple[object, object, object, object, object]] = set()
        for line_number, raw in plan_rows:
            label = f"plan {plan_member}:{line_number}"
            action = parse_operation(raw, label)
            key = operation_key(action)
            if action["action_id"] in globally_seen_action_ids:
                raise MaterializationError(f"{label}: duplicate plan action_id {action['action_id']!r}")
            if key in globally_seen_keys:
                raise MaterializationError(f"{label}: duplicate plan operation key")
            globally_seen_action_ids.add(action["action_id"])
            globally_seen_keys.add(key)
            plan_keys.add(key)
            actions.append(action)

        latest: dict[tuple[object, object, object, object, object], tuple[int, dict[str, Any]]] = {}
        for line_number, raw in ledger_rows:
            label = f"result ledger {ledger_member}:{line_number}"
            result_action = parse_operation(raw, label)
            key = operation_key(result_action)
            if key not in plan_keys:
                raise MaterializationError(
                    f"{label}: operation key is not registered by {plan_member}"
                )
            latest[key] = (line_number, raw)

        for action in actions:
            key = operation_key(action)
            terminal = latest.get(key)
            if terminal is None:
                raise MaterializationError(
                    f"plan {plan_member}: unclosed action {action['action_id']!r} has no result"
                )
            line_number, result = terminal
            status = result.get("status")
            if status not in SUCCESS_STATUSES:
                raise MaterializationError(
                    f"result ledger {ledger_member}:{line_number}: action {action['action_id']!r} "
                    f"is not materializable (latest status={status!r})"
                )
            pairs.append((action, result))

        plan_hashes.append(
            {"batch": batch_index, "path": plan_member, "sha256": sha256_file(plan_path)}
        )
        ledger_hashes.append(
            {"batch": batch_index, "path": ledger_member, "sha256": sha256_file(ledger_path)}
        )
    return pairs, plan_hashes, ledger_hashes


def run_relative_path(path: Path, run_dir: Path, label: str) -> str:
    """Return a portable run-bundle member path or reject an external input."""

    root = run_dir.resolve()
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as error:
        raise MaterializationError(f"{label} must stay inside the run directory") from error


def load_base_entities(scan_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    entities: dict[str, dict[str, Any]] = {}
    paths: dict[str, str] = {}
    for line_number, row in read_jsonl(scan_path, "base scan"):
        label = f"base scan:{line_number}"
        if "agg_files" in row or "agg_size" in row:
            raise MaterializationError(f"{label}: aggregate rows are not a complete file-level scan")
        parent = canonical_path(row.get("path"), f"{label}.path")
        name = non_empty_string(row.get("name"), f"{label}.name")
        if name in {".", ".."} or "/" in name:
            raise MaterializationError(f"{label}.name is not a single entity name")
        file_id = non_empty_string(row.get("id"), f"{label}.id")
        if not isinstance(row.get("dir"), bool):
            raise MaterializationError(f"{label}.dir must be boolean")
        if not row["dir"]:
            size = row.get("size")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise MaterializationError(f"{label}.size must be a non-negative integer for files")
        full_path = child_path(parent, name)
        if file_id in entities:
            raise MaterializationError(f"{label}: duplicate file_id {file_id!r}")
        if full_path in paths:
            raise MaterializationError(f"{label}: path conflict at {full_path!r}")
        entities[file_id] = {
            "id": file_id,
            "path": full_path,
            "dir": row["dir"],
            "row": dict(row),
        }
        paths[full_path] = file_id
    return entities, paths


def require_directory(path: str, paths: dict[str, str], entities: dict[str, dict[str, Any]], label: str) -> None:
    if path == "/":
        return
    file_id = paths.get(path)
    if file_id is None or not entities[file_id]["dir"]:
        raise MaterializationError(f"{label}: target parent is not a known directory: {path!r}")


def apply_mkdir(
    action: dict[str, Any],
    result: dict[str, Any],
    entities: dict[str, dict[str, Any]],
    paths: dict[str, str],
    directory_identities: dict[str, str],
) -> None:
    target = action["to"]
    if target in paths:
        raise MaterializationError(f"mkdir {action['action_id']!r}: path conflict at {target!r}")
    parent, name = parent_and_name(target)
    require_directory(parent, paths, entities, f"mkdir {action['action_id']!r}")
    file_id = mkdir_file_id(
        action,
        result,
        f"mkdir {action['action_id']!r}",
        directory_identities,
    )
    if file_id in entities:
        raise MaterializationError(f"mkdir {action['action_id']!r}: duplicate file_id {file_id!r}")
    row = {"path": parent, "name": name, "id": file_id, "dir": True}
    entities[file_id] = {"id": file_id, "path": target, "dir": True, "row": row}
    paths[target] = file_id


def apply_relocation(
    action: dict[str, Any], entities: dict[str, dict[str, Any]], paths: dict[str, str]
) -> None:
    source = action["from"]
    file_id = action["file_id"]
    source_id = paths.get(source)
    if source_id is None:
        raise MaterializationError(f"{action['op']} {action['action_id']!r}: source is absent: {source!r}")
    if source_id != file_id:
        raise MaterializationError(
            f"{action['op']} {action['action_id']!r}: source file_id mismatch "
            f"(expected {file_id!r}, got {source_id!r})"
        )

    source_parent, source_name = parent_and_name(source)
    if action["op"] == "mv":
        target_parent = action["to"]
        require_directory(target_parent, paths, entities, f"mv {action['action_id']!r}")
        target = child_path(target_parent, source_name)
    else:
        target = action["to"]
        target_parent, _ = parent_and_name(target)
        if target_parent != source_parent:  # parse_operation also enforces this.
            raise MaterializationError(f"rename {action['action_id']!r}: target parent changed")
        require_directory(target_parent, paths, entities, f"rename {action['action_id']!r}")

    if target == source:
        raise MaterializationError(f"{action['op']} {action['action_id']!r}: source and target are identical")
    if entities[file_id]["dir"] and path_is_within(target_parent, source):
        raise MaterializationError(f"{action['op']} {action['action_id']!r}: cannot move a directory into itself")

    moved_ids = [
        candidate_id for candidate_id, entity in entities.items()
        if path_is_within(entity["path"], source)
    ]
    replacements = {
        candidate_id: target + entities[candidate_id]["path"][len(source):]
        for candidate_id in moved_ids
    }
    if len(set(replacements.values())) != len(replacements):  # defensive; paths are already unique.
        raise MaterializationError(f"{action['op']} {action['action_id']!r}: descendant path conflict")
    moved_id_set = set(moved_ids)
    for candidate_id, destination in replacements.items():
        occupant = paths.get(destination)
        if occupant is not None and occupant not in moved_id_set:
            raise MaterializationError(
                f"{action['op']} {action['action_id']!r}: path conflict at {destination!r}"
            )

    for candidate_id in moved_ids:
        paths.pop(entities[candidate_id]["path"])
    for candidate_id, destination in replacements.items():
        entities[candidate_id]["path"] = destination
        paths[destination] = candidate_id


def apply_actions(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    entities: dict[str, dict[str, Any]],
    paths: dict[str, str],
    directory_identities: dict[str, str],
) -> None:
    for action, result in pairs:
        if action["op"] == "mkdir":
            apply_mkdir(action, result, entities, paths, directory_identities)
        else:
            apply_relocation(action, entities, paths)


def load_directory_identities(path: Path | None) -> dict[str, str]:
    """Load exact directory path/file_id evidence from shallow terminal listings."""

    if path is None:
        return {}
    identities: dict[str, str] = {}
    seen_ids: dict[str, str] = {}
    for line_number, row in read_jsonl(path, "directory identities"):
        label = f"directory identities:{line_number}"
        directory_path = canonical_path(row.get("path"), f"{label}.path")
        file_id = non_empty_string(row.get("id"), f"{label}.id")
        if row.get("dir") is not True:
            raise MaterializationError(f"{label}.dir must be true")
        previous_id = identities.get(directory_path)
        if previous_id is not None and previous_id != file_id:
            raise MaterializationError(f"{label}: path has conflicting directory identities")
        previous_path = seen_ids.get(file_id)
        if previous_path is not None and previous_path != directory_path:
            raise MaterializationError(f"{label}: file_id has conflicting directory paths")
        identities[directory_path] = file_id
        seen_ids[file_id] = directory_path
    return identities


def snapshot_rows(
    entities: dict[str, dict[str, Any]],
    paths: dict[str, str],
    target_root: str,
    target_root_file_id: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    root_id = paths.get(target_root)
    if root_id != target_root_file_id:
        raise MaterializationError(
            f"target root identity mismatch at {target_root!r}: expected {target_root_file_id!r}, got {root_id!r}"
        )
    if not entities[root_id]["dir"]:
        raise MaterializationError(f"target root is not a directory: {target_root!r}")

    selected = [entity for entity in entities.values() if path_is_within(entity["path"], target_root)]
    selected.sort(key=lambda entity: (entity["path"].casefold(), entity["path"]))
    rows: list[dict[str, Any]] = []
    files = directories = total_bytes = 0
    for entity in selected:
        parent, name = parent_and_name(entity["path"])
        row = dict(entity["row"])
        row.update({"path": parent, "name": name, "id": entity["id"], "dir": entity["dir"]})
        rows.append(row)
        if entity["dir"]:
            directories += 1
        else:
            files += 1
            total_bytes += row["size"]
    return rows, {"entities": len(rows), "files": files, "directories": directories, "bytes": total_bytes}


def materialize(
    base_scan: Path,
    run_dir: Path,
    target_root: str,
    target_root_file_id: str,
    directory_identities_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run_dir = run_dir.resolve()
    manifest_path = run_dir / "run.json"
    manifest = read_json(manifest_path, "run manifest")
    pairs, plan_hashes, ledger_hashes = load_closed_actions(run_dir, manifest)
    entities, paths = load_base_entities(base_scan)
    directory_identities = load_directory_identities(directory_identities_path)
    existing_root_identity = directory_identities.get(target_root)
    if existing_root_identity is not None and existing_root_identity != target_root_file_id:
        raise MaterializationError("target root identity conflicts with directory identity evidence")
    directory_identities[target_root] = target_root_file_id
    apply_actions(pairs, entities, paths, directory_identities)
    rows, statistics = snapshot_rows(entities, paths, target_root, target_root_file_id)
    provenance = {
        "schema_version": 1,
        "target_root": target_root,
        "target_root_file_id": target_root_file_id,
        "inputs": {
            "base_scan": {
                "path": run_relative_path(base_scan, run_dir, "base scan"),
                "sha256": sha256_file(base_scan),
            },
            "run_manifest": {"path": "run.json", "sha256": sha256_file(manifest_path)},
            "plans": plan_hashes,
            "result_ledgers": ledger_hashes,
        },
        "statistics": statistics,
    }
    if directory_identities_path is not None:
        provenance["inputs"]["directory_identities"] = {
            "path": run_relative_path(
                directory_identities_path,
                run_dir,
                "directory identities",
            ),
            "sha256": sha256_file(directory_identities_path),
        }
    return rows, provenance


def output_rows(rows: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")


def atomic_replace_many(outputs: list[tuple[Path, bytes]]) -> None:
    temporary_paths: list[tuple[Path, Path]] = []
    try:
        for destination, payload in outputs:
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
            )
            temporary = Path(temporary_name)
            temporary_paths.append((destination, temporary))
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        for destination, temporary in temporary_paths:
            os.replace(temporary, destination)
    finally:
        for _, temporary in temporary_paths:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="run bundle containing run.json")
    parser.add_argument(
        "--initial-scan", "--base-scan", dest="base_scan", type=Path,
        help="complete file-level base scan; defaults to run.files.initial_scan",
    )
    parser.add_argument("--target-root", required=True, help="final target partition root path")
    parser.add_argument(
        "--target-root-file-id", "--root-file-id", dest="target_root_file_id", required=True,
        help="expected directory file_id for --target-root",
    )
    parser.add_argument(
        "--directory-identities",
        type=Path,
        help="optional JSONL of exact terminal directory rows: path/id/dir=true",
    )
    parser.add_argument("--out", "--out-scan", dest="out_scan", required=True, type=Path)
    parser.add_argument("--out-errors", type=Path, help="defaults to <out>.errors")
    parser.add_argument("--out-provenance", type=Path, help="defaults to <out>.provenance.json")
    return parser.parse_args(argv)


def choose_base_scan(args: argparse.Namespace, run_dir: Path, manifest: dict[str, Any]) -> Path:
    if args.base_scan is not None:
        return args.base_scan.resolve()
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise MaterializationError("run.files must be an object when --initial-scan is omitted")
    path, _ = resolve_run_member(run_dir, files.get("initial_scan"), "run.files.initial_scan")
    return path


def registered_regular_inputs(run_dir: Path, manifest: dict[str, Any]) -> list[Path]:
    """Return exactly the normal-batch evidence this materializer may read."""

    batches = manifest.get("batches")
    if not isinstance(batches, list):
        raise MaterializationError("run.batches must be an array")
    paths: list[Path] = []
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict):
            raise MaterializationError(f"run.batches[{index}] must be an object")
        plan, _ = resolve_run_member(run_dir, batch.get("plan"), f"run.batches[{index}].plan")
        result, _ = resolve_run_member(run_dir, batch.get("result"), f"run.batches[{index}].result")
        paths.extend((plan, result))
    return paths


def ensure_safe_output_paths(outputs: list[Path], protected_inputs: list[Path]) -> None:
    resolved = [path.resolve() for path in outputs]
    if len(set(resolved)) != len(resolved):
        raise MaterializationError("snapshot, errors sidecar, and provenance outputs must be distinct")
    protected = {path.resolve() for path in protected_inputs}
    overlap = set(resolved) & protected
    if overlap:
        raise MaterializationError(f"output must not overwrite an input: {sorted(map(str, overlap))[0]}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        run_dir = args.run_dir.resolve()
        manifest_path = run_dir / "run.json"
        manifest = read_json(manifest_path, "run manifest")
        base_scan = choose_base_scan(args, run_dir, manifest)
        target_root = canonical_path(args.target_root, "--target-root")
        target_root_file_id = non_empty_string(args.target_root_file_id, "--target-root-file-id")
        out_scan = args.out_scan.resolve()
        out_errors = args.out_errors.resolve() if args.out_errors else Path(f"{out_scan}.errors")
        out_provenance = (
            args.out_provenance.resolve()
            if args.out_provenance else Path(f"{out_scan}.provenance.json")
        )
        ensure_safe_output_paths(
            [out_scan, out_errors, out_provenance],
            [
                base_scan,
                manifest_path,
                *registered_regular_inputs(run_dir, manifest),
                *([args.directory_identities.resolve()] if args.directory_identities else []),
            ],
        )
        rows, provenance = materialize(
            base_scan,
            run_dir,
            target_root,
            target_root_file_id,
            args.directory_identities.resolve() if args.directory_identities else None,
        )
        atomic_replace_many([
            (out_scan, output_rows(rows)),
            (out_errors, b""),
            (out_provenance, (json.dumps(provenance, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")),
        ])
    except MaterializationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "passed", "snapshot": str(out_scan), "provenance": str(out_provenance)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
