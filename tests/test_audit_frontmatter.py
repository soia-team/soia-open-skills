#!/usr/bin/env python3
"""Regression tests for mechanically enforced skill authoring contracts."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/audit_skills.py"
SPEC = importlib.util.spec_from_file_location("audit_frontmatter_under_test", SCRIPT)
assert SPEC and SPEC.loader
audit_skills = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_skills
SPEC.loader.exec_module(audit_skills)


CUSTOMER_BODY = """\
## 客户可读说明
### 这个技能可以做什么
能力。
### 客户如何使用
用法。
### 依赖与安装
无。
### 私密信息与中间数据
不保存。
### 日志与完成回执
输出结果。
"""


def write_skill(
    root: Path,
    name: str,
    *,
    omit: frozenset[str] = frozenset(),
    created_at: str = "2026-07-22 12:00:00",
    updated_at: str = "2026-07-22 12:00:00",
    include_private_section: bool = True,
) -> Path:
    values = {
        "name": name,
        "description": "测试技能",
        "version": "1.0.0",
        "created_at": created_at,
        "updated_at": updated_at,
        "created_by": "test-model",
        "updated_by": "test-model",
    }
    frontmatter = "\n".join(f"{key}: {value}" for key, value in values.items() if key not in omit)
    body = CUSTOMER_BODY
    if not include_private_section:
        body = body.replace("### 私密信息与中间数据\n不保存。\n", "")
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter}\n---\n\n# {name}\n\n{body}",
        encoding="utf-8",
    )
    return skill_dir


def findings_for(root: Path, name: str):
    prefix = f"skills/{name}"
    return [finding for finding in audit_skills.collect_findings(root) if finding.path.startswith(prefix)]


class RequiredFrontmatterTests(unittest.TestCase):
    def test_each_missing_required_field_is_error_when_not_grandfathered(self) -> None:
        for key in sorted(audit_skills.REQUIRED_FRONTMATTER):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                name = "soia-dev-test-frontmatter"
                write_skill(root, name, omit=frozenset({key}))
                findings = findings_for(root, name)
                self.assertTrue(
                    any(
                        finding.severity == "ERROR"
                        and finding.message == f"missing required frontmatter: {key}"
                        for finding in findings
                    )
                )

    def test_missing_required_field_is_nonblocking_warn_when_grandfathered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "soia-dev-test-frontmatter"
            write_skill(root, name, omit=frozenset({"name"}))
            with patch.object(audit_skills, "GRANDFATHER_MISSING_FRONTMATTER", frozenset({name})):
                findings = findings_for(root, name)
            hit = next(f for f in findings if "grandfathered missing required frontmatter" in f.message)
            self.assertEqual(hit.severity, "WARN")
            self.assertFalse(hit.strict_blocking)
            self.assertFalse(any(f.severity == "ERROR" and "frontmatter name" in f.message for f in findings))


class FrontmatterDatetimeTests(unittest.TestCase):
    def test_invalid_datetime_source_format_is_error_when_not_grandfathered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "soia-dev-test-datetime"
            write_skill(root, name, updated_at="2026-07-22T12:00:00")
            findings = findings_for(root, name)
            self.assertTrue(
                any(
                    finding.severity == "ERROR"
                    and finding.message == "frontmatter updated_at must use YYYY-MM-DD HH:mm:ss"
                    for finding in findings
                )
            )

    def test_invalid_datetime_is_nonblocking_warn_when_grandfathered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "soia-dev-test-datetime"
            write_skill(root, name, created_at='"2026-13-22 12:00:00"')
            with patch.object(audit_skills, "GRANDFATHER_INVALID_DATETIME", frozenset({name})):
                findings = findings_for(root, name)
            hit = next(f for f in findings if "grandfathered frontmatter created_at" in f.message)
            self.assertEqual(hit.severity, "WARN")
            self.assertFalse(hit.strict_blocking)


class PrivateDataSectionTests(unittest.TestCase):
    def test_missing_section_is_error_for_new_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "soia-dev-test-private"
            write_skill(root, name, include_private_section=False)
            findings = findings_for(root, name)
            self.assertTrue(
                any(
                    finding.severity == "ERROR"
                    and finding.message == "missing customer-readable private/intermediate data section"
                    for finding in findings
                )
            )

    def test_missing_section_is_nonblocking_warn_for_real_grandfathered_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "soia-dev-task-execute"
            write_skill(root, name, include_private_section=False)
            findings = findings_for(root, name)
            hit = next(f for f in findings if "grandfathered missing customer-readable" in f.message)
            self.assertEqual(hit.severity, "WARN")
            self.assertFalse(hit.strict_blocking)


class SkillNameSegmentTests(unittest.TestCase):
    def test_range_is_enforced_and_explicit_exemption_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exempt = "soia-pkm-maintain"
            short = "soia-dev-helper"
            long = "soia-dev-one-two-three-four-five"
            valid = "soia-dev-test-helper"
            for name in (exempt, short, long, valid):
                write_skill(root, name)

            exempt_findings = findings_for(root, exempt)
            exemption = next(f for f in exempt_findings if "segment-count exemption" in f.message)
            self.assertEqual(exemption.severity, "WARN")
            self.assertFalse(exemption.strict_blocking)

            for name in (short, long):
                self.assertTrue(
                    any(
                        finding.severity == "ERROR" and "must have 4-6 kebab-case segments" in finding.message
                        for finding in findings_for(root, name)
                    )
                )
            self.assertFalse(
                any("segments" in finding.message for finding in findings_for(root, valid))
            )


if __name__ == "__main__":
    unittest.main()
