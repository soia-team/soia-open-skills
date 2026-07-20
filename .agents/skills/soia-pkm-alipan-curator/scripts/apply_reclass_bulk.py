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
import sys
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
preflight_gate = _SINGLE.preflight_gate
RUNNER_ENV = "SOIA_ALIPAN_RUNNER"


def alipan_runner_path() -> Path | None:
    """Locate the atomic skill's environment-loading runner without user paths."""
    override = os.environ.get(RUNNER_ENV)
    candidate = Path(override).expanduser() if override else (
        Path(__file__).resolve().parents[2] / "soia-pkm-alipan-drive-ops" / "scripts" / "run_with_env.py"
    )
    return candidate if candidate.is_file() else None


def require_preflight(
    run_dir: str | Path,
    plan_path: str | Path,
    drive_id: str | None = None,
) -> dict:
    """Fail closed unless the current run evidence covers this exact plan."""
    options = {"plan_path": Path(plan_path)}
    if drive_id is not None:
        options["drive_id"] = drive_id
    result = preflight_gate.verify_preflight_gate(Path(run_dir), **options)
    if result.get("status") == "passed":
        return result
    violations = result.get("violations")
    kinds = sorted({
        str(item.get("kind", "unknown"))
        for item in violations if isinstance(item, dict)
    }) if isinstance(violations, list) else ["unknown"]
    raise ValueError("preflight 执行门禁失败：" + ", ".join(kinds or ["unknown"]))


def run_aliyunpan(command: str, drive_id: str, *paths: str) -> subprocess.CompletedProcess:
    """Run one explicit-drive CLI command.

    Keeping this wrapper local makes the bulk executor straightforward to
    mock in tests and preserves each path argument byte-for-byte, including
    repeated spaces in a filename.
    """
    runner = alipan_runner_path()
    if runner is None:
        return subprocess.CompletedProcess([], 127, "", "RUNNER_UNAVAILABLE")
    args = [sys.executable, str(runner), "--", "aliyunpan", command, "--driveId", drive_id, *paths]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=90)
    except Exception:  # do not expose runner/private-env failure details
        return subprocess.CompletedProcess(args, 255, "", "RUNNER_EXECUTION_FAILED")


def parse_ll(output: str) -> dict[str, str]:
    """Parse the existing ``ll`` table into ``name -> file_id`` mappings."""
    return _SINGLE.parse_ll(output)


def ll(drive_id: str, path: str) -> tuple[bool, dict[str, str], dict]:
    """Read one directory and return its ``name -> file_id`` evidence."""
    result = run_aliyunpan("ll", drive_id, path)
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    ok = result.returncode == 0 and "当前目录" in stdout
    entries = parse_ll(stdout) if ok else {}
    evidence = {
        "path": path,
        "returncode": result.returncode,
        "marker": "当前目录" in stdout,
        "entries": len(entries),
    }
    if not ok:
        evidence["stdout"] = stdout[:200]
        evidence["stderr"] = stderr[:200]
    return ok, entries, evidence


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


def apply_single(
    item: dict,
    drive_id: str,
    throttle_ms: int = _SINGLE.DEFAULT_THROTTLE_MS,
    rate_limit_event=None,
) -> tuple[str, dict]:
    """Use the existing executor for mkdir/rename (and its verification)."""
    with _single_executor_uses_bulk_cli():
        return _SINGLE.apply_one(item, drive_id, throttle_ms, rate_limit_event)


