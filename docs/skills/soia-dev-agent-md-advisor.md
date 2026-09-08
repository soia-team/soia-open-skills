# soia-dev-agent-md-advisor

> 诊断、起草或精简 AI 项目指令，解决无效规则、重复和入口冲突

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-agent-md-advisor) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

精简 AGENTS.md、CLAUDE.md 怎么组织、检查 AI 指令冲突

## 能力与用法

**能做什么：** 判断 AGENTS/CLAUDE/GEMINI 等指令文件是否清楚、有效、职责合适；按请求诊断、起草或改写。跨文档状态对账归 doc-sync，项目初始化归 project-scaffold。

**如何使用：** 提供文件或目标项目及不满意之处。只问答就直接回答；审查默认只读；明确要求优化/重写时可直接修改已授权文件，不再让用户重复批准同一动作。

## 安装

客户明确选择安装整个 `soia-dev` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-agent-md-advisor -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
