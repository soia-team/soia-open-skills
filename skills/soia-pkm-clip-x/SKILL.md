---
name: soia-pkm-clip-x
description: 把 X (Twitter) 推文 / thread / Article 长文一键归档到 Obsidian vault。基于 fxtwitter API，零配置、无需 X API key。支持 Telegram 我的收藏批量同步（JSON 导出路径，零风险）。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内优先调用 Obsidian 自带 PDF 导出。Triggers：「归档这条 X」「archive this」「clip 这条推文」「整理这条 thread」「同步我的电报收藏」
---

# soia-pkm-clip-x

把 X 上有价值的内容沉淀到 Obsidian vault，构建可检索的知识资产。

## 定位

X 的原生 UI 不利于长期回看：thread 散在时间线、Article 排版乱、链接易失效、搜索弱。本 skill 把 X 上的优质长内容一键沉淀进 Obsidian：

- thread 完整 unroll
- X Article 取全量 `content.blocks`
- 元数据齐全（作者、metrics、媒体直链、created_at）
- frontmatter 主题双链，方便 MOC 聚合
- 多语言识别（zh / en / ja / ko）

## 前置依赖

- Obsidian vault（任意结构）
- Python 3，纯 stdlib（无第三方依赖，归档单条推文）
- 可选：`pip install telethon`（仅 MTProto 同步用）
- vault 定位优先级：
  1. 命令行 `--vault <path>`
  2. 环境变量 `OBSIDIAN_VAULT`
  3. 从当前工作目录向上自动发现 vault（找 `AGENTS.md` / `.obsidian`）
- 文章目录定位优先级：
  1. 命令行 `--articles-dir <subdir>`
  2. 环境变量 `OBSIDIAN_ARTICLES`
  3. 退回通用默认 `Articles`

> 说明：Claude Code / Codex / Gemini CLI / opencode 等工具经常在非登录 shell 中执行命令，未必继承 shell 启动文件里的 `export`。脚本会先加载私有 env 文件，再从 cwd 自动发现 vault；如果 agent 已经在 vault 目录里，直接运行即可。

- 私有 env 文件（可选，**不要放在 vault 或开源 skill 仓库**）：

  优先级：`$SOIA_PKM_ENV_FILE` > `~/.config/soia-pkm/env` > `~/.soia-pkm.env`。

  支持变量名：`OBSIDIAN_VAULT`、`OBSIDIAN_ARTICLES`、`X_ARCHIVE_LANG`；仅 MTProto 同步需要 `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` / `TELEGRAM_SESSION_STRING`。真实值只写在私有 env 文件里，不写入本文件。

## 核心 API：fxtwitter

把 X URL 里的 `x.com` 换成 `api.fxtwitter.com`，直接 GET 回 JSON。无需 X API key、无需登录、零成本。

| 关键字段 | 用途 |
|---------|------|
| `tweet.text` / `tweet.raw_text.text` | 推文正文 |
| `tweet.article.title` | X Article 标题 |
| `tweet.article.content.blocks[]` | Article 长文 blocks |
| `tweet.replying_to_status` | 上一条推文（thread 回溯） |
| `tweet.quote` | 引用的推文 |
| `tweet.media[]` | 媒体（图/视频直链） |
| `tweet.created_timestamp` | UNIX 时间戳 |
| `tweet.views / likes / bookmarks / retweets` | metrics |

兜底：fxtwitter 失败 → `cdn.syndication.twimg.com` 公开端点。

## 触发词

| 用户说 | 调用 |
|--------|------|
| 「归档这条 X：URL」 / 「archive this：URL」 | 在 vault 根目录运行 `archive_x.py <URL>`；不在 vault 内时加 `--vault <path>`。非中文内容默认自动补译文（见下方工作流第 4 步），不用额外说「翻译」 |
| 「归档并转 PDF：URL」 / 「归档并导出 PDF：URL」 | 先按默认归档流程写入并补全 Markdown，再按 `references/obsidian-pdf-export.md` 走 Obsidian 原生导出；不要优先用 pandoc/wkhtmltopdf |
| 「整理一下这条 thread：URL」 | 同上，强制 thread 回溯 |
| 「同步我的电报收藏」 + 给 JSON 路径 | `sync_telegram_export.py <path> --dry-run` 先看，确认后实跑 |
| 「用 API 同步电报」（已有凭证） | `sync_telegram_saved.py` |

