---
name: soia-pkm-library
description: 维护 Obsidian 书库（图书馆书目 + 阅读记录）——同步微信读书已读书目与划线、补单本书详情、补建待读记录、重新生成图书馆总览/阅读记录总览/按类型总览三份 markdown 视图。底层是 7 个机械脚本（幂等、可重复跑），参数化支持任意 vault 路径与分类表。Triggers：「同步微信读书」「同步划线」「重新生成图书馆总览」「更新阅读记录总览」「补建待读记录」「补一下这本书的详情」「书库整理」
---

# soia-pkm-library

PKM 闭环的**支撑·书库环节**：维护"书本"这条独立于文章摘抄的数据线——图书馆书目 + 阅读记录的同步、补全与总览生成。

## 客户可见介绍

这个 skill 把微信读书里的书架、阅读进度、划线和想法同步到 Obsidian 书库，并维护本地的图书馆总览、阅读记录总览和分类视图。客户可以把它理解成“把微信读书变成自己的长期阅读档案”的工具。

客户能看到的结果包括：

- 微信读书书架同步成 Obsidian 书卡。
- 已读 / 在读书籍生成阅读记录。
- 单本书的划线、想法、章节目录、阅读进度补到阅读记录或书卡里。
- 图书馆总览、阅读记录总览、按类型总览三份 Markdown 视图重新生成。
- 每次运行都在终端输出进度、成功/跳过/失败数量、写入位置和下一步建议，方便客户判断“到底做了什么”。

## 能做什么

7 个机械层脚本（无 LLM 判断，纯确定性操作），覆盖书库维护的完整链路：

| 脚本 | 功能 | 何时运行 |
|------|------|---------|
| `sync_weread_to_library.py` | 微信读书已读书目 → 图书馆书卡 + 阅读记录（新建） | 想同步最新阅读状态时 |
| `sync_weread_highlights.py` | 微信读书划线/想法 → 已有阅读记录（追加机器段） | 想同步划线笔记时 |
| `enrich_book_details.py <书名>...` | 补单本书详情（简介/章节/进度/相似书） | 想深挖某本书的详情时 |
| `backfill_reading_records.py` | 有书卡、无阅读记录的书 → 批量补建「待读」记录 | 想让图书馆与阅读记录数量对齐时 |
| `gen_library_md.py` | 重生成图书馆总览（一级+二级分类嵌套） | 书卡变动后 |
| `gen_records_md.py` | 重生成阅读记录总览（书卡权威分类 + 7 态生命周期状态） | 阅读记录变动后 |
| `gen_genre_library_md.py` | 重生成按类型分组的图书馆总览（单级类型分组，无二级嵌套） | 书卡变动后（如孩子书库场景） |

## 首次安装与配置

### 1. 安装 SOIA 自建 skill

```bash
npx skills add soia-team/soia-open-skills
```

### 2. 安装微信读书官方 skill（同步类脚本强依赖）

```bash
npx skills add Tencent/WeChatReading -g
```

安装后至少应存在一个入口：

```bash
ls -ld ~/.agents/skills/weread-skills ~/.codex/skills/weread-skills ~/.claude/skills/weread-skills
```

### 3. 获取 `WEREAD_API_KEY`

打开微信读书官方 Skill 页面：`https://weread.qq.com/r/weread-skills`，登录微信读书后获取 API Key。

### 4. 写入本机私有配置

配置文件路径：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-library/config.yml
```

示例：

```yaml
env:
  OBSIDIAN_VAULT: "/你的/vault/绝对路径"
  WEREAD_API_KEY: "<微信读书官方页面给你的 API Key>"
```

秘钥只放私有 `config.yml` 或进程环境里，不写入 vault、文章、日志、README 或开源 skill 仓库。

## 如何运行

```bash
cd skills/soia-pkm-library/scripts

# 1. 同步微信读书书架：书架 → 书卡 + 阅读记录
python3 sync_weread_to_library.py --vault <vault-path>   # 已读书目 → 书卡 + 阅读记录

