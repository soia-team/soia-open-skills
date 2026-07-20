#!/usr/bin/env python3
"""Static contract tests for soia-dev-prompt-clarity."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "skills" / "soia-dev-prompt-clarity"
SKILL = SKILL_ROOT / "SKILL.md"


def read(relative: str) -> str:
    return (SKILL_ROOT / relative).read_text(encoding="utf-8")


class PromptClaritySkillTests(unittest.TestCase):
    def test_skill_keeps_all_four_modes_and_stays_concise(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for marker in [
            "模式 A · 从零起草",
            "模式 B · 诊断优化",
            "模式 C · 防误伤改写",
            "模式 D · 扩展成规格",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertLess(len(text.splitlines()), 500)

    def test_english_and_bilingual_triggers_are_discoverable(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        for marker in [
            "写英文提示词",
            "中英双语提示词",
            "write a prompt",
            "improve this prompt",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, frontmatter)

    def test_language_contract_separates_prompt_and_explanation(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        english = read("references/english-prompt-authoring.md")
        for marker in [
            "input_language",
            "prompt_language",
            "explanation_language",
            "不能先写中文再逐句直译",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        for marker in [
            "must",
            "should",
            "may",
            "must not",
            "two complete versions",
            "Do not ask the target AI to expose private or hidden chain-of-thought",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, english)

    def test_receipt_requires_language_framework_and_execution_fields(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("最终回答的第一行都必须是下面这条完整回执头", text)
        self.assertIn("七个字段即使“不适用”也不得省略", text)
        self.assertLess(text.splitlines().index("## 硬性输出合同"), 40)
        for marker in [
            "mode=<A/B/C/D，可含辅助模式>",
            "input=<语言>",
            "prompt=<语言>",
            "explanation=<语言>",
            "framework=<none 或名称>",
            "execution=<output-only 或执行器>",
            "files=<none 或变更摘要>",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_frameworks_are_optional_and_cannot_replace_safety_or_specs(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        frameworks = read("references/prompt-framework-patterns.md")
        self.assertIn("先选模式，再决定是否需要框架", text)
        self.assertIn("最多选择一个主框架和一个辅助框架", text)
        self.assertIn("Named frameworks are optional organizing aids", frameworks)
        self.assertIn("cannot replace mode C", frameworks)
        self.assertIn("Do not use “Chain of Thought”", frameworks)

    def test_mode_c_and_mode_d_quality_gates_remain_hard(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        mode_c = read("references/mode-c-disambiguation.md")
        gate = read("references/mode-d-quality-gate.md")
        self.assertIn("不能替用户编造", text)
        self.assertIn("Do not provide a cosmetically safer rewrite", mode_c)
        for marker in [
            "语言转换把 `must` 弱化成 `should/may`",
            "双语版本的需求",
            "用命名框架替代模式 C 红线",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, gate)

    def test_all_direct_references_exist(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        links = re.findall(r"\]\((references/[^)]+)\)", text)
        self.assertTrue(links)
        for relative in links:
            with self.subTest(relative=relative):
                self.assertTrue((SKILL_ROOT / relative).is_file())

    def test_public_skill_has_no_maintainer_paths_or_secret_values(self) -> None:
        chunks = []
        for path in sorted(SKILL_ROOT.rglob("*")):
            if path.is_file() and path.suffix in {".md", ".yaml", ".yml"}:
                chunks.append(path.read_text(encoding="utf-8"))
        text = "\n".join(chunks)
        self.assertNotRegex(text, r"/Users/[A-Za-z0-9._-]+/")
        self.assertNotRegex(text, r"/home/[A-Za-z0-9._-]+/")
        self.assertNotRegex(
            text,
            r"(?i)\b(?:api[_-]?key|access[_-]?token|password|cookie|session)"
            r"\s*[:=]\s*[\"'][^<\n]{8,}[\"']",
        )


if __name__ == "__main__":
    unittest.main()
