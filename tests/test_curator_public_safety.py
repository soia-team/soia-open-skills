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
