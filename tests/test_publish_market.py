#!/usr/bin/env python3
"""Offline tests for market staging (SkillHub / Red Skill)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
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
description: 一个零依赖技能。触发：「上架演示」
version: 1.0.0
---

# demo-plain

正文一字不改。

## 不负责什么

- 不代客户上传。

## 输出样例

| 输入 | 输出 |
|---|---|
| 你好 | 世界 |
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

# 门禁 fixture：满足 R1-R4 的最小技能（R5 无 URL 直接通过）。
GATE_BASE = """---
name: demo-gate
description: 一个零依赖技能。触发：「上架演示」
version: 1.0.0
---

# demo-gate

## 不负责什么

- 不代客户执行。

## 输出样例

| 输入 | 输出 |
|---|---|
| 你好 | 世界 |
"""

# 自包含的最小测试：含 skills/<技能名>/ 引用（R4 的查找依据），
# 但不依赖仓布局，进包后能跑通。
GOOD_SMOKE_TEST = """import unittest

SKILL_REF = "skills/{skill}/"


class SmokeTest(unittest.TestCase):
    def test_mentions_skill(self) -> None:
        self.assertIn("{skill}", SKILL_REF)


if __name__ == "__main__":
    unittest.main()
"""

# 只按仓布局解析路径的测试：在包里 parents[2] 不再是仓根，必跑挂，
# 应被 R4 以「布局耦合」抓出来。
COUPLED_LAYOUT_TEST = """import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class RepoLayoutCoupled(unittest.TestCase):
    def test_skill_md_exists(self) -> None:
        self.assertTrue((REPO_ROOT / "skills/{skill}/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
"""

# 分段拼路径引用技能的测试：源码里只出现技能名，不出现 `skills/<技能名>/`
# 路径字面串（真实测试常写成 `ROOT / "skills" / "<技能名>" / ...`）。
# 旧规则按路径字面串匹配会永远找不到它；按技能名子串匹配（R4）才能命中，
# 是本缺陷的回归夹具。测试自身不依赖仓布局，进包后能跑通。
SEGMENTED_PATH_TEST = """import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "demo-gate"
SCRIPTS = SKILL_DIR / "scripts"


class SegmentedPathTest(unittest.TestCase):
    def test_skill_scripts_path_shape(self) -> None:
        self.assertTrue(SKILL_DIR.name == "demo-gate")
        self.assertTrue(SCRIPTS.name == "scripts")


if __name__ == "__main__":
    unittest.main()
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
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_demo_plain.py").write_text(
            GOOD_SMOKE_TEST.format(skill="demo-plain"), encoding="utf-8")
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

    def test_redskill_channel_requires_display_name(self) -> None:
        """缺 --display-name 时必须拒跑：回落到长技能名会被平台拒收。"""
        rc = STAGE.main(["--repo-dir", str(self.repo), "--skill", "demo-plain",
                         "--out", str(self.out), "--channel", "redskill",
                         "--allow-unreleased"])
        self.assertEqual(rc, 1)
        self.assertFalse((self.out / "demo-plain").exists(), "被拒时不应打包")

    def test_redskill_command_carries_name_and_identifier(self) -> None:
        """投递命令必须同时钉住展示名与平台主键。"""
        cmd = STAGE.redskill_publish_command(
            self.out / "demo-plain", "demo-plain", "演示技能")
        self.assertIn('--name "演示技能"', cmd)
        self.assertIn('--identifier "demo-plain"', cmd)
        self.assertIn("--dry-run", cmd, "给出的命令必须是预检，不能直接真投")

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
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_demo_plain.py").write_text(
            GOOD_SMOKE_TEST.format(skill="demo-plain"), encoding="utf-8")
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


