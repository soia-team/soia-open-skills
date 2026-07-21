---
name: soia-pkm-clip-rednote
description: 归档小红书单篇笔记（图文或视频）到 Obsidian vault。纯 stdlib 解析 __INITIAL_STATE__，无需登录；媒体存本地 Downloads，vault 只留轻量 Markdown。Triggers：「归档这条小红书」「clip 这篇小红书笔记」「archive this rednote」「存这篇 rednote」
version: 1.0.0
created_at: 2026-07-21 14:40:40
updated_at: 2026-07-21 15:20:00
created_by: claude fable 5
updated_by: claude fable 5
---

# soia-pkm-clip-rednote

把小红书（rednote）上有价值的单篇笔记沉淀到 Obsidian vault，构建可检索的知识资产。视频/图片二进制文件不进 vault，只在笔记里记一条本地路径。

## 客户可读说明

### 这个技能可以做什么

归档小红书单篇笔记（图文或视频）到 Obsidian vault：抓取标题、正文、作者、发布时间、互动数据、话题标签，并把视频/图片下载到本地；vault 内生成一份轻量 Markdown 笔记。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档一篇小红书笔记 | 解析分享链接 → 抓取笔记详情页 → 提取元数据和正文 → 写入 vault | 一份带 frontmatter 的 Markdown 笔记 + 终端回执 |
| 保留笔记里的视频/图片 | 下载到本地 `~/Downloads/soia-pkm-clip-rednote/<note_id>/` | 本地文件路径（记在笔记 `media_local_path` 字段里，vault 本身不存二进制） |
| 先看看链接能不能解析 | 加 `--metadata-only`，只写元数据+正文，不下载媒体 | 笔记文件仍会生成，媒体候选直链列在文件里，供之后手动/重跑下载 |
| 已经归档过的笔记 | 按 `url:` 中的 note_id 去重，默认跳过 | `SKIP: <路径>` 提示，不覆盖 |

### 客户如何使用

1. 从小红书 App 打开目标笔记 →「分享」→「复制链接」，得到完整分享链接（**必须包含 `xsec_token` 参数**，手打或截断的链接无法正常渲染笔记内容）。
2. 把链接发给 Agent，说「归档这条小红书」或直接调用 `python3 scripts/archive_rednote.py <URL>`。
3. Agent 在 vault 根目录（或指定 `--vault`）运行脚本；脚本先查重，再抓取、下载媒体、写入 Markdown。
4. 执行后 Agent 补全 `## 摘要`、`topics`/`people` 双链；`## 我的看法` 永远留空给用户。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-clip-rednote -y
```

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| Python 3（stdlib：`urllib`、`re`、`html`、`json`） | 强依赖 | 系统自带 | 无法运行，提示安装 Python 3 |
| Obsidian vault | 强依赖 | 任意已存在的本地 vault | 提示 `--vault <path>` 或设置 `OBSIDIAN_VAULT` |
| `XHS_COOKIE`（可选） | 可选增强 | 从浏览器登录态复制 cookie，写入私有 `config.yml` 或进程环境 | 大多数公开笔记无需登录即可抓取；仅当页面提示需要登录态时才需要 |

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-rednote/config.yml
SOIA_PKM_CLIP_REDNOTE_CONFIG_FILE=<custom-config-path>
```

- 如果不需要私有配置（大多数公开笔记），可以不创建 `config.yml`。
- `XHS_COOKIE` 只能放进私有 `config.yml`、进程环境，不能写进仓库、vault 正文或日志；脚本从不打印其值。为防止配了 `XHS_COOKIE` 后被恶意/伪造链接骗去发给第三方主机，脚本只接受 `xiaohongshu.com`/`xhslink.com` 域名下的链接，其余一律拒绝。
- 参考 [config.example.yml](config.example.yml)。

### 日志与完成回执

