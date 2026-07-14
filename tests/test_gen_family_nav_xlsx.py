#!/usr/bin/env python3
"""CLI contract tests for the family navigation workbook generator."""

from __future__ import annotations

import subprocess
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "soia-pkm-alipan-curator"
    / "scripts"
    / "gen_family_nav_xlsx.mjs"
)


class FamilyNavigationCliTests(unittest.TestCase):
    def test_help_is_available_without_artifact_runtime(self) -> None:
        result = subprocess.run(
            ["node", str(SCRIPT), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("navigation.json", result.stdout)
        self.assertIn("family-navigation-excel.md", result.stdout)
        self.assertIn("file/all/backup", result.stdout)

    def test_missing_required_args_points_to_help(self) -> None:
        result = subprocess.run(
            ["node", str(SCRIPT), "--input", "missing.json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--help", result.stderr)

    def test_invalid_drive_url_fails_before_loading_artifact_tool(self) -> None:
        payload = {
            "title": "家庭导航",
            "summary": "说明",
            "generatedAt": "2026-01-01",
            "partition": "10_示例",
            "guidance": [{"label": "先选主线", "text": "一次只选一套。"}],
            "rows": [
                {
                    "category": "10_课程",
                    "name": "示例课程",
                    "audience": "启蒙阶段",
                    "type": "视频",
                    "usage": "亲子观看",
                    "pace": "每次十分钟",
                    "path": "/10_示例/10_课程",
                    "url": "https://www.alipan.com/drive/folder/wrong",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "navigation.json"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    "node",
                    str(SCRIPT),
                    "--input",
                    str(source),
                    "--output",
                    str(root / "out.xlsx"),
                    "--artifact-runtime",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("file/all/backup", result.stderr)
        self.assertNotIn("artifact-tool", result.stderr)


if __name__ == "__main__":
    unittest.main()
