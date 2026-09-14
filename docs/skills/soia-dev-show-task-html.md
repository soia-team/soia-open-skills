# soia-dev-show-task-html

> 展示任务进度、调用关系或数据流；用户要求任务视图或关系图时使用，复杂布局才生成 HTML。普通问答、单一状态和常规回执不自动触发

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-show-task-html) · [← 全部技能](README.md)

## 能力与用法

**能做什么：** 把当前问题、进度或代码关系讲明白。直接给最小有用视图，少写前言；不默认做看板、报告或证据墙。

**如何使用：** 说“展示这个任务”或指出想看懂的关系即可。默认用当前话题，只有范围会实质改变答案时才问。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-show-task-html -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