## 工作流（默认归档）

1. 解析 URL → handle + status_id
2. 调脚本 `archive_x.py <URL>`
3. 脚本检查 vault 是否已归档（按 frontmatter `url:` 字段）
   - 已存在 → 输出 SKIP，退出
   - 否则 → 抓 fxtwitter，写入 vault
4. AI 之后补：
   - 1 句话中文 `## 摘要`
   - 1-3 个 `topics` 双链 + `people` 双链
   - **非中文内容（`language` 不是 zh）：默认把 `## 中文译文` 段补成完整译文**，不用用户额外说「翻译」。要求**意译不直译**——读起来要像人写的中文，不是机器翻译腔；专有名词、产品名、代码/命令/API 参数保留英文原文，只翻译叙述性文字和说明
5. 「我的看法」段永远留空给用户

## 归档后导出 PDF

用户同时要求「转 PDF / 导出 PDF」时，先完成 Markdown 归档、摘要、topics/people 与月份归位，再读取并执行 **[references/obsidian-pdf-export.md](references/obsidian-pdf-export.md)**。只要目标文件位于 Obsidian vault 内，就优先调用 Obsidian 自带「导出 PDF」；外部 PDF 引擎只能作为明确降级方案。

## Telegram 我的收藏批量同步

把手机随手转发到 Telegram「我的收藏」的 X 链接批量归档进 vault。**推荐 JSON 导出路径**（零风险、零依赖）。

两条路径（JSON 导出 / MTProto API）的完整步骤、命令、注意事项 → 见 **[references/telegram-sync.md](references/telegram-sync.md)**。

## 文件命名

```
<YYYY-MM-DD>-X-<handle>-<title前 50 字>.md
```

例：
- `2026-05-24-X-cyrilXBT-How-to-Organize-Your-Obsidian-Vault.md`
- `2026-05-29-X-ObsidianOtaku-保存版AIエージェントのためのObsidian活用術.md`

同日同作者多条 → 末尾加 `-<status_id 后 6 位>`。

## 输出 frontmatter

```yaml
---
tags: [文章摘抄]
source: X
url: https://x.com/<handle>/status/<id>
author: <显示名>
handle: "@<handle>"
published_at: YYYY-MM-DD HH:mm
captured_at: YYYY-MM-DD HH:mm
language: zh / en / ja / ko
type: tweet / thread / article
topics: ["[[xxx]]", ...]   # AI 填
people: ["[[xxx]]", ...]   # AI 填
media: [...] / 0
content_complete: true
metrics:
  views: N
  likes: N
  bookmarks: N
---
```

## 边界与异常

| 场景 | 处理 |
|------|------|
| fxtwitter 返回 404 | 推文被删/私密，建议查 archive.org |
| fxtwitter 5xx | 重试 1 次，失败兜底 syndication 端点 |
| URL 非 x.com / twitter.com | 拒绝，建议用 Web Clipper |
| 推文文本空且无 article 且无 media | 警告：「纯转推/纯回复，可能无独立内容」 |
| 同日同作者文件名重复 | 末尾加 `-<status_id 后 6 位>` |
| 视频媒体 | frontmatter `media[]` 记 mp4 直链，不内嵌 |

## 命令行参考（归档）

```bash
python3 archive_x.py <URL>
python3 archive_x.py <URL> --force                  # 覆盖已归档
python3 archive_x.py <URL> --vault /path/to/vault   # 覆盖环境变量
python3 archive_x.py <URL> --articles-dir <articles-subdir>
```

Telegram 同步命令 → 见 [references/telegram-sync.md](references/telegram-sync.md)。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
