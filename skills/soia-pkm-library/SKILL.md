---
name: soia-pkm-library
version: 1.0.0
description: 维护 Obsidian 书库（图书馆书目 + 阅读记录）——同步微信读书已读书目与划线、补单本书详情、补建待读记录、重新生成图书馆总览/阅读记录总览/按类型总览三份 markdown 视图。底层是 7 个机械脚本（幂等、可重复跑），参数化支持任意 vault 路径与分类表。Triggers：「同步微信读书」「同步划线」「重新生成图书馆总览」「更新阅读记录总览」「补建待读记录」「补一下这本书的详情」「书库整理」
---

# soia-pkm-library

PKM 闭环的**支撑·书库环节**：维护"书本"这条独立于文章摘抄的数据线——图书馆书目 + 阅读记录的同步、补全与总览生成。

## 做什么

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

## 运行示例

```bash
export OBSIDIAN_VAULT=~/Documents/MyVault   # vault 根目录
export WEREAD_API_KEY=wrk-xxxxxxxx          # 仅同步类脚本需要

cd skills/soia-pkm-library/scripts

# 同步微信读书
python3 sync_weread_to_library.py                # 已读书目 → 书卡 + 阅读记录
python3 sync_weread_highlights.py                # 列 noteCount 前 30（预览）
python3 sync_weread_highlights.py --all          # 全量同步划线/想法
python3 sync_weread_highlights.py 三体 失控      # 按书名同步

# 补单本书详情 / 批量补全
python3 enrich_book_details.py 系统之美
python3 enrich_book_details.py --all

# 补建待读记录（图书馆有卡、但没阅读记录的书）
python3 backfill_reading_records.py

# 重生成三份总览
python3 gen_library_md.py
python3 gen_records_md.py
python3 gen_genre_library_md.py --base 40_图书视频馆/40_孩子书库
```

所有脚本共享同一套参数化约定：

- **`--vault <path>`** 或 **`OBSIDIAN_VAULT` env**：vault 根目录（二选一，`--vault` 优先）。
- **`--base <relpath>`**：书库相对 vault 的路径。默认对应「个人书库」（`gen_genre_library_md.py` 默认对应「孩子书库」场景，可用 `--base` 切到个人书库）。**不要在正文里硬编码这个默认值**——vault 未来可能重构目录结构，需要哪个库直接传 `--base` 覆盖即可。
- **`--config <json>`**：覆盖脚本内置的分类表/状态表/字段表默认值（分类映射、二级排序、状态图标、透传字段等），JSON 结构与脚本内 `DEFAULT_*` 常量的键一致，不用改代码，改配置就行。
- **`--output <path>`**（仅 3 个 `gen_*` 脚本）：把生成结果写到指定文件而不是覆盖 vault 里的总览文件，用于干跑预览。

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

## Soft-dependency：weread-skills

同步类脚本（`sync_weread_to_library.py` / `sync_weread_highlights.py` / `enrich_book_details.py`）直接调用微信读书 Agent API Gateway（`https://i.weread.qq.com/api/agent/gateway`），需要 `WEREAD_API_KEY` 环境变量。

这套 API 的完整能力文档由第三方 skill `weread-skills` 维护——**本 skill 只依赖它的 API 文档，不修改它的任何文件**。若环境里没装 `weread-skills`，同步脚本仍可独立运行（`WEREAD_API_KEY` 是唯一硬依赖，不依赖该 skill 本身的存在），只是失去了它文档里对各 API 字段含义的详细说明。

## 边界声明

与相邻 skill 的分工，一句话说清：

- **`huashu-weread-advisor`**：顾问 AI 层——基于书架+笔记做个性化推荐/进阶书单/复盘文章；本 skill 只管数据同步与落盘，不做任何"读什么/怎么读"的判断。
- **`soia-pkm-reading-plan`**：排计划——把一批书组织成带排期的可执行阅读计划；本 skill 不排计划，只保证书库数据（书目/阅读记录/总览）是新鲜、对齐的。
- **`soia-pkm-alipan-curator`**：云盘资源 catalog——盘点/整理阿里云盘里的资源并落成 Obsidian 索引；本 skill 只管"书"这条数据线，不碰云盘。

## 异常处理

| 场景 | 处理 |
|------|------|
| 未设置 `WEREAD_API_KEY` | 同步类脚本报错退出（`exit 1`），提示设置 env |
| 未指定 `--vault` 且无 `OBSIDIAN_VAULT` env | 报错退出，提示二选一 |
| 书名在图书馆/阅读记录里找不到对应文件 | 跳过并打印警告，不中断批量流程（`--all` 模式） |
| 微信读书书名与本地文件名对不上（含副标题/合集后缀） | `sync_weread_highlights.py` 优先按 `bookId` 精确匹配，标题匹配是兜底 |
| 想干跑预览生成结果，不覆盖 vault 原文件 | 3 个 `gen_*` 脚本都支持 `--output <临时路径>` |


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
