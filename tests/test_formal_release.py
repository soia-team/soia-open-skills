#!/usr/bin/env python3
"""Offline tests for the formal-release helpers (dev-branch model)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "soia-meta-skill-release" / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_next_snapshot_bumps_minor(self) -> None:
        self.assertEqual(RELEASE.next_snapshot("1.9.0"), "1.10.0-SNAPSHOT")
        self.assertEqual(RELEASE.next_snapshot("2.0.3"), "2.1.0-SNAPSHOT")


if __name__ == "__main__":
    unittest.main()
