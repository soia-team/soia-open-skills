---
name: x-to-obsidian
description: 把 X (Twitter) 推文 / thread / Article 长文一键归档到 Obsidian vault。基于 fxtwitter API，零配置、无需 X API key。支持 Telegram 我的收藏批量同步（JSON 导出路径，零风险）。Triggers：「归档这条 X」「archive this」「clip 这条推文」「整理这条 thread」「同步我的电报收藏」
---

# x-to-obsidian

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
- 设置环境变量：

  ```bash
  export OBSIDIAN_VAULT=~/Documents/MyVault
  # 可选：自定义归档子目录（默认 "Articles"）
  export OBSIDIAN_ARTICLES="Articles"
  ```

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

## 可选补充: 已批准的 OpenClaw / TweetClaw 导出

当用户提供已批准的 OpenClaw / TweetClaw JSON 或 JSONL 导出时，只把它作为只读
上下文使用：

- 保留原始 URL、tweet ID、作者、抓取时间、截图路径和 metrics 来源
- 用导出内容辅助 `Summary`、`topics`、`people`、`Related` 和来源说明
- 不覆盖用户写的 `## My Thoughts`
- 不根据导出内容点赞、回复、转发、关注、私信或发推

如果导出内容和 fxtwitter 结果冲突，优先保留两个来源并在笔记中标注差异，不要
编造缺失的 metrics 或作者信息。

## 触发词

| 用户说 | 调用 |
|--------|------|
| 「归档这条 X：URL」 / 「archive this：URL」 | `archive_x.py <URL>` |
| 「归档并翻译：URL」 | `archive_x.py <URL>` + AI 填 Translation 段 |
| 「整理一下这条 thread：URL」 | 同上，强制 thread 回溯 |
| 「同步我的电报收藏」 + 给 JSON 路径 | `sync_telegram_export.py <path> --dry-run` 先看，确认后实跑 |
| 「用 API 同步电报」（已有凭证） | `sync_telegram_saved.py` |

## 工作流（默认归档）

1. 解析 URL → handle + status_id
2. 调脚本 `archive_x.py <URL>`
3. 脚本检查 vault 是否已归档（按 frontmatter `url:` 字段）
   - 已存在 → 输出 SKIP，退出
   - 否则 → 抓 fxtwitter，写入 vault
4. AI 之后补：1 句话中文 `## Summary` + 1-3 个 `topics` 双链 + `people` 双链
5. 「My Thoughts」段永远留空给用户

## Telegram 同步两条路径

### A. JSON 导出（推荐，零风险）

```
Telegram Desktop
  → Settings → Advanced → Export Telegram data
  → 勾「私聊」+ 选 JSON 格式
  → 得到 result.json
```

```bash
python3 sync_telegram_export.py <result.json> --dry-run   # 看清单
python3 sync_telegram_export.py <result.json>             # 实跑
```

自动按 URL 去重、自动跳过已归档。每月导出一次即可增量同步。

### B. MTProto API（高阶，国内慎用）

需要：
- `https://my.telegram.org/auth` 申请 api_id / api_hash
- 跑 `generate_telegram_session.py` 拿 session_string
- 住宅 IP（中国大陆用户必须 HK/JP 住宅段，机房 IP 必触发 ERROR）

⚠️ **国内用户优先用方案 A**。my.telegram.org 创建 app 在大陆几乎必踩 IP 风控，反复尝试会触发账号级 24-72h 冻结。

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

## 命令行参考

```bash
# 归档单条
python3 archive_x.py <URL>
python3 archive_x.py <URL> --force                  # 覆盖已归档
python3 archive_x.py <URL> --vault /path/to/vault   # 覆盖环境变量

# Telegram JSON 导出同步
python3 sync_telegram_export.py <result.json>
python3 sync_telegram_export.py <result.json> --dry-run
python3 sync_telegram_export.py <result.json> --since 2026-06-01
python3 sync_telegram_export.py <result.json> --limit 30

# MTProto 同步（需先 setup）
python3 generate_telegram_session.py    # 一次性
python3 sync_telegram_saved.py --dry-run
python3 sync_telegram_saved.py --days 30
python3 sync_telegram_saved.py --all
```
