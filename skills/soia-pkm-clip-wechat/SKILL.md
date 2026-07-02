---
name: soia-pkm-clip-wechat
description: 把微信公众号文章一键归档到 Obsidian vault。抓 mp.weixin.qq.com 的静态 HTML，提取标题/作者/正文/发布时间/配图，按 clip 家族统一规范落地。Triggers：「归档这篇公众号」「clip 这个公众号文章」「存这篇微信文章」
---

# soia-pkm-clip-wechat

`clip` 家族的**公众号成员**：把公众号文章沉淀进 vault。

## 抓取

- 输入：`https://mp.weixin.qq.com/s/...`
- 公众号文章是**静态 HTML**（比 X 好抓，不需 API）：`requests` 拉页面 → 解析 `#js_content`（正文）、`#activity-name`（标题）、`#js_name`（公众号名）、`publish_time`（发布时间）。
- 图片：提取 `data-src`，可选下载或保留链接。
- 脚本：`scripts/archive_wechat.py <url> --vault <path>`（规格对标 clip-x 的 archive_x.py）。

## 落地（clip 家族统一规范）

- 路径：`40_阅读与摘抄/10_文章摘抄/<年>/YYYY-MM-DD-公众号-<作者>-<标题>.md`
- frontmatter：`tags:[文章摘抄]`、`source: 公众号`、`url`、`author`、`published_at`、`captured_at`、`topics:[]`、`content_complete`
- 正文段：`## 摘要`（AI 补）、`## 原文`、`## 我的看法`（留空）、`## 关联`
- 归档后 AI 补摘要 + topics；之后走 `organize` 归位到月份。

## 闭环位置

`★clip-wechat(收) → organize → distill → compose → publish`。与 clip-x/web/drive 共享落地规范，仅源不同。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
