#!/usr/bin/env python3
"""把 SOIA 域技能组合物化成 WorkBuddy 专家包。

WorkBuddy 的「专家」= 角色化 agent 预设（人设 MD + 技能组合 + 展示元数据），
是它自己的一套插件格式，与 Claude / Codex 的市场清单并列，属于本生态的第三个分发面。

真源仍是各域仓的 skills/；本仓 experts/ 只放**专家定义**（元数据 + 人设 + 头像），
技能在生成时从域仓拷进专家包。这样做的原因：
  - WorkBuddy 校验器要求 plugin.json 里 skills 声明的每个路径下都有 SKILL.md，
    即技能必须实体存在于专家包内（`validate_expert.py: skill path has no SKILL.md`）；
  - 但把 26 个知识库技能的副本提交进本仓会造成双份真源，改一处要改两处。
  取舍是：仓里只存定义，副本在本机生成，随时可重生成。

物化后调用 WorkBuddy 官方 expert-manager 的 validate/register 脚本完成校验与注册，
不自己写 marketplace.json——官方 SKILL.md 的铁律 12 明确禁止绕过注册脚本。

用法：
    python3 scripts/generate_workbuddy_experts.py --dry-run     # 只看计划
    python3 scripts/generate_workbuddy_experts.py               # 生成并注册
    python3 scripts/generate_workbuddy_experts.py --expert soia-vault-curator
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# WorkBuddy 官方 expert-manager 随桌面端安装，不是本仓依赖
OFFICIAL_TOOLKIT = pathlib.Path(
    "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked"
    "/resources/builtin-skills/expert-manager/scripts"
)

# 官方规定的专家目录，不可改到别处，否则 WorkBuddy 检测不到
DEFAULT_MARKETPLACE = "plugins/marketplaces/my-experts"

# 域仓工作副本里会有本机跑出来的产物，整目录拷贝会把它们一并带进专家包。
# 实测一次未过滤的生成：3 个技能的包里 1.1MB 是 __pycache__，其中单个 .pyc 达 272KB。
COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.pyo", ".venv", "node_modules",
    ".DS_Store", ".git", ".pytest_cache", "*.egg-info",
)

REQUIRED_FIELDS = (
    "name", "agentName", "expertType", "sourceRepo", "description",
    "displayName", "profession", "displayDescription", "categoryId",
    "tags", "quickPrompts",
)


class DefinitionError(Exception):
    """专家定义本身有问题，与本机环境无关——CI 也应拦下。"""


def workbuddy_config_dir() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get("WORKBUDDY_CONFIG_DIR", pathlib.Path.home() / ".workbuddy")
    ).expanduser()


def load_definition(expert_dir: pathlib.Path) -> dict:
    """读取并校验一个专家定义；校验规则对齐官方 validate_expert.py。"""
    spec_path = expert_dir / "expert.json"
    if not spec_path.exists():
        raise DefinitionError(f"{expert_dir.name}: 缺少 expert.json")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    missing = [f for f in REQUIRED_FIELDS if f not in spec]
    if missing:
        raise DefinitionError(f"{expert_dir.name}: 缺少字段 {', '.join(missing)}")
    if spec["name"] != expert_dir.name:
        raise DefinitionError(
            f"{expert_dir.name}: name 与目录名不一致（{spec['name']}）"
        )
    # 官方铁律 2：agentName = agents/ 下的 MD 文件名
    if spec["agentName"] != spec["name"]:
        raise DefinitionError(f"{spec['name']}: agentName 须与 name 一致")
    # 官方铁律 4：tags 与 quickPrompts 各固定 3 条
    for field in ("tags", "quickPrompts"):
        if len(spec[field]) != 3:
            raise DefinitionError(
                f"{spec['name']}: {field} 必须正好 3 条，实际 {len(spec[field])} 条"
            )
    zh_len = len(spec["displayDescription"].get("zh", ""))
    if not 40 <= zh_len <= 50:
        raise DefinitionError(
            f"{spec['name']}: displayDescription.zh 应为 40-50 字，实际 {zh_len} 字"
        )
    for name in ("agent.md", "avatar.png"):
        if not (expert_dir / name).exists():
            raise DefinitionError(f"{spec['name']}: 缺少 {name}")
    return spec


def resolve_skills(spec: dict, skills_root: pathlib.Path) -> list[pathlib.Path]:
    """定位该专家要携带的技能目录；未声明 skills 时取源仓全域。"""
    repo_skills = skills_root / spec["sourceRepo"] / "skills"
    if not repo_skills.is_dir():
        raise DefinitionError(
            f"{spec['name']}: 找不到源仓技能目录 {repo_skills}"
            f"（用 --skills-root 指向存放各域仓的目录）"
        )
    available = {
        d.name: d for d in sorted(repo_skills.iterdir())
        if d.is_dir() and (d / "SKILL.md").exists()
    }
    wanted = spec.get("skills")
    if wanted is None:
        return list(available.values())
    unknown = [s for s in wanted if s not in available]
    if unknown:
        raise DefinitionError(f"{spec['name']}: 源仓没有这些技能 {', '.join(unknown)}")
    return [available[s] for s in wanted]


def build_plugin_json(spec: dict, skills: list[pathlib.Path]) -> dict:
    """组装 WorkBuddy plugin.json。defaultInitPrompt 必须等于 quickPrompts 第一条。"""
    return {
        "name": spec["name"],
        "version": spec.get("version", "1.0.0"),
        "description": spec["description"],
        "author": {"name": "SOIA"},
        "agents": [f"./agents/{spec['agentName']}.md"],
        "skills": [f"./skills/{s.name}" for s in skills],
        "expertType": spec["expertType"],
        "agentName": spec["agentName"],
        "displayName": spec["displayName"],
        "profession": spec["profession"],
        "displayDescription": spec["displayDescription"],
        "avatar": "avatars/expert.png",
        "categoryId": spec["categoryId"],
        "defaultInitPrompt": spec["quickPrompts"][0],
        "tags": spec["tags"],
        "quickPrompts": spec["quickPrompts"],
    }


def materialize(spec: dict, expert_dir: pathlib.Path, skills: list[pathlib.Path],
                target_root: pathlib.Path) -> pathlib.Path:
    """把一个专家写进专家目录。整目录重建，避免上一轮的残留技能留在包里。"""
    out = target_root / "plugins" / spec["name"]
    if out.exists():
        shutil.rmtree(out)
    (out / ".codebuddy-plugin").mkdir(parents=True)
    (out / "agents").mkdir()
    (out / "avatars").mkdir()
    (out / "skills").mkdir()

    (out / ".codebuddy-plugin" / "plugin.json").write_text(
        json.dumps(build_plugin_json(spec, skills), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(expert_dir / "agent.md", out / "agents" / f"{spec['agentName']}.md")
    shutil.copy2(expert_dir / "avatar.png", out / "avatars" / "expert.png")
    for skill in skills:
        shutil.copytree(skill, out / "skills" / skill.name, ignore=COPY_IGNORE)
    (out / "README.md").write_text(
        f"# {spec['profession']['zh']}（{spec['displayName']['zh']}）\n\n"
        f"{spec['displayDescription']['zh']}\n\n"
        f"由 `soia-open-skills/scripts/generate_workbuddy_experts.py` 从 "
        f"`{spec['sourceRepo']}` 生成，请勿手改——重跑生成器会整目录重建。\n",
        encoding="utf-8",
    )
    return out


def run_official(script: str, *args: str) -> bool:
    """调用官方 expert-manager 脚本；WorkBuddy 未安装时返回 False 由调用方降级。"""
    path = OFFICIAL_TOOLKIT / script
    if not path.exists():
        return False
    result = subprocess.run([sys.executable, str(path), *args],
                            capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if output:
        print("\n".join(f"      {line}" for line in output.splitlines()))
    if result.returncode != 0:
        raise DefinitionError(f"官方 {script} 未通过")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--experts-dir", type=pathlib.Path,
                        default=REPO_ROOT / "experts",
                        help="专家定义目录，默认 <仓根>/experts")
    parser.add_argument("--skills-root", type=pathlib.Path,
                        default=REPO_ROOT.parent,
                        help="存放各域仓的目录，默认本仓的上级目录")
    parser.add_argument("--marketplace-dir", type=pathlib.Path, default=None,
                        help=f"专家市场目录，默认 $WORKBUDDY_CONFIG_DIR/{DEFAULT_MARKETPLACE}")
    parser.add_argument("--expert", action="append", dest="experts", metavar="NAME",
                        help="只处理指定专家，可重复")
    parser.add_argument("--dry-run", action="store_true",
                        help="只校验定义并打印计划，不写任何文件")
    args = parser.parse_args(argv)

    target_root = args.marketplace_dir or (workbuddy_config_dir() / DEFAULT_MARKETPLACE)

    dirs = sorted(d for d in args.experts_dir.iterdir()
                  if d.is_dir() and (d / "expert.json").exists())
    if args.experts:
        selected = set(args.experts)
        unknown = selected - {d.name for d in dirs}
        if unknown:
            print(f"❌ 没有这些专家定义：{', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        dirs = [d for d in dirs if d.name in selected]
    if not dirs:
        print("❌ 没有找到任何专家定义", file=sys.stderr)
        return 2

    try:
        plans = []
        for expert_dir in dirs:
            spec = load_definition(expert_dir)
            skills = resolve_skills(spec, args.skills_root)
            plans.append((spec, expert_dir, skills))
    except DefinitionError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    print(f"专家目录：{target_root}")
    for spec, _, skills in plans:
        print(f"  {spec['name']:24s} {spec['profession']['zh']:8s} "
              f"{len(skills):2d} 个技能 ← {spec['sourceRepo']}")

    if args.dry_run:
        print("\n（--dry-run，未写入任何文件）")
        return 0

    toolkit_available = OFFICIAL_TOOLKIT.exists()
    if not toolkit_available:
        print(f"\n⚠️  未找到 WorkBuddy 官方 expert-manager（{OFFICIAL_TOOLKIT}）。")
        print("    专家包会照常生成，但跳过官方校验与注册；")
        print("    在装有 WorkBuddy 的机器上重跑本脚本即可完成注册。")

    print()
    for spec, expert_dir, skills in plans:
        out = materialize(spec, expert_dir, skills, target_root)
        print(f"  ✓ 已生成 {spec['name']}")
        if not toolkit_available:
            continue
        try:
            run_official("validate_expert.py", str(out))
            run_official("register_expert.py", str(out),
                         "--marketplace-dir", str(target_root))
        except DefinitionError as exc:
            print(f"  ❌ {spec['name']}: {exc}", file=sys.stderr)
            return 1
        print(f"  ✓ 已校验并注册 {spec['name']}")

    print(f"\n完成 {len(plans)} 个专家。重启 WorkBuddy 后在【专家中心 - 我的专家】可见。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