# 2. 同步划线 / 想法：先预览，再按需全量或单本
python3 sync_weread_highlights.py                # 列 noteCount 前 30（预览）
python3 sync_weread_highlights.py --all          # 全量同步划线/想法
python3 sync_weread_highlights.py 三体 失控      # 按书名同步

# 3. 补单本书详情 / 批量补全
python3 enrich_book_details.py 系统之美
python3 enrich_book_details.py --all

# 4. 补建待读记录（图书馆有卡、但没阅读记录的书）
python3 backfill_reading_records.py

# 5. 重生成三份总览
python3 gen_library_md.py
python3 gen_records_md.py
python3 gen_genre_library_md.py --base <vault-book-library-dir>
```

所有脚本共享同一套参数化约定：

- **`--vault <path>`** 或 **`OBSIDIAN_VAULT` env**：vault 根目录（二选一，`--vault` 优先）。
- **`--base <relpath>`**：书库相对 vault 的路径。默认对应「个人书库」（`gen_genre_library_md.py` 默认对应「孩子书库」场景，可用 `--base` 切到个人书库）。**不要在正文里硬编码这个默认值**——vault 未来可能重构目录结构，需要哪个库直接传 `--base` 覆盖即可。
- **`--config <json>`**：覆盖脚本内置的分类表/状态表/字段表默认值（分类映射、二级排序、状态图标、透传字段等），JSON 结构与脚本内 `DEFAULT_*` 常量的键一致，不用改代码，改配置就行。
- **`--output <path>`**（仅 3 个 `gen_*` 脚本）：把生成结果写到指定文件而不是覆盖 vault 里的总览文件，用于干跑预览。
- **私有配置加载**：脚本会自动读取 `$SOIA_PKM_LIBRARY_CONFIG_FILE`（或兼容别名 `$SOIA_PKM_LIBRARY_ENV_FILE`）以及默认路径 `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-library/config.yml`。配置文件使用 YAML `env:` 映射；秘钥只放这些私有文件，不放 vault、不放开源 skill 仓库。
- 私有配置文件只记录变量名对应的本机值；文档和开源仓库只保留变量名，不保留真实值。

## 客户可见日志与总结

执行本 skill 时，终端输出就是客户可见日志。所有脚本必须遵守：

- 开始时说明正在做什么，例如“拉取微信读书书架”“待同步 N 本”。
- 过程中输出关键进度，例如当前书名、bookId、划线数、想法数、写入文件。
- 结束时输出总结数字，例如新增书卡、更新记录、成功、跳过、失败。
- 结束时输出下一步建议，例如重生成 `gen_library_md.py` / `gen_records_md.py`。
- 遇到缺依赖或缺 key 时，必须输出可执行修复步骤，不只报错。

客户可见输出示例：

```text
拉取微信读书书架...
书架共 123 本

=== 同步完成 ===
  新增书卡:       4
  新增已完成记录: 2
  新增在读记录:   1

下一步：
  python3 gen_library_md.py
  python3 gen_records_md.py
```

缺少 `WEREAD_API_KEY` 时，必须提示客户去官方页面获取：

```text
未设置 WEREAD_API_KEY：请先去微信读书官方 Skill 页面申请/获取 API Key：
请打开 https://weread.qq.com/r/weread-skills 登录微信读书获取 WEREAD_API_KEY；
强依赖 weread-skills 状态：已安装；
拿到后放到私有 config.yml，不要写入 vault 或开源 skill 仓库
```

### `WEREAD_API_KEY` 为什么不会自动初始化

- 当前同步链路调用的是微信读书 Agent API Gateway：`https://i.weread.qq.com/api/agent/gateway`。
- 这条链路的认证方式是显式的 `Authorization: Bearer <WEREAD_API_KEY>`，不是从微信读书 Cookie、浏览器登录态或 App 会话里自动换出来的。
- 初始化时我只在旧配置里看到了 `WEREAD_COOKIE` / `WEREAD_COOKIE_B64` / `WEREAD_VID` 这些旧字段，而且它们是空值；没有任何可迁移的 `WEREAD_API_KEY`。
- 所以 skill 只能帮你初始化 `config.yml` 结构，不能替你伪造一枚 key，也不会把旧 Cookie 冒充成 Bearer key。

