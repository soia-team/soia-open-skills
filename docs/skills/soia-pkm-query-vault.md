# soia-pkm-query-vault

> 以只读方式搜索整个 Markdown/Obsidian 知识库或指定模块，检索文件名、正文、frontmatter、标签、反向链接、代码与附件，并按来源层级返回可核验结果

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-query-vault) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「搜索知识库」「搜索知识库某个模块」「在知识库里找」「从知识库回答」「查需求/代码/PDF/Word/图片」「查反向链接」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 检索笔记、需求、frontmatter、标签、代码与反向链接 | 调用 `query_vault.py` 按文件名/正文/字段/标签/入链精确搜索 | 按可信层级排序的相对路径/wikilink 与短片段 |
| 查询 PDF / DOCX / 图片 / 音视频 | 优先走 Omnisearch/Text Extractor 或 MCP 查正文；无后端则退回文件名命中并明示限制 | 明确标注 `filename_hit`、`content_hit` 或 `ocr` 命中类型 |
| 避免敏感语料正文泄露 | 对历史导入、账号、安全或私人范围默认使用 `--no-snippets` | 只含路径、计数与元数据的脱敏回执 |

### 客户如何使用

给出 vault 路径与关键词/问题；只要求检索或回答时，先读根 `AGENTS.md` 与命中区规则，用最窄模式缩小候选后再打开必要正文。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-query-vault -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
