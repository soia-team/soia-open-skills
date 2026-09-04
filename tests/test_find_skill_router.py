#!/usr/bin/env python3
"""Offline tests for project-aware SOIA skill discovery."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/soia-meta-find-skill/scripts/find_skill.py"


class FindSkillRouterTests(unittest.TestCase):
    def write_skill(self, root: Path, name: str, description: str) -> Path:
        skill = root / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n",
            encoding="utf-8",
        )
        return skill

    @staticmethod
    def write_directory(path: Path, entries: list[dict[str, object]]) -> None:
        path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    def run_finder(
        self,
        directory: Path,
        query: str,
        *extra: str,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--query", query, "--directory", str(directory), *extra],
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
        )

    def test_auto_scope_prefers_explicit_project_not_global(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            project = root / "project"
            project_skills = project / ".agents" / "skills"
            global_skills = root / "global"
            self.write_skill(project_skills, "soia-pkm-clip-project", "剪藏网页到项目知识库")
            self.write_skill(global_skills, "soia-pkm-clip-global", "剪藏网页到全局知识库")
            directory = root / "directory.json"
            self.write_directory(directory, [])

            result = self.run_finder(
                directory, "剪藏", "--project", str(project), "--skills-dir", str(global_skills)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual([item["name"] for item in payload], ["soia-pkm-clip-project"])
            self.assertEqual(payload[0]["installed_scopes"], ["project"])
            self.assertEqual(payload[0]["source_scope"], "project")

    def test_explicit_legacy_skills_dir_remains_a_global_root_without_a_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            skills = root / "global"
            self.write_skill(skills, "soia-pkm-clip-global", "剪藏网页到全局知识库")
            directory = root / "directory.json"
            self.write_directory(directory, [])
            no_project = root / "no-project"
            no_project.mkdir()

            result = self.run_finder(directory, "剪藏", "--skills-dir", str(skills), cwd=no_project)

            self.assertEqual(result.returncode, 0, result.stderr)
            item = json.loads(result.stdout)[0]
            self.assertEqual(item["name"], "soia-pkm-clip-global")
            self.assertEqual(item["installed_scopes"], ["global"])

    def test_both_scope_merges_project_and_global_with_project_first(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            project = root / "project"
            project_skills = project / ".agents" / "skills"
            global_skills = root / "global"
            self.write_skill(project_skills, "soia-pkm-clip-web", "剪藏网页到项目知识库")
            self.write_skill(global_skills, "soia-pkm-clip-web", "剪藏网页到全局知识库")
            directory = root / "directory.json"
            self.write_directory(directory, [])

            result = self.run_finder(
                directory,
                "剪藏",
                "--project",
                str(project),
                "--scope",
                "both",
                "--skills-dir",
                str(global_skills),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["installed_scopes"], ["project", "global"])
            self.assertEqual(payload[0]["source_scope"], "project")
            self.assertIn("项目", payload[0]["description"])

    def test_same_real_path_is_not_reported_twice_across_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            project = root / "project"
            project_skills = project / ".agents" / "skills"
            global_skills = root / "global"
            target = self.write_skill(global_skills, "soia-pkm-clip-web", "剪藏网页")
            project_skills.mkdir(parents=True)
            os.symlink(target, project_skills / target.name)
            directory = root / "directory.json"
            self.write_directory(directory, [])

            result = self.run_finder(
                directory,
                "剪藏",
                "--project",
                str(project),
                "--scope",
                "both",
                "--skills-dir",
                str(global_skills),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)[0]["installed_scopes"], ["project"])

    def test_local_and_directory_candidates_are_ranked_together(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            skills = root / "global"
            self.write_skill(skills, "soia-pkm-clip-local", "剪藏网页到本地知识库")
            directory = root / "directory.json"
            self.write_directory(
                directory,
                [
                    {
                        "name": "soia-pkm-clip-remote",
                        "description": "剪藏网页",
                        "source": {"repository": "soia-open-pkm-vault-skills"},
                    }
                ],
            )

            result = self.run_finder(directory, "剪藏", "--scope", "global", "--skills-dir", str(skills))

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual([item["name"] for item in payload], ["soia-pkm-clip-local", "soia-pkm-clip-remote"])
            self.assertTrue(payload[0]["installed"])
            self.assertFalse(payload[1]["installed"])

    def test_missing_scope_and_agents_require_a_selection_instead_of_a_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            directory = root / "directory.json"
            self.write_directory(
                directory,
                [
                    {
                        "name": "soia-pkm-clip-remote",
                        "description": "剪藏网页",
                        "source": {"repository": "soia-open-pkm-vault-skills"},
                    }
                ],
            )
            no_project = root / "no-project"
            no_project.mkdir()

            result = self.run_finder(directory, "剪藏", cwd=no_project)

            self.assertEqual(result.returncode, 0, result.stderr)
            item = json.loads(result.stdout)[0]
            self.assertTrue(item["install_selection"]["selection_required"])
            self.assertEqual(item["install_selection"]["pending"], ["scope", "agents"])
            self.assertNotIn("install_cmd", item)

    def test_agents_are_intent_metadata_and_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            directory = root / "directory.json"
            self.write_directory(
                directory,
                [
                    {
                        "name": "soia-pkm-clip-remote",
                        "description": "剪藏网页",
                        "source": {"repository": "soia-open-pkm-vault-skills"},
                    }
                ],
            )
            project = root / "project"

            result = self.run_finder(
                directory,
                "剪藏",
                "--project",
                str(project),
                "--agent",
                "claude",
                "--agent",
                "codex",
                "--agent",
                "claude",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            item = json.loads(result.stdout)[0]
            self.assertEqual(item["requested_agents"], ["claude", "codex"])
            self.assertFalse(item["install_selection"]["selection_required"])
            self.assertEqual(item["install_selection"]["target"], {"kind": "skill", "name": item["name"]})
            self.assertEqual(item["install_selection"]["available_target_kinds"], ["skill", "domain", "all"])

    def test_both_is_a_discovery_scope_not_an_implicit_install_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            project = root / "project"
            directory = root / "directory.json"
            self.write_directory(
                directory,
                [
                    {
                        "name": "soia-pkm-clip-remote",
                        "description": "剪藏网页",
                        "source": {"repository": "soia-open-pkm-vault-skills"},
                    }
                ],
            )

            result = self.run_finder(
                directory,
                "剪藏",
                "--project",
                str(project),
                "--scope",
                "both",
                "--agent",
                "codex",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            selection = json.loads(result.stdout)[0]["install_selection"]
            self.assertIsNone(selection["scope"])
            self.assertEqual(selection["pending"], ["scope"])

    def test_chinese_review_phrases_expand_from_the_reference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            directory = root / "directory.json"
            self.write_directory(
                directory,
                [
                    {
                        "name": "soia-dev-review-panel",
                        "description": "review 调用链、数据流和模块边界",
                        "source": {"repository": "soia-open-dev-skills"},
                    }
                ],
            )

            result = self.run_finder(directory, "请做架构评审，理清调用链和数据流", cwd=root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)[0]["name"], "soia-dev-review-panel")

    def test_legacy_install_command_is_explicit_and_marked_deprecated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            directory = root / "directory.json"
            self.write_directory(
                directory,
                [
                    {
                        "name": "soia-pkm-clip-remote",
                        "description": "剪藏网页",
                        "source": {"repository": "soia-open-pkm-vault-skills"},
                    }
                ],
            )

            result = self.run_finder(directory, "剪藏", "--legacy-install-cmd", cwd=root)

            self.assertEqual(result.returncode, 0, result.stderr)
            item = json.loads(result.stdout)[0]
            self.assertIn("-g -a '*'", item["install_cmd"])
            self.assertTrue(item["install_cmd_deprecated"])

    def test_router_does_not_return_itself(self) -> None:
        with tempfile.TemporaryDirectory(prefix="find-skill-") as temp:
            root = Path(temp)
            project = root / "project"
            self.write_skill(project / ".agents" / "skills", "soia-meta-find-skill", "检索剪藏网盘技能")
            directory = root / "directory.json"
            self.write_directory(directory, [])

            result = self.run_finder(directory, "剪藏", "--project", str(project))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [])


if __name__ == "__main__":
    unittest.main()