def run_write_with_backoff(command: str, drive_id: str, *paths: str, throttle_ms: int, event_sink=None):
    """Reuse the single executor's canonical write throttle and retry policy."""
    with _single_executor_uses_bulk_cli():
        return _SINGLE.run_write_with_backoff(
            command, drive_id, *paths, throttle_ms=throttle_ms, event_sink=event_sink
        )


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
    items: list[dict],
    drive_id: str,
    throttle_ms: int = _SINGLE.DEFAULT_THROTTLE_MS,
    rate_limit_event=None,
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
        expected_file_id = item["file_id"]
        source_file_id = before_sources.get(source_name)
        target_file_id = before_targets.get(source_name)
        if source_file_id is None and target_file_id == expected_file_id:
            records[item["action_id"]] = (
                "verified",
                {
                    "stage": "idempotent-resume",
                    "source_parent": source_before_ev,
                    "target_dir": target_before_ev,
                    "source_absent": True,
                    "target_present": True,
                    "target_name": source_name,
                    "expected_file_id": expected_file_id,
                    "target_file_id": target_file_id,
                },
            )
        elif source_file_id is None and target_file_id is not None:
            records[item["action_id"]] = (
                "failed",
                _failure(
                    "TARGET_FILE_ID_MISMATCH",
                    stage="precheck",
                    source_parent=source_before_ev,
                    target_dir=target_before_ev,
                    target_name=source_name,
                    expected_file_id=expected_file_id,
                    target_file_id=target_file_id,
                ),
            )
        elif source_file_id is None:
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
        elif source_file_id != expected_file_id:
            records[item["action_id"]] = (
                "failed",
                _failure(
                    "SOURCE_FILE_ID_MISMATCH",
                    stage="precheck",
                    source_parent=source_before_ev,
                    target_dir=target_before_ev,
                    source_name=source_name,
                    expected_file_id=expected_file_id,
                    source_file_id=source_file_id,
                ),
            )
        elif target_file_id is not None:
            records[item["action_id"]] = (
                "failed",
                _failure(
                    "TARGET_ALREADY_PRESENT",
                    stage="precheck",
                    source_parent=source_before_ev,
                    target_dir=target_before_ev,
                    target_name=source_name,
                    expected_file_id=expected_file_id,
                    target_file_id=target_file_id,
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
        _, rate_limit_failure = run_write_with_backoff(
            "mv",
            drive_id,
            *(item["from"] for item in to_move),
            target_dir,
            throttle_ms=throttle_ms,
            event_sink=rate_limit_event,
        )
        if rate_limit_failure:
            results = [(item, "failed", rate_limit_failure) for item in items]
            return results, True

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
            expected_file_id = item["file_id"]
            source_file_id = after_sources.get(source_name)
            target_file_id = after_targets.get(source_name)
            source_absent = after_source_ok and source_file_id is None
            target_present = after_target_ok and target_file_id == expected_file_id
            if source_absent and target_present:
                records[item["action_id"]] = (
                    "verified",
                    {
                        "stage": "terminal-ll",
                        **after,
                        "source_absent": True,
                        "target_present": True,
                        "target_name": source_name,
                        "expected_file_id": expected_file_id,
                        "target_file_id": target_file_id,
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
                        "expected_file_id": expected_file_id,
                        "source_file_id": source_file_id,
                        "target_file_id": target_file_id,
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
    throttle_ms: int = _SINGLE.DEFAULT_THROTTLE_MS,
) -> int:
    counts = {"verified": 0, "skipped": 0, "failed": 0, "resumed": 0}
    index = 0
    with open(ledger_path, "a", encoding="utf-8") as ledger:
        def record_rate_limit(event: dict) -> None:
            ledger.write(json.dumps(event, ensure_ascii=False) + "\n")
            ledger.flush()

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
                results, stop = apply_move_batch(batch, drive_id, throttle_ms, record_rate_limit)
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

            status, verify = apply_single(item, drive_id, throttle_ms, record_rate_limit)
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
        raise argparse.ArgumentTypeError("--max-parallel 只能是 1（云盘写入单写者硬门禁）") from error
    if number != 1:
        raise argparse.ArgumentTypeError("--max-parallel 只能是 1（云盘写入单写者硬门禁）")
    return number


@contextmanager
def execution_slot(drive_id: str, max_parallel: int) -> Iterator[None]:
    """Acquire the one and only bulk-writer slot before any cloud write."""
    if max_parallel != 1:
        raise ValueError("--max-parallel 只能是 1（云盘写入单写者硬门禁）")
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    lock_dir = state_home / "soia-pkm-alipan-curator" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    drive_key = hashlib.sha256(drive_id.encode("utf-8")).hexdigest()[:16]
    handle = None
    try:
        handle = (lock_dir / f"bulk-{drive_key}.lock").open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(
                "同一云盘已有批量写入进程；请等待完成后使用 --resume，不要并行写入"
            ) from error
        yield
    finally:
        if handle is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="迁移计划 JSONL")
    ap.add_argument("--driveId", required=True, help="阿里云盘 driveId")
    ap.add_argument("--root", required=True, help="允许写入的云盘根边界")
    ap.add_argument("--archive-root", help="可选归档根边界")
    ap.add_argument("--ledger", required=True, help="执行账本 JSONL")
    ap.add_argument("--run-dir", help="运行包目录；--execute 时必需，dry-run 提供时同样校验")
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
        help="固定为 1；云盘写入单写者硬门禁",
    )
    ap.add_argument(
        "--throttle-ms", type=_SINGLE.nonnegative_int, default=_SINGLE.DEFAULT_THROTTLE_MS,
        help="每次 mkdir/mv/rename 云盘写调用后的节流毫秒数（默认 2000；0 关闭）",
    )
    args = ap.parse_args()

    try:
        roots = [posixpath.normpath(args.root)]
        if args.archive_root:
            roots.append(posixpath.normpath(args.archive_root))
        if any(not root.startswith("/") or root == "/" for root in roots):
            raise ValueError("--root/--archive-root 必须是非根目录的绝对云盘路径")
        if len(set(roots)) != len(roots):
            raise ValueError("--root 与 --archive-root 不能相同")
        plan = load_plan(args.plan, roots)
        if args.execute and not args.run_dir:
            raise ValueError("--execute 必须提供 --run-dir")
        if args.run_dir and not args.execute:
            require_preflight(args.run_dir, args.plan, args.driveId)
    except ValueError as error:
        ap.error(str(error))

    if not args.execute:
        preview(plan, args.batch_size)
        return

    try:
        completed = load_completed(args.ledger) if args.resume else set()
        with execution_slot(args.driveId, args.max_parallel):
            require_preflight(args.run_dir, args.plan, args.driveId)
            returncode = execute(
                plan, args.driveId, args.ledger, completed, args.batch_size, args.throttle_ms
            )
    except (OSError, RuntimeError, ValueError) as error:
        ap.error(str(error))
    if returncode:
        raise SystemExit(returncode)


if __name__ == "__main__":
    main()
