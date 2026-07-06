---
name: soia-pkm-clip-drive
version: 1.0.0
description: 把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理。Triggers：「导入云盘资料」「把这批 PDF 导进来」「clip 这个文档」「整理云盘」
---

# soia-pkm-clip-drive

`clip` 家族的**云盘成员**：把网盘 / 本地的存量资料（PDF、DOCX 等）导入 vault。区别于抓网页，它处理**本地 / 云盘文件**。

## 处理

- 输入：文件路径 / 目录（PDF、DOCX、TXT、Markdown）
- 提取：`pypdf` / `pdfplumber`（PDF）、`python-docx`（Word）提取文本；原文件留到 `_附件/`。
- 大批量：目录批处理，每个文件 → 一篇笔记。
- 脚本：`scripts/import_drive.py <路径> --vault <path> [--recursive]`。

## 落地

- 资料 / 参考类 → `20_资料库/<主题>/`；文章类 → `40_图书视频馆/10_文章摘抄/`。
- frontmatter：`tags:[资料]` 或 `[文章摘抄]`、`source: 云盘/pdf`、`original_path`、`captured_at`、`topics:[]`。
- 导入后**必走 `organize`**：云盘资料通常量大又杂，靠 organize 分类 / 建 MOC / 去重。

## 闭环位置

`★clip-drive(收) → organize（云盘资料尤其依赖整理） → distill → …`。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
