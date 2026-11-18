# soia-pkm-clip-web

> 归档网页、博客文章或公开播客节目到 Obsidian vault；可同时保留 shownotes 与本地音频

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-web) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这个网页」「clip 这个链接」「存这篇博客或播客」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档网页、博客或外文长文 | 抓取标题/作者/时间与完整正文；非中文正文自动补充意译 `## 中文译文`，默认随手交 `organize` 增量整理 | `<articles>/YYYY/MM/` Markdown 笔记与分步入库回执 |
| 归档公开播客单集（小宇宙/Apple Podcasts 等） | 调 `archive_podcast.py` 剥离分享 query、收 shownotes、按需下载音频落 `_attachments/podcasts/` 并嵌 `![[...]]` 播放器 | 播客笔记、音频本地路径/SHA-256 或 `--metadata-only` 纯文本 |
| 归档后转 PDF | 完成归档整理后按 [references/obsidian-pdf-export.md](references/obsidian-pdf-export.md) 走 Obsidian 原生导出 | 同目录 PDF 产物 |

### 客户如何使用

- 「归档这个网页链接到知识库，并同步更新文章 MOC。」（加“仅归档/不要整理”则停在 clip）
- 「存一下这期播客节目，保留 shownotes 并下载本地音频。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-web -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
