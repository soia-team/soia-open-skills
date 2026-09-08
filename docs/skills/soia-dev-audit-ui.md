# soia-dev-audit-ui

> 只读验收界面，将布局、键盘等技术证据与 UX、视觉判断分开报告

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-audit-ui) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

验收这个界面、检查键盘和布局、评审视觉与体验

## 能力与用法

**能做什么：** 对固定页面、原型或截图做一次聚焦验收，给出可复现的问题和优先修复建议。默认只读，不自动改页面。

**如何使用：** 提供目标、版本/入口、用户任务及已批准设计。按请求选技术验收、UX/视觉判断或两者；两个结果分开，不用 lint、截图或主观观感互相替代。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-audit-ui -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
