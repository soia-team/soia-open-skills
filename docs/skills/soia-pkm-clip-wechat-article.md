# soia-pkm-clip-wechat-article

> 归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-wechat-article) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这篇公众号」「clip 这个公众号文章」「存这篇微信文章」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档单篇微信公众号链接 | 跑 `archive_wechat.py` 按标准化 URL 去重、解析 `#js_content` 与元数据，按默认五段收口整理 MOC | `<articles>/YYYY/MM/` Markdown 笔记与分步入库回执 |
| 归档后导出 PDF | 先完成 Markdown 归档与月份归位，再按 [references/obsidian-pdf-export.md](references/obsidian-pdf-export.md) 原生导出 | Markdown 与同目录 PDF 路径 |

### 客户如何使用

- 「归档这篇公众号文章 `https://mp.weixin.qq.com/s/...` 到知识库。」（明确说“仅归档”则停在 clip）
- 「存这篇微信文章并导出 PDF。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-wechat-article -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
