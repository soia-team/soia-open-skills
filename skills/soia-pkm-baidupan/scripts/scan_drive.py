#!/usr/bin/env python3
"""Read-only Baidu Netdisk DFS scan using the official ``bdpan`` CLI.

The scanner only invokes ``bdpan ls --json``. Provider paths are deliberately
not copied into the output: rows use a virtual root (``/``), while recursive
calls use paths relative to the official ``/apps/bdpan/`` application root.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path, PurePosixPath

from baidupan_env import configured_binary, load_private_env

load_private_env(required=False)


def normalize_virtual_path(path: str) -> str:
    """Normalize a user-facing virtual path and reject traversal."""
    value = str(path).strip()
    if not value:
        return "/"
    if "~" in value or any(part == ".." for part in value.split("/")):
        raise ValueError("remote path must not contain '~' or '..'")
    return "/" + value.strip("/") if value.strip("/") else "/"


def command_path(path: str) -> str:
    """Convert a virtual path to the relative path accepted by bdpan."""
    normalized = normalize_virtual_path(path)
    return normalized.lstrip("/")


def join_remote(parent: str, name: str) -> str:
    if parent == "/":
        return "/" + name
    return parent.rstrip("/") + "/" + name


def _as_bool(value: object) -> bool:
    return value in (True, 1, "1", "true", "True")


def _first(entry: dict[str, object], *keys: str) -> object:
    for key in keys:
        if key in entry and entry[key] is not None:
            return entry[key]
    return None


def _as_size(value: object, is_dir: bool) -> int | None:
    if is_dir or value in (None, ""):
        return None if is_dir else 0
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid size in bdpan JSON: {value!r}") from exc


def parse_json_output(output: str, parent: str) -> list[dict[str, object]]:
    """Parse official bdpan JSON and build paths from the recursion parent.

    The official output includes a display path such as ``我的应用数据/...``.
    It is intentionally ignored for command construction so a display-path
    change cannot escape the virtual root or be passed back as a provider path.
    """
    payload = json.loads(output)
    if isinstance(payload, dict):
        payload = payload.get("list", payload.get("entries", []))
    if not isinstance(payload, list):
        raise ValueError("bdpan ls --json did not return an array")

    normalized_parent = normalize_virtual_path(parent)
    rows: list[dict[str, object]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("bdpan JSON list contains a non-object entry")
        name = str(_first(entry, "server_filename", "Name", "name") or "")
        if not name or "/" in name or name in {".", ".."}:
            raise ValueError(f"bdpan JSON entry has invalid file name: {name!r}")
        is_dir = _as_bool(_first(entry, "isdir", "IsDir", "dir") or False)
        item_path = join_remote(normalized_parent, name)
        item_parent = str(PurePosixPath(item_path).parent)
        if item_parent == ".":
            item_parent = "/"
        raw_id = _first(entry, "fs_id", "FsId", "id")
        rows.append(
            {
                "path": item_parent,
                "name": name,
                "id": str(raw_id) if raw_id is not None else None,
                "dir": is_dir,
                "size": _as_size(_first(entry, "size", "Size"), is_dir),
                "sha1": _first(entry, "sha1", "Sha1"),
                "md5": _first(entry, "md5", "Md5"),
                "mtime": _first(entry, "server_mtime", "Modified", "mtime"),
                "_remote_path": item_path,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True, dest="roots")
    parser.add_argument("--out", required=True)
    parser.add_argument("--binary", default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-descend", action="append", default=[])
    args = parser.parse_args()

    if args.workers < 1 or args.attempts < 1 or args.timeout < 1:
        parser.error("--workers, --attempts and --timeout must be positive")

    try:
        roots = [normalize_virtual_path(root) for root in args.roots]
        binary = args.binary or configured_binary()
    except ValueError as exc:
        parser.error(str(exc))

    error_path = args.out + ".errors"
    progress_path = args.out + ".progress"
    done_path = args.out + ".done"
    done: set[str] = set()
    if args.resume and os.path.exists(done_path):
        with open(done_path, encoding="utf-8") as stream:
            done.update(line.strip() for line in stream if line.strip())

    # Rebuild the scan frontier from the existing JSONL: directories that were
    # discovered (emitted by a parent listing) but never themselves listed
    # (absent from the done file). Without this, resume silently drops whole
    # subtrees whose parent finished but which were still queued when the
    # previous run was interrupted.
    frontier: set[str] = set()
    if args.resume and os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    # A torn write implies its parent dir never reached the
                    # done file, so that parent will be rescanned anyway.
                    continue
                if not isinstance(row, dict) or not row.get("dir"):
                    continue
                name = str(row.get("name") or "")
                if not name or name in args.no_descend:
                    continue
                remote_path = join_remote(str(row.get("path") or "/"), name)
                if remote_path not in done:
                    frontier.add(remote_path)

    lock = threading.Lock()
    output = open(args.out, "a", encoding="utf-8")
    errors = open(error_path, "a", encoding="utf-8")
    completed = open(done_path, "a", encoding="utf-8")
    tasks: queue.Queue[str] = queue.Queue()
    counts = {"dirs": 0, "files": 0, "errors": 0, "calls": 0}

    def emit(row: dict[str, object]) -> None:
        row.pop("_remote_path", None)
        with lock:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()

    def report_scanned(path: str) -> None:
        with lock:
            completed.write(path + "\n")
            completed.flush()

    def log_error(message: str) -> None:
        with lock:
            errors.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] {message}\n")
            errors.flush()
            counts["errors"] += 1

    def list_dir(path: str) -> str | None:
        last = "unknown"
        relative = command_path(path)
        if Path(binary).name == "baidupan-cli":
            command = [binary, "--json", "ls"]
            if relative:
                command.append(relative)
        else:
            command = [binary, "ls"]
            if relative:
                command.append(relative)
            command.append("--json")
        for attempt in range(1, args.attempts + 1):
            with lock:
                counts["calls"] += 1
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout,
                    check=False,
                )
                if result.returncode == 0:
                    return result.stdout
                last = f"rc={result.returncode} stderr={result.stderr[:240]!r}"
            except (OSError, subprocess.TimeoutExpired) as exc:
                last = repr(exc)
            if attempt < args.attempts:
                time.sleep(1.5 * attempt)
        log_error(f"LIST_FAIL {path!r} {last}")
        return None

    def worker() -> None:
        while True:
            try:
                path = tasks.get(timeout=2)
            except queue.Empty:
                return
            if path in done:
                tasks.task_done()
                continue
            try:
                with lock:
                    with open(progress_path, "w", encoding="utf-8") as progress:
                        progress.write(
                            f"calls={counts['calls']} dirs={counts['dirs']} files={counts['files']} "
                            f"errors={counts['errors']} queue={tasks.qsize()} current={path}\n"
                        )
                raw = list_dir(path)
                if raw is None:
                    continue
                try:
                    rows = parse_json_output(raw, path)
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    log_error(f"PARSE_FAIL {path!r} {exc}")
                    continue
                for row in rows:
                    remote_path = str(row["_remote_path"])
                    is_dir = bool(row["dir"])
                    emit(row)
                    if is_dir:
                        with lock:
                            counts["dirs"] += 1
                        if row["name"] in args.no_descend or remote_path in done:
                            continue
                        tasks.put(remote_path)
                    else:
                        with lock:
                            counts["files"] += 1
                report_scanned(path)
            finally:
                tasks.task_done()

    seeds = {root for root in roots if root not in done} | frontier
    for seed in sorted(seeds):
        tasks.put(seed)
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(args.workers)]
    for thread in threads:
        thread.start()
    tasks.join()
    output.close()
    errors.close()
    completed.close()
    print(
        f"DONE dirs={counts['dirs']} files={counts['files']} "
        f"errors={counts['errors']} calls={counts['calls']}"
    )
    return 0 if counts["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
