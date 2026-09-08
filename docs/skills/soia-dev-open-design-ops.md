# soia-dev-open-design-ops

> 操作 Open Design 环境、项目与导出，并交付 HTML 原型、deck 和动画

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-open-design-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

检查 Open Design、制作 HTML deck、继续设计会话

## 能力与用法

**能做什么：** 操作 Open Design 环境、设计系统、目录、项目、会话和渲染/导出；也承接 HTML 原型、幻灯片、动画的工具流程。UI 方法和视觉审查分别由 design-ui / audit-ui 承担，不强制安装或串行加载。

**如何使用：** 给目标与已有项目/素材；生成时说明内容、品牌、画幅和输出，导出时给格式与路径。PPTX 要区分截图保真与可编辑，HTML deck/动画不能被 PPTX 或静态图代替。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-open-design-ops -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
