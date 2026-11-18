# soia-pkm-bootstrap-vault-base

> 以 plan-first、create-only、可检查的方式初始化平台中立的 AI-native Markdown vault 基座，包含分区下钻规则、工作台生命周期、模板与多 AI 适配层

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-bootstrap-vault-base) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「初始化知识库」「新建 Markdown vault」「搭建 AI-native PKM」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 初始化中立 PKM 骨架与规则层 | 创建 00–90 分区（20 精选固定 `10_主题知识`/`20_规范与手册`/`30_学习指南`、历史导入 `90_历史导入`，默认 `00_Obsidian系统/` 与 `10_工作台/00_Inbox/`）及模板 | json `plan`、逐文件 create/skip/conflict/drift 与 `--check` 结果 |

### 客户如何使用

提供目标目录及可选自定义 `config.json`（Schema v2 支持 `extends_default`、`directories`、`files`），先跑默认 plan 审查 create/skip/drift，再 `--apply` 与 `--check`。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-bootstrap-vault-base -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
