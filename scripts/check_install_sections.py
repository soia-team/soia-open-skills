#!/usr/bin/env python3
"""跨仓体检：每个技能的「依赖与安装」是否覆盖三个一等宿主。

存在的理由：`SKILL_SPEC.md` 长期只要求「有依赖与安装章节」，没规定这一节要写什么，
而模板里那张表讲的是**技能之间**的依赖。于是作者填完依赖表就以为写完了，
本技能自己怎么装到客户宿主里全靠各自发挥——2026-08-05 实测 101 个技能中
只有 7 个提到 WorkBuddy。

WorkBuddy 是三个一等宿主之一，且 **`npx skills add -a '*'` 覆盖不到它**：
它只从硬编码目录 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/<专家名>/`
加载专家，且软链无效（官方校验器 `resolve()` 会穿透后判定不在专家目录下）。
只写 npx 一条命令，等于静默漏掉一个一等宿主。

本脚本只读，不修改任何文件。

用法：
    python3 scripts/check_install_sections.py --repos-root ..
    python3 scripts/check_install_sections.py --repos-root .. --json
    python3 scripts/check_install_sections.py --repos-root .. --repo soia-open-dev-skills

退出码：
    0  全部覆盖
    1  有技能缺少任一一等宿主
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

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

# 章节标题的既有变体；SKILL_SPEC 允许这几种写法
SECTION_RE = re.compile(
    r"^###\s*(依赖与安装|首次安装与配置|安装与配置|安装)\s*$.*?(?=^###\s|\Z)",
    re.M | re.S,
)

CHECKS = (
    ("域插件", re.compile(r"claude plugin install")),
    ("npx", re.compile(r"npx skills add")),
    ("workbuddy", re.compile(r"workbuddy", re.I)),
)


def install_section(text: str) -> str | None:
    match = SECTION_RE.search(text)
    return match.group(0) if match else None


def audit_skill(path: pathlib.Path, repo_dir: pathlib.Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    # 子仓目录（workspace/skills、harness/skills）里的技能要能一眼看出位置
    rel = path.parent.relative_to(repo_dir)
    label = path.parent.name if rel.parts[0] == "skills" else str(rel)
    section = install_section(text)
    if section is None:
        return {"skill": label, "section": False, "missing": ["无安装章节"]}
    missing = [name for name, pattern in CHECKS if not pattern.search(section)]
    return {"skill": label, "section": True, "missing": missing}


def find_skills(repo_dir: pathlib.Path) -> list[pathlib.Path]:
    """技能以 <某目录>/skills/<名>/SKILL.md 的形式存在。

    private-skills 除 skills/ 外还有 workspace/skills/ 与 harness/skills/，
    第一版只扫 skills/ 漏掉了它们。docs/skills/ 放的是派生文档（<名>.md，
    没有 SKILL.md），glob 天然不会命中。
    """
    found = {p for p in repo_dir.glob("skills/*/SKILL.md")}
    found |= {p for p in repo_dir.glob("*/skills/*/SKILL.md")}
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查技能安装章节的宿主覆盖")
    parser.add_argument("--repos-root", help="包含各域仓工作副本的目录（跨仓模式）")
    parser.add_argument("--self", dest="self_only", action="store_true",
                        help="只检查当前仓，供 CI 使用（CI 环境没有其它仓的工作副本）")
    parser.add_argument("--repo", help="只查某一个仓")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.self_only:
        # CI 里只 checkout 了自己这一个仓；跨仓全量检查放在发版前置里做
        here = pathlib.Path(__file__).resolve().parent.parent
        root, targets = here.parent, [here.name]
    elif args.repos_root:
        root = pathlib.Path(args.repos_root).expanduser().resolve()
        targets = [args.repo] if args.repo else REPOS
    else:
        parser.error("需要 --repos-root（跨仓）或 --self（本仓）")
    report: dict[str, list[dict[str, object]]] = {}
    total = bad = 0

    for repo in targets:
        repo_dir = root / repo
        if not repo_dir.is_dir():
            continue
        rows = []
        for skill_md in find_skills(repo_dir):
            row = audit_skill(skill_md, repo_dir)
            total += 1
            if row["missing"]:
                bad += 1
                rows.append(row)
        if rows:
            report[repo] = rows

    if args.json:
        print(json.dumps({"total": total, "incomplete": bad, "repos": report},
                         ensure_ascii=False, indent=2))
        return 1 if bad else 0

    if not report:
        print(f"✓ 全部 {total} 个技能的安装章节都覆盖了三个一等宿主")
        return 0

    print(f"❌ {bad}/{total} 个技能的安装章节缺少一等宿主：\n")
    for repo, rows in report.items():
        print(f"  {repo}  ({len(rows)} 个)")
        for row in rows:
            print(f"    {row['skill']:<40} 缺: {'、'.join(row['missing'])}")
        print()
    print("规范见 SKILL_SPEC.md「Install section: host coverage」；")
    print("模板见 templates/skill-template/SKILL.md.template「本技能怎么装」。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
