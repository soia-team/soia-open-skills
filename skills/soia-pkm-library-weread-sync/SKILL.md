---
name: soia-pkm-library-weread-sync
description: 同步微信读书已读书目与划线到 Obsidian 书库，并调用微信读书 API 补单本书详情。Triggers：「同步微信读书」「同步划线」「同步已读书目」「补一下这本书的详情」「补书详情」
dependencies:
  external:
    - name: weread-skills
      required: true
      install: "npx skills add Tencent/WeChatReading -g -y"
version: 2.0.0
created_at: 2026-07-06 11:12:07
updated_at: 2026-07-16 18:08:08
created_by: claude opus 4.6
updated_by: gpt-5.6-luna
---

# soia-pkm-library-weread-sync

PKM 书库的数据同步层：把微信读书书架、已读状态、划线和想法写入 Obsidian，并通过微信读书 API 补充单本书详情。书卡和阅读记录的本地补建、总览生成由相邻的 `soia-pkm-library-book-catalog` 负责。

## 客户可读说明

### 这个技能可以做什么

这个技能负责所有需要访问微信读书的动作：同步已读书目、同步划线/想法，以及为指定书卡补充简介、章节、相似书和阅读进度。它会读取用户提供的 vault 路径和私有配置，把结果幂等地落到书卡与阅读记录中。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 同步微信读书书架 | 拉取已读书目，创建或更新书卡和阅读记录 | 处理数量、新增/更新/跳过/失败统计 |
| 同步划线 | 拉取划线和想法，覆盖机器维护段并保留用户笔记 | 每本书的处理进度和写入结果 |
| 补一下这本书的详情 | 调用微信读书 API，补充书籍信息、章节、相似书和阅读进度 | API 阶段、写入类别和失败原因 |

### 客户如何使用

1. 用自然语言说明要同步书架、同步划线，或提供要补详情的书名。
2. 提供 `--vault <path>`，或在私有配置中设置 `OBSIDIAN_VAULT`；同步前确认 `weread-skills` 和 `WEREAD_API_KEY` 可用。
3. 先用划线脚本的默认预览或单本模式确认范围，再运行 `--all` 全量同步。
4. 执行后核对终端回执；如需刷新本地视图，再运行 `soia-pkm-library-book-catalog` 的生成脚本。

### 依赖与安装

安装本技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-library-weread-sync -y
```

强依赖：

```bash
npx skills add Tencent/WeChatReading -g -y
```

微信读书 API Key 需在官方页面登录后获取：<https://weread.qq.com/r/weread-skills>。私有配置路径：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-library-weread-sync/config.yml
SOIA_PKM_LIBRARY_WEREAD_SYNC_CONFIG_FILE=<custom-config-path>
SOIA_PKM_LIBRARY_WEREAD_SYNC_ENV_FILE=<compat-config-path>
```

配置只放本机值，不提交密钥：

```yaml
env:
  OBSIDIAN_VAULT: "<vault-path>"
  WEREAD_API_KEY: "<YOUR_WEREAD_API_KEY>"
```

为兼容旧调用方式，脚本仍接受 `SOIA_PKM_LIBRARY_CONFIG_FILE` 和 `SOIA_PKM_LIBRARY_ENV_FILE` 作为配置路径环境变量；新配置优先使用上面的新名称。

### 日志与完成回执

终端日志会说明开始阶段、处理数量、写入类别、跳过/失败原因和下一步建议。不得输出 API key、cookie、token 或私有配置内容。缺少依赖或 key 时必须停止 API 调用，并给出安装命令或官方获取地址。

## 能做什么

| 脚本 | 功能 | 何时运行 |
|---|---|---|
| `sync_weread_to_library.py` | 微信读书已读书目 → 图书馆书卡 + 阅读记录 | 想同步最新阅读状态时 |
| `sync_weread_highlights.py` | 微信读书划线/想法 → 已有阅读记录的机器段 | 想同步划线笔记时 |
| `enrich_book_details.py <书名>...` | 通过微信读书 API 补简介、章节、进度、相似书 | 想补单本书详情时 |

## 如何运行

以下命令从本技能的 `scripts/` 目录执行：

```bash
python3 sync_weread_to_library.py --vault <vault-path>
python3 sync_weread_highlights.py                # 预览 noteCount 前 30 本
python3 sync_weread_highlights.py --all          # 全量同步
python3 sync_weread_highlights.py <书名>          # 指定书名
python3 enrich_book_details.py <书名>
python3 enrich_book_details.py --all
python3 enrich_book_details.py --refresh-chapters
```

所有脚本共享以下参数化约定：

- `--vault <path>` 或 `OBSIDIAN_VAULT`：vault 根目录，命令行优先。
- `--base <relpath>`：书库相对 vault 的路径；需要其他书库时显式覆盖。
- `--config <json>`：覆盖分类、状态或字段映射（由具体脚本支持）。
- 私有配置使用 `SOIA_PKM_LIBRARY_WEREAD_SYNC_CONFIG_FILE`、兼容别名或默认配置路径加载；不会覆盖进程中已经存在的环境变量。

## 目录契约与上下游

书库目录由 `--base` 决定，核心结构为：

```text
<base>/
├── 00_图书馆/书目/<分类目录>/<书名>.md
└── 阅读记录/<状态>/<书名>.md
```

书卡中的 `category`/`subcategory` 是分类权威源；阅读记录通过 `book: "[[书名]]"` 反查书卡。同步脚本产生的书卡和阅读记录是下游本地 catalog 脚本的输入；catalog skill 可选安装，不影响已有数据的本地整理和视图生成。

`sync_weread_highlights.py` 维护 `## 📌 划线` / `## 💭 想法` 机器段；用户手写内容应放在其中的 `### 用户笔记` 子区块，否则下一次同步可能被覆盖。

## 强依赖：weread-skills 与 API Key

三个脚本都需要微信读书官方 `weread-skills`。同步前必须满足：

- `weread-skills` 已安装在 workspace 或用户的 agent skill 目录中。
- `WEREAD_API_KEY` 已写入私有 `config.yml` 的 `env.WEREAD_API_KEY`，或由进程环境提供。
- `OBSIDIAN_VAULT` 已配置，或命令行传入 `--vault`。
- 本机可访问 `https://i.weread.qq.com/api/agent/gateway`。
- Python 3 可用；脚本只使用 Python 标准库与本技能自带的 `library_env.py`。

缺依赖时执行：

```bash
npx skills add Tencent/WeChatReading -g -y
```

缺少 `WEREAD_API_KEY` 时，打开 <https://weread.qq.com/r/weread-skills> 登录微信读书获取，再写入私有配置；不要用旧 cookie 冒充 Bearer key，也不要把 key 写入 vault 或本仓库。

## 边界与异常

| 场景 | 处理 |
|---|---|
| 未安装 `weread-skills` | API 类脚本直接退出并给出官方安装命令 |
| 未设置 `WEREAD_API_KEY` | 退出并给出官方获取地址及私有配置位置 |
| 未指定 vault | 退出并提示传 `--vault` 或配置 `OBSIDIAN_VAULT` |
| 找不到本地书卡/阅读记录 | 批量模式跳过并打印警告，不中断其他书 |
| 微信读书书名与文件名不同 | 划线同步优先按 `bookId` 匹配，标题匹配兜底 |

## 完成后回执

复杂同步任务先用小范围、单本或 fixture 做一次前向测试，核对新增、更新、跳过、失败和产出，再扩大到全量。完成后必须回报：同步范围、成功/跳过/失败数量、书卡与阅读记录的文件变化、遇到的问题和下一步（通常是运行 catalog 的总览生成脚本）。
