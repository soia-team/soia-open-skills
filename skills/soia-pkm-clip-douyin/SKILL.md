---
name: soia-pkm-clip-douyin
description: 归档单条抖音视频到 Obsidian vault：Playwright 拦截签名 API 拿到直链元数据（作者/文案/时长/互动数），MP4 下载到本地 Downloads（不进 vault），vault 里只留轻量 Markdown 笔记 + 本地路径索引。Triggers：「归档这条抖音」「clip 这个抖音视频」「存一下这条抖音」「archive this douyin video」
version: 1.0.0
created_at: 2026-07-21 00:00:00
updated_at: 2026-07-21 15:30:00
created_by: claude fable 5
updated_by: claude fable 5
---

# soia-pkm-clip-douyin

把有价值的抖音视频沉淀到 Obsidian vault：轻量 Markdown 笔记记元数据和文案，视频文件单独落地本机 Downloads 目录，不把大体积二进制塞进 git 追踪的知识库。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档一条抖音视频链接 | 用 Playwright 打开视频页拦截签名 API，拿到作者/文案/时长/互动数和可下载直链；下载 MP4 到本地；在 vault 写一篇轻量 Markdown 笔记（含 `media_local_path`） | vault 里新增一个 `.md` 文件，终端打印文件路径、作者、发布时间、下载路径、互动数据 |
| 只想先看这条链接能不能解析，暂不下载视频 | 加 `--metadata-only`：只抓元数据和文案写笔记，跳过视频下载 | 笔记里 `media_local_path` 为空、`media_fetched: false`，日志提示候选直链数量 |
| 同一条视频重复归档 | 按 vault 内已有笔记的 frontmatter `url:` 做去重 | 打印 `⚠️ Already archived` 并退出，不重复下载/不重复写笔记 |
| 缺少 Playwright 依赖 | 停止并给出安装命令，不猜测降级方案 | `❌` 开头的错误信息 + `pip install playwright && python -m playwright install chromium` |

### 客户如何使用

1. 给出一条抖音视频链接（`https://www.douyin.com/video/<id>`、带 `modal_id=`/`resource_id=` 参数的链接，或 `v.douyin.com` 短链）。
2. 在 vault 根目录运行 `python3 scripts/archive_douyin.py <URL>`；不在 vault 内时加 `--vault <path>`。
3. 脚本自动去重、抓取、下载、写笔记；全过程失败会用 `❌` 报出具体原因，不会留下半成品笔记。
4. 归档完成后，按回执里的「Next step」提示补 `## 摘要`、`topics`、`people`。

### 依赖与安装

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| `playwright`（Python 包） | 强依赖 | `pip install playwright && python -m playwright install chromium` | 停止并打印安装命令，退出码非 0，不做任何猜测性降级 |
| Obsidian vault | 强依赖 | 任意结构，需能被 `--vault` / `OBSIDIAN_VAULT` / cwd 自动发现三选一定位到 | 报错并说明如何指定路径 |
| Python 3 stdlib（`urllib`） | 强依赖 | 随 Python 自带，无需安装 | — |

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-clip-douyin -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-douyin/config.yml
SOIA_PKM_CLIP_DOUYIN_CONFIG_FILE=<custom-config-path>
```

- 如果只是偶尔归档、不想固定 vault 路径，可以不建 `config.yml`，每次用 `--vault` 传参即可。
- 支持变量名：`OBSIDIAN_VAULT`、`OBSIDIAN_ARTICLES`。真实路径只写在私有 `config.yml` 里，参考 [config.example.yml](config.example.yml)。
- 优先级：`--vault`/`--articles-dir` CLI 参数 > `OBSIDIAN_VAULT`/`OBSIDIAN_ARTICLES` 进程环境变量 > `SOIA_PKM_CLIP_DOUYIN_CONFIG_FILE` 指向的私有 `config.yml` > 从当前工作目录向上自动发现 vault（找 `AGENTS.md` / `.obsidian`）> 通用兜底 `Articles/`（并向 stderr 打印警告）。

### 私密信息与中间数据

- 视频文件本身**不进 vault**（vault 是 git 追踪的 Markdown 知识库，不适合放大体积二进制）；MP4 落地 `~/Downloads/soia-pkm-clip-douyin/<video_id>/video.mp4`，vault 笔记里只存这个本地绝对路径的索引。
- Playwright 拦截到的签名直链（含 `msToken` / `a_bogus` 等 token 参数）**不写入 vault、不写入日志、不写入 stdout**——失败回执里只打印去掉 query string 的 host+path，避免把认证 token 明文留在可能被分享的日志/笔记里。
- 签名直链本身是短时效的：脚本设计上不会把裸的原始视频直链缓存到磁盘或跨进程传递；`--metadata-only` 之后如果用户想要视频，必须重新运行脚本（见「边界与异常」）。
- Playwright 用一次性 headless 浏览器上下文（不持久化登录态、不使用用户的真实抖音账号 cookie），只做匿名网页浏览；不写 provider 登录态目录。
- 不缓存、不落盘用户以外任何人的隐私信息；抓到的作者昵称/UID 仅用于本条笔记的 frontmatter/正文。

### 日志与完成回执

```markdown
完成：<一句话说明本次归档了什么>。