每次执行都要让客户看见过程和结果。最低回执格式：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <检查到的 vault / articles-dir / 是否配置 XHS_COOKIE，不打印秘密值>
- processed: <笔记 ID / 类型>
- created/updated: <笔记文件路径>
- skipped/failed: <数量和原因>

文件变化：
- <vault 内 Markdown 笔记的绝对路径>
- <本地媒体目录路径，或"未下载">

验证：
- <脚本 stdout 回执 / 人工核对点>

问题与下一步：
- <缺配置 / 媒体下载失败 / 需要客户确认；没有则写“无”>
```

## 定位

小红书原生 App 不利于长期检索：内容只在信息流里，笔记会被删除或设为私密，跨设备查找困难。本 skill 把一篇笔记完整沉淀进 Obsidian：

- 标题、正文（含原始话题标签标记 `#tag[话题]#`，不做二次处理）
- 作者、发布时间、互动数据（点赞/收藏/评论/分享）
- 话题标签列表
- 视频/图片下载到本地，笔记里只记路径
- frontmatter 结构与本仓库其他 `clip` 系列一致，方便统一 MOC 聚合

## 前置依赖

- Obsidian vault（任意结构）
- Python 3，纯 stdlib（`urllib.request` / `re` / `html` / `json`），无第三方依赖
- vault 定位优先级：
  1. 命令行 `--vault <path>`
  2. 环境变量 `OBSIDIAN_VAULT`
  3. 从当前工作目录向上自动发现 vault（找 `AGENTS.md` / `.obsidian`）
- 文章目录定位优先级：
  1. 命令行 `--articles-dir <subdir>`
  2. 环境变量 `OBSIDIAN_ARTICLES`
  3. 退回通用默认 `Articles`；脚本会向 stderr 打印警告，退出码保持 0：`WARN: 未找到 articles 目录配置（--articles-dir / OBSIDIAN_ARTICLES / config.yml），已落默认 Articles/——该目录不是本 vault 的正式归档位，请确认或配置`

> 说明：Claude Code / Codex / Gemini CLI / opencode 等工具经常在非登录 shell 中执行命令，未必继承 shell 启动文件里的 `export`。脚本会先加载私有 `config.yml`，再从 cwd 自动发现 vault；如果 agent 已经在 vault 目录里，直接运行即可。

- 私有 `config.yml`（可选，**不要放在 vault 或开源 skill 仓库**）：

  优先级：`$SOIA_PKM_CLIP_REDNOTE_CONFIG_FILE`（或兼容别名 `$SOIA_PKM_CLIP_REDNOTE_ENV_FILE`）> `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-rednote/config.yml`。

  支持变量名：`OBSIDIAN_VAULT`、`OBSIDIAN_ARTICLES`、`XHS_COOKIE`（可选，仅登录态门槛笔记需要）。真实值只写在私有 `config.yml` 里，不写入本文件。

## 抓取方式：解析笔记详情页的 `window.__INITIAL_STATE__`

小红书笔记详情页是服务端渲染的，正文里内嵌一段 `window.__INITIAL_STATE__ = {...};` 的 JS 对象字面量。脚本流程：

1. 用带真实桌面 Chrome UA 的 `urllib.request` 直接 GET 分享链接（**必须保留完整 query string，包括 `xsec_token`**，去掉 token 大概率拿到不完整/被拦截的页面）。
2. 正则定位 `window.__INITIAL_STATE__\s*=\s*` 到下一个 `</script>` 之间的文本，去掉结尾分号。
3. `html.unescape()` 处理 HTML 实体，再把裸露的 `undefined` 关键字替换成 `null`（JS 对象字面量里常见，不是合法 JSON）。
4. `json.loads()` 得到笔记状态树，递归查找含 `noteDetailMap` 键的字典，按 `note_id` 取出 `{"note": {...}}`。
5. 从 `note` 里取字段：`title` / `desc` / `type`（`video`/`normal`）/ `user.nickname` / `time`（**毫秒**时间戳）/ `tagList` / `interactInfo`（**字符串类型**的计数字段，需 `int()` 转换）/ `imageList` / `video.media.stream.h264[0].masterUrl`（视频直链，**签名 URL，不可截断**）。

