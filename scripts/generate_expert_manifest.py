#!/usr/bin/env python3
"""刷新 WorkBuddy 专家清单里的 skills 数组，使其与本仓 skills/ 一致。

本仓同时是三个宿主的插件：`.claude-plugin/`（Claude Code）、`.codex-plugin/`（Codex）、
`.codebuddy-plugin/`（WorkBuddy 专家）。前两者只声明元数据，技能由宿主扫 skills/ 发现；
WorkBuddy 的专家清单要**逐条列出**技能路径，所以新增或删除技能后这份清单会失配。

清单里的其余字段（花名、职业、标签、推荐提示词、人设）是人写的，本脚本不碰。

    python3 scripts/generate_expert_manifest.py           # 刷新
    python3 scripts/generate_expert_manifest.py --check   # 只比对，CI 用
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".codebuddy-plugin" / "plugin.json"


def discovered_skills(repo_root: pathlib.Path) -> list[str]:
    skills_dir = repo_root / "skills"
    return [
        f"./skills/{d.name}"
        for d in sorted(skills_dir.iterdir())
        if d.is_dir() and (d / "SKILL.md").exists()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="只比对不写，失配时以非零码退出")
    args = parser.parse_args(argv)

    if not MANIFEST.exists():
        print(f"❌ 找不到 {MANIFEST.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = discovered_skills(REPO_ROOT)
    current = manifest.get("skills", [])

    if current == expected:
        print(f"expert manifest is current ({len(expected)} skills)")
        return 0

    missing = [s for s in expected if s not in current]
    extra = [s for s in current if s not in expected]
    if args.check:
        print("❌ 专家清单与 skills/ 失配，请跑 "
              "python3 scripts/generate_expert_manifest.py", file=sys.stderr)
        for s in missing:
            print(f"   缺少 {s}", file=sys.stderr)
        for s in extra:
            print(f"   多余 {s}（技能已删除或改名）", file=sys.stderr)
        return 1

    manifest["skills"] = expected
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    for s in missing:
        print(f"  + {s}")
    for s in extra:
        print(f"  - {s}")
    print(f"已更新，共 {len(expected)} 个技能")
    return 0


if __name__ == "__main__":
    sys.exit(main())
