#!/usr/bin/env python3
"""Offline tests for market staging (SkillHub / Red Skill)."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-meta-publish-market" / "scripts" / "stage_for_market.py"

_spec = importlib.util.spec_from_file_location("stage_for_market", SCRIPT)
assert _spec and _spec.loader
STAGE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(STAGE)

PLAIN = """---
name: demo-plain
description: 一个零依赖技能
version: 1.0.0
---

# demo-plain

正文一字不改。
"""

WITH_HARD = """---
name: demo-hard
description: 有强依赖
dependencies:
  hard: [demo-plain]
version: 1.0.0
---

# demo-hard
"""

WITH_OPTIONAL = """---
name: demo-optional
description: 只有可选依赖
dependencies:
  optional: [demo-plain]
version: 1.0.0
---

# demo-optional
"""


class StagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.repo = Path(self.tmp) / "repo"
        for name, text in (("demo-plain", PLAIN), ("demo-hard", WITH_HARD),
                           ("demo-optional", WITH_OPTIONAL)):
            d = self.repo / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(text, encoding="utf-8")
        self.out = Path(self.tmp) / "out"
        self.out.mkdir()

    def test_hard_dependency_blocks_eligibility(self) -> None:
        rows = {name: ok for name, ok, _ in STAGE.eligible_skills(self.repo)}
        self.assertTrue(rows["demo-plain"])
        self.assertFalse(rows["demo-hard"], "hard 依赖的技能上架后断链，必须挡住")
        self.assertTrue(rows["demo-optional"], "optional 依赖不阻断上架")

    def test_stage_overlays_platform_fields_and_keeps_body(self) -> None:
        target = STAGE.stage(self.repo, "demo-plain", self.out,
                             display_name="演示技能", allow_unreleased=True)
        text = (target / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("slug: demo-plain", text)
        self.assertIn("displayName: 演示技能", text)
        self.assertIn("license: MIT", text)
        self.assertIn("name: demo-plain", text, "原字段必须保留")
        self.assertIn("正文一字不改。", text)

    def test_display_name_falls_back_to_original_name(self) -> None:
        target = STAGE.stage(self.repo, "demo-plain", self.out, allow_unreleased=True)
        text = (target / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("displayName: demo-plain", text)

    def test_staging_a_hard_dependency_skill_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            STAGE.stage(self.repo, "demo-hard", self.out, allow_unreleased=True)
        self.assertIn("hard 依赖", str(ctx.exception))
        self.assertFalse((self.out / "demo-hard").exists(), "被拒时不应留下暂存产物")


class ChannelFilterTests(unittest.TestCase):
    """Red Skill 有文件白名单，SkillHub 没有。

    回归 2026-08-05：带 agents/openai.yaml 上传 Red Skill 被拒——
    「目录中包含不支持上传的文件」；同一份目录 SkillHub dry-run 却通过。
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.repo = Path(self.tmp) / "repo"
        d = self.repo / "skills" / "demo-plain"
        (d / "agents").mkdir(parents=True)
        (d / "SKILL.md").write_text(PLAIN, encoding="utf-8")
        (d / "agents" / "openai.yaml").write_text("interface: {}\n", encoding="utf-8")
        (d / "scripts").mkdir()
        (d / "scripts" / "run.py").write_text("print(1)\n", encoding="utf-8")
        self.out = Path(self.tmp) / "out"
        self.out.mkdir()

    def test_redskill_strips_unsupported_files(self) -> None:
        target = STAGE.stage(self.repo, "demo-plain", self.out,
                             allow_unreleased=True, channel="redskill")
        self.assertFalse((target / "agents" / "openai.yaml").exists(),
                         ".yaml 不在 Red Skill 白名单，必须剔除")
        self.assertTrue((target / "SKILL.md").exists())
        self.assertTrue((target / "scripts" / "run.py").exists(), ".py 应保留")

    def test_skillhub_keeps_everything(self) -> None:
        target = STAGE.stage(self.repo, "demo-plain", self.out,
                             allow_unreleased=True, channel="skillhub")
        self.assertTrue((target / "agents" / "openai.yaml").exists(),
                        "SkillHub 无此限制，不该剔除")


if __name__ == "__main__":
    unittest.main()