失败时不写半成品文件，直接报错退出（非 0 exit code）：找不到 `__INITIAL_STATE__` 或找不到目标 `note_id` 数据时，提示「笔记可能需要有效登录态或 xsec_token 已失效」，并建议设置 `XHS_COOKIE` 重试。

## 触发词

| 用户说 | 调用 |
|--------|------|
| 「归档这条小红书：URL」/「clip 这篇小红书笔记」/「archive this rednote：URL」 | 在 vault 根目录运行 `archive_rednote.py <URL>`；不在 vault 内时加 `--vault <path>` |
| 「先看看这个链接能不能解析」/「不用下载视频」 | 加 `--metadata-only`：只写元数据+正文，媒体候选直链记入文件，不下载 |
| 「重新归档这篇（内容有更新）」 | 加 `--force`：覆盖已归档的同一 note_id，保留已有 `topics`/`people`/`## 摘要` |

## 工作流（默认归档）

1. 解析分享链接 → 用正则依次尝试 `/explore/([id])`、`/discovery/item/([id])`、`[?&]note_id=([id])` 提取 `note_id`
2. 调脚本 `archive_rednote.py <URL>`
3. 脚本检查 vault 是否已归档（按 frontmatter `url:` 字段中是否含该 `note_id`）
   - 已存在且未加 `--force` → 输出 `SKIP: <路径>`，退出码 0
   - 否则 → 抓取笔记详情页、下载媒体（除非 `--metadata-only`）、写入 vault
4. AI 之后补：
   - 1 句话中文 `## 摘要`
   - 1-3 个 `topics` 双链 + `people` 双链
5. 「我的看法」段永远留空给用户

## 媒体存放（不进 vault）

视频/图片下载到 `~/Downloads/soia-pkm-clip-rednote/<note_id>/`（视频存为 `video.mp4`，图片存到 `images/<序号>.<扩展名>`），**不写入 vault**（vault 是 git 追踪的 Markdown 知识库，不适合放大体积二进制）。笔记 frontmatter 的 `media_local_path` 字段记录这个本地目录的绝对路径；`--metadata-only` 或下载失败时该字段留空，媒体的原始直链会记在正文 `## 媒体候选（未下载）` 段落里，方便之后手动下载或重跑脚本。

## 文件命名

```
<YYYY-MM-DD>-rednote-<作者前 20 字>-<标题前 50 字>.md
```

同日同作者同标题多条 → 末尾加 `-<note_id 后 6 位>`。

## 输出 frontmatter

```yaml
---
tags: [视频摘抄]
source: 小红书
url: <完整分享链接，原样保留>
author: <昵称>
published_at: YYYY-MM-DD HH:mm
captured_at: YYYY-MM-DD HH:mm
language: zh
type: video / image
topics: []   # AI 填
people: []   # AI 填
media_local_path: "<本地绝对路径，未下载则为空字符串>"
content_complete: true
metrics:
  likes: N
  collects: N
  comments: N
  shares: N
---
```

## 边界与异常

