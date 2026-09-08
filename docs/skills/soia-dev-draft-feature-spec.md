# soia-dev-draft-feature-spec

> 把产品想法或需求材料整理成可验收的功能规格，并按需拆成纵向交付切片

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-draft-feature-spec) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

起草功能规格、把需求写成 PRD、拆分可验收功能

## 能力与用法

**能做什么：** 从想法或已有材料起草产品功能规格/PRD；需要实施计划时，再按可独立验证的用户结果拆分。交付是草稿与待确认项，不是立项、排期或实现承诺。

**如何使用：** 描述用户、问题、用途与已知约束，或给已有需求。只追问会改变范围、权限或验收的缺口；其余标明假设继续，不为填模板阻塞。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-draft-feature-spec -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