### `WEREAD_API_KEY` 如何申请

微信读书官方 Skill 页面提供自助获取入口：`https://weread.qq.com/r/weread-skills`。页面说明安装 Skill 后，登录微信读书即可获取 API Key。

执行微信读书同步前，先做两件事：

1. 检查依赖 skill 是否已安装：`~/.agents/skills/weread-skills`、`~/.codex/skills/weread-skills` 或 `~/.claude/skills/weread-skills` 至少存在一个。
2. 如果没有安装，先执行官方安装命令：`npx skills add Tencent/WeChatReading -g`。
3. 打开 `https://weread.qq.com/r/weread-skills`，登录微信读书并获取 API Key。
4. 拿到 key 后，写入 `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-library/config.yml`。
5. 写法如下：

```yaml
env:
  OBSIDIAN_VAULT: "/你的/vault/绝对路径"
  WEREAD_API_KEY: "<微信读书官方页面给你的 API Key>"
```

如果缺少 `WEREAD_API_KEY`，同步类脚本必须提示用户去 `https://weread.qq.com/r/weread-skills` 获取，而不是让用户去找内部网关维护方。

## 目录契约

本 skill 依赖书库遵循以下结构（具体目录名由 `--base` 决定，下面用相对路径描述，不代表写死的绝对路径）：

```
<base>/
├── 00_图书馆/
│   └── 书目/<分类目录>/<书名>.md      # 书卡：客观信息（title/author/category/bookId/...）
└── 阅读记录/
    ├── 想读/     ┐
    ├── 待读/     │
    ├── 计划读/   │  7 态生命周期（按阅读推进顺序）
    ├── 在读/     │  状态由阅读记录 frontmatter 的 `status` 字段决定，
    ├── 暂停/     │  与所在子目录名无强绑定——脚本按 frontmatter 归类统计，
    ├── 搁置/     │  子目录只是人工归档习惯
    └── 完成/     ┘
```

- 书卡是**分类权威源**（`category`/`subcategory`）；阅读记录反查书卡拿分类，不用自己的旧字段。
- 阅读记录通过 `book: "[[书名]]"` 反查书卡；没有任何记录指向的书卡即为"待补"（`backfill_reading_records.py` 的判定口径）。
- `sync_weread_highlights.py` 的机器段（`## 📌 划线`/`## 💭 想法`）会被整段覆盖，用户手写笔记需放在段内的 `### 用户笔记` 子区块（脚本会保留）。

## 强依赖：weread-skills

同步类脚本（`sync_weread_to_library.py` / `sync_weread_highlights.py` / `enrich_book_details.py`）强依赖微信读书官方 `weread-skills`，并直接调用微信读书 Agent API Gateway（`https://i.weread.qq.com/api/agent/gateway`）。执行同步前必须满足：

- `weread-skills` 已安装：`~/.agents/skills/weread-skills`、`~/.codex/skills/weread-skills` 或 `~/.claude/skills/weread-skills` 至少存在一个。
- `WEREAD_API_KEY` 已写入私有 `config.yml` 的 `env.WEREAD_API_KEY`，或由进程环境提供。
- `OBSIDIAN_VAULT` 已配置，或命令行传入 `--vault <path>`。
- 本机可联网访问 `https://i.weread.qq.com/api/agent/gateway`。
- 运行环境有 Python 3；脚本只用 Python 标准库和本 skill 自带的 `scripts/soia_env.py`，不需要额外 pip 依赖。

本地生成/补全类脚本（`backfill_reading_records.py` / `gen_library_md.py` / `gen_records_md.py` / `gen_genre_library_md.py`）不调用微信读书 API，因此不需要 `WEREAD_API_KEY`；它们只依赖 Python 3、vault 路径和本地 markdown 文件。

