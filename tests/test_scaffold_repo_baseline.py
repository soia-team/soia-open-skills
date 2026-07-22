"""Tests for scripts/scaffold_repo_baseline.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scaffold_repo_baseline.py"


class ScaffoldRepoBaselineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_root = Path(self.temp_dir.name)
        self.output_root = self.temp_root / "output"
        self.manifest = self.temp_root / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                [
                    {
                        "name": "soia-pkm-skills",
                        "visibility": "public",
                        "domain": "pkm",
                        "title_zh": "SOIA 个人知识技能",
                        "desc": "面向个人知识管理的可复用技能。",
                        "incubator": False,
                    },
                    {
                        "name": "soia-corp-skills",
                        "visibility": "private",
                        "domain": "corp",
                        "title_zh": "SOIA 企业内部技能",
                        "desc": "企业内部专用技能。",
                        "incubator": True,
                        "readme_note": "注意：corp 表示企业内部域。",
                    },
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def run_scaffolder(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--manifest",
                str(self.manifest),
                "--source-root",
                str(ROOT),
                "--output-root",
                str(self.output_root),
                *extra,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_generates_public_and_private_baselines(self) -> None:
        result = self.run_scaffolder()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        public = self.output_root / "soia-pkm-skills"
        private = self.output_root / "soia-corp-skills"
        for repo in (public, private):
            for relative in (
                "README.md",
                "README.en.md",
                "AGENTS.md",
                "SKILL_SPEC.md",
                "DATA_STORAGE_SPEC.md",
                "CONTRIBUTING.md",
                "SECURITY.md",
                ".gitignore",
                "requirements-dev.txt",
                "templates/skill-template/SKILL.md.template",
                "scripts/audit_skills.py",
                "scripts/generate_skill_catalog.py",
                ".github/workflows/audit.yml",
                "skills/README.md",
                "tests/test_baseline.py",
                "BASELINE_VERSION",
            ):
                self.assertTrue((repo / relative).is_file(), f"missing {repo.name}/{relative}")

        self.assertTrue((public / "LICENSE").is_file())
        self.assertFalse((private / "LICENSE").exists())
        self.assertEqual((public / "README.md").read_text(encoding="utf-8").splitlines()[0], "# SOIA 个人知识技能")
        private_readme = (private / "README.md").read_text(encoding="utf-8")
        self.assertEqual(private_readme.splitlines()[0], "# SOIA 企业内部技能")
        self.assertIn("Proprietary - internal use only", private_readme)
        self.assertIn("本仓永不开源；不进入公开 catalog 与路由清单", private_readme)
        self.assertIn("暂无技能", (public / "skills" / "README.md").read_text(encoding="utf-8"))
        self.assertNotIn("soia-open-skills", (public / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn(
            'VALID_DOMAINS = ("corp",)',
            (private / "scripts" / "audit_skills.py").read_text(encoding="utf-8"),
        )
        baseline = (public / "BASELINE_VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(baseline, r"^[0-9a-f]{40} \d{4}-\d{2}-\d{2} baseline-v1$")

        for repo in (public, private):
            smoke = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(smoke.returncode, 0, smoke.stdout + smoke.stderr)

    def test_check_reports_diff_without_writing(self) -> None:
        self.assertEqual(self.run_scaffolder().returncode, 0)
        readme = self.output_root / "soia-pkm-skills" / "README.md"
        readme.write_text("changed\n", encoding="utf-8")

        result = self.run_scaffolder("--check")

        self.assertEqual(result.returncode, 1)
        self.assertIn("actual/README.md", result.stdout)
        self.assertEqual(readme.read_text(encoding="utf-8"), "changed\n")


if __name__ == "__main__":
    unittest.main()
