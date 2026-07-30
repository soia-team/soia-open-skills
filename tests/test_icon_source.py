"""图形资产必须同源：一张配色/字形表，派生所有面。

回归 2026-07-29：配色表原本只在会话临时目录里，元仓 assets/plugins/、8 个域仓
assets/、以及当时放在元仓的专家头像各存一份副本，没有东西保证同源；
generate_marketplaces.py 还自带一张 BRAND_COLORS，图标换成紫色系后那张表仍是
琥珀期的橙色号，市场主题色与图标对不上。

WorkBuddy 专家的 avatar 不再是独立的一面——它直接指域仓的 assets/icon.png，
与 Codex 的 logo 是同一个文件（见各域仓的 .codebuddy-plugin/plugin.json）。
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# soia-design-brand-guidelines §配色 的 Primary，规范明写用于「插件与应用图标底色」
BRAND_PRIMARY = "#F5A623"


class SharedIconSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "generate_icons", ROOT / "scripts/generate_icons.py")
        self.icons = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.icons)

    def test_brand_primary_anchors_the_palette(self) -> None:
        """回归 2026-07-29：为了「统一图标来源」顺手把整套刷成紫色并部署到 8 个仓，
        品牌锚点因此消失，且事前没查规范。改色值前先读规范。"""
        self.assertEqual(
            self.icons.PALETTE["soia-meta"][2], BRAND_PRIMARY,
            "soia-meta 应直接用品牌主色，它是整套配色的锚点",
        )

    def test_every_plugin_has_a_distinct_glyph(self) -> None:
        """gov 与 corp 曾被写成同一个盾牌+对勾，两个插件在市场里无法区分。"""
        seen: dict[str, str] = {}
        for name, glyph in self.icons.GLYPHS.items():
            key = " ".join(glyph.split())
            self.assertNotIn(key, seen, f"{name} 与 {seen.get(key)} 字形完全相同")
            seen[key] = name

    def test_every_palette_entry_has_a_glyph(self) -> None:
        self.assertEqual(set(self.icons.PALETTE), set(self.icons.GLYPHS))

    def test_marketplace_generator_reuses_the_icon_palette(self) -> None:
        source = (ROOT / "scripts/generate_marketplaces.py").read_text(encoding="utf-8")
        self.assertIn("_icons.PALETTE", source,
                      "brandColor 必须取自 generate_icons.py，不得另存一张表")
        self.assertNotRegex(source, r'BRAND_COLORS\s*=\s*\{\s*\n\s*"soia-',
                            "检测到硬编码的 brandColor 表")

    def test_no_separate_avatar_face(self) -> None:
        """专家头像不单独出图。域仓的 .codebuddy-plugin 直接把 avatar 指向 assets/icon.png，
        与 Codex 的 logo 同一个文件——再加一面就又是一份副本。"""
        source = (ROOT / "scripts/generate_icons.py").read_text(encoding="utf-8")
        self.assertNotIn("EXPERTS", source)
        self.assertFalse((ROOT / "experts").exists(),
                         "专家定义属于域仓，不属于元仓")


if __name__ == "__main__":
    unittest.main()