日志摘要：
- started: 已定位 vault / video_id=<id>
- processed: 1 条抖音视频
- created/updated: <vault 内笔记相对路径>
- skipped/failed: <0 或具体原因>

文件变化：
- <vault 笔记绝对路径>
- <本地 MP4 绝对路径，或"未下载（--metadata-only）">

验证：
- 笔记内 `media_local_path` 文件是否存在、MP4 文件头是否为有效 ftyp box

问题与下一步：
- <缺 playwright / 视频不可见 / 需要客户确认 / 建议下一条命令；没有则写"无">
```

## 定位

抖音 App 内的视频不方便长期沉淀成可检索的文字知识资产：文案会被埋没在信息流里，找不到、搜不到、也没法和其他笔记双链。本 skill 把单条抖音视频的元数据和文案一键归档进 Obsidian，视频本体则留在本机磁盘，vault 保持轻量。

## 前置依赖

- Obsidian vault（任意结构）
- Python 3 + `playwright`（拦截签名 API 必需，见上方安装命令）；下载步骤本身是纯 stdlib `urllib`，不需要额外依赖
- vault 定位优先级：
  1. 命令行 `--vault <path>`
  2. 环境变量 `OBSIDIAN_VAULT`
  3. 从当前工作目录向上自动发现 vault（找 `AGENTS.md` / `.obsidian`）
- 文章目录定位优先级：
  1. 命令行 `--articles-dir <subdir>`
  2. 环境变量 `OBSIDIAN_ARTICLES`
  3. 退回通用默认 `Articles`；脚本会向 stderr 打印警告，退出码保持 0

> 说明：Claude Code / Codex / Gemini CLI / opencode 等工具经常在非登录 shell 中执行命令，未必继承 shell 启动文件里的 `export`。脚本会先加载私有 `config.yml`，再从 cwd 自动发现 vault；如果 agent 已经在 vault 目录里，直接运行即可。

- 私有 `config.yml`（可选，**不要放在 vault 或开源 skill 仓库**）：

  优先级：`$SOIA_PKM_CLIP_DOUYIN_CONFIG_FILE`（或兼容别名 `$SOIA_PKM_CLIP_DOUYIN_ENV_FILE`）> `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-douyin/config.yml`。

  支持变量名：`OBSIDIAN_VAULT`、`OBSIDIAN_ARTICLES`。真实值只写在私有 `config.yml` 里，不写入本文件。

## 核心机制：Playwright 拦截签名 API

抖音网页版播放地址由客户端签名（`msToken`/`a_bogus`）动态生成，页面 SSR JSON（`RENDER_DATA`）不含 `play_addr`，没有纯 HTTP 的取数方式，必须走一次真实浏览器：

1. `playwright.chromium.launch(headless=True)` + `new_context(user_agent=<desktop UA>, locale="zh-CN")`。
2. `page.on("response", handler)` 监听所有 `douyin.com` 域名下的 JSON 响应。
3. 匹配策略**按内容而非端点名**：递归搜索每个响应体，找 `str(node["aweme_id"]) == 目标id` 且自身带 `"video"` 键的字典——不管它出现在预期的 `aweme/detail/` 端点，还是混在 `aweme/mix/` 这类合集端点返回的 `aweme_list[]` 数组里。
4. 轮询直到命中或超时（默认 60s，`--timeout` 可调）。
5. 命中后按优先级取直链：`play_addr` → `play_addr_h264` → `download_addr`，逐个尝试下载直到成功。

| 关键字段 | 用途 |
|---------|------|
| `aweme["video"]["play_addr"]["url_list"][0]` | 视频直链（h264/download_addr 兜底） |
| `aweme["desc"]` | 文案/标题 |
| `aweme["author"]["nickname"]` / `["uid"]` | 作者 |
| `aweme["create_time"]` | 发布时间（Unix 秒） |
| `aweme["video"]["duration"]` | 时长（毫秒） |
| `aweme["statistics"]` | `digg_count`/`comment_count`/`collect_count`/`share_count`/`play_count`/`admire_count`/`recommend_count` |

下载步骤用纯 stdlib `urllib.request`：`User-Agent` + `Referer: https://www.douyin.com/` + `Range: bytes=0-`，流式写盘并校验字节数与 MP4 magic bytes（`ftyp` box）。

