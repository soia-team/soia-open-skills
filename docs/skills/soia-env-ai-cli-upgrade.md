# soia-env-ai-cli-upgrade

> 审计并按授权升级多款 AI CLI，先预演并核验结果

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-ai-cli-upgrade) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「升级 AI CLI」「更新 Claude/Kimi」「检查 CLI 版本」。

## 能力与用法

### 这个技能可以做什么

Audit and upgrade AI/developer CLIs (codex, claude, Antigravity/agy,
Gemini's supported non-consumer lanes, kimi, qwen, opencode, cursor,
deepcode, pi, etc.)
with dry-run reports and logs.

进阶维护工具：面向已装多套 AI CLI 的用户，与本仓其他面向小白的单工具安装技能定位不同。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。

## 安装

本技能随 `soia-env` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-env@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-env@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-ai-cli-upgrade -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
