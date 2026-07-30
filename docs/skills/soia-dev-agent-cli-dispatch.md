# soia-dev-agent-cli-dispatch

> 外部 AI CLI 调度与模型路由，支持受控派活与用量回执

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-agent-cli-dispatch) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「派活给外部 AI」「调用 agy」「多 CLI 派发」

## 能力与用法

### 这个技能可以做什么

调度外部 AI 模型/CLI（codex/claude/agy/gemini/kimi/opencode/qwen，非宿主内置子代理，`qodercli` 也有命令模板但未纳入下方精简清单）进行受控派发，覆盖编码、审查、分析、研究、文档和内容任务：任务边界拆分、独立 workdir、防注入 prompt 写法、模型分级矩阵、Worktree 审批门、Anti-Fake-Fix 三步验证。在此之上，可显式指定执行器 + 模型 + 推理深度，或只给执行器家族由任务难度自动选型（见「自动路由」）；每次调用后输出 Token/费用汇总（见「调用总结回执」）、模型完整性检测（见「Model Integrity Gate」）、额度预检（见「额度预检」）与断点续跑（见「可恢复执行」）。各执行器详细命令模板在 `references/` 子目录下按需加载。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。

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
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-agent-cli-dispatch -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
