---
name: soia-pkm-clip-web
description: 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内优先调用 Obsidian 自带 PDF 导出。Triggers：「归档这个网页」「clip 这个链接」「存这篇博客」
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

- 路径：`40_图书视频馆/10_文章摘抄/<年>/YYYY-MM-DD-<来源>-<作者>-<标题>.md`（来源如 博客 / Substack / Medium）
- frontmatter 同 clip 家族；正文 `## 摘要 / 原文 / 我的看法 / 关联`。
- 归档后补摘要 + topics；走 `organize` 归位。

## 归档后导出 PDF

用户同时要求「转 PDF / 导出 PDF」时，先完成 Markdown 归档、摘要、topics 与月份归位，再读取并执行 **[references/obsidian-pdf-export.md](references/obsidian-pdf-export.md)**。只要目标文件位于 Obsidian vault 内，就优先调用 Obsidian 自带「导出 PDF」；外部 PDF 引擎只能作为明确降级方案。

## 闭环位置

`★clip-web(收) → organize → distill → compose → publish`。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
