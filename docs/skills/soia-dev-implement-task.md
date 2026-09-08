# soia-dev-implement-task

> 在明确授权内实现需求、诊断修复或处理 findings，合并执行与修复流程

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-implement-task) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

实现这个任务、修复这个 bug、处理审查发现

## 能力与用法

**能做什么：** 把一个工程需求、缺陷或 finding 做到可验证的完成；代码、配置和文档都可用。不把“只诊断”变成改代码。

**如何使用：** 提供目标、所在项目及已知约束。有足够信息就推进；只有会改变结果、权限或安全的歧义才暂停对应动作。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-implement-task -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
