"""技能详情页的守门测试。

页面放在门户仓 docs/skills/ 而不是各技能目录里——SKILL_SPEC.md 明文禁止
per-skill README（"No documentation clutter … do not add per-skill README"），
理由是避免同一份清单散进多个文件。2026-07-30 曾按 per-skill README 做过一版，
八个仓的 audit_skills.py --strict 全线变红后才发现撞了这条规范，已撤回。

内容全部从各技能的 SKILL.md 派生，本文件锁住「只搬运不创作」这个性质：
派生器不得凭空产出 SKILL.md 里没有的内容，也不得把给 Agent 看的内部约定
漏进面向读者的页面。
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES = ROOT / "docs/skills"
SCRIPT = ROOT / "scripts/generate_skill_pages.py"

_spec = importlib.util.spec_from_file_location("generate_skill_pages", SCRIPT)
gsp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gsp)


class OutputLocationTests(unittest.TestCase):
    def test_pages_live_in_the_portal_not_in_skill_directories(self) -> None:
        """SKILL_SPEC 禁止 per-skill README；页面必须在门户仓 docs/ 下。"""
        self.assertTrue(PAGES.is_dir())
        spec = (ROOT / "SKILL_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("do not\n  add per-skill `README`", spec,
                      "SKILL_SPEC 的禁令措辞变了，请复核本方案是否仍成立")

    def test_every_public_skill_has_a_page(self) -> None:
        manifest = json.loads((ROOT / "routing/routing-manifest.json").read_text(encoding="utf-8"))
        expected = {e["skill_name"] for e in manifest}
        # 路由器不路由自己，但它仍是公开技能，详情页该有
        expected.add("soia-meta-find-skill")
        actual = {p.stem for p in PAGES.glob("*.md") if p.name != "README.md"}
        self.assertEqual(actual, expected)

    def test_index_lists_every_page(self) -> None:
        index = (PAGES / "README.md").read_text(encoding="utf-8")
        for p in PAGES.glob("*.md"):
            if p.name == "README.md":
                continue
            with self.subTest(page=p.name):
                self.assertIn(f"]({p.name})", index)


class ContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pages = {p.stem: p.read_text(encoding="utf-8")
                      for p in PAGES.glob("*.md") if p.name != "README.md"}

    def test_no_internal_sections_leak(self) -> None:
        """「日志与完成回执」这类是给 Agent 的执行约定，不该出现在面向读者的页上。"""
        for name, text in self.pages.items():
            for banned in ("### 日志与完成回执", "### 私密信息与中间数据",
                           "### 客户可见日志与总结"):
                with self.subTest(page=name, section=banned):
                    self.assertNotIn(banned, text)

    def test_install_section_is_not_duplicated(self) -> None:
        """派生内容里的「依赖与安装」与页面自带的安装节重复，必须已剔除。"""
        for name, text in self.pages.items():
            with self.subTest(page=name):
                self.assertNotIn("### 依赖与安装", text)
                self.assertEqual(text.count("\n## 安装\n"), 1)

    def test_every_page_states_its_plugin_and_install_route(self) -> None:
        for name, text in self.pages.items():
            with self.subTest(page=name):
                self.assertIn("claude plugin install", text)
                self.assertIn("codex plugin add", text)
                self.assertIn("装到 WorkBuddy", text)

    def test_pages_declare_they_are_generated(self) -> None:
        """避免有人手改页面——改动会在下次重生成时被覆盖。"""
        for name, text in self.pages.items():
            with self.subTest(page=name):
                self.assertIn("generate_skill_pages.py", text)
                self.assertIn("请勿手改", text)

    @staticmethod
    def _strip_code_blocks(text: str) -> str:
        """bash 代码块里的 # 注释不是标题——不剥离会把它们误判成 h1。"""
        return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)

    def test_heading_levels_do_not_skip(self) -> None:
        """派生内容以 ### 开头，页面必须有 h2 承接，否则目录层级断裂。"""
        for name, text in self.pages.items():
            body = self._strip_code_blocks(text)
            levels = [len(m.group(1)) for m in re.finditer(r"^(#{1,4}) ", body, re.M)]
            with self.subTest(page=name):
                for prev, cur in zip(levels, levels[1:]):
                    self.assertLessEqual(cur - prev, 1,
                                         f"{name}: 标题从 h{prev} 跳到 h{cur}")


class DerivationTests(unittest.TestCase):
    """派生器只搬运不创作。"""

    def test_parse_strips_trigger_segment_from_duty(self) -> None:
        got = gsp.parse("---\nname: x\ndescription: 做某件事。触发：「甲」「乙」\n---\n")
        self.assertEqual(got["duty"], "做某件事")
        self.assertEqual(got["triggers"], "「甲」「乙」")

    def test_parse_drops_internal_subsections(self) -> None:
        md = ("---\nname: x\ndescription: d\n---\n"
              "## 客户可读说明\n\n### 这个技能可以做什么\n\n保留\n\n"
              "### 日志与完成回执\n\n剔除\n\n## 别的\n")
        got = gsp.parse(md)
        self.assertIn("保留", got["customer"])
        self.assertNotIn("剔除", got["customer"])

    def test_every_repo_maps_to_a_plugin(self) -> None:
        manifest = json.loads((ROOT / "routing/routing-manifest.json").read_text(encoding="utf-8"))
        for entry in manifest:
            with self.subTest(repo=entry["repo"]):
                self.assertIn(entry["repo"], gsp.REPO_TO_PLUGIN)


if __name__ == "__main__":
    unittest.main()