## 触发词

| 用户说 | 调用 |
|--------|------|
| 「归档这条抖音：URL」/「clip 这个抖音视频」 | 在 vault 根目录运行 `archive_douyin.py <URL>`；不在 vault 内时加 `--vault <path>` |
| 「先看看这条链接能不能解析」/「只要文案不要视频」 | 加 `--metadata-only`，跳过视频下载 |
| 「这条抖音重新归档一下」（已存在） | 加 `--force`，会保留已有的 `topics`/`people`/`## 摘要` |

## 工作流（默认归档）

1. 解析 URL → `video_id`（短链会先做一次 HTTP 重定向解析再匹配）
2. 调脚本 `archive_douyin.py <URL>`
3. 脚本检查 vault 是否已归档（按笔记 frontmatter `url:` 行是否包含该 `video_id`）
   - 已存在 → 输出 `SKIP`，退出 0
   - 否则 → 起 Playwright 拦截签名响应，拿到 `aweme` 对象
4. 未 `--metadata-only` 时：下载 MP4 到 `~/Downloads/soia-pkm-clip-douyin/<video_id>/video.mp4`；任一环节失败都不写笔记
5. 写入 vault 笔记（frontmatter + 正文）
6. AI 之后补：
   - 1 句话中文 `## 摘要`
   - 1-3 个 `topics` 双链 + `people` 双链
7. 「我的看法」段永远留空给用户

## 文件命名

```
<YYYY-MM-DD>-抖音-<作者昵称前 20 字>-<文案前 50 字>.md
```

同日同作者多条 → 末尾加 `-<video_id 后 6 位>`。

## 输出 frontmatter

```yaml
---
tags: [视频摘抄]
source: 抖音
url: <用户给出的原始链接>
author: <昵称>
published_at: YYYY-MM-DD HH:mm
captured_at: YYYY-MM-DD HH:mm
language: zh
type: video
topics: []   # AI 填
people: []   # AI 填
media_local_path: "<本地 MP4 绝对路径，--metadata-only 时为空>"
content_complete: true
metrics:
  likes: N
  comments: N
  collects: N
  shares: N
  plays: N
  admires: N
  recommends: N
---
```

正文结构：`# <标题>` → `> [!source]-` 来源折叠块（来源/抓取方式/元数据/媒体状态）→ `## 摘要`（AI 补）→ `## 原文`（抖音文案原文，不加工）→ `## 我的看法`（留空）→ `## 关联`。

