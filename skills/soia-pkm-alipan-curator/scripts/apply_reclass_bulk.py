#!/usr/bin/env python3
"""Batch executor for an approved reclassification JSONL plan.

This is deliberately a separate entry point from ``apply_reclass.py``.  It
keeps that executor's plan validation, path boundaries, ledger keys, and
single-action mkdir/rename behavior, while coalescing compatible move actions
into one ``aliyunpan mv`` call.

The default is a dry-run.  A write is considered successful only when the
source and target listings prove the terminal state; command exit codes are
not used as write evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import posixpath
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import fcntl


_SINGLE_EXECUTOR_PATH = Path(__file__).with_name("apply_reclass.py")
_SINGLE_SPEC = importlib.util.spec_from_file_location(
    "_apply_reclass_bulk_single_executor", _SINGLE_EXECUTOR_PATH
)
if _SINGLE_SPEC is None or _SINGLE_SPEC.loader is None:  # pragma: no cover
    raise ImportError(f"cannot import {_SINGLE_EXECUTOR_PATH}")
_SINGLE = importlib.util.module_from_spec(_SINGLE_SPEC)
_SINGLE_SPEC.loader.exec_module(_SINGLE)


def run_aliyunpan(command: str, drive_id: str, *paths: str) -> subprocess.CompletedProcess:
    """Run one explicit-drive CLI command.

    Keeping this wrapper local makes the bulk executor straightforward to
    mock in tests and preserves each path argument byte-for-byte, including
    repeated spaces in a filename.
    """
    args = ["aliyunpan", command, "--driveId", drive_id, *paths]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=90)
    except Exception as error:  # the single executor uses the same contract
        return subprocess.CompletedProcess(args, 255, "", repr(error))


def parse_ll(output: str) -> list[str]:
    """Parse the existing ``ll`` table without collapsing name whitespace."""
    return _SINGLE.parse_ll(output)


def ll(drive_id: str, path: str) -> tuple[bool, set[str], dict]:
    """Read one directory and return its names plus machine-readable evidence."""
    result = run_aliyunpan("ll", drive_id, path)
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    ok = result.returncode == 0 and "当前目录" in stdout
    names = set(parse_ll(stdout)) if ok else set()
    evidence = {
        "path": path,
        "returncode": result.returncode,
        "marker": "当前目录" in stdout,
        "entries": len(names),
    }
    if not ok:
        evidence["stdout"] = stdout[:200]
        evidence["stderr"] = stderr[:200]
    return ok, names, evidence


def parent_and_name(path: str) -> tuple[str, str]:
    return _SINGLE.parent_and_name(path)


def operation_key(item: dict) -> tuple:
    return _SINGLE.operation_key(item)


def load_completed(path: str | Path) -> set[tuple]:
    return _SINGLE.load_completed(path)


def load_plan(path: str | Path, roots: list[str]) -> list[dict]:
    return _SINGLE.load_plan(path, roots)


@contextmanager
def _single_executor_uses_bulk_cli() -> Iterator[None]:
    """Route the original single-action implementation through our CLI hook."""
    original_runner = _SINGLE.run_aliyunpan
    _SINGLE.run_aliyunpan = run_aliyunpan
    try:
        yield
    finally:
        _SINGLE.run_aliyunpan = original_runner


def apply_single(item: dict, drive_id: str) -> tuple[str, dict]:
    """Use the existing executor for mkdir/rename (and its verification)."""
    with _single_executor_uses_bulk_cli():
        return _SINGLE.apply_one(item, drive_id)


def _batch_key(item: dict) -> tuple[str, str]:
    source_parent, _ = parent_and_name(item["from"])
    return source_parent, posixpath.normpath(item["to"])


def _append(ledger, item: dict, status: str, verify: dict) -> None:
    entry = {
        **item,
        "status": status,
        "verify": verify,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
    ledger.flush()


def _failure(reason: str, **evidence: object) -> dict:
    return {"error": reason, **evidence}


def apply_move_batch(
    items: list[dict], drive_id: str
) -> tuple[list[tuple[dict, str, dict]], bool]:
    """Apply and verify one compatible move batch.

    The returned records are in plan order.  ``failed`` means the caller must
    stop the plan; successful records may still coexist with failed records in
    one batch when the provider partially applies a multi-source move.
    """
    source_parent, target_dir = _batch_key(items[0])

    # Exactly one source read and one target read before the write.
    source_ok, before_sources, source_before_ev = ll(drive_id, source_parent)
    target_ok, before_targets, target_before_ev = ll(drive_id, target_dir)
    before = {
        "source_parent": source_before_ev,
        "target_dir": target_before_ev,
    }

    if not source_ok or not target_ok:
        records = [
            (item, "failed", _failure("终态前置 ll 复核失败", **before))
            for item in items
        ]
        return records, True

    to_move: list[dict] = []
    records: dict[str, tuple[str, dict]] = {}
    for item in items:
        source_name = parent_and_name(item["from"])[1]
        if source_name not in before_sources and source_name in before_targets:
            records[item["action_id"]] = (
                "verified",
                {
                    "stage": "idempotent-resume",
                    "source_parent": source_before_ev,
                    "target_dir": target_before_ev,
                    "source_absent": True,
                    "target_present": True,
                    "target_name": source_name,
                },
            )
        elif source_name not in before_sources:
            records[item["action_id"]] = (
                "failed",
                _failure(
                    "SOURCE_NOT_LISTED",
                    stage="precheck",
                    source_parent=source_before_ev,
                    target_dir=target_before_ev,
                    missing_name=source_name,
                ),
            )
        elif source_name in before_targets:
            records[item["action_id"]] = (
                "failed",
                _failure(
                    "目标已存在且源仍存在",
                    stage="precheck",
                    source_parent=source_before_ev,
                    target_dir=target_before_ev,
                    source_name=source_name,
                ),
            )
        else:
            to_move.append(item)

    # Never issue a partial write when the precondition already proves a
    # missing source or a destination collision.
    if any(status == "failed" for status, _ in records.values()):
        for item in to_move:
            records[item["action_id"]] = (
                "failed",
                _failure(
                    "BATCH_ABORTED_DUE_TO_PRECHECK",
                    stage="precheck",
                    source_parent=source_before_ev,
                    target_dir=target_before_ev,
                ),
            )
        return [(item, *records[item["action_id"]]) for item in items], True

    if to_move:
        # Paths are individual argv entries; shell quoting is intentionally
        # not involved, so repeated spaces remain part of the filename.
        run_aliyunpan(
            "mv",
            drive_id,
            *(item["from"] for item in to_move),
            target_dir,
        )

        # Exactly one source read and one target read after the write.
        after_source_ok, after_sources, source_after_ev = ll(drive_id, source_parent)
        after_target_ok, after_targets, target_after_ev = ll(drive_id, target_dir)
        after = {
            "source_parent": source_after_ev,
            "target_dir": target_after_ev,
        }
        if not after_source_ok or not after_target_ok:
            results = [
                (
                    item,
                    "failed",
                    {
                        "error": "终态 ll 复核失败",
                        "stage": "terminal-ll",
                        **after,
                    },
                )
                for item in items
            ]
            return results, True
        for item in to_move:
            source_name = parent_and_name(item["from"])[1]
            source_absent = after_source_ok and source_name not in after_sources
            target_present = after_target_ok and source_name in after_targets
            if source_absent and target_present:
                records[item["action_id"]] = (
                    "verified",
                    {
                        "stage": "terminal-ll",
                        **after,
                        "source_absent": True,
                        "target_present": True,
                        "target_name": source_name,
                    },
                )
            else:
                records[item["action_id"]] = (
                    "failed",
                    {
                        "error": "终态 ll 复核失败",
                        "stage": "terminal-ll",
                        **after,
                        "source_absent": source_absent,
                        "target_present": target_present,
                        "target_name": source_name,
                    },
                )

        results = [(item, *records[item["action_id"]]) for item in items]
        return results, any(status == "failed" for _, status, _ in results)

    # All actions were already in their terminal state; no write means no
    # second pair of reads is needed.
    return [(item, *records[item["action_id"]]) for item in items], False


def _compatible_batch(plan: list[dict], start: int, completed: set[tuple], batch_size: int) -> list[dict]:
    first = plan[start]
    key = _batch_key(first)
    batch: list[dict] = []
    index = start
    while index < len(plan) and len(batch) < batch_size:
        item = plan[index]
        if item["op"] != "mv" or _batch_key(item) != key:
            break
        if operation_key(item) not in completed:
            batch.append(item)
        index += 1
    return batch


def preview(plan: list[dict], batch_size: int) -> None:
    counts = {"mkdir": 0, "mv": 0, "rename": 0}
    for index, item in enumerate(plan, 1):
        counts[item["op"]] += 1
        source = item.get("from", "-")
        print(f"[{index}] {item['op']} {source} → {item['to']} · {item['reason']}")
    print(
        f"统计: mkdir={counts['mkdir']} mv={counts['mv']} "
        f"rename={counts['rename']} total={len(plan)} batch-size={batch_size}"
    )


def execute(
    plan: list[dict],
    drive_id: str,
    ledger_path: str | Path,
    completed: set[tuple],
    batch_size: int,
) -> int:
    counts = {"verified": 0, "skipped": 0, "failed": 0, "resumed": 0}
    index = 0
    with open(ledger_path, "a", encoding="utf-8") as ledger:
        while index < len(plan):
            item = plan[index]
            if operation_key(item) in completed:
                counts["resumed"] += 1
                print(f"[{index + 1}] 已完成，--resume 跳过：{item['op']} {item.get('from', '-')} → {item['to']}")
                index += 1
                continue

            if item["op"] == "mv":
                batch = _compatible_batch(plan, index, completed, batch_size)
                if not batch:  # defensive: the current item is not completed
                    raise ValueError("无法建立 mv 批次")
                results, stop = apply_move_batch(batch, drive_id)
                for result_item, status, verify in results:
                    _append(ledger, result_item, status, verify)
                    counts[status] += 1
                print(f"[{index + 1}] mv 批次={len(batch)} target={batch[0]['to']}")
                if stop:
                    break
                index += 1
                while index < len(plan):
                    candidate = plan[index]
                    if candidate["op"] != "mv" or _batch_key(candidate) != _batch_key(batch[0]):
                        break
                    if operation_key(candidate) not in completed:
                        # It was included only if it fit the size limit.  Do
                        # not skip a compatible action that starts next batch.
                        if candidate["action_id"] in {item["action_id"] for item, _, _ in results}:
                            pass
                        else:
                            break
                    index += 1
                continue

            status, verify = apply_single(item, drive_id)
            _append(ledger, item, status, verify)
            counts[status] += 1
            print(f"[{index + 1}] {status}: {item['op']} {item.get('from', '-')} → {item['to']}")
            if status == "failed":
                break
            index += 1

    print(
        f"摘要: verified={counts['verified']} skipped={counts['skipped']} "
        f"failed={counts['failed']} resumed={counts['resumed']} ledger={ledger_path}"
    )
    return 1 if counts["failed"] else 0


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("--batch-size 必须是正整数") from error
    if number <= 0 or number > 20:
        raise argparse.ArgumentTypeError("--batch-size 必须是 1 到 20 的整数")
    return number


def parallel_limit(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("--max-parallel 必须是 1 或 2") from error
    if number not in {1, 2}:
        raise argparse.ArgumentTypeError("--max-parallel 必须是 1 或 2")
    return number


@contextmanager
def execution_slot(drive_id: str, max_parallel: int) -> Iterator[None]:
    """Limit concurrent bulk writers before any cloud write is attempted.

    ``aliyunpan`` processes share one local login/profile.  Field evidence
    shows that a third writer can make an otherwise successful ``mv``
    disappear before terminal verification, while two writers can make a
    20-item batch exceed the executor timeout and land only partially.  The
    safe default is therefore one writer; two must be explicitly requested
    together with smaller batches and acceptance of resumable partial work.
    The drive id is hashed so local state does not leak account identifiers.
    """
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    lock_dir = state_home / "soia-pkm-alipan-curator" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    drive_key = hashlib.sha256(drive_id.encode("utf-8")).hexdigest()[:16]
    handles = []
    acquired = []
    try:
        for slot in range(1, 3):
            handle = (lock_dir / f"bulk-{drive_key}-{slot}.lock").open("a+", encoding="utf-8")
            handles.append(handle)
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            acquired.append(handle)
            if max_parallel == 2:
                break
        required_slots = 2 if max_parallel == 1 else 1
        if len(acquired) != required_slots:
            raise RuntimeError(
                "同一云盘已有批量写入进程，当前并发模式不兼容；请等待完成后使用 --resume，"
                "不要提高并发规避保护"
            )
        yield
    finally:
        for handle in acquired:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        for handle in handles:
            handle.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="迁移计划 JSONL")
    ap.add_argument("--driveId", required=True, help="阿里云盘 driveId")
    ap.add_argument("--root", required=True, help="允许写入的云盘根边界")
    ap.add_argument("--archive-root", help="可选归档根边界")
    ap.add_argument("--ledger", required=True, help="执行账本 JSONL")
    ap.add_argument("--execute", action="store_true", help="真正执行；默认仅 dry-run")
    ap.add_argument("--resume", action="store_true", help="跳过历史已 verified/completed 动作")
    ap.add_argument(
        "--batch-size",
        type=positive_int,
        default=20,
        help="每个兼容 mv 批次的最大动作数（1 到 20）",
    )
    ap.add_argument(
        "--max-parallel",
        type=parallel_limit,
        default=1,
        help="同一 drive 允许的批量写入进程数（1 或 2；默认 1；双路须显式开启）",
    )
    args = ap.parse_args()

    if args.max_parallel == 2 and args.batch_size > 10:
        ap.error("--max-parallel 2 时 --batch-size 不能超过 10；大批次可能在超时前只完成一部分")

    try:
        roots = [posixpath.normpath(args.root)]
        if args.archive_root:
            roots.append(posixpath.normpath(args.archive_root))
        if any(not root.startswith("/") or root == "/" for root in roots):
            raise ValueError("--root/--archive-root 必须是非根目录的绝对云盘路径")
        if len(set(roots)) != len(roots):
            raise ValueError("--root 与 --archive-root 不能相同")
        plan = load_plan(args.plan, roots)
    except ValueError as error:
        ap.error(str(error))

    if not args.execute:
        preview(plan, args.batch_size)
        return

    try:
        completed = load_completed(args.ledger) if args.resume else set()
        with execution_slot(args.driveId, args.max_parallel):
            returncode = execute(plan, args.driveId, args.ledger, completed, args.batch_size)
    except (OSError, RuntimeError, ValueError) as error:
        ap.error(str(error))
    if returncode:
        raise SystemExit(returncode)


if __name__ == "__main__":
    main()
