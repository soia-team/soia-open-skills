# soia-dev-show-task-html

> 将开发进度与 AI 代码变更转成最小可用视图：简单关系直接画，阶段状态用紧凑看板，复杂调用链与数据流生成离线 HTML

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-show-task-html) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「show me」「展示这个任务」「给我画一下」

## 能力与用法

### 这个技能可以做什么

- 简单关系：在对话中给最小表格、调用树或 Mermaid。
- 阶段汇报：用紧凑 KPI、任务行、阻塞和下一步快速看全局。
- 复杂跨文件改动：生成离线、紧凑高密度、响应式且可复制文字的 HTML，展示文件 owner/layer、调用链、数据流、模块边界、规范符合性、验证证据、风险、阻塞和下一步。

### 客户如何使用

先说明范围和重点，例如“展示这个变更集的核心调用链”。复杂 HTML 前，Agent 按要表达的结论类型加载最小证据：`progress` 读取适用项目规则、任务状态和已有证据；只有调用链、数据流、边界或规范符合性结论才读取对应架构/设计契约、真实 diff 和相关代码。将事实标为 `observed`、有链路依据的推断标为 `inferred`，无证据标为 `unknown`，并保留准确 `file:line`。脚本不负责这些核实工作。

输入字段、scope/view 选项和引用格式见 [references/input-schema.md](references/input-schema.md)。审查视角和最小区块选择见 [references/code-review-views.md](references/code-review-views.md)。复杂输入再读取这些 reference，简单对话图不必读取。

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
