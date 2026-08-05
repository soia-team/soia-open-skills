#!/usr/bin/env python3
"""把仓内技能打包成可上架外部市场的形态。

外部市场（SkillHub、小红书 Red Skill）一次只收一个技能，且拿到的人不会同时
装我们仓里的同伴技能。因此上架要做两件仓内不需要的事：

1. **筛掉有 hard 依赖的技能**——它们在市场上是断链的：用户装了也跑不起来，
   因为强依赖的同伴技能不在那边。optional 依赖只在描述里提一句「装了更好」。
2. **叠加平台 frontmatter**——SkillHub 要求 `slug`/`displayName`/`summary`/
   `license`，我们仓内的 frontmatter 没有这几个字段。

命名策略（2026-08-04 用户裁决）：`slug` 直接用仓内技能名（已带 `soia-` 前缀，
天然全网唯一，且与仓内一一对应便于追溯）；`displayName` 用中文可读名。

用法：
    python3 stage_for_market.py --repo-dir <域仓> --skill <技能名> --out <暂存目录>
    python3 stage_for_market.py --repo-dir <域仓> --list-eligible
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LICENSE_DEFAULT = "MIT"


def read_frontmatter(skill_md: pathlib.Path) -> tuple[str, str]:
    """返回 (frontmatter 文本, 正文)；缺少 frontmatter 时抛错。"""
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{skill_md} 缺少 frontmatter")
    return match.group(1), text[match.end():]


def field(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*(.+?)\s*$", frontmatter, re.M)
    return match.group(1) if match else None


def has_hard_dependency(frontmatter: str) -> bool:
    """技能是否声明了 hard 依赖（上架后会断链）。"""
    match = re.search(r"^\s*hard:\s*\[(.*?)\]", frontmatter, re.M)
    return bool(match and match.group(1).strip())


def eligible_skills(repo_dir: pathlib.Path) -> list[tuple[str, bool, str]]:
    """列出 (技能名, 是否可上架, 原因)。"""
    rows = []
    skills_dir = repo_dir / "skills"
    for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        md = skill / "SKILL.md"
        if not md.is_file():
            continue
        try:
            frontmatter, _ = read_frontmatter(md)
        except ValueError as exc:
            rows.append((skill.name, False, str(exc)))
            continue
        if has_hard_dependency(frontmatter):
            hard = re.search(r"^\s*hard:\s*\[(.*?)\]", frontmatter, re.M).group(1)
            rows.append((skill.name, False, f"有 hard 依赖：{hard}"))
        else:
            rows.append((skill.name, True, "可独立运行"))
    return rows


def stage(repo_dir: pathlib.Path, skill_name: str, out_dir: pathlib.Path,
          display_name: str | None = None, summary: str | None = None,
          license_id: str = LICENSE_DEFAULT) -> pathlib.Path:
    """把一个技能复制到暂存目录并叠加平台 frontmatter。"""
    src = repo_dir / "skills" / skill_name
    if not (src / "SKILL.md").is_file():
        raise ValueError(f"找不到技能：{src}")

    frontmatter, body = read_frontmatter(src / "SKILL.md")
    if has_hard_dependency(frontmatter):
        raise ValueError(
            f"{skill_name} 声明了 hard 依赖，上架后会断链；"
            f"先去掉依赖或改为 optional 再上架")

    target = out_dir / skill_name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(src, target)

    overlay = [
        f"slug: {skill_name}",
        f"displayName: {display_name or field(frontmatter, 'name') or skill_name}",
        f"summary: {summary or field(frontmatter, 'description') or ''}",
        f"license: {license_id}",
    ]
    (target / "SKILL.md").write_text(
        "---\n" + "\n".join(overlay) + "\n" + frontmatter + "\n---\n" + body,
        encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=pathlib.Path, required=True)
    parser.add_argument("--skill", help="要打包的技能名")
    parser.add_argument("--out", type=pathlib.Path, help="暂存目录")
    parser.add_argument("--display-name", help="对外中文展示名")
    parser.add_argument("--summary", help="对外简介；缺省用 description")
    parser.add_argument("--license", default=LICENSE_DEFAULT)
    parser.add_argument("--list-eligible", action="store_true",
                        help="只列出哪些技能可上架，不打包")
    args = parser.parse_args(argv)

    if args.list_eligible:
        for name, ok, reason in eligible_skills(args.repo_dir.resolve()):
            print(f"{'✓' if ok else '✗'} {name}: {reason}")
        return 0

    if not args.skill or not args.out:
        print("error: 打包需要同时给出 --skill 与 --out", file=sys.stderr)
        return 1

    try:
        target = stage(args.repo_dir.resolve(), args.skill, args.out.resolve(),
                       args.display_name, args.summary, args.license)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"已暂存：{target}")
    print("下一步（不会自动执行）：")
    print(f"  skillhub publish {target} --dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
