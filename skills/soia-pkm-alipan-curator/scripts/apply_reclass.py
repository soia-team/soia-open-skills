#!/usr/bin/env python3
"""apply_reclass.py — 按 JSONL 计划执行云盘 mkdir/mv/rename，并逐条复核记账。

默认只预演；`--execute` 才写云盘。所有终态以独立 `aliyunpan ll` 复核为准，
失败立即停止；`--resume` 按账本中 completed 条目断点续跑。

用法：
  apply_reclass.py --plan plan.jsonl --driveId ID --root /目标分区 --ledger result.jsonl
                   [--archive-root /归档分区]
                   [--execute] [--resume]

计划每行：{"action_id":"B10-001","op":"mkdir|mv|rename","from":"源全路径","to":"目标路径","reason":"原因","file_id":"来源实体 ID"}
其中 `mv`/`rename` 必须带 file_id；执行器在写前、写后和断点恢复时都用它核验实体身份。
仅允许 `--root` 和可选 `--archive-root` 边界内的非删除操作；公共 skill 不内置用户目录。
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


OPS = {"mkdir", "mv", "rename"}
RUNNER_ENV = "SOIA_ALIPAN_RUNNER"

_PREFLIGHT_GATE_PATH = Path(__file__).with_name("preflight_gate.py")
_PREFLIGHT_GATE_SPEC = importlib.util.spec_from_file_location(
    "_apply_reclass_preflight_gate", _PREFLIGHT_GATE_PATH
)
if _PREFLIGHT_GATE_SPEC is None or _PREFLIGHT_GATE_SPEC.loader is None:  # pragma: no cover
    raise ImportError(f"cannot import {_PREFLIGHT_GATE_PATH}")
preflight_gate = importlib.util.module_from_spec(_PREFLIGHT_GATE_SPEC)
_PREFLIGHT_GATE_SPEC.loader.exec_module(preflight_gate)


def alipan_runner_path():
    """Locate the atomic skill's environment-loading runner without user paths."""
    override = os.environ.get(RUNNER_ENV)
    candidate = Path(override).expanduser() if override else (
        Path(__file__).resolve().parents[2] / "soia-pkm-alipan" / "scripts" / "run_with_env.py"
    )
    return candidate if candidate.is_file() else None


def require_preflight(run_dir, plan_path, drive_id=None):
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


@contextmanager
def execution_slot(drive_id: str) -> Iterator[None]:
    """Use the bulk executor's drive-level lock for every cloud write path."""
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


def run_aliyunpan(command, drive_id, *paths):
    """Run aliyunpan only through the atomic skill's private-env runner."""
    runner = alipan_runner_path()
    if runner is None:
        return subprocess.CompletedProcess([], 127, "", "RUNNER_UNAVAILABLE")
    args = [sys.executable, str(runner), "--", "aliyunpan", command, "--driveId", drive_id, *paths]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=90)
    except Exception:
        # Never expose exception text: argv can contain user paths and the
        # runner may load private configuration.
        return subprocess.CompletedProcess(args, 255, "", "RUNNER_EXECUTION_FAILED")


def parse_ll(output):
    """按 scan_drive.py 的 ll 表格规则提取 ``name -> file_id``。"""
    entries = {}
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("当前目录") or line.startswith("----"):
            continue
        if "总:" in line and "文件总数" in line:
            continue
        # aliyunpan ll 的名称是最后一列，名称本身可能包含连续空格。
        # 只切前九个固定字段，不能用 ``\s{2,}`` 拆整行，否则会改写名称。
        parts = line.split(None, 9)
        if not parts or parts[0] == "#":
            continue
        try:
            int(parts[0])
        except ValueError:
            continue
        if len(parts) < 10:
            continue
        name = parts[9]
        entries[name[:-1] if name.endswith("/") else name] = parts[1]
    return entries


def ll(drive_id, path):
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


def inside_root(path, root):
    root = posixpath.normpath(root)
    normalized = posixpath.normpath(path)
    raw_inside = path == root or path.startswith(root + "/")
    normalized_inside = normalized == root or normalized.startswith(root + "/")
    return raw_inside and normalized_inside


def parent_and_name(path):
    clean = path.rstrip("/") or "/"
    return posixpath.dirname(clean) or "/", posixpath.basename(clean)


