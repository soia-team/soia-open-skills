---
name: soia-pkm-publish
version: 1.0.0
description: 把写好的文章草稿适配并发布到多平台——公众号（排版 + 推草稿箱）、X thread、小红书卡片。核心是公众号：按三级强调规则渲染成带样式 HTML，调微信 draft/add API 推到草稿箱（只建草稿、绝不自动群发）。Triggers：「发布这篇」「把这篇发成公众号」「一稿多发」「把草稿适配成三个平台」「排版这篇公众号」「publish 这篇」
---

# soia-pkm-publish

PKM 闭环的**发布环节（发）**：把 `compose` 产出的成文草稿，适配成各平台格式并投递。核心场景是**公众号**（排版最费手工），其次 X thread、小红书卡片。

> 蓝本：vault 里 `40_图书视频馆/10_文章摘抄/2026/2026-07-02-X-xiaoluv12o-Obsidian+AI公众号排版工作流…` 那篇——本 skill 是它的落地实现。

## 动笔前：读个人上下文

适配任何平台前，先读 `00_Obsidian系统/个人说明书.md` §5「各平台定位」，按该平台的**读者与口吻**调措辞。本 skill 内置的是各平台**格式规则**（下文），个人说明书补的是**口吻与读者定位**，两者叠加——格式对不等于口吻对。个人说明书无此文件或缺该平台定义时，回退到通用格式。

## 公众号发布（主流程）

### 排版规则：三级强调系统

| 级别 | Markdown | 用于 | 数量 |
|------|---------|------|------|
| L1 重点短语 | `**…**` | 核心概念、关键步骤、转折 | 每段 ≤2 |
| L2 关键内容 | `==…==` | 结论、警告、关键数字 | 每篇 ≤5 |
| L3 整句强调 | 单独成句 | 全段最重要的判断 | 每篇 ≤3 |

- 量化：每 1000 字 4–8 个短语级强调，总强调占比 **<15%**。禁背景色 / 框。
- 文章类型：frontmatter `workflow_type: tech`（有代码 / 表格）或 `editorial`（纯文字），渲染器据此选风格。
- 配图：Alt 为空 → 图下不显示 caption；Alt 有内容 → 写清图里是什么（别用"配图""截图"这种无信息词）。

### 5 步流程

1. **检查** frontmatter 的 `workflow_type`。
2. **强调润色**：AI 按三级规则给全文加 `**` / `==` 标记，检查密度 <15%。
3. **渲染**：`scripts/render.py` 把 Markdown → 带样式 HTML（tech / editorial 两风格）。
4. **推草稿箱**：`scripts/publish.py` → 调微信 `draft/add` 建草稿（图片传 CDN、传封面）。
5. **人工确认发布后** → `scripts/archive.py` 标记已发布、记链接、更新日志。

### 脚本规格（scripts/，可让 AI 按规格现场生成）

- `render.py <in.md> <out.html> [--style tech|editorial]`：解析 frontmatter；`**…**` → 主题色加粗，`==…==` → 红色加粗；tech 模式加代码块 / 表格 / 引用样式。
- `publish.py --article <md> --cover <png> [--dry-run]`：渲染 → 传图 / 封面到微信 CDN → `draft/add` 建草稿。凭据从 `.env` 读 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`。
- `archive.py --article <md> --url <link>`：frontmatter 置 `status: 已发布` + 记日期 / 链接 + 追加日志。

> 首次搭 <1 小时（规则 15 分 + AI 生成脚本 20 分 + Skill 文档 10 分），之后每篇排版 ≈ 0。

## ⚠️ 安全规则（必守）

- **只建草稿，绝不自动群发**——群发必须用户在公众号后台手动点。
- 凭据存 `.env`（`WECHAT_APP_ID` / `WECHAT_APP_SECRET`），**不提交 Git**。
- 需先在 developers.weixin.qq.com / mp 后台启用开发 API、配 IP 白名单。

## 其他平台（简版适配）

- **X thread**：长文按逻辑拆成 (1/N)，首条抓钩子、末条给 CTA，每条 ≤280 字。
- **小红书**：提炼成卡片式——标题党（带 emoji）+ 3–5 段短文 + 话题标签 + 配图建议。

## 执行后回执

推完草稿后告诉用户：① 草稿在公众号后台（哪篇、什么风格）② 提醒"确认无误后你手动群发" ③ 群发后回来说一声，我跑 archive 归档。X / 小红书版同理告知产出位置。

## 闭环位置

```
clip(收) → organize(整理) → distill(点) → compose(写) → ★publish(发)
```

上游 `compose` 给成文草稿；`publish` 负责多平台适配 + 投递，是闭环最后一环。凭据与"手动群发"这道人工闸门由用户把控。
