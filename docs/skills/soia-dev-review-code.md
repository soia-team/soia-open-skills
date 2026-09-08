# soia-dev-review-code

> 对固定代码候选或技能包做一次只读审查，区分规格符合性与工程标准，报告可核实问题

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-review-code) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

审查这次改动、review 代码、检查技能包

## 能力与用法

**能做什么：** 判断给定改动是否满足请求、是否引入具体风险；只读，不修复、不提交、不评论到远端、不合并。

**如何使用：** 提供 diff/PR/技能目录及目标。先确认候选版本或本地快照、范围和项目规则；材料不足只说明缺口，不猜版本，也不声称已审。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-review-code -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