def load_plan(path, roots):
    plan = []
    errors = []
    action_ids = set()
    try:
        source = open(path, encoding="utf-8")
    except OSError as error:
        raise ValueError(f"无法读取计划：{error}") from error
    with source:
        for line_no, raw in enumerate(source, 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as error:
                errors.append(f"第 {line_no} 行 JSON 无效：{error.msg}")
                continue
            if not isinstance(item, dict):
                errors.append(f"第 {line_no} 行必须是 JSON 对象")
                continue
            op = item.get("op")
            if op not in OPS:
                errors.append(f"第 {line_no} 行 op={op!r} 不允许，仅支持 mkdir/mv/rename")
                continue
            reason = item.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"第 {line_no} 行 reason 必须是非空字符串")
            action_id = item.get("action_id")
            if not isinstance(action_id, str) or not action_id.strip():
                errors.append(f"第 {line_no} 行 action_id 必须是非空字符串")
            elif action_id in action_ids:
                errors.append(f"第 {line_no} 行 action_id 重复：{action_id}")
            else:
                action_ids.add(action_id)
            required = ["to"] if op == "mkdir" else ["from", "to"]
            for field in required:
                if not isinstance(item.get(field), str) or not item[field]:
                    errors.append(f"第 {line_no} 行 {op} 缺少字符串字段 {field}")
            if op == "mkdir" and "from" in item:
                errors.append(f"第 {line_no} 行 mkdir 不应包含 from")
            if op != "mkdir" and (not isinstance(item.get("file_id"), str) or not item["file_id"].strip()):
                errors.append(f"第 {line_no} 行 {op} 缺少非空 file_id；身份校验不能降级")
            paths = [item.get("to")]
            if op != "mkdir":
                paths.insert(0, item.get("from"))
            for field, value in zip(required, paths):
                if isinstance(value, str) and value and not any(inside_root(value, root) for root in roots):
                    errors.append(f"第 {line_no} 行 {field} 越界：{value}")
            if op == "rename" and all(isinstance(item.get(k), str) and item[k] for k in ("from", "to")):
                if parent_and_name(item["from"])[0] != parent_and_name(item["to"])[0]:
                    errors.append(f"第 {line_no} 行 rename 的 from/to 必须在同一父目录")
            if not any(error.startswith(f"第 {line_no} 行") for error in errors):
                record = {"action_id": action_id, "op": op, "to": item["to"], "reason": reason}
                if op != "mkdir":
                    record["from"] = item["from"]
                    record["file_id"] = item["file_id"].strip()
                plan.append(record)
    if errors:
        raise ValueError("计划校验失败：\n" + "\n".join(errors))
    return plan


def operation_key(item):
    """Use the planned entity identity as part of the resume key."""
    return item.get("action_id"), item.get("op"), item.get("from"), item.get("to"), item.get("file_id")


def load_completed(path):
    latest = {}
    try:
        source = open(path, encoding="utf-8")
    except FileNotFoundError:
        return set()
    except OSError as error:
        raise ValueError(f"无法读取账本：{error}") from error
    with source:
        for line_no, raw in enumerate(source, 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"账本第 {line_no} 行 JSON 无效：{error.msg}") from error
            if isinstance(item, dict):
                latest[operation_key(item)] = item.get("status")
    return {key for key, status in latest.items() if status in {"verified", "completed"}}


def verify_mkdir(item, drive_id):
    target_ok, _, target_ev = ll(drive_id, item["to"])
    verify = {"target": target_ev, "target_exists": target_ok}
    if target_ok:
        return True, verify
    parent, name = parent_and_name(item["to"])
    parent_ok, names, parent_ev = ll(drive_id, parent)
    verify.update({"parent": parent_ev, "target_name": name, "target_in_parent": parent_ok and name in names})
    return verify["target_in_parent"], verify


def verify_mv(item, drive_id):
    source_parent, source_name = parent_and_name(item["from"])
    target_ok, target_entries, target_ev = ll(drive_id, item["to"])
    source_ok, source_entries, source_ev = ll(drive_id, source_parent)
    target_file_id = target_entries.get(source_name)
    verify = {
        "target_dir": target_ev,
        "source_parent": source_ev,
        "target_name": source_name,
        "expected_file_id": item["file_id"],
        "target_file_id": target_file_id,
        "target_present": target_ok and target_file_id == item["file_id"],
        "source_absent": source_ok and source_name not in source_entries,
    }
    return verify["target_present"] and verify["source_absent"], verify


def verify_rename(item, drive_id):
    parent, old_name = parent_and_name(item["from"])
    _, new_name = parent_and_name(item["to"])
    parent_ok, entries, parent_ev = ll(drive_id, parent)
    target_file_id = entries.get(new_name)
    verify = {
        "parent": parent_ev,
        "old_name": old_name,
        "new_name": new_name,
        "expected_file_id": item["file_id"],
        "target_file_id": target_file_id,
        "new_present": parent_ok and target_file_id == item["file_id"],
        "old_absent": parent_ok and old_name not in entries,
    }
    return verify["new_present"] and verify["old_absent"], verify


