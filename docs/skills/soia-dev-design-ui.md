# soia-dev-design-ui

> 设计界面的信息结构、交互、视觉与实现交接，保持已批准的品牌和样式边界

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-design-ui) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

设计这个界面、梳理交互流程、做 UI 设计交接、按任务书设计界面、交互状态与实现交接

## 能力与用法

**能做什么：** 把用户任务变成清晰的界面与交互设计；按需要交付结构、状态说明、可见原型或实现交接。不是默认重做整站，也不代替产品规格和生产实现。

**如何使用：** 提供目标页面/流程、受众、平台、真实内容和现有设计。先读取适用的设计规范与当前页面；沿用已批准品牌、组件、token 和文案规则。用户要求保持样式时，只动获准部分。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-design-ui -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
