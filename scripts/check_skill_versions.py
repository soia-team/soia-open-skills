#!/usr/bin/env python3
"""技能内容变了就必须 bump 该技能自己的版本。

`plugin.json` 的 version 是**插件**（交付单元）的版本；每个
`skills/<name>/SKILL.md` 的 frontmatter `version` 是**该技能**自己的版本。两者
独立——只 bump 插件版本会让技能版本说谎，装机侧的版本对账（release_skills 的
六列回执）也就跟着失真。

2026-08-03 实际漏过：`soia-meta-skill-release` 的脚本与正文连改两轮，技能版本
一直停在 4.1.0，靠人工比对才发现。

用法（默认比对 origin/main）：
    python3 scripts/check_skill_versions.py
    python3 scripts/check_skill_versions.py --base origin/main --repo-dir .
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

VERSION_RE = re.compile(r"^version:\s*(.+?)\s*$", re.MULTILINE)


def git(repo_dir: pathlib.Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(["git", "-C", str(repo_dir), *args],
                            capture_output=True, text=True)
    return result.returncode, result.stdout


def changed_skills(repo_dir: pathlib.Path, base: str) -> list[str]:
    """相对 base 有文件变动的技能目录名。

    用两点 diff 且不带 HEAD：这样工作树里尚未提交的改动也算数，本地提交前跑
    与 CI 里跑结果一致（CI 的工作树等于 HEAD）。
    """
    code, out = git(repo_dir, "diff", "--name-only", base)
    if code != 0:
        return []
    names = []
    for line in out.splitlines():
        parts = line.split("/")
        if len(parts) >= 2 and parts[0] == "skills" and parts[1] not in names:
            names.append(parts[1])
    return names


def base_version(repo_dir: pathlib.Path, base: str, skill: str) -> str | None:
    code, out = git(repo_dir, "show", f"{base}:skills/{skill}/SKILL.md")
    if code != 0:
        return None  # 新增技能：base 上不存在
    match = VERSION_RE.search(out)
    return match.group(1) if match else None


def working_version(repo_dir: pathlib.Path, skill: str) -> str | None:
    """读工作树里的版本——未提交的 bump 也要认。"""
    path = repo_dir / "skills" / skill / "SKILL.md"
    if not path.is_file():
        return None  # 已删除
    match = VERSION_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--base", default="origin/main",
                        help="比对基线，默认 origin/main")
    args = parser.parse_args(argv)

    repo_dir = args.repo_dir.resolve()
    code, _ = git(repo_dir, "rev-parse", "--verify", args.base)
    if code != 0:
        print(f"跳过：取不到基线 {args.base}（浅克隆？）")
        return 0

    stale = []
    for skill in changed_skills(repo_dir, args.base):
        before = base_version(repo_dir, args.base, skill)
        after = working_version(repo_dir, skill)
        if before is None or after is None:
            continue  # 新增或删除的技能，无版本可比
        if before == after:
            stale.append((skill, after))

    if stale:
        print("❌ 技能内容变了但版本没 bump：", file=sys.stderr)
        for skill, version in stale:
            print(f"   skills/{skill}/SKILL.md 仍是 {version}", file=sys.stderr)
        print("   改了技能的正文或脚本，就要提 version 与 updated_at。", file=sys.stderr)
        return 1

    print("✓ 变更技能的版本均已 bump")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