| 场景 | 处理 |
|------|------|
| 链接不是 `xiaohongshu.com`/`xhslink.com` 域名 | **拒绝抓取，直接报错退出**——脚本会把 `XHS_COOKIE`（若配置）带在 HTML 请求头里，不校验主机会把登录态发给任意域名；这道校验在解析 URL 前最先执行 |
| 分享链接缺 `xsec_token` 或是手打的短链 | 大概率拿到不完整/拦截页面；提示用户从 App「分享」→「复制链接」重新获取 |
| 页面里找不到 `window.__INITIAL_STATE__` | 报错退出，不写文件；提示可能需要登录态或 token 已失效，建议设置 `XHS_COOKIE` |
| 视频直链下载 403 / 超时 | 直链带时效签名（`t=` 参数）；候选（`masterUrl` + `backupUrls`，h264→h265→av1）逐个尝试，全部失败则跳过下载但仍写入笔记正文+候选直链，不算脚本失败 |
| `interactInfo` 计数字段全为空/0 | frontmatter 标注「互动数据未公开」，不当作真实 0 呈现 |
| `--metadata-only` | 只写元数据+正文，不下载媒体；候选直链记入正文 `## 媒体候选` 段 |
| 同一 `note_id` 已归档、未加 `--force` | `SKIP: <路径>`，不覆盖 |
| `--force` 覆盖 | 保留已有 `topics`/`people`/`## 摘要`，只更新其余字段和正文 |
| 笔记本身是登录限定内容 | 设置 `XHS_COOKIE`（仅加到 HTML 请求头，不加到媒体下载请求） |

## 命令行参考

```bash
python3 scripts/archive_rednote.py <URL>
python3 scripts/archive_rednote.py <URL> --force                  # 覆盖已归档（保留人工填写字段）
python3 scripts/archive_rednote.py <URL> --vault /path/to/vault  # 覆盖环境变量
python3 scripts/archive_rednote.py <URL> --articles-dir <articles-subdir>
python3 scripts/archive_rednote.py <URL> --metadata-only          # 只写元数据+正文，不下载媒体
```

## 验证与测试

三镜头独立对抗审查后修复（2026-07-21）：①（安全，阻断级）`fetch_note_html` 曾对 `args.url` 不做主机校验就直接请求并附带 `XHS_COOKIE`——伪造一个能命中 `note_id` 正则的非小红书链接即可把用户登录态发给任意第三方主机；已加 `validate_host()`，只放行 `xiaohongshu.com`/`xhslink.com`（含子域名，防绕过拼接），在解析 URL 前最先执行。②（正确性）`clip_rednote_env.py` 独立运行时会把 `XHS_COOKIE` 明文打印到 stdout，与自身"从不打印"的声明矛盾；已对 COOKIE/TOKEN/SECRET/KEY 类字段做脱敏。③（正确性）`--force` 重跑时若视频直链因签名过期而重新下载失败，`media_local_path` 会被清空，即使磁盘上仍有上一次成功下载的文件；已改为下载失败时先检查本地是否已有文件再决定是否清空。

真实端到端验证（非 mock/fixture，2026-07-21，真实小红书笔记）：
- 完整归档一条真实视频笔记：视频下载 30MB、`file` 确认为合法 MP4、frontmatter 点赞/收藏/评论/转发数与浏览器里人工核对的实时数字一致
- 重跑同一链接（未加 `--force`）：正确 `SKIP`，未重复下载
- CLI 层实测安全修复：伪造 `https://evil.example/explore/x1y2z3?note_id=x1y2z3` 被 `validate_host` 在发出任何网络请求前拒绝（退出码 1），未触达 `fetch_note_html`
- `clip_rednote_env.py` 独立运行：配置真实 `XHS_COOKIE` 后输出 `export XHS_COOKIE='<redacted>'`，不再泄露明文
- `media_local_path` 回退逻辑：构造磁盘已有 `video.mp4` 但本次下载判定失败的场景，确认路径仍正确保留而非清空

---

## 完成后回执

**交付顺序**：先把文件落盘，再输出下面的回执，不得反过来；不确定的元数据（如作者昵称解析失败）在回执里显式标注"未核实"，不编造。

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改的 vault 笔记路径，以及本地媒体目录路径（或"未下载"）。
   - 回执必须包含实际落盘目录；若走了 `Articles/` 兜底，必须显式标注该目录不是本 vault 的正式归档位，并建议用户配置 `--articles-dir`、`OBSIDIAN_ARTICLES` 或私有 `config.yml` 后归位。
3. **下一步** — 可选的后续建议（补摘要/topics/people、媒体下载失败需重试等）。
