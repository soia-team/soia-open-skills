#!/usr/bin/env python3
"""Offline tests for the formal-release helpers (dev-branch model)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "soia-meta-skill-release" / "scripts"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(name: str):
    """加载 skill-release 的发布脚本。"""
    return _load(SCRIPTS / f"{name}.py")


def load_script(name: str):
    """加载元仓 scripts/ 下的治理脚本。"""
    return _load(ROOT / "scripts" / f"{name}.py")


NOTES = load("generate_release_notes")
RELEASE = load("formal_release")


class ReleaseNotesTests(unittest.TestCase):
    def test_classify_conventional_prefixes_with_scope(self) -> None:
        self.assertEqual(NOTES.classify("feat(image): add preset (#32)"), "新增")
        self.assertEqual(NOTES.classify("fix: crash on success path (#208)"), "修复")
        self.assertEqual(NOTES.classify("docs(readme): badges (#31)"), "维护")
        self.assertEqual(NOTES.classify("Update translation"), "其他")

    def test_build_notes_omits_empty_sections_and_keeps_placeholder(self) -> None:
        notes = NOTES.build_notes("1.9.0", ["feat: a (#1)", "fix: b (#2)"])
        self.assertIn("# v1.9.0", notes)
        self.assertIn("## 新增", notes)
        self.assertIn("## 修复", notes)
        self.assertNotIn("## 维护", notes)
        self.assertIn("一句话摘要", notes)

    def test_build_notes_uses_given_summary(self) -> None:
        notes = NOTES.build_notes("1.9.0", [], summary="本版聚焦发布自动化。")
        self.assertIn("本版聚焦发布自动化。", notes)
        self.assertNotIn("<!--", notes)


class ChangelogTests(unittest.TestCase):
    NOTES = "# v1.9.0\n\n本版聚焦发布自动化。\n\n## 新增\n- feat: a (#1)\n"

    def test_entry_transforms_notes_heading(self) -> None:
        entry = RELEASE.changelog_entry("1.9.0", self.NOTES, "2026-08-02")
        self.assertTrue(entry.startswith("## v1.9.0 — 2026-08-02"))
        self.assertIn("本版聚焦发布自动化。", entry)
        self.assertNotIn("# v1.9.0\n", entry.split("——")[0])

    def test_prepend_creates_file_with_header(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            RELEASE.prepend_changelog(Path(tmp), "1.9.0", self.NOTES, date="2026-08-02")
            text = (Path(tmp) / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Changelog"))
        self.assertIn("## v1.9.0 — 2026-08-02", text)

    def test_prepend_keeps_existing_entries_newest_first(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            RELEASE.prepend_changelog(Path(tmp), "1.9.0", self.NOTES, date="2026-08-01")
            RELEASE.prepend_changelog(
                Path(tmp), "1.10.0", "# v1.10.0\n\n下一版。\n", date="2026-08-02")
            text = (Path(tmp) / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertLess(text.find("## v1.10.0"), text.find("## v1.9.0"))
        self.assertEqual(text.count("# Changelog"), 1)


class VersionHelperTests(unittest.TestCase):
    def test_strip_snapshot(self) -> None:
        self.assertEqual(RELEASE.strip_snapshot("1.9.0-SNAPSHOT"), "1.9.0")

    def test_strip_snapshot_rejects_release_version(self) -> None:
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.strip_snapshot("1.9.0")

    def test_next_snapshot_bumps_patch_not_minor(self) -> None:
        """默认只 +patch：刚发完版还不知道下一版性质，+minor 属于预判。"""
        self.assertEqual(RELEASE.next_snapshot("1.9.0"), "1.9.1-SNAPSHOT")
        self.assertEqual(RELEASE.next_snapshot("2.0.3"), "2.0.4-SNAPSHOT")
        self.assertEqual(RELEASE.next_snapshot("1.11.0"), "1.11.1-SNAPSHOT")


class VersionTrainCheckerTests(unittest.TestCase):
    """跨仓列车体检：dev 必带 -SNAPSHOT、main 必不带。

    回归 2026-08-03：pkm 与 media 的发版中断在定稿与重开之间，dev 静默停在
    正式版本号，无任何检测发现。
    """

    def setUp(self) -> None:
        self.mod = load_script("check_version_trains")

    def _inspect(self, main_v: str, dev_v: str) -> dict:
        from unittest.mock import patch

        with patch.object(self.mod, "fetch_version",
                          side_effect=lambda _r, ref: dev_v if ref == "dev" else main_v):
            return self.mod.inspect("demo")

    def test_flags_dev_without_snapshot(self) -> None:
        result = self._inspect("1.9.0", "1.9.0")
        self.assertTrue(any("dev 未开列车" in p for p in result["problems"]))

    def test_flags_snapshot_leaking_into_main(self) -> None:
        result = self._inspect("1.9.0-SNAPSHOT", "1.10.0-SNAPSHOT")
        self.assertTrue(any("main 带 -SNAPSHOT" in p for p in result["problems"]))

    def test_healthy_pair_has_no_problems(self) -> None:
        result = self._inspect("1.9.0", "1.10.0-SNAPSHOT")
        self.assertEqual(result["problems"], [])


class MergeConflictDetectionTests(unittest.TestCase):
    """冲突检测必须靠退出码 + stage 条目，不能匹配 "CONFLICT" 文案。

    回归 2026-08-03：初版按字符串匹配，在中文 locale 下 git 输出「冲突（内容）」，
    检测静默失效——真造一个冲突仓才发现。
    """

    def setUp(self) -> None:
        self.mod = load_script("check_version_trains")

    def _make_repo(self, conflicting: bool) -> Path:
        import os
        import shutil
        import subprocess
        import tempfile

        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "a@b",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "a@b",
            "PATH": os.environ["PATH"],
        }

        def git(*args: str) -> None:
            subprocess.run(["git", "-C", tmp, *args], check=True,
                           capture_output=True, env=env)

        subprocess.run(["git", "init", "-q", tmp], check=True,
                       capture_output=True, env=env)
        git("branch", "-m", "main")
        (Path(tmp) / "f.txt").write_text("base\n", encoding="utf-8")
        git("add", ".")
        git("commit", "-qm", "init")
        git("checkout", "-qb", "dev")
        (Path(tmp) / "f.txt").write_text("dev\n", encoding="utf-8")
        git("commit", "-qam", "dev")
        git("checkout", "-q", "main")
        # conflicting=True 时两边改同一文件；否则 main 只新增无关文件
        (Path(tmp) / ("f.txt" if conflicting else "g.txt")).write_text(
            "main\n", encoding="utf-8")
        git("add", ".")
        git("commit", "-qam", "main")
        git("update-ref", "refs/remotes/origin/main", "refs/heads/main")
        git("update-ref", "refs/remotes/origin/dev", "refs/heads/dev")
        return Path(tmp)

    def _merge_tree(self, repo: Path):
        import subprocess
        return subprocess.run(
            ["git", "-C", str(repo), "merge-tree", "--write-tree",
             "origin/main", "origin/dev"], capture_output=True, text=True)

    def test_detects_real_conflict(self) -> None:
        result = self._merge_tree(self._make_repo(conflicting=True))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mod.conflicted_paths(result.stdout), ["f.txt"])

    def test_clean_merge_reports_no_conflict(self) -> None:
        result = self._merge_tree(self._make_repo(conflicting=False))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.mod.conflicted_paths(result.stdout), [])


class SkillVersionGuardTests(unittest.TestCase):
    """生成物落在技能目录里，刷新它不该被当成技能改动。

    回归 2026-08-03：路由索引 skill-directory.json 位于 soia-meta-find-skill/
    references/ 下，重生成后守卫误报「技能内容变了但版本没 bump」，CI 直接挂。
    """

    def setUp(self) -> None:
        self.mod = load_script("check_skill_versions")

    def test_generated_index_is_not_a_skill_change(self) -> None:
        self.assertIn(
            "skills/soia-meta-find-skill/references/skill-directory.json",
            self.mod.GENERATED_PATHS)

    def test_changed_skills_skips_generated_paths(self) -> None:
        from unittest.mock import patch

        listing = (
            "skills/soia-meta-find-skill/references/skill-directory.json\n"
            "skills/soia-meta-skill-release/SKILL.md\n"
        )
        with patch.object(self.mod, "git", return_value=(0, listing)):
            changed = self.mod.changed_skills(Path("."), "origin/dev")
        self.assertEqual(changed, ["soia-meta-skill-release"])


if __name__ == "__main__":
    unittest.main()
