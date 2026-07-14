#!/usr/bin/env python3
"""Public-package safety checks for soia-pkm-alipan-curator."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "skills" / "soia-pkm-alipan-curator"
TEXT_SUFFIXES = {".md", ".py", ".mjs", ".js", ".json", ".yaml", ".yml"}


def skill_text() -> str:
    chunks = []
    for path in sorted(SKILL_ROOT.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            chunks.append(f"\n--- {path.relative_to(SKILL_ROOT)} ---\n")
            chunks.append(path.read_text(encoding="utf-8"))
    return "".join(chunks)


class CuratorPublicSafetyTests(unittest.TestCase):
    def test_no_maintainer_absolute_paths_or_real_cloud_ids(self) -> None:
        text = skill_text()
        self.assertNotRegex(text, r"/Users/[A-Za-z0-9._-]+/")
        self.assertNotRegex(text, r"/home/[A-Za-z0-9._-]+/")
        self.assertNotRegex(text, r"/Volumes/[A-Za-z0-9._ -]+/")
        self.assertNotRegex(text, r"(?i)\b[0-9a-f]{40}\b")
        self.assertNotRegex(text, r"(?i)--driveId(?:=|\s+)\d{5,}")

    def test_no_private_vault_conventions_or_agent_names(self) -> None:
        text = skill_text()
        forbidden = [
            "10_工作台",
            "40_图书视频馆",
            "50_云盘馆藏",
            "20_云盘地图",
            "SuperSimpleSongs",
            "Fable",
            "sonnet",
        ]
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, text)

    def test_generated_workbooks_do_not_embed_input_absolute_paths(self) -> None:
        builder = (
            SKILL_ROOT / "scripts" / "catalog_xlsx" / "build_workbooks.mjs"
        ).read_text(encoding="utf-8")
        self.assertNotIn("catalog.source]", builder)
        self.assertNotIn("item.source]", builder)
        self.assertNotIn('["源文件", source]', builder)
        self.assertNotIn("const ROOT_URL", builder)
        self.assertNotIn('timeZone: "Asia/Shanghai"', builder)
        self.assertNotIn("max-old-space-size=8192", skill_text())

    def test_catalog_generator_has_no_user_specific_section_map(self) -> None:
        generator = (
            SKILL_ROOT / "scripts" / "gen_catalog.py"
        ).read_text(encoding="utf-8")
        self.assertIn("--heading-pattern", generator)
        self.assertIn("--section-icons", generator)
        self.assertNotIn("EMOJI={'孩子'", generator)
        self.assertNotIn("'个人':'📖'", generator)

    def test_classification_method_is_generic_and_evidence_first(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        method = (
            SKILL_ROOT / "references" / "classification-methods.md"
        ).read_text(encoding="utf-8")
        self.assertIn("references/classification-methods.md", skill)
        for marker in [
            "先真读再分类",
            "选择主分类轴",
            "教育资源",
            "编程与技术学习",
            "读书与个人学习",
            "分区边界必须写成互斥判断句",
            "导览合同",
            "不确定项的复核区",
            "审计表模板",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, method)
        for hardcoded_rule in [
            "一二级目录统一",
            "90 固定=存档/待拆",
            "按人群分层",
            "至少建 全部馆藏/按学科/按孩子",
        ]:
            with self.subTest(hardcoded_rule=hardcoded_rule):
                self.assertNotIn(hardcoded_rule, skill_text())

    def test_structure_closure_is_mechanically_auditable(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        script = SKILL_ROOT / "scripts" / "audit_structure.py"
        self.assertTrue(script.is_file())
        for marker in [
            "编号可配置且必须闭环",
            "学习导航必须闭环",
            "required_guides",
            "required_artifacts",
            "resource_maps",
            "flat_series_discovery",
            "audit_structure.py",
            "不确定项可隔离复核",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, skill)

    def test_no_literal_secret_assignments(self) -> None:
        text = skill_text()
        patterns = [
            r"(?i)\b(?:api[_-]?key|access[_-]?token|password|cookie|session)\s*[:=]\s*[\"'][^<\n]{8,}[\"']",
            r"\bghp_[A-Za-z0-9]{20,}",
            r"\bsk-[A-Za-z0-9_-]{20,}",
            r"\bAIza[A-Za-z0-9_-]{20,}",
        ]
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                self.assertNotRegex(text, pattern)


if __name__ == "__main__":
    unittest.main()
