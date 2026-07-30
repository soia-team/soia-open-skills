#!/usr/bin/env python3
"""把 SOIA 域仓安装为 WorkBuddy 专家。

WorkBuddy 是 Electron 桌面端，**没有 CLI**——不存在 `workbuddy plugin install`
这种命令，也没有能指向我们 GitHub 的市场通道（实测：市场条目的 source 只能是
路径字符串，没有 sha pin 那一层；`expert/install` 深链要 sharecode，走官方云）。
所以 Claude/Codex 的「一条命令」在这里没有对等物，安装只能由本脚本代劳。

三条实测约束决定了实现方式：

1. 自建专家只认硬编码目录 `$WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins`
   （应用内出现 38 处，含 `=== "my-experts" ? true : targetExpert.isCustomExpert`
   这类分支）。别处放了不会显示。
2. **软链不行**：官方 validate_expert.py 对路径做 resolve()，会穿透到真实路径后
   判定「不在专家目录下」。所以必须是实体副本。
3. 域仓根本身就是专家包（`.codebuddy-plugin/plugin.json` 引用本仓 skills/ 与
   assets/icon.png），所以复制一份 checkout 即可，等价于 Claude/Codex 各自在
   插件缓存里放一份克隆。

用法：
    python3 install_workbuddy_experts.py --dry-run              # 只看计划
    python3 install_workbuddy_experts.py                        # 装全部
    python3 install_workbuddy_experts.py soia-dev soia-pkm-vault  # 只装指定的
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

MY_EXPERTS = "plugins/marketplaces/my-experts"

# 插件名 → 域仓名。私有仓不在此表，它们的专家由各自仓库自行决定是否开放。
DOMAIN_REPOS = {
    "soia-dev": "soia-open-dev-skills",
    "soia-dev-design": "soia-open-dev-design-skills",
    "soia-pkm-vault": "soia-open-pkm-vault-skills",
    "soia-media-content": "soia-open-media-content-skills",
    "soia-cwork-office": "soia-open-cwork-office-skills",
    "soia-edu-course": "soia-open-edu-course-skills",
    "soia-env": "soia-open-env-skills",
    "soia-meta": "soia-open-skills",
}

# 复制时排除：本机产物与版本库，不应进专家包
COPY_IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", "*.pyc", "*.pyo", ".venv", "node_modules",
    ".DS_Store", ".pytest_cache", "*.egg-info",
)

OFFICIAL_TOOLKIT = pathlib.Path(
    "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked"
    "/resources/builtin-skills/expert-manager/scripts"
)


class InstallError(Exception):
    """安装前提不满足，与具体专家无关。"""


def workbuddy_config_dir() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get("WORKBUDDY_CONFIG_DIR", pathlib.Path.home() / ".workbuddy")
    ).expanduser()


def locate_repo(repo_name: str, search_roots: list[pathlib.Path]) -> pathlib.Path | None:
    for root in search_roots:
        candidate = root / repo_name
        if (candidate / ".codebuddy-plugin/plugin.json").exists():
            return candidate
    return None


def install_one(plugin: str, repo: pathlib.Path, target_root: pathlib.Path) -> pathlib.Path:
    out = target_root / "plugins" / plugin
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo, out, ignore=COPY_IGNORE)
    return out


def register(expert_dir: pathlib.Path, target_root: pathlib.Path) -> None:
    """优先调官方 register_expert.py。官方规范禁止绕过它直接写 marketplace.json。"""
    script = OFFICIAL_TOOLKIT / "register_expert.py"
    if not script.exists():
        raise InstallError(
            f"未找到 WorkBuddy 官方 expert-manager（{script}）。"
            "请先安装 WorkBuddy 桌面端（技能 soia-env-workbuddy-install）。"
        )
    result = subprocess.run(
        [sys.executable, str(script), str(expert_dir),
         "--marketplace-dir", str(target_root)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise InstallError(
            f"官方 register_expert.py 未通过：\n{(result.stdout + result.stderr).strip()}"
        )


def main(argv: list[str] | None = None) -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plugins", nargs="*", metavar="PLUGIN",
                        help=f"要安装的插件名，缺省为全部。可选：{', '.join(sorted(DOMAIN_REPOS))}")
    parser.add_argument("--repos-root", type=pathlib.Path, action="append", default=None,
                        help="存放各域仓的目录，可重复；缺省为元仓的上级目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写文件")
    args = parser.parse_args(argv)

    wanted = args.plugins or sorted(DOMAIN_REPOS)
    unknown = [p for p in wanted if p not in DOMAIN_REPOS]
    if unknown:
        print(f"❌ 未知插件名：{', '.join(unknown)}", file=sys.stderr)
        print(f"   可选：{', '.join(sorted(DOMAIN_REPOS))}", file=sys.stderr)
        return 2

    search_roots = args.repos_root or [repo_root.parent]
    target_root = workbuddy_config_dir() / MY_EXPERTS

    plans: list[tuple[str, pathlib.Path]] = []
    missing: list[str] = []
    for plugin in wanted:
        repo = locate_repo(DOMAIN_REPOS[plugin], search_roots)
        if repo is None:
            missing.append(f"{plugin} → {DOMAIN_REPOS[plugin]}")
        else:
            plans.append((plugin, repo))

    print(f"专家目录：{target_root}")
    for plugin, repo in plans:
        manifest = json.loads((repo / ".codebuddy-plugin/plugin.json").read_text(encoding="utf-8"))
        print(f"  {plugin:20s} {manifest['profession']['zh']:10s} "
              f"{len(manifest['skills']):2d} 个技能 ← {repo}")
    if missing:
        print("\n⚠️  以下域仓没找到（缺 .codebuddy-plugin/plugin.json，或不在搜索路径下）：")
        for m in missing:
            print(f"   {m}")
        print(f"   搜索路径：{', '.join(str(r) for r in search_roots)}")
        print("   用 --repos-root 指定，或先 git clone 对应域仓。")

    if args.dry_run:
        print("\n（--dry-run，未写入任何文件）")
        return 0
    if not plans:
        print("\n❌ 没有可安装的专家", file=sys.stderr)
        return 1

    print()
    for plugin, repo in plans:
        out = install_one(plugin, repo, target_root)
        try:
            register(out, target_root)
        except InstallError as exc:
            print(f"  ❌ {plugin}: {exc}", file=sys.stderr)
            return 1
        print(f"  ✓ 已安装并注册 {plugin}")

    print(f"\n完成 {len(plans)} 个专家。**重启 WorkBuddy** 后在【专家·技能·连接器 → 我的专家】可见。")
    if missing:
        print(f"另有 {len(missing)} 个未安装，见上方提示。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
