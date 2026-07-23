#!/usr/bin/env python3
"""Offline tests for the two-tier SOIA skill finder."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/soia-meta-find-skill/scripts/find_skill.py"


class FindSkillRouterTests(unittest.TestCase):
    def write_skill(self, root: Path, name: str, description: str) -> None:
        skill = root / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n",
            encoding="utf-8",
        )

    def run_finder(
        self, skills_dir: Path, directory: Path, query: str, domain: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT),
            "--query",
            query,
            "--skills-dir",
            str(skills_dir),
            "--directory",
            str(directory),
        ]
        if domain:
            command.extend(["--domain", domain])
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def test_installed_match_has_priority_over_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            skills = root / "skills"
            self.write_skill(skills, "soia-pkm-clip-local", "剪藏网页到本地知识库")
            directory = root / "directory.json"
            directory.write_text(
                json.dumps(
                    [
                        {
                            "name": "soia-pkm-clip-remote",
                            "repo": "soia-open-pkm-clip-skills",
                            "description": "剪藏网页",
                            "install_cmd": "npx skills add remote",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_finder(skills, directory, "剪藏")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual([item["name"] for item in payload], ["soia-pkm-clip-local"])
            self.assertTrue(payload[0]["installed"])
            self.assertIn("path", payload[0])
            self.assertNotIn("install_cmd", payload[0])

    def test_directory_fallback_filters_domain_and_limits_top_three(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            directory = root / "directory.json"
            entries = [
                {
                    "name": f"soia-pkm-clip-example-{index}",
                    "repo": "soia-open-pkm-clip-skills",
                    "description": f"剪藏资源示例 {index}",
                    "install_cmd": f"npx skills add example-{index}",
                }
                for index in range(5)
            ]
            entries.append(
                {
                    "name": "soia-dev-review-example",
                    "repo": "soia-open-dev-coding-skills",
                    "description": "剪藏需求的代码审查示例",
                    "install_cmd": "npx skills add review",
                }
            )
            directory.write_text(json.dumps(entries), encoding="utf-8")
            result = self.run_finder(root / "missing", directory, "剪藏", "剪藏网盘")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload), 3)
            self.assertTrue(all(not item["installed"] for item in payload))
            self.assertTrue(all("install_cmd" in item for item in payload))
            self.assertTrue(all("clip" in item["name"] for item in payload))

    def test_router_does_not_return_itself_for_domain_keywords(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            skills = root / "skills"
            self.write_skill(skills, "soia-meta-find-skill", "检索剪藏网盘技能")
            directory = root / "directory.json"
            directory.write_text("[]\n", encoding="utf-8")
            result = self.run_finder(skills, directory, "剪藏")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [])

    def test_chinese_query_expands_to_ecosystem_wording(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            skills = root / "skills"
            self.write_skill(skills, "soia-pkm-archive-web", "归档网页到知识库")
            directory = root / "directory.json"
            directory.write_text("[]\n", encoding="utf-8")
            result = self.run_finder(skills, directory, "剪藏")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)[0]["name"], "soia-pkm-archive-web")


if __name__ == "__main__":
    unittest.main()
