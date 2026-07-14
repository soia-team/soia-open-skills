#!/usr/bin/env python3
"""Regression tests for the repository skill audit."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit_skills = load_module("audit_skills_under_test", "scripts/audit_skills.py")


def write_skill(root: Path, name: str, body: str) -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: 测试技能\n---\n\n# {name}\n\n{body}\n",
        encoding="utf-8",
    )
    return skill_dir


def link_findings(root: Path):
    return [
        finding
        for finding in audit_skills.collect_findings(root)
        if finding.message.startswith("relative link")
    ]


class RepositoryDocumentAuditTests(unittest.TestCase):
    def test_english_readme_is_included_in_repository_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(root, "soia-test-root-doc", "No resources.")
            (root / "README.en.md").write_text(
                "Private path: /Users/alice/private/notes.md\n",
                encoding="utf-8",
            )
            findings = audit_skills.collect_findings(root)
            self.assertTrue(
                any(
                    finding.path == "README.en.md"
                    and finding.message == "hardcoded absolute user path"
                    for finding in findings
                )
            )

    def test_documentation_url_with_home_segment_is_not_a_local_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(root, "soia-test-root-doc-url", "No resources.")
            (root / "README.md").write_text(
                "Official docs: https://open.feishu.cn/document/home/introduction-to-custom-app-development\n",
                encoding="utf-8",
            )
            findings = audit_skills.collect_findings(root)
            self.assertFalse(
                any(
                    finding.path == "README.md"
                    and finding.message == "hardcoded absolute user path"
                    for finding in findings
                )
            )


class FrontmatterYamlTests(unittest.TestCase):
    def test_folded_frontmatter_description_is_supported(self) -> None:
        text = "---\nname: soia-folded\ndescription: >\n  First line\n  second line\n---\n"
        fields, errors = audit_skills.parse_frontmatter(text)
        self.assertEqual(errors, [])
        self.assertEqual(fields["description"], "First line second line")

    def test_invalid_and_non_string_frontmatter_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad_yaml = root / "skills/soia-bad-yaml"
            bad_yaml.mkdir(parents=True)
            (bad_yaml / "SKILL.md").write_text(
                '---\nname: soia-bad-yaml\ndescription: "unterminated\n---\n',
                encoding="utf-8",
            )
            nonstring = root / "skills/soia-nonstring"
            nonstring.mkdir(parents=True)
            (nonstring / "SKILL.md").write_text(
                "---\nname: soia-nonstring\ndescription: [foo]\n---\n",
                encoding="utf-8",
            )
            messages = [hit.message for hit in audit_skills.collect_findings(root)]
            self.assertTrue(any("invalid YAML frontmatter" in message for message in messages))
            self.assertTrue(any("frontmatter description must be a string" in message for message in messages))


class AuthoringQualityTests(unittest.TestCase):
    def test_long_skill_is_flagged_for_refactoring(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            body = "\n".join(f"line-{index}" for index in range(audit_skills.MAX_SKILL_LINES + 1))
            skill = write_skill(root, "soia-long-skill", body)
            findings = audit_skills.collect_findings(root)
            self.assertTrue(
                any(
                    finding.path == str(skill.relative_to(root) / "SKILL.md")
                    and finding.severity == "INFO"
                    and "split durable detail" in finding.message
                    for finding in findings
                )
            )

    def test_complex_skill_gets_forward_test_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = write_skill(root, "soia-complex-skill", "正文。")
            (skill / "scripts").mkdir()
            findings = audit_skills.collect_findings(root)
            self.assertTrue(
                any(
                    finding.severity == "INFO"
                    and "forward test" in finding.message
                    for finding in findings
                )
            )


class OpenaiMetadataYamlTests(unittest.TestCase):
    def test_invalid_yaml_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = write_skill(root, "soia-test-broken-yaml", "正文。")
            (skill / "agents").mkdir()
            (skill / "agents/openai.yaml").write_text(
                'interface:\n  display_name: "unterminated\n',
                encoding="utf-8",
            )
            messages = [hit.message for hit in audit_skills.collect_findings(root)]
            self.assertTrue(any("invalid YAML metadata" in message for message in messages))

    def test_missing_interface_mapping_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = write_skill(root, "soia-test-no-interface", "正文。")
            (skill / "agents").mkdir()
            (skill / "agents/openai.yaml").write_text("name: whatever\n", encoding="utf-8")
            messages = [hit.message for hit in audit_skills.collect_findings(root)]
            self.assertTrue(any("missing interface mapping" in message for message in messages))

    def test_non_string_interface_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = write_skill(root, "soia-test-nonstring-field", "正文。")
            (skill / "agents").mkdir()
            (skill / "agents/openai.yaml").write_text(
                "interface:\n"
                "  display_name: null\n"
                "  short_description: fine\n"
                "  default_prompt: fine\n",
                encoding="utf-8",
            )
            messages = [hit.message for hit in audit_skills.collect_findings(root)]
            self.assertTrue(any("interface.display_name must be a string" in message for message in messages))


class LinkAuditTests(unittest.TestCase):
    def test_missing_relative_markdown_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(root, "soia-test-link", "见 [流程](references/missing.md)。")
            findings = audit_skills.collect_findings(root)
            self.assertTrue(
                any(
                    finding.message == "relative link target not found: references/missing.md"
                    for finding in findings
                )
            )

    def test_existing_relative_markdown_link_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = write_skill(root, "soia-test-link", "见 [流程](references/present.md)。")
            (skill / "references").mkdir()
            (skill / "references/present.md").write_text("# Present\n", encoding="utf-8")
            self.assertEqual(link_findings(root), [])

    def test_existing_destination_with_title_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = write_skill(
                root,
                "soia-test-link-title",
                '见 [流程](references/present.md "Title")。',
            )
            (skill / "references").mkdir()
            (skill / "references/present.md").write_text("# Present\n", encoding="utf-8")
            self.assertEqual(link_findings(root), [])

    def test_src_target_escape_is_reported_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(root, "soia-test-src", '<img src="../../outside.png">')
            findings = audit_skills.collect_findings(root)
            self.assertTrue(
                any(
                    finding.message == "relative link escapes skill directory: ../../outside.png"
                    for finding in findings
                )
            )

    def test_allowed_root_doc_link_still_requires_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(root, "soia-test-root-link", "见 [规范](../../SKILL_SPEC.md)。")
            self.assertTrue(
                any(
                    "relative link target not found" in hit.message
                    for hit in link_findings(root)
                )
            )
            (root / "SKILL_SPEC.md").write_text("# Spec\n", encoding="utf-8")
            self.assertEqual(link_findings(root), [])

    def test_fenced_example_links_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(
                root,
                "soia-test-fence",
                "```markdown\n[示例](references/missing.md)\n![img](assets/missing.png)\n```",
            )
            self.assertEqual(link_findings(root), [])

    def test_nested_reference_docs_are_scanned_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = write_skill(root, "soia-test-nested", "正文。")
            nested = skill / "references" / "sub"
            nested.mkdir(parents=True)
            (nested / "deep.md").write_text("见 [缺失](missing.md)。\n", encoding="utf-8")
            findings = link_findings(root)
            self.assertTrue(
                any(
                    "relative link target not found: missing.md" in hit.message
                    and hit.path.endswith("references/sub/deep.md")
                    for hit in findings
                )
            )


if __name__ == "__main__":
    unittest.main()
