"""本仓同时是三个宿主的插件，测试锁住三张清单之间的约束。

本仓根目录同时是：
  .claude-plugin/    Claude Code 插件
  .codex-plugin/     Codex 插件
  .codebuddy-plugin/ WorkBuddy 专家（角色化 agent 预设 + 技能组合）

WorkBuddy 要求人设放在 <plugin root>/agents/<agentName>.md，而 Claude Code 默认把
<plugin root>/agents/*.md 当 subagent 加载——同一个目录名，两个宿主两种含义。
实证（2026-07-30，`claude --plugin-dir . plugin details soia-meta`）：
不声明 `agents` 时组件清单是 Agents (1)，声明 `"agents": []` 后是 Agents (0)。
Codex 无此问题：它的清单只认 skills/apps/mcpServers，没有 plugin 级 agents 字段。
"""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLAUDE = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
EXPERT = json.loads((ROOT / ".codebuddy-plugin/plugin.json").read_text(encoding="utf-8"))

# 官方 manifest 的行业分类枚举（WorkBuddy app/cache/experts/manifest.json）
VALID_CATEGORIES = {
    "01-ProductDesign", "02-Engineering", "03-GameSpatial", "04-DataAI",
    "05-MarketingGrowth", "06-ContentCreative", "07-SalesCommerce",
    "08-FinanceInvestment", "09-OperationsHR", "10-ProjectQuality",
    "11-SecurityCompliance", "12-IndustryConsultant", "13-TencentZone",
    "14-GlobalDevelopment",
}


class CrossHostManifestTests(unittest.TestCase):
    def test_claude_suppresses_the_agents_scan(self) -> None:
        """去掉这一行，Claude 侧会凭空多出一个 subagent。"""
        self.assertIn("agents", CLAUDE,
                      ".claude-plugin/plugin.json 必须显式声明 agents")
        self.assertEqual(CLAUDE["agents"], [],
                         "agents 必须为空数组：agents/ 是 WorkBuddy 的人设目录，不是 Claude 的 subagent")

    def test_one_identifier_across_all_three_manifests(self) -> None:
        """一仓一标识符：插件名 = 专家名 = agentName。"""
        self.assertEqual(EXPERT["name"], CLAUDE["name"])
        self.assertEqual(EXPERT["agentName"], CLAUDE["name"])

    def test_avatar_reuses_the_codex_logo(self) -> None:
        """图形资产只有一套：专家头像与 Codex logo 是同一个文件。"""
        codex = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        logo = codex.get("interface", {}).get("logo", "").lstrip("./")
        self.assertEqual(EXPERT["avatar"].lstrip("./"), logo)
        self.assertTrue((ROOT / EXPERT["avatar"]).is_file())


class ExpertContractTests(unittest.TestCase):
    """复刻 WorkBuddy 官方 validate_expert.py 的硬性约束。

    那个校验器只在装了 WorkBuddy 的机器上有，CI 跑不到；这里复刻一份，
    让写坏的清单在提交时就被拦下。
    """

    def test_agent_file_matches_agent_name(self) -> None:
        """官方铁律 2：agentName = agents/ 下的 MD 文件名。"""
        path = ROOT / f"agents/{EXPERT['agentName']}.md"
        self.assertTrue(path.is_file(), path)
        self.assertEqual(EXPERT["agents"], [f"./agents/{EXPERT['agentName']}.md"])
        body = path.read_text(encoding="utf-8")
        self.assertIn(f"name: {EXPERT['agentName']}\n", body)

    def test_agent_md_declares_no_tools(self) -> None:
        """官方 agent-md-spec：frontmatter 禁止声明 tools，权限由宿主统一分配。"""
        head = (ROOT / f"agents/{EXPERT['agentName']}.md").read_text(
            encoding="utf-8").split("---")[1]
        self.assertNotIn("\ntools:", head)

    def test_exactly_three_tags_and_quick_prompts(self) -> None:
        """官方铁律 4。"""
        self.assertEqual(len(EXPERT["tags"]), 3)
        self.assertEqual(len(EXPERT["quickPrompts"]), 3)

    def test_default_init_prompt_equals_first_quick_prompt(self) -> None:
        self.assertEqual(EXPERT["defaultInitPrompt"], EXPERT["quickPrompts"][0])

    def test_display_description_length(self) -> None:
        """官方建议中文 40-50 字，超出会在校验器里报 warning。"""
        self.assertTrue(40 <= len(EXPERT["displayDescription"]["zh"]) <= 50)

    def test_category_is_known(self) -> None:
        self.assertIn(EXPERT["categoryId"], VALID_CATEGORIES)

    def test_display_name_follows_brand(self) -> None:
        """品牌规范禁止 SOIA 全大写、SoiaAI 驼峰、Soia-AI 连字符。"""
        for value in EXPERT["displayName"].values():
            self.assertNotRegex(value, r"SOIA|SoiaAI|Soia-AI")

    def test_skill_paths_exist_and_cover_the_repo(self) -> None:
        """专家清单逐条列技能，新增或删除技能后会失配——generate_expert_manifest.py 负责刷新。"""
        declared = {p.lstrip("./") for p in EXPERT["skills"]}
        actual = {f"skills/{d.name}" for d in (ROOT / "skills").iterdir()
                  if d.is_dir() and (d / "SKILL.md").exists()}
        self.assertEqual(declared, actual)
        for rel in declared:
            self.assertTrue((ROOT / rel / "SKILL.md").is_file(), rel)


if __name__ == "__main__":
    unittest.main()
