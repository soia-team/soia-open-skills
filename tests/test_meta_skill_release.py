#!/usr/bin/env python3
"""Offline regression tests for the merge-after skill release workflow."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/soia-meta-skill-release/scripts/release_skills.py"
SPEC = importlib.util.spec_from_file_location("release_skills", SCRIPT)
assert SPEC and SPEC.loader
release_skills = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_skills
SPEC.loader.exec_module(release_skills)


class MetaSkillReleaseTests(unittest.TestCase):
    def args(self, *extra: str):
        return release_skills.parse_args(["--repo", "owner/repo", "--skills", "soia-new", *extra])

    def skill(self, directory: Path, name: str, version: str = "1.0.0") -> Path:
        path = directory / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(
            f"---\nname: {name}\nversion: {version}\ndescription: fixture\n---\n",
            encoding="utf-8",
        )
        return path

    def lock(self, home: Path, names: dict[str, str]) -> None:
        path = home / ".agents/.skill-lock.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"skills": {name: {"source": source} for name, source in names.items()}}), encoding="utf-8")

    def prepare_versions(self, root: Path) -> tuple[Path, Path]:
        home = root / "home"
        repo = root / "repo"
        self.skill(repo / "skills", "soia-new")
        self.skill(home / ".agents/skills", "soia-new")
        self.skill(home / ".agents/skills", "soia-meta-sync-skills")
        self.lock(home, {"soia-new": "owner/repo"})
        return home, repo

    def test_repo_dir_explicit_argument_wins_over_environment_root(self) -> None:
        home = Path("/test/home")
        explicit = Path("/checkouts/explicit-repo")
        resolved = release_skills.resolve_repo_dir(
            "owner/any-repo",
            home,
            str(explicit),
            {"SOIA_SKILL_REPOS_ROOT": "/checkouts/shared"},
        )
        self.assertEqual(resolved, explicit)

    def test_repo_dir_uses_environment_root_for_arbitrary_repo_name(self) -> None:
        resolved = release_skills.resolve_repo_dir(
            "another-owner/skill-repo-14",
            Path("/test/home"),
            environ={"SOIA_SKILL_REPOS_ROOT": "/checkouts/shared"},
        )
        self.assertEqual(resolved, Path("/checkouts/shared/skill-repo-14"))

    def test_repo_dir_uses_private_config_root_after_process_environment(self) -> None:
        resolved = release_skills.resolve_repo_dir(
            "another-owner/skill-repo-14",
            Path("/test/home"),
            environ={},
            config_env={"SOIA_SKILL_REPOS_ROOT": "/checkouts/private"},
        )
        self.assertEqual(resolved, Path("/checkouts/private/skill-repo-14"))

    def test_process_environment_wins_over_private_config_root(self) -> None:
        resolved = release_skills.resolve_repo_dir(
            "another-owner/skill-repo-14",
            Path("/test/home"),
            environ={"SOIA_SKILL_REPOS_ROOT": "/checkouts/process"},
            config_env={"SOIA_SKILL_REPOS_ROOT": "/checkouts/private"},
        )
        self.assertEqual(resolved, Path("/checkouts/process/skill-repo-14"))

    def test_default_config_uses_v2_then_falls_back_to_v1_with_migration_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            current = release_skills.default_config_file(home, {})
            legacy = next(release_skills.legacy_config_files(home, {}))
            legacy.parent.mkdir(parents=True)
            legacy.write_text("schema_version: 1\nenv: {}\n", encoding="utf-8")
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(release_skills.resolve_config_file(None, home, {}), legacy)
            self.assertIn("migrate when convenient", stderr.getvalue())
            current.parent.mkdir(parents=True)
            current.write_text("schema_version: 1\nenv: {}\n", encoding="utf-8")
            self.assertEqual(release_skills.resolve_config_file(None, home, {}), current)

    def test_repo_dir_falls_back_to_deprecated_legacy_convention(self) -> None:
        home = Path("/test/home")
        with self.assertWarns(DeprecationWarning):
            resolved = release_skills.resolve_repo_dir("owner/legacy-repo", home, environ={})
        self.assertEqual(
            resolved,
            home / "owen/code/gitrepo/jiuan/server/v7/legacy-repo",
        )

    def test_steps_run_in_order_and_stop_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home, repo = self.prepare_versions(Path(temp))
            args = self.args("--repo-dir", str(repo))
            calls: list[list[str]] = []

            def fake_run(command):
                calls.append(command)
                if command[:3] == ["npx", "skills", "update"]:
                    raise release_skills.ReleaseError("update failed")

            with patch.object(release_skills, "run_command", side_effect=fake_run):
                self.assertEqual(release_skills.release(args, home=home), 1)
            self.assertEqual([call[:3] for call in calls], [["npx", "skills", "add"], ["npx", "skills", "update"]])

    def test_removed_names_are_cleaned_from_five_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            for root in release_skills.INSTALL_ROOTS:
                self.skill(home / root, "soia-old")
            cleaned = release_skills.remove_old_skills(home, ["soia-old"], dry_run=False)
            self.assertEqual(cleaned, {"soia-old": 5})
            for root in release_skills.INSTALL_ROOTS:
                self.assertFalse((home / root / "soia-old").exists())

    def test_codex_links_missing_installed_skills_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            source = self.skill(home / ".agents/skills", "soia-new")
            evidence = home / ".agents/skills/historical-evidence"
            evidence.mkdir(parents=True)
            created = release_skills.fill_codex_links(home, dry_run=False)
            link = home / ".codex/skills/soia-new"
            self.assertEqual(created, ["soia-new"])
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), source.resolve())
            self.assertFalse((home / ".codex/skills/historical-evidence").exists())

    def test_lock_reconciliation_accepts_expected_source_and_rejects_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            self.lock(home, {"soia-new": "owner/repo"})
            release_skills.verify_lock(home, "owner/repo", ["soia-new"], [])
            with self.assertRaisesRegex(release_skills.ReleaseError, "missing/wrong source"):
                release_skills.verify_lock(home, "owner/repo", ["soia-missing"], [])

    def test_dry_run_executes_no_command_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            args = self.args("--repo-dir", str(Path(temp) / "repo"), "--removed", "soia-old", "--dry-run")
            with patch.object(release_skills, "run_command") as run, patch.object(release_skills, "remove_old_skills") as remove, patch.object(release_skills, "fill_codex_links") as links:
                self.assertEqual(release_skills.release(args, home=home), 0)
            run.assert_not_called()
            remove.assert_not_called()
            links.assert_not_called()
            self.assertFalse(home.exists())


if __name__ == "__main__":
    unittest.main()
