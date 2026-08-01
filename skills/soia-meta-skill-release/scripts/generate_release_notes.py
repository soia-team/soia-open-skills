#!/usr/bin/env python3
"""从上一个 tag 以来的提交生成 Release Notes 草稿。

squash 合并流程下每个 PR 落地为一个提交，subject 即 PR 标题（含 #编号），
按 conventional 前缀归类为 新增 / 修复 / 维护 / 其他 四节，空节省略。
产出是草稿——发布前人工润色一句话摘要。
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

SECTION_ORDER = ["新增", "修复", "维护", "其他"]
PREFIX_SECTIONS = {
    "feat": "新增",
    "fix": "修复",
    "docs": "维护",
    "chore": "维护",
    "refactor": "维护",
    "test": "维护",
    "ci": "维护",
    "style": "维护",
    "perf": "维护",
    "build": "维护",
    "release": "维护",
}


def classify(subject: str) -> str:
    """按 conventional 前缀（含可选 scope）归类一条提交标题。"""
    head = subject.split(":", 1)[0].strip().lower()
    if "(" in head:
        head = head.split("(", 1)[0]
    return PREFIX_SECTIONS.get(head, "其他")


def build_notes(version: str, subjects: list[str], summary: str = "") -> str:
    """组装 markdown 草稿；summary 为空时留占位提醒人工补写。"""
    sections: dict[str, list[str]] = {name: [] for name in SECTION_ORDER}
    for subject in subjects:
        sections[classify(subject)].append(subject)

    lines = [f"# v{version}", ""]
    lines.append(summary if summary else "<!-- 一句话摘要：发布前人工补写 -->")
    lines.append("")
    for name in SECTION_ORDER:
        items = sections[name]
        if not items:
            continue
        lines.append(f"## {name}")
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def git(repo_dir: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def collect_subjects(repo_dir: pathlib.Path, ref: str, tag_prefix: str) -> list[str]:
    try:
        last_tag = git(
            repo_dir, "describe", "--tags", "--abbrev=0", f"--match={tag_prefix}*", ref
        )
        span = f"{last_tag}..{ref}"
    except RuntimeError:
        span = ref  # 首个正式版：从仓库起点算起
    out = git(repo_dir, "log", span, "--no-merges", "--pretty=%s")
    return [line for line in out.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--ref", default="HEAD", help="统计终点，默认 HEAD")
    parser.add_argument("--tag-prefix", default="v")
    parser.add_argument("--release-version", required=True, help="如 1.9.0")
    parser.add_argument("--summary", default="", help="一句话摘要；缺省留占位")
    parser.add_argument("--output", type=pathlib.Path, help="缺省输出到 stdout")
    args = parser.parse_args(argv)

    try:
        subjects = collect_subjects(args.repo_dir, args.ref, args.tag_prefix)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    notes = build_notes(args.release_version, subjects, args.summary)
    if args.output:
        args.output.write_text(notes, encoding="utf-8")
        print(f"wrote {args.output} ({len(subjects)} commits)")
    else:
        print(notes, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
