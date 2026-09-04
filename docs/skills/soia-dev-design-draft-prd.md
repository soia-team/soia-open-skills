# soia-dev-design-draft-prd

> 起草互联网通用 PRD、产品需求文档与用户故事；适用于一句话需求补全、功能范围和验收标准梳理

所属：[`soia-dev-design`](https://github.com/soia-team/soia-open-dev-design-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-design-skills/tree/main/skills/soia-dev-design-draft-prd) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把一句话想法变成 PRD | 用最少的追问引导补全关键上下文，并显式记录未知项 | 一份带假设和开放项的 PRD 草稿 |
| 整理已有需求材料 | 归纳问题、目标、用户故事、范围和验收条件 | 可评审的结构化需求清单 |
| 为需求评审做准备 | 检查范围边界、可验证性、依赖和风险 | 评审问题、里程碑建议与风险表 |

### 客户如何使用

直接描述产品机会、目标用户、要解决的问题或预期结果；也可提供已有访谈摘要、需求笔记或约束。示例：`为 ExampleCorp 的示例产品起草一个 PRD：让新用户在移动端完成首次任务。`

若输入只有一句话，先提出不超过五个、按影响排序的问题，优先确认目标用户、问题证据、成功指标、约束和上线窗口。客户暂时无法回答时，使用清晰的“假设”占位继续起草，不把假设写成事实。

## 安装

客户明确选择安装整个 `soia-dev-design` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev-design@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev-design@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-dev-design-skills -a <agent> -s soia-dev-design-draft-prd -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
