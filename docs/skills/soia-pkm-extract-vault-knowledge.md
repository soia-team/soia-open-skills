# soia-pkm-extract-vault-knowledge

> 从整个 Markdown/Obsidian 知识库或指定模块的工作台、冻结证据、文章、项目研究与历史语料中，提炼去状态、可复用且带来源的长期知识，同时保留原始证据并隔离敏感信息

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-extract-vault-knowledge) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「从知识库提炼长期知识」「把这份材料沉淀为知识」「从指定模块提炼」「从这份报告抽方法」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把报告/日志/历史语料沉淀为 20 区知识 | 查重、去状态、剥离凭据/身份等敏感信息，create-only 新建带来源 wikilink 笔记 | 去向候选清单、manifest 验证与新建文件路径 |

### 客户如何使用

给出 vault 路径及来源笔记/模块（20 区新建须落 `10_主题知识`/`20_规范与手册`/`30_学习指南` 唯一编号子目录，历史导入仅作来源）；单篇且明确可直接建，超 3 篇、重名或涉敏感须先确认清单。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-extract-vault-knowledge -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
