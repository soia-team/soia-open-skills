# soia-pkm-log-agent-sessions

> 为 Claude Code、Codex 等本地 AI 接入最小化 vault 会话改动快照，支持去重、dry-run、既有 notify 合并和安全卸载

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-log-agent-sessions) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「接入 AI 会话日志」「记录 Codex 改动」「配置 SessionEnd 日志」

## 能力与用法

### 这个技能可以做什么

- 为 Claude Code `SessionEnd` 或 Codex `notify` 生成轻量日志。
- 用 git 状态、tracked diff 和 untracked 内容哈希去重，连续编辑同一文件仍会产生新快照。
- 保留客户已有 Codex notify 命令，并提供 dry-run、安装检查和卸载步骤。
- 报告旧日志数量/体量；默认不自动删除或轮转。

### 客户如何使用

提供 vault 路径、AI 名称和期望日志目录。Agent 先展示将修改的用户配置片段；只有客户明确同意后才合并写入。首次先手动 dry-run，再触发一次真实小改动验证。

## 安装

客户明确选择安装整个 `soia-pkm-vault` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-log-agent-sessions -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
