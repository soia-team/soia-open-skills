"""WorkBuddy 专家定义与物化的守门测试。

专家包最终由 WorkBuddy 官方 validate_expert.py 判定，但那个校验器只在装了
WorkBuddy 的机器上有，CI 跑不到。这里把官方的硬性约束在本仓复刻一份，
让一个写坏的 expert.json 在提交时就被拦下，而不是等到用户机器上生成失败。
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPERTS_DIR = ROOT / "experts"

_spec = importlib.util.spec_from_file_location(
    "generate_workbuddy_experts", ROOT / "scripts/generate_workbuddy_experts.py"
)
gwe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gwe)

# 官方 manifest 的分类枚举（app/cache/experts/manifest.json），随 WorkBuddy 发布
VALID_CATEGORIES = {
    "01-ProductDesign", "02-Engineering", "03-GameSpatial", "04-DataAI",
    "05-MarketingGrowth", "06-ContentCreative", "07-SalesCommerce",
    "08-FinanceInvestment", "09-OperationsHR", "10-ProjectQuality",
    "11-SecurityCompliance", "12-IndustryConsultant", "13-TencentZone",
    "14-GlobalDevelopment",
}

EXPERT_DIRS = sorted(d for d in EXPERTS_DIR.iterdir()
                     if d.is_dir() and (d / "expert.json").exists())


class ExpertDefinitionTests(unittest.TestCase):
    def test_repo_has_expert_definitions(self) -> None:
        self.assertTrue(EXPERT_DIRS, "experts/ 下没有任何专家定义")

    def test_every_definition_loads(self) -> None:
        """load_definition 覆盖官方铁律：name/agentName 对齐、tags 与 quickPrompts 各 3 条。"""
        for expert_dir in EXPERT_DIRS:
            with self.subTest(expert=expert_dir.name):
                gwe.load_definition(expert_dir)

    def test_category_ids_are_known(self) -> None:
        """categoryId 写错不会被 load_definition 拦下，但会让专家在市场里归错类。"""
        for expert_dir in EXPERT_DIRS:
            spec = json.loads((expert_dir / "expert.json").read_text(encoding="utf-8"))
            with self.subTest(expert=expert_dir.name):
                self.assertIn(spec["categoryId"], VALID_CATEGORIES)

    def test_agent_md_frontmatter_matches_definition(self) -> None:
        """官方铁律 2：agentName = agents/ 下的 MD 文件名，而 MD 的 name 必须与之一致。"""
        for expert_dir in EXPERT_DIRS:
            spec = json.loads((expert_dir / "expert.json").read_text(encoding="utf-8"))
            body = (expert_dir / "agent.md").read_text(encoding="utf-8")
            with self.subTest(expert=expert_dir.name):
                self.assertTrue(body.startswith("---\n"), "agent.md 缺 frontmatter")
                self.assertIn(f"name: {spec['agentName']}\n", body)

    def test_agent_md_declares_no_tools(self) -> None:
        """官方 agent-md-spec 明写 frontmatter 禁止声明 tools，权限由系统统一分配。"""
        for expert_dir in EXPERT_DIRS:
            head = (expert_dir / "agent.md").read_text(encoding="utf-8").split("---")[1]
            with self.subTest(expert=expert_dir.name):
                self.assertNotIn("\ntools:", head)

    def test_avatars_within_size_budget(self) -> None:
        """官方 avatar-spec：单张不超过 500KB。"""
        for expert_dir in EXPERT_DIRS:
            avatar = expert_dir / "avatar.png"
            with self.subTest(expert=expert_dir.name):
                self.assertLessEqual(avatar.stat().st_size, 500 * 1024)


class PluginJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = json.loads(
            (EXPERT_DIRS[0] / "expert.json").read_text(encoding="utf-8")
        )
        self.skills = [pathlib.Path("skills/a"), pathlib.Path("skills/b")]
        self.plugin = gwe.build_plugin_json(self.spec, self.skills)

    def test_default_init_prompt_equals_first_quick_prompt(self) -> None:
        """官方铁律 4，且 validate_expert.py 会检查这一条。"""
        self.assertEqual(self.plugin["defaultInitPrompt"], self.spec["quickPrompts"][0])

    def test_agent_path_matches_agent_name(self) -> None:
        self.assertEqual(
            self.plugin["agents"], [f"./agents/{self.spec['agentName']}.md"]
        )

    def test_skill_paths_are_plugin_relative(self) -> None:
        """校验器按 plugin 根解析 skills 路径，绝对路径或裸名都会判找不到 SKILL.md。"""
        for path in self.plugin["skills"]:
            self.assertTrue(path.startswith("./skills/"), path)


class MaterializeTests(unittest.TestCase):
    """回归：整目录拷贝会把域仓工作副本里的本机产物一并带进专家包。

    首次生成时 3 个技能的包里有 1.1MB 是 __pycache__，单个 .pyc 达 272KB——
    这些既拖体积，又可能把与本机 Python 版本绑定的字节码发给用户。
    """

    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        self.source = self.tmp / "repo/skills/demo-skill"
        (self.source / "scripts/__pycache__").mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: demo-skill\n---\n")
        (self.source / "scripts/run.py").write_text("print('ok')\n")
        (self.source / "scripts/__pycache__/run.cpython-314.pyc").write_bytes(b"\x00" * 32)
        (self.source / ".DS_Store").write_bytes(b"\x00")

        self.spec = json.loads(
            (EXPERT_DIRS[0] / "expert.json").read_text(encoding="utf-8")
        )
        self.out = gwe.materialize(
            self.spec, EXPERT_DIRS[0], [self.source], self.tmp / "market"
        )

    def test_skill_content_is_copied(self) -> None:
        self.assertTrue((self.out / "skills/demo-skill/SKILL.md").exists())
        self.assertTrue((self.out / "skills/demo-skill/scripts/run.py").exists())

    def test_build_artifacts_are_excluded(self) -> None:
        for junk in ("skills/demo-skill/scripts/__pycache__",
                     "skills/demo-skill/.DS_Store"):
            with self.subTest(path=junk):
                self.assertFalse((self.out / junk).exists())

    def test_rebuild_drops_skills_no_longer_declared(self) -> None:
        """专家包整目录重建，否则上一轮的技能会滞留成幽灵条目。"""
        stale = self.out / "skills/removed-skill"
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("---\nname: removed-skill\n---\n")
        rebuilt = gwe.materialize(
            self.spec, EXPERT_DIRS[0], [self.source], self.tmp / "market"
        )
        self.assertFalse((rebuilt / "skills/removed-skill").exists())


class ResolveSkillsTests(unittest.TestCase):
    def test_missing_source_repo_reports_the_flag_to_use(self) -> None:
        with self.assertRaises(gwe.DefinitionError) as ctx:
            gwe.resolve_skills({"name": "x", "sourceRepo": "nope"}, pathlib.Path("/tmp"))
        self.assertIn("--skills-root", str(ctx.exception))

    def test_unknown_skill_in_allowlist_is_rejected(self) -> None:
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        skill = tmp / "repo/skills/real-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: real-skill\n---\n")
        spec = {"name": "x", "sourceRepo": "repo", "skills": ["real-skill", "ghost"]}
        with self.assertRaises(gwe.DefinitionError) as ctx:
            gwe.resolve_skills(spec, tmp)
        self.assertIn("ghost", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
