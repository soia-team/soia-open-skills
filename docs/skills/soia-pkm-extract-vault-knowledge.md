# soia-pkm-extract-vault-knowledge

> 从整个 Markdown/Obsidian 知识库或指定模块的工作台、冻结证据、文章、项目研究与历史语料中，提炼去状态、可复用且带来源的长期知识，同时保留原始证据并隔离敏感信息

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-extract-vault-knowledge) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「从知识库提炼长期知识」「把这份材料沉淀为知识」「从指定模块提炼」「从这份报告抽方法」

## 能力与用法

### 这个技能可以做什么

- 先查重，再从一个或多个来源提炼概念、指南、参考、检查表或通用模式。
- 删除当前进度、责任人、下一步和一次性环境值，保留适用边界、反例、时效说明与来源 wikilink。
- 在写入前识别账号、密码、token、cookie、个人路径、客户数据等敏感内容；知识笔记只保留抽象方法，不复制秘密值。
- 盘点 20 区时区分“精选长期知识”和“历史导入/来源语料”，不把旧语料的目录位置当成可信度。
- 处理 PDF、Word、表格或图片来源时，先标记原始附件类型和提取/OCR 状态；没有正文提取证据时只能引用文件名/路径，不能把附件标题当成结论。

### 客户如何使用

提供 vault 路径以及来源笔记、主题或待整理的 20 区范围。Agent 先给候选与去向；单篇且目标明确时可直接 create-only，新建超过 3 篇、存在重名或涉及敏感内容时必须先确认逐项计划。

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
