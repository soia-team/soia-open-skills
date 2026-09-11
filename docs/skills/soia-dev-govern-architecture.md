# soia-dev-govern-architecture

> 设计架构、审查给定方案或核对长期漂移，明确职责、契约、事实真源与迁移边界

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-govern-architecture) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

架构方案怎么选、审查架构边界、检查架构漂移、按任务书核对架构边界、评估迁移边界

## 能力与用法

**能做什么：** 解决会影响多个组件的架构判断。交付可实施的选择、针对给定方案的问题，或实际漂移清单；不是画图工具，也不替代普通代码实现。

**如何使用：** 提供目标问题、架构/代码范围和已批准约束。先判断本次是设计、评审还是漂移核对，只做所需模式；局部修复不重开架构。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-govern-architecture -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
