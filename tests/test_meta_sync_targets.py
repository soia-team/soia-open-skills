#!/usr/bin/env python3
"""Offline regression tests for distinct Antigravity and Gemini skill targets."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/soia-meta-sync-skills/scripts/sync_soia_skills.py"
)


class MetaSyncTargetTests(unittest.TestCase):
    def test_repository_split_retired_names_are_registered(self) -> None:
        retired = set(runpy.run_path(str(SCRIPT))["RETIRED_SKILLS"])
        expected = {
            "soia-pkm-compose-article-draft",
            "soia-pkm-cover-image",
            "soia-pkm-publish-wechat-draft",
            "soia-pkm-publish-x-thread",
            "soia-pkm-publish-x-article",
            "soia-pkm-publish-rednote-card",
            "soia-dev-sync-skills",
            "soia-dev-skill-release",
            "soia-dev-prompt-clarity",
            "soia-dev-ai-cli-upgrade",
        }
        self.assertTrue(expected.issubset(retired), expected - retired)

    def run_script(self, home: Path, *args: str, path: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["XDG_STATE_HOME"] = str(home / "state")
        if path is not None:
            env["PATH"] = path
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def make_source(self, root: Path) -> Path:
        source = root / "source"
        skill = source / "soia-test-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: soia-test-skill\ndescription: test fixture\n---\n",
            encoding="utf-8",
        )
        return source

    def add_skill(self, source: Path, name: str) -> None:
        skill = source / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test fixture\n---\n",
            encoding="utf-8",
        )

    def test_list_targets_keeps_agy_and_gemini_distinct(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            home = Path(temp)
            result = self.run_script(home, "--list-targets")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("agy", result.stdout)
            self.assertIn("~/.gemini/antigravity-cli/skills", result.stdout)
            self.assertIn("gemini", result.stdout)
            self.assertIn("~/.gemini/skills", result.stdout)

    def test_write_sync_creates_two_independent_targets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                "agy,gemini",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            agy_link = root / "home/.gemini/antigravity-cli/skills/soia-test-skill"
            gemini_link = root / "home/.gemini/skills/soia-test-skill"
            self.assertTrue(agy_link.is_symlink())
            self.assertTrue(gemini_link.is_symlink())
            self.assertNotEqual(agy_link.parent, gemini_link.parent)
            expected = (source / "soia-test-skill").resolve()
            self.assertEqual(agy_link.resolve(), expected)
            self.assertEqual(gemini_link.resolve(), expected)

    def test_prune_dangling_soia_symlinks_respects_scope_and_no_prune(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            target = root / "target"
            target.mkdir()

            dangling_soia = target / "soia-retired-skill"
            dangling_unrelated = target / "third-party-retired-skill"
            live_target = root / "live-skill"
            live_target.mkdir()
            live_soia = target / "soia-live-skill"

            dangling_soia.symlink_to(root / "missing-soia-skill", target_is_directory=True)
            dangling_unrelated.symlink_to(
                root / "missing-third-party-skill", target_is_directory=True
            )
            live_soia.symlink_to(live_target, target_is_directory=True)
            live_link_target = live_soia.readlink()

            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                str(target),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(dangling_soia.is_symlink())
            self.assertIn("retired dirs cleaned: 1", result.stdout)
            self.assertTrue(dangling_unrelated.is_symlink())
            self.assertTrue(live_soia.is_symlink())
            self.assertEqual(live_soia.readlink(), live_link_target)

            dangling_soia.symlink_to(root / "still-missing", target_is_directory=True)
            no_prune = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                str(target),
                "--no-prune",
            )
            self.assertEqual(no_prune.returncode, 0, no_prune.stderr)
            self.assertIn("retired dirs cleaned: 0", no_prune.stdout)
            self.assertTrue(dangling_soia.is_symlink())
            self.assertTrue(dangling_unrelated.is_symlink())
            self.assertTrue(live_soia.is_symlink())
            self.assertEqual(live_soia.readlink(), live_link_target)

    def test_default_targets_detect_installed_agy_without_existing_skill_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            agy = bin_dir / "agy"
            agy.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            agy.chmod(0o755)
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--dry-run",
                path=f"{bin_dir}:/usr/bin:/bin",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[agy] Antigravity CLI", result.stdout)

    def test_discovery_includes_public_pkm_from_shared_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            self.add_skill(source, "soia-pkm-library")
            self.add_skill(source, "third-party-skill")
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--list-skills",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("soia-test-skill", result.stdout)
            self.assertIn("soia-pkm-library", result.stdout)
            self.assertNotIn("third-party-skill", result.stdout)

    def test_single_public_pkm_sync_is_not_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            self.add_skill(source, "soia-pkm-library")
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                "soia",
                "--skills",
                "soia-pkm-library",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            link = root / "home/.soia/skills/soia-pkm-library"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (source / "soia-pkm-library").resolve())

    def test_two_runs_in_same_second_keep_two_audit_logs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            home = root / "home"
            first = self.run_script(
                home,
                "--source-dir",
                str(source),
                "--targets",
                "soia",
                "--dry-run",
            )
            second = self.run_script(
                home,
                "--source-dir",
                str(source),
                "--targets",
                "soia",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            logs = sorted((home / "state/soia-meta-sync-skills").glob("sync-*.log"))
            self.assertEqual(len(logs), 2)
            modes = {line for log in logs for line in log.read_text().splitlines() if line.startswith("mode:")}
            self.assertEqual(modes, {"mode: dry-run", "mode: write"})

    def add_skill_with_deps(self, source: Path, name: str, hard: list[str], flow: bool = True) -> None:
        skill = source / name
        skill.mkdir(parents=True)
        if flow:
            deps_block = f"dependencies:\n  hard: [{', '.join(hard)}]\n"
        else:
            items = "\n".join(f"    - {dep}" for dep in hard)
            deps_block = f"dependencies:\n  hard:\n{items}\n"
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test fixture\n{deps_block}---\n",
            encoding="utf-8",
        )

    def test_single_skill_sync_pulls_hard_dependency_closure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            self.add_skill(source, "soia-pkm-alipan")
            self.add_skill_with_deps(source, "soia-pkm-alipan-curator", ["soia-pkm-alipan"])
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                "soia",
                "--skills",
                "soia-pkm-alipan-curator",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("auto-including hard dependency: soia-pkm-alipan", result.stdout)
            curator = root / "home/.soia/skills/soia-pkm-alipan-curator"
            dep = root / "home/.soia/skills/soia-pkm-alipan"
            self.assertTrue(curator.is_symlink())
            self.assertTrue(dep.is_symlink())
            # closure sync must not link unrelated skills
            self.assertFalse((root / "home/.soia/skills/soia-test-skill").exists())

    def test_hard_dependency_closure_is_transitive_block_list(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            self.add_skill(source, "soia-dep-c")
            self.add_skill_with_deps(source, "soia-dep-b", ["soia-dep-c"], flow=False)
            self.add_skill_with_deps(source, "soia-dep-a", ["soia-dep-b"], flow=False)
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                "soia",
                "--skills",
                "soia-dep-a",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("soia-dep-a", "soia-dep-b", "soia-dep-c"):
                self.assertTrue(
                    (root / f"home/.soia/skills/{name}").is_symlink(), name
                )

    def test_no_deps_flag_skips_closure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            self.add_skill(source, "soia-pkm-alipan")
            self.add_skill_with_deps(source, "soia-pkm-alipan-curator", ["soia-pkm-alipan"])
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                "soia",
                "--skills",
                "soia-pkm-alipan-curator",
                "--no-deps",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("auto-including", result.stdout)
            self.assertTrue(
                (root / "home/.soia/skills/soia-pkm-alipan-curator").is_symlink()
            )
            self.assertFalse((root / "home/.soia/skills/soia-pkm-alipan").exists())

    def test_missing_hard_dependency_warns_but_syncs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            self.add_skill_with_deps(
                source, "soia-pkm-alipan-curator", ["soia-pkm-alipan"]
            )
            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                "soia",
                "--skills",
                "soia-pkm-alipan-curator",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("hard dependency not in source-dir: soia-pkm-alipan", result.stderr)
            self.assertIn("npx skills add", result.stderr)
            self.assertTrue(
                (root / "home/.soia/skills/soia-pkm-alipan-curator").is_symlink()
            )

    def test_cli_exclude_unlinks_existing_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            source = self.make_source(root)
            self.add_skill(source, "soia-keep-skill")
            target = root / "target"
            initial = self.run_script(
                root / "home", "--source-dir", str(source), "--targets", str(target)
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)

            result = self.run_script(
                root / "home",
                "--source-dir",
                str(source),
                "--targets",
                str(target),
                "--exclude-skills",
                "soia-test-skill",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("unlink excluded: soia-test-skill", result.stdout)
            self.assertFalse((target / "soia-test-skill").is_symlink())
            self.assertTrue((target / "soia-keep-skill").is_symlink())

    def test_saved_exclude_survives_later_full_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            home = root / "home"
            source = self.make_source(root)
            saved = self.run_script(
                home,
                "--source-dir",
                str(source),
                "--targets",
                "soia",
                "--exclude-skills",
                "soia-test-skill",
                "--save-excludes",
            )
            self.assertEqual(saved.returncode, 0, saved.stderr)
            config = home / ".config/soia-skills/soia-meta-sync-skills/config.yml"
            self.assertIn("soia-test-skill", config.read_text(encoding="utf-8"))

            full_sync = self.run_script(
                home, "--source-dir", str(source), "--targets", "soia"
            )
            self.assertEqual(full_sync.returncode, 0, full_sync.stderr)
            self.assertIn("excludes: soia-test-skill", full_sync.stdout)
            self.assertFalse((home / ".soia/skills/soia-test-skill").is_symlink())

    def test_persistent_exclude_does_not_affect_other_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sync-targets-") as temp:
            root = Path(temp)
            home = root / "home"
            source = self.make_source(root)
            saved = self.run_script(
                home,
                "--source-dir",
                str(source),
                "--targets",
                "codex",
                "--exclude-skills",
                "soia-test-skill",
                "--save-excludes",
            )
            self.assertEqual(saved.returncode, 0, saved.stderr)

            result = self.run_script(
                home,
                "--source-dir",
                str(source),
                "--targets",
                "codex,claude",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((home / ".codex/skills/soia-test-skill").is_symlink())
            self.assertTrue((home / ".claude/skills/soia-test-skill").is_symlink())


if __name__ == "__main__":
    unittest.main()