def apply_one(item, drive_id):
    precheck = None
    if item["op"] in {"mv", "rename"}:
        source_parent, source_name = parent_and_name(item["from"])
        pre_ok, source_entries, precheck = ll(drive_id, source_parent)
        if not pre_ok:
            return "skipped", {"stage": "precheck", "error": "LIST_FAIL", "ll": precheck}
        expected_file_id = item["file_id"]
        source_file_id = source_entries.get(source_name)
        if source_file_id is not None and source_file_id != expected_file_id:
            return "failed", {
                "stage": "precheck",
                "error": "SOURCE_FILE_ID_MISMATCH",
                "ll": precheck,
                "source_name": source_name,
                "expected_file_id": expected_file_id,
                "source_file_id": source_file_id,
            }

        if item["op"] == "mv":
            target_parent, target_name = item["to"], source_name
            target_ok, target_entries, target_ev = ll(drive_id, target_parent)
        else:
            target_parent, target_name = source_parent, parent_and_name(item["to"])[1]
            target_ok, target_entries, target_ev = pre_ok, source_entries, precheck
        if not target_ok:
            return "skipped", {"stage": "precheck", "error": "LIST_FAIL", "ll": target_ev}
        target_file_id = target_entries.get(target_name)

        if source_file_id is None:
            if target_file_id == expected_file_id:
                return "verified", {
                    "stage": "idempotent-resume",
                    "source_parent": precheck,
                    "target_dir": target_ev,
                    "target_name": target_name,
                    "expected_file_id": expected_file_id,
                    "target_file_id": target_file_id,
                    "source_absent": True,
                    "target_present": True,
                }
            if target_file_id is not None:
                return "failed", {
                    "stage": "precheck",
                    "error": "TARGET_FILE_ID_MISMATCH",
                    "source_parent": precheck,
                    "target_dir": target_ev,
                    "target_name": target_name,
                    "expected_file_id": expected_file_id,
                    "target_file_id": target_file_id,
                }
            return "skipped", {
                "stage": "precheck",
                "error": "SOURCE_NOT_LISTED",
                "ll": precheck,
                "missing_name": source_name,
            }

        if target_file_id is not None:
            return "failed", {
                "stage": "precheck",
                "error": "TARGET_ALREADY_PRESENT",
                "source_parent": precheck,
                "target_dir": target_ev,
                "target_name": target_name,
                "expected_file_id": expected_file_id,
                "target_file_id": target_file_id,
            }

    paths = [item["to"]] if item["op"] == "mkdir" else [item["from"], item["to"]]
    run_aliyunpan(item["op"], drive_id, *paths)  # 写命令返回码不作为成功证据
    if item["op"] == "mkdir":
        ok, verify = verify_mkdir(item, drive_id)
    elif item["op"] == "mv":
        ok, verify = verify_mv(item, drive_id)
    else:
        ok, verify = verify_rename(item, drive_id)
    if precheck is not None:
        verify["precheck"] = precheck
    if not ok:
        verify["error"] = "终态 ll 复核失败"
    return ("verified" if ok else "failed"), verify


def preview(plan):
    counts = {op: 0 for op in sorted(OPS)}
    for index, item in enumerate(plan, 1):
        counts[item["op"]] += 1
        source = item.get("from", "-")
        print(f"[{index}] {item['op']} {source} → {item['to']} · {item['reason']}")
    print(
        f"统计: mkdir={counts['mkdir']} mv={counts['mv']} "
        f"rename={counts['rename']} total={len(plan)}"
    )


def execute(plan, drive_id, ledger_path, completed):
    counts = {"verified": 0, "skipped": 0, "failed": 0, "resumed": 0}
    with open(ledger_path, "a", encoding="utf-8") as ledger:
        for index, item in enumerate(plan, 1):
            if operation_key(item) in completed:
                counts["resumed"] += 1
                print(f"[{index}] 已完成，--resume 跳过：{item['op']} {item.get('from', '-')} → {item['to']}")
                continue
            status, verify = apply_one(item, drive_id)
            entry = {**item, "status": status, "verify": verify, "ts": datetime.now(timezone.utc).isoformat()}
            ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
            ledger.flush()
            counts[status] += 1
            if status == "skipped":
                print(f"[{index}] 警告：源路径预检 {verify['error']}，已降级跳过")
            else:
                print(f"[{index}] {status}: {item['op']} {item.get('from', '-')} → {item['to']}")
            if status == "failed":
                break
    print(
        f"摘要: verified={counts['verified']} skipped={counts['skipped']} "
        f"failed={counts['failed']} resumed={counts['resumed']} ledger={ledger_path}"
    )
    return 1 if counts["failed"] else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="迁移计划 JSONL")
    ap.add_argument("--driveId", required=True, help="阿里云盘 driveId")
    ap.add_argument("--root", required=True, help="允许写入的云盘根边界")
    ap.add_argument("--archive-root", help="可选归档根边界；用于把不确定内容移出业务区")
    ap.add_argument("--ledger", required=True, help="执行账本 JSONL")
    ap.add_argument("--run-dir", help="运行包目录；--execute 时必需，dry-run 提供时同样校验")
    ap.add_argument("--execute", action="store_true", help="真正执行；默认仅 dry-run")
    ap.add_argument("--resume", action="store_true", help="跳过账本中已 verified/completed 的条目，并识别已落盘的歧义写入")
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
        preview(plan)
        return
    try:
        completed = load_completed(args.ledger) if args.resume else set()
        with execution_slot(args.driveId):
            require_preflight(args.run_dir, args.plan, args.driveId)
            returncode = execute(plan, args.driveId, args.ledger, completed)
    except (OSError, RuntimeError, ValueError) as error:
        ap.error(str(error))
    if returncode:
        raise SystemExit(returncode)


if __name__ == "__main__":
    main()
