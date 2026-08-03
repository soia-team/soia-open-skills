#!/usr/bin/env python3
"""跨仓分支体检：版本列车不变量 + 发版可合并性。

检查两类会静默积累、只在下次发版时才暴露的问题：

1. **版本列车**：dev 必须带 `-SNAPSHOT`、main 必须不带。发版的定稿步骤会短暂
   把 dev 置于正式版本号，第 5 步重开列车才恢复——中途中断就会停在违规状态
   （2026-08-03：pkm 与 media 两个仓静默停在无 SNAPSHOT）。

2. **发版可合并性**（需 `--repos-root`）：dev→main 能否干净合并。发版 PR 若用
   squash 合并，会造出与 dev 无祖先关系的新提交，merge base 停在旧点，两边对同
   一批文件各自演进，下次发版 PR 必然 CONFLICTING（2026-08-03 两个仓实际发生，
   靠人工 sync PR 才走通）。发版改用 merge commit 后不再累积，此项用于回归监测。

用法：
    python3 scripts/check_version_trains.py                      # 只查版本列车
    python3 scripts/check_version_trains.py --repos-root ..      # 并查可合并性
    python3 scripts/check_version_trains.py --repo <name> --json
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import subprocess
import sys

OWNER = "soia-team"
MANIFEST = ".claude-plugin/plugin.json"
REPOS = [
    "soia-open-skills",
    "soia-open-dev-skills",
    "soia-open-dev-design-skills",
    "soia-open-pkm-vault-skills",
    "soia-open-media-content-skills",
    "soia-open-cwork-office-skills",
    "soia-open-env-skills",
    "soia-open-edu-course-skills",
    "soia-private-skills",
    "soia-private-corp-skills",
]


def fetch_version(repo: str, ref: str) -> str | None:
    """读取指定 ref 上的插件版本；分支或文件不存在时返回 None。"""
    result = subprocess.run(
        ["gh", "api", f"repos/{OWNER}/{repo}/contents/{MANIFEST}?ref={ref}", "--jq", ".content"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        payload = base64.b64decode(result.stdout.strip()).decode("utf-8")
        return json.loads(payload).get("version")
    except (ValueError, UnicodeDecodeError):
        return None


def conflicted_paths(merge_tree_stdout: str) -> list[str]:
    """从 merge-tree 输出里取冲突文件名。

    冲突条目形如 `<mode> <oid> <stage>\\t<path>`，stage 为 1/2/3；同一文件会出现
    多个 stage，去重后返回。不解析 "CONFLICT ..." 文案——那段会被 git 按本机语言
    本地化（实测中文环境输出「冲突（内容）」），字符串匹配必然漏判。
    """
    paths: list[str] = []
    for line in merge_tree_stdout.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) == 3 and parts[2] in {"1", "2", "3"} and path not in paths:
            paths.append(path)
    return paths


def check_mergeable(repo_dir: pathlib.Path) -> str | None:
    """dev→main 能否干净合并；返回问题描述，无问题返回 None。"""
    fetch = subprocess.run(
        ["git", "-C", str(repo_dir), "fetch", "origin",
         "+refs/heads/dev:refs/remotes/origin/dev",
         "+refs/heads/main:refs/remotes/origin/main"],
        capture_output=True, text=True)
    if fetch.returncode != 0:
        return f"取不到远端分支：{fetch.stderr.strip()[:80]}"
    merged = subprocess.run(
        ["git", "-C", str(repo_dir), "merge-tree", "--write-tree",
         "origin/main", "origin/dev"],
        capture_output=True, text=True)
    if merged.returncode == 0:
        return None
    paths = conflicted_paths(merged.stdout)
    if not paths:  # 非冲突原因的失败（缺分支、坏对象等）
        return f"合并预演失败：{(merged.stderr or merged.stdout).strip()[:80]}"
    shown = ", ".join(paths[:3]) + ("…" if len(paths) > 3 else "")
    return f"下次发版 PR 会冲突（{len(paths)} 个文件：{shown}）——需先 sync main→dev"


def inspect(repo: str, repos_root: pathlib.Path | None = None) -> dict:
    main_v = fetch_version(repo, "main")
    dev_v = fetch_version(repo, "dev")
    problems = []
    if main_v is None:
        problems.append("main 读不到 plugin.json")
    elif "-SNAPSHOT" in main_v:
        problems.append(f"main 带 -SNAPSHOT（{main_v}）——开发版本泄漏到发布分支")
    if dev_v is None:
        problems.append("dev 读不到 plugin.json（分支缺失？）")
    elif "-SNAPSHOT" not in dev_v:
        problems.append(f"dev 未开列车（{dev_v}）——发版可能中断在定稿与重开之间")

    if repos_root is not None:
        repo_dir = repos_root / repo
        if repo_dir.is_dir():
            issue = check_mergeable(repo_dir)
            if issue:
                problems.append(issue)
        else:
            problems.append(f"本地 checkout 不存在：{repo_dir}")

    return {"repo": repo, "main": main_v, "dev": dev_v, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", help="只检查指定仓，可重复")
    parser.add_argument("--repos-root", type=pathlib.Path,
                        help="各仓本地 checkout 的父目录；给出后并查 dev→main 可合并性")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    targets = args.repo or REPOS
    results = [inspect(r, args.repos_root) for r in targets]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = "✗" if r["problems"] else "✓"
            print(f"{mark} {r['repo']}: main={r['main']} dev={r['dev']}")
            for p in r["problems"]:
                print(f"    {p}")

    broken = [r for r in results if r["problems"]]
    if broken:
        print(f"\n{len(broken)} 个仓存在问题", file=sys.stderr)
        return 1
    if not args.json:
        checks = "版本列车" + ("、发版可合并性" if args.repos_root else "")
        print(f"\n全部 {len(results)} 个仓通过（{checks}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
