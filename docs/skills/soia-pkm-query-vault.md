# soia-pkm-query-vault

> 以只读方式检索 Markdown/Obsidian vault 的文件名、正文、frontmatter、标签、反向链接与分区清单，并按当前状态、稳定知识、冻结证据、历史归档排序

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-query-vault) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「在知识库里找」「搜索 PKM」「从 vault 回答」「查反向链接」

## 能力与用法

### 这个技能可以做什么

- 按文件名、正文、frontmatter 字段或标签搜索 Markdown 与 Bases 定义。
- 查某个笔记的 wikilink 入链。
- 统计分区和文件类型，帮助 AI 先缩小范围再读取正文。
- 以 `10 当前 → 20 精选长期知识 → 30 证据 → 40/50/60 专项 → 20 待分流/历史导入 → 90 历史` 为默认排序，并明确标记来源层；20 区只有 `10_主题知识/`、`20_规范与手册/`、`30_学习指南/` 标为 `stable`，其余内容标为 `imported`，不因路径自动获得可信度。

### 客户如何使用

提供 vault 路径和问题/关键词。只要求回答时，Agent 不改任何文件。先读取根与命中区规则，再用脚本缩小候选，最后只打开足以回答问题的文件。

## 安装

本技能随 `soia-pkm-vault` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-query-vault -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
