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

# 不维护「插件名 → 仓名」的硬编码表：那会把非公开仓的仓名、插件名与目录结构
# 写进这个公开仓的源码里。改为自动发现——扫搜索路径下每个带
# .codebuddy-plugin/plugin.json 的 plugin root，插件名从该清单的 name 字段读。
#
# 一个仓可能有多个 plugin root（靠目录分隔），所以要往下多找一层。
PLUGIN_MANIFEST = ".codebuddy-plugin/plugin.json"
MAX_ROOT_DEPTH = 2  # 仓根本身，以及仓根下一层的子目录

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


def discover_plugin_roots(search_roots: list[pathlib.Path]) -> dict[str, pathlib.Path]:
    """扫出搜索路径下所有可用的 plugin root。

    插件名以 .codebuddy-plugin/plugin.json 的 name 字段为准，不靠目录名猜——
    一个仓可能靠目录分隔出多个 plugin root，目录名与插件名并不一一对应。

    找不到的仓不报错：非公开仓只有授权者能 clone，它们不出现是正常情况。
    """
    found: dict[str, pathlib.Path] = {}
    for root in search_roots:
        if not root.is_dir():
            continue
        for repo in sorted(root.iterdir()):
            if not repo.is_dir():
                continue
            candidates = [repo]
            candidates += [d for d in sorted(repo.iterdir()) if d.is_dir()]
            for cand in candidates:
                manifest = cand / PLUGIN_MANIFEST
                if not manifest.is_file():
                    continue
                try:
                    name = json.loads(manifest.read_text(encoding="utf-8"))["name"]
                except (json.JSONDecodeError, KeyError, OSError):
                    continue
                found.setdefault(name, cand)
    return found



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
                        help="要安装的插件名，缺省为搜索路径下发现的全部")
    parser.add_argument("--repos-root", type=pathlib.Path, action="append", default=None,
                        help="存放各仓的目录，可重复；缺省为元仓的上级目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写文件")
    args = parser.parse_args(argv)

    search_roots = args.repos_root or [repo_root.parent]
    available = discover_plugin_roots(search_roots)
    if not available:
        print(f"❌ 搜索路径下没有发现任何 plugin root：{', '.join(str(r) for r in search_roots)}",
              file=sys.stderr)
        print("   用 --repos-root 指定各仓所在目录。", file=sys.stderr)
        return 2

    wanted = args.plugins or sorted(available)
    unknown = [p for p in wanted if p not in available]
    if unknown:
        print(f"❌ 搜索路径下没有这些插件：{', '.join(unknown)}", file=sys.stderr)
        print(f"   已发现：{', '.join(sorted(available))}", file=sys.stderr)
        print("   缺少的仓可能你没有访问权限，或还没 clone 下来。", file=sys.stderr)
        return 2

    target_root = workbuddy_config_dir() / MY_EXPERTS
    plans = [(p, available[p]) for p in wanted]

    print(f"专家目录：{target_root}")
    for plugin, repo in plans:
        manifest = json.loads((repo / PLUGIN_MANIFEST).read_text(encoding="utf-8"))
        print(f"  {plugin:20s} {manifest['profession']['zh']:12s} "
              f"{len(manifest['skills']):2d} 个技能 ← {repo}")

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
