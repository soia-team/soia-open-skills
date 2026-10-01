# soia-dev-enforce-coding-protocol

> 给工程改动加范围、权限与验证底线，不另起流程

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-enforce-coding-protocol) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

执行编码协议、核对工程改动是否越界

## 能力与用法

**能做什么：** 给实现、修复和审查一条共同底线；项目规则已覆盖的不重复安排，也不接管专业验收。

**如何使用：** 把下面约束直接应用到手头的工程改动，不另建计划、状态库、审查轮次或协议报告。只约束代码、配置、测试、Git 与行为契约的改动及其诊断/审查；混合任务只管相关部分，契约不变的纯文字修正、解释和状态汇报不适用。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-enforce-coding-protocol -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
