"""公开仓不得暴露非公开仓的存在、命名与规模。

回归 2026-07-31：学习指南写着「10 个 Git 仓库，共 100 个技能（开源 74 + 私有 26）」，
安装指南给出了可复制的非公开仓安装命令，WorkBuddy 安装脚本硬编码了 4 个非公开
插件名与目录结构，元仓 assets/plugins/ 还提交了 4 张印着 gov/corp/workspace/harness
标签的图标。这些都不是功能必需，纯属信息外溢。

保留的例外只有两类，都必须是功能必需：
- 已废弃技能的清理名单（RETIRED_SKILLS）：删了旧技能就清不掉
- 域前缀 → 分类的映射表：删了目录分类会错
"""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# 非公开插件名。出现在面向读者的文档或叙述性文案里即视为泄露。
PRIVATE_NAMES = ("soia-private", "soia-gov", "soia-corp", "soia-workspace", "soia-harness")

# 功能必需的白名单：文件 → 允许出现的理由
FUNCTIONAL_ALLOWLIST = {
    "scripts/generate_skill_catalog.py": "域前缀 → 分类映射表",
    "skills/soia-meta-sync-skills/scripts/sync_soia_skills.py": "已废弃技能清理名单",
    "skills/soia-meta-sync-skills/references/soia-managed-skills.md": "受管域前缀清单",
    "tests/test_no_private_leakage.py": "本守卫自身",
    "tests/test_workbuddy_expert_install.py": "防泄露断言自身",
}


class PublicDocsTests(unittest.TestCase):
    def test_no_private_repo_names_in_public_docs(self) -> None:
        leaks = []
        for md in ROOT.rglob("*.md"):
            rel = md.relative_to(ROOT).as_posix()
            if rel.startswith(".git/") or rel in FUNCTIONAL_ALLOWLIST:
                continue
            text = md.read_text(encoding="utf-8")
            for name in PRIVATE_NAMES:
                if name in text:
                    leaks.append(f"{rel}: {name}")
        self.assertEqual(leaks, [], "公开文档暴露了非公开仓/插件名")

    def test_no_private_skill_counts(self) -> None:
        """不得公布非公开技能的数量或全生态合计。"""
        for f in ("docs/learning-guide.md", "docs/learning-guide.en.md",
                  "README.md", "README.en.md"):
            text = (ROOT / f).read_text(encoding="utf-8")
            with self.subTest(file=f):
                self.assertNotRegex(text, r"私有\s*\d+")
                self.assertNotRegex(text, r"\d+\s*private\b")


class PublicAssetsTests(unittest.TestCase):
    def test_no_private_plugin_icons_committed(self) -> None:
        """元仓的 assets/plugins/ 只放公开市场条目引用的图标。"""
        assets = ROOT / "assets/plugins"
        if not assets.is_dir():
            return
        stray = [p.name for p in assets.iterdir()
                 if any(n in p.stem for n in PRIVATE_NAMES)]
        self.assertEqual(stray, [], "元仓提交了非公开插件的图标")

    def test_icon_palette_covers_public_plugins_only(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "generate_icons", ROOT / "scripts/generate_icons.py")
        icons = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(icons)
        stray = [n for n in icons.PALETTE if any(p in n for p in PRIVATE_NAMES)]
        self.assertEqual(stray, [], "配色表含非公开插件")

    def test_marketplaces_never_list_private_plugins(self) -> None:
        for f in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
            blob = json.dumps(json.loads((ROOT / f).read_text(encoding="utf-8")))
            for name in PRIVATE_NAMES:
                with self.subTest(file=f, name=name):
                    self.assertNotIn(name, blob)


class ScriptTests(unittest.TestCase):
    def test_install_script_discovers_instead_of_hardcoding(self) -> None:
        """WorkBuddy 安装脚本必须自动发现 plugin root，不得写死仓名。"""
        src = (ROOT / "skills/soia-meta-skill-release/scripts"
                      "/install_workbuddy_experts.py").read_text(encoding="utf-8")
        for name in PRIVATE_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(name, src)
        self.assertIn("discover_plugin_roots", src)


if __name__ == "__main__":
    unittest.main()