第三方 skill 关系必须按下面口径说明，避免把“第三方 skill 总览”误读成运行依赖：

| 第三方 skill | 对 `soia-pkm-library` 的关系 |
|---|---|
| `weread-skills` (`Tencent/WeChatReading`) | **强依赖**：微信读书同步类脚本必须先检测它已安装 |
| `huashu-weread-advisor` | 非依赖：读书顾问 / 推荐 / 复盘上层工作流，可消费同步后的书架与笔记数据，但本 skill 不调用它 |
| `book-to-skill` | 非依赖：文档/书籍转 skill 工具，与书库同步无运行关系 |
| `find-skills` | 非依赖：skill 发现/安装辅助工具，与书库同步无运行关系 |

执行同步前应检查强依赖 skill 是否已安装。推荐检查路径：

```bash
ls -ld ~/.agents/skills/weread-skills ~/.codex/skills/weread-skills ~/.claude/skills/weread-skills
```

若三处都不存在，提示用户先按官方页面安装：

```bash
npx skills add Tencent/WeChatReading -g
```

如果缺少 `weread-skills`，同步类脚本必须直接退出并提示安装官方 skill；如果缺少 `WEREAD_API_KEY`，同步类脚本必须提示用户去 `https://weread.qq.com/r/weread-skills` 登录微信读书获取 API Key。

## 边界声明

与相邻 skill 的分工，一句话说清：

- **`huashu-weread-advisor`**：顾问 AI 层——基于书架+笔记做个性化推荐/进阶书单/复盘文章；本 skill 只管数据同步与落盘，不做任何"读什么/怎么读"的判断。
- **`soia-pkm-reading-plan`**：排计划——把一批书组织成带排期的可执行阅读计划；本 skill 不排计划，只保证书库数据（书目/阅读记录/总览）是新鲜、对齐的。
- **`soia-pkm-alipan-curator`**：云盘资源 catalog——盘点/整理阿里云盘里的资源并落成 Obsidian 索引；本 skill 只管"书"这条数据线，不碰云盘。

## 异常处理

| 场景 | 处理 |
|------|------|
| 未设置 `WEREAD_API_KEY` | 同步类脚本报错退出（`exit 1`），提示用户去 `https://weread.qq.com/r/weread-skills` 登录微信读书获取 API Key，再放入私有 `config.yml` |
| 未指定 `--vault` 且无 `OBSIDIAN_VAULT` env | 报错退出，提示传 `--vault` 或在私有 `config.yml` 设置 |
| 书名在图书馆/阅读记录里找不到对应文件 | 跳过并打印警告，不中断批量流程（`--all` 模式） |
| 微信读书书名与本地文件名对不上（含副标题/合集后缀） | `sync_weread_highlights.py` 优先按 `bookId` 精确匹配，标题匹配是兜底 |
| 想干跑预览生成结果，不覆盖 vault 原文件 | 3 个 `gen_*` 脚本都支持 `--output <临时路径>` |


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结本次执行的动作，例如“已同步微信读书书架并新增 4 张书卡”。
2. **客户可见日志摘要** — 抄录或概括脚本末尾的关键数字：成功 / 跳过 / 失败 / 新增 / 更新数量。
3. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明“未改动文件”。
4. **遇到的问题** — 缺少 key、依赖未安装、某本书找不到记录、接口失败等都要明说，并给出下一步修复路径。
5. **下一步** — 可选的后续建议，如重生成总览、同步划线、补单本书详情，或衔接 `soia-pkm-reading-plan`。

推荐回执格式：

```markdown
已完成：同步微信读书书架。

日志摘要：
- 书架共 123 本
- 新增书卡 4 张
- 新增已完成记录 2 条
- 新增在读记录 1 条
- 失败 0 条

文件变更：
- /path/to/vault/40_图书视频馆/30_个人书库/00_图书馆/书目/...
- /path/to/vault/40_图书视频馆/30_个人书库/阅读记录/...

下一步：
- 运行 `python3 gen_library_md.py`
- 运行 `python3 gen_records_md.py`
```
