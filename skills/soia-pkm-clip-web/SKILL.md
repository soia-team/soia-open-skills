---
name: soia-pkm-clip-web
description: 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。Triggers：「归档这个网页」「clip 这个链接」「存这篇博客」
---

# soia-pkm-clip-web

`clip` 家族的**通用网页成员**：把博客 / 网页文章沉淀进 vault。

## 抓取

- 输入：任意文章 URL（博客 / Substack / Medium / 新闻 / 知乎等）
- 正文抽取：`trafilatura` 或 `readability-lxml` 抽正文（去广告 / 导航），提取标题、作者、发布时间。
- 抓不到正文 → `content_complete: false`，**绝不静默截断**。
- 脚本：`scripts/archive_web.py <url> --vault <path>`。
- 手机端可用 Obsidian Web Clipper 落到 `10_工作台/00_Inbox/`，再由本 skill 迁入。

## 落地（clip 家族统一规范）

- 路径：`40_阅读与摘抄/10_文章摘抄/<年>/YYYY-MM-DD-<来源>-<作者>-<标题>.md`（来源如 博客 / Substack / Medium）
- frontmatter 同 clip 家族；正文 `## 摘要 / 原文 / 我的看法 / 关联`。
- 归档后补摘要 + topics；走 `organize` 归位。

## 闭环位置

`★clip-web(收) → organize → distill → compose → publish`。
