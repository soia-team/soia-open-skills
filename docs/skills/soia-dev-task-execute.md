# soia-dev-task-execute

> 执行任意工程任务的通用闭环：定义边界、实施最小改动、验证、独立复核与回执。适用于代码、配置、文档和维护任务

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-task-execute) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「把这件事做完」「按闭环执行」「有风险的维护」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 执行闭环 | 客户能看到 |
|---|---|---|
| 实现或修改一项工程工作 | 定义边界后做最小可靠改动 | 改动映射与验证结果 |
| 完成一项有风险的维护工作 | 识别高风险面并用独立路径复核 | 已验证事实、未验证项和风险 |
| 交接一个已完成任务 | 汇总输入、产物、检查和残余风险 | 可复制的完成回执 |

### 完成定义

“完成”同时满足：请求的可观察结果已实现；相关验证真实运行；关键结论有独立证据；工作树中只包含本任务的改动。无法满足任一项时，明确报告阻塞或未覆盖范围，不把意图写成完成。

### 客户如何使用

提供目标、目标工作区、预期的可观察结果，以及已知的测试或复现方式。涉及删除、覆盖、发送、发布、远端写入或不可逆数据变更时，说明授权范围；缺少这项信息时先停在预览或诊断阶段。

## 安装

本技能随 `soia-dev` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-task-execute -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
