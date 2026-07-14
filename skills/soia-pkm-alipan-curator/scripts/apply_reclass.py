#!/usr/bin/env python3
"""apply_reclass.py — 按 JSONL 计划执行云盘 mkdir/mv/rename，并逐条复核记账。

默认只预演；`--execute` 才写云盘。所有终态以独立 `aliyunpan ll` 复核为准，
失败立即停止；`--resume` 按账本中 completed 条目断点续跑。

用法：
  apply_reclass.py --plan plan.jsonl --driveId ID --root /目标分区 --ledger result.jsonl
                   [--archive-root /归档分区]
                   [--execute] [--resume]

计划每行：{"action_id":"B10-001","op":"mkdir|mv|rename","from":"源全路径","to":"目标路径","reason":"原因"}
仅允许 `--root` 和可选 `--archive-root` 边界内的非删除操作；公共 skill 不内置用户目录。
"""
from __future__ import annotations

import argparse
import json
import posixpath
import subprocess
from datetime import datetime, timezone


OPS = {"mkdir", "mv", "rename"}


def run_aliyunpan(command, drive_id, *paths):
    """集中调用 aliyunpan；所有命令都显式指定 driveId。"""
    args = ["aliyunpan", command, "--driveId", drive_id, *paths]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=90)
    except Exception as error:
        return subprocess.CompletedProcess(args, 255, "", repr(error))


def parse_ll(output):
    """按 scan_drive.py 的 ll 表格规则提取条目名称。"""
    names = []
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
        names.append(name[:-1] if name.endswith("/") else name)
    return names


def ll(drive_id, path):
    result = run_aliyunpan("ll", drive_id, path)
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    ok = result.returncode == 0 and "当前目录" in stdout
    names = parse_ll(stdout) if ok else []
    evidence = {
        "path": path,
        "returncode": result.returncode,
        "marker": "当前目录" in stdout,
        "entries": len(names),
    }
    if not ok:
        evidence["stdout"] = stdout[:200]
        evidence["stderr"] = stderr[:200]
    return ok, set(names), evidence


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
                plan.append(record)
    if errors:
        raise ValueError("计划校验失败：\n" + "\n".join(errors))
    return plan


def operation_key(item):
    return item.get("action_id"), item.get("op"), item.get("from"), item.get("to")


def load_completed(path):
    completed = set()
    try:
        source = open(path, encoding="utf-8")
    except FileNotFoundError:
        return completed
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
            if isinstance(item, dict) and item.get("status") in {"verified", "completed"}:
                completed.add(operation_key(item))
    return completed


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
    target_ok, target_names, target_ev = ll(drive_id, item["to"])
    source_ok, source_names, source_ev = ll(drive_id, source_parent)
    verify = {
        "target_dir": target_ev,
        "source_parent": source_ev,
        "target_name": source_name,
        "target_present": target_ok and source_name in target_names,
        "source_absent": source_ok and source_name not in source_names,
    }
    return verify["target_present"] and verify["source_absent"], verify


def verify_rename(item, drive_id):
    parent, old_name = parent_and_name(item["from"])
    _, new_name = parent_and_name(item["to"])
    parent_ok, names, parent_ev = ll(drive_id, parent)
    verify = {
        "parent": parent_ev,
        "old_name": old_name,
        "new_name": new_name,
        "new_present": parent_ok and new_name in names,
        "old_absent": parent_ok and old_name not in names,
    }
    return verify["new_present"] and verify["old_absent"], verify


def apply_one(item, drive_id):
    precheck = None
    if item["op"] in {"mv", "rename"}:
        source_parent, source_name = parent_and_name(item["from"])
        pre_ok, source_names, precheck = ll(drive_id, source_parent)
        if not pre_ok:
            return "skipped", {"stage": "precheck", "error": "LIST_FAIL", "ll": precheck}
        if source_name not in source_names:
            if item["op"] == "mv":
                target_ok, target_names, target_ev = ll(drive_id, item["to"])
                if target_ok and source_name in target_names:
                    return "verified", {
                        "stage": "idempotent-resume",
                        "source_parent": precheck,
                        "target_dir": target_ev,
                        "target_name": source_name,
                        "source_absent": True,
                        "target_present": True,
                    }
            else:
                _, new_name = parent_and_name(item["to"])
                if new_name in source_names:
                    return "verified", {
                        "stage": "idempotent-resume",
                        "parent": precheck,
                        "old_name": source_name,
                        "new_name": new_name,
                        "old_absent": True,
                        "new_present": True,
                    }
            return "skipped", {
                "stage": "precheck",
                "error": "SOURCE_NOT_LISTED",
                "ll": precheck,
                "missing_name": source_name,
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
    except ValueError as error:
        ap.error(str(error))
    if not args.execute:
        preview(plan)
        return
    try:
        completed = load_completed(args.ledger) if args.resume else set()
        returncode = execute(plan, args.driveId, args.ledger, completed)
    except (OSError, ValueError) as error:
        ap.error(str(error))
    if returncode:
        raise SystemExit(returncode)


if __name__ == "__main__":
    main()