class ReadinessGateTests(unittest.TestCase):
    """上架就绪门禁：R1-R5 一正一反，全部走 --allow-unreleased（离线）。"""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.repo = Path(self.tmp) / "repo"
        d = self.repo / "skills" / "demo-gate"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(GATE_BASE, encoding="utf-8")
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_demo_gate.py").write_text(
            GOOD_SMOKE_TEST.format(skill="demo-gate"), encoding="utf-8")
        self.out = Path(self.tmp) / "out"
        self.out.mkdir()

    def write_skill(self, text: str) -> None:
        (self.repo / "skills" / "demo-gate" / "SKILL.md").write_text(
            text, encoding="utf-8")

    def stage(self) -> tuple[Path, str]:
        """跑 stage 并捕获门禁报告，返回 (目标目录, 捕获的报告文本)。

        门禁的逐项报告直印 stdout，失败尾部可能含子测试的
        `FAILED (failures=1)`——绿跑日志里出现 FAILED 字样会误导读日志的人，
        所以在测试里捕获；生产脚本的 print 行为不变。
        """
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            target = STAGE.stage(self.repo, "demo-gate", self.out,
                                 allow_unreleased=True)
        return target, buffer.getvalue()

    def test_r1_missing_boundary_section_rejected(self) -> None:
        self.write_skill(GATE_BASE.replace(
            "## 不负责什么\n\n- 不代客户执行。\n\n", ""))
        with self.assertRaises(ValueError) as ctx:
            self.stage()
        self.assertIn("R1", str(ctx.exception))
        self.assertFalse((self.out / "demo-gate").exists(),
                         "被拒后不应留下暂存产物")

    def test_r1_boundary_section_added_passes(self) -> None:
        target, _ = self.stage()
        self.assertTrue((target / "SKILL.md").exists(), "R1 补齐后不再失败")

    def test_r2_description_without_trigger_rejected(self) -> None:
        self.write_skill(GATE_BASE.replace("触发：「上架演示」", "演示技能"))
        with self.assertRaises(ValueError) as ctx:
            self.stage()
        self.assertIn("R2", str(ctx.exception))

    def test_r2_description_with_trigger_passes(self) -> None:
        self.write_skill(GATE_BASE.replace(
            "触发：「上架演示」", "触发：「上架演示」「发到市场」"))
        target, _ = self.stage()
        self.assertTrue((target / "SKILL.md").exists())

    def test_r3_placeholder_only_table_rejected(self) -> None:
        self.write_skill(GATE_BASE.replace(
            "| 输入 | 输出 |\n|---|---|\n| 你好 | 世界 |",
            "| <输入> | <输出> |"))
        with self.assertRaises(ValueError) as ctx:
            self.stage()
        self.assertIn("R3", str(ctx.exception))
        self.assertIn("占位符模板不算", str(ctx.exception))
        self.assertFalse((self.out / "demo-gate").exists())

    def test_r3_real_sample_row_passes(self) -> None:
        target, _ = self.stage()
        self.assertTrue((target / "SKILL.md").exists())

    def test_r4_no_matching_test_rejected(self) -> None:
        (self.repo / "tests" / "test_demo_gate.py").unlink()
        with self.assertRaises(ValueError) as ctx:
            self.stage()
        self.assertIn("R4", str(ctx.exception))
        self.assertIn("无专属测试", str(ctx.exception))

    def test_r4_self_contained_test_copied_and_passes(self) -> None:
        target, _ = self.stage()
        self.assertTrue((target / "tests").is_dir(),
                        "专属测试应随包作为证据")
        self.assertTrue((target / "tests" / "test_demo_gate.py").is_file())

    def test_r4_segmented_path_test_copied_and_passes(self) -> None:
        """回归：路径分段拼接的测试（无 `skills/<技能名>/` 字面串）也能被 R4 找到。"""
        (self.repo / "tests" / "test_demo_gate.py").write_text(
            SEGMENTED_PATH_TEST, encoding="utf-8")
        target, _ = self.stage()
        self.assertTrue((target / "tests" / "test_demo_gate.py").is_file(),
                        "按技能名匹配，分段拼路径的测试也应被找到并随包")

    def test_r4_repo_layout_coupled_test_rejected(self) -> None:
        (self.repo / "tests" / "test_demo_gate.py").write_text(
            COUPLED_LAYOUT_TEST.format(skill="demo-gate"), encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            self.stage()
        self.assertIn("R4", str(ctx.exception))
        self.assertIn("仓布局耦合", str(ctx.exception))
        self.assertFalse((self.out / "demo-gate").exists())

    def test_r5_foreign_only_urls_warn_without_blocking(self) -> None:
        self.write_skill(GATE_BASE + "参考：https://example.com/tool\n")
        target, output = self.stage()
        self.assertTrue((target / "SKILL.md").exists(), "警告不阻断打包")
        self.assertIn("R5", output)
        self.assertIn("警告", output)

    def test_r5_domestic_url_has_no_warning(self) -> None:
        self.write_skill(GATE_BASE + "镜像：https://registry.npmmirror.com/pkg\n")
        target, output = self.stage()
        self.assertTrue((target / "SKILL.md").exists())
        self.assertNotIn("R5 [警告]", output)
        self.assertNotIn("境外", output)

    def test_check_only_leaves_no_staging(self) -> None:
        rc = STAGE.main(["--repo-dir", str(self.repo), "--skill", "demo-gate",
                         "--out", str(self.out), "--allow-unreleased",
                         "--check-only"])
        self.assertEqual(rc, 0)
        self.assertFalse((self.out / "demo-gate").exists(),
                         "--check-only 不应留下暂存产物")


if __name__ == "__main__":
    unittest.main()