## 边界与异常

| 场景 | 处理 |
|------|------|
| URL 不含 `/video/<id>`、`modal_id=`、`resource_id=`，也不是能重定向解析的短链 | 拒绝，报错说明支持的格式 |
| Playwright 轮询超时未拦截到目标 `aweme` | 视频已删除/私密/地区不可见，或抖音改版接口结构；明确报错，不猜测 |
| 拦截到 `aweme` 但所有候选直链下载都失败 | 逐条打印失败原因（URL 去 query string），退出非 0，**不写笔记** |
| 用 `--metadata-only` 归档后想要视频 | 必须重新完整运行一次脚本——签名直链短时效，脚本不做"先记直链、以后再下载"的两段式设计 |
| 同一条视频再次用短链归档、此前用完整链接归档过 | 短链文本本身不含数字 video_id，去重按 frontmatter `url:` 行做子串匹配可能失效；建议优先用完整 `douyin.com/video/<id>` 链接归档 |
| 同日同作者文件名重复 | 末尾加 `-<video_id 后 6 位>` |
| vault 内已归档 | 默认 `SKIP` 并退出 0；`--force` 才覆盖（保留已有 `topics`/`people`/`## 摘要`） |

## 命令行参考

```bash
python3 scripts/archive_douyin.py <URL>
python3 scripts/archive_douyin.py <URL> --force                  # 覆盖已归档
python3 scripts/archive_douyin.py <URL> --vault /path/to/vault   # 覆盖环境变量
python3 scripts/archive_douyin.py <URL> --articles-dir <articles-subdir>
python3 scripts/archive_douyin.py <URL> --metadata-only          # 只抓元数据，跳过视频下载
python3 scripts/archive_douyin.py <URL> --timeout 90             # 拦截等待超时秒数（默认 60）
```

## 验证与测试

对抗审查（正确性 + 安全双镜头）发现 1 处 should-fix：`find_existing_archive` 的去重匹配原为对 `url:` 整行做裸子串测试，未像 `archive_x.py` 的 `/status/{id}` 那样加边界锚点——`video_id` 恰好是另一条已归档链接里更长数字串（或某个查询参数值）的子串时会误判"已归档"，静默漏掉真实新视频。已改为 `(?<!\d){video_id}(?!\d)` 数字边界匹配：不假设 `url:` 存的是哪种链接形态（`/video/`、`modal_id=`、`resource_id=` 或短链解析后的形态均可能），只要求两侧不是数字，兼顾防误判与格式无关性。

真实端到端验证（非 mock，2026-07-21，真实公开抖音视频）：
- 完整归档：Playwright 拦截 `aweme/detail` 拿到 132MB 视频候选直链、下载完成、`file` 确认合法 MP4、frontmatter 点赞/评论/收藏/转发数与人工核对的实时数字一致（同一视频 40 分钟内两次读数的微小差异是真实点赞增长，非 bug）
- 重跑同一视频（未加 `--force`）：正确 `SKIP`
- 去重边界修复用真实归档结果验证：正常场景（真实 `/video/<id>` 链接）未受影响，仍正确识别已归档

`py_compile` + `audit_skills.py`：无 findings。

---

## 完成后回执

**交付顺序**：先把文件落盘，再输出下面的回执，不得反过来；不确定的元数据（如作者、发布时间解析失败）在回执里显式标注"未核实"，不编造。

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建的 vault 笔记路径和本地 MP4 路径（完整路径）；`--metadata-only` 时说明视频未下载。
   - 若走了 `Articles/` 兜底，必须显式标注该目录不是本 vault 的正式归档位，并建议用户配置 `--articles-dir`、`OBSIDIAN_ARTICLES` 或私有 `config.yml` 后归位。
3. **下一步** — 可选的后续建议（如补 `## 摘要`/`topics`/`people`，或衔接 `soia-pkm-organize-article-moc`）。
