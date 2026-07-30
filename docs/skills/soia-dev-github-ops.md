# soia-dev-github-ops

> GitHub gh CLI 运维、PR 合规审查与修复

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-github-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「查 CI 挂了」「发 release」「加协作者权限」

## 能力与用法

### 这个技能可以做什么

Use gh CLI for GitHub issue, PR, checks, review, workflow run, release, and collaborator-permission operations, plus a pre-merge rule-review procedure and an author-side "address a review and fix it" procedure, with structured JSON output and safety gates

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
| 给某个人加/查/撤仓库协作者权限 | 先确认目标仓库、用户名、权限级别，再执行 `gh api` 写操作并核实生效 | 权限级别说明、确认清单、生效核实结果 |
| 合并前想知道这个 PR 符不符合规则 | 拉 diff + 这个仓库自己的规则文件，交叉核对后给分档建议；不自动合并 | 一句话结论、按阻断/应改/无异议分档的发现清单、CI 与 mergeable 状态 |
| 收到评审意见（贴 PR/评审 URL 说"帮我修复"）| 拉取评审（含行内 + 会话评论）→ checkout 分支 → 委托 fix-loop 逐条修 → push 回原分支并请求重审；不自动合并 | 每条意见的处理状态、验证证据、push 结果、请求重审回执 |
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
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-github-ops -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
