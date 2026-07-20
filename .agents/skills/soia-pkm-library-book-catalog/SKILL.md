---
name: soia-pkm-library-book-catalog
description: 纯本地、幂等、可重复运行地维护 Obsidian 书库：补建待读记录并重新生成图书馆、阅读记录和按类型总览，不依赖微信读书。Triggers：「重新生成图书馆总览」「更新阅读记录总览」「补建待读记录」「书库整理」
version: 1.0.0
created_at: 2026-07-16 18:01:32
updated_at: 2026-07-16 18:08:08
created_by: gpt-5.6-luna
updated_by: gpt-5.6-luna
---

# soia-pkm-library-book-catalog

PKM 书库的本地 catalog 层：只读取和写入 vault 内的 Markdown 与 YAML frontmatter，补建缺失的待读记录，并生成三份可供 Obsidian 浏览的总览。它不调用微信读书 API、不需要第三方 skill，也不会因为缺少微信读书配置而停止。

## 客户可读说明

### 这个技能可以做什么

这个技能适合在已有书卡或阅读记录的基础上整理本地书库。它会按书卡的分类字段生成图书馆总览和阅读记录总览，也可以把“有书卡但没有阅读记录”的书幂等地补成“待读”记录，并生成按类型分组的视图。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 补建待读记录 | 扫描书卡与阅读记录，创建缺失记录，已有目标则跳过 | 新建、跳过和失败数量 |
| 重新生成图书馆总览 | 读取本地书卡并生成分类嵌套视图 | 输出文件与书目统计 |
| 更新阅读记录总览 | 以书卡分类为准汇总 7 态阅读生命周期 | 状态、分类和处理统计 |
| 书库整理 | 依次执行补建与三份视图生成 | 每阶段回执和可重复执行结果 |

### 客户如何使用

1. 用自然语言说明要补建待读记录、更新某份总览，或整理整个书库。
2. 提供 `--vault <path>`，或在私有配置中设置 `OBSIDIAN_VAULT`；不需要 `WEREAD_API_KEY` 或微信读书登录态。
3. 生成脚本支持 `--output <path>` 预览，确认内容后再省略该参数写回 vault。
4. 执行后核对真实输出与统计；所有脚本均可安全重复运行。

### 依赖与安装

安装本技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-library-book-catalog -y
```

运行依赖只有 Python 3 和本地 vault 中的 Markdown 文件；不依赖微信读书、`weread-skills`、`WEREAD_API_KEY`、网络或额外 pip 包。

私有配置路径：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-library-book-catalog/config.yml
SOIA_PKM_LIBRARY_BOOK_CATALOG_CONFIG_FILE=<custom-config-path>
SOIA_PKM_LIBRARY_BOOK_CATALOG_ENV_FILE=<compat-config-path>
```

示例：

```yaml
env:
  OBSIDIAN_VAULT: "<vault-path>"
```

为兼容旧调用方式，脚本也接受 `SOIA_PKM_LIBRARY_CONFIG_FILE` 和 `SOIA_PKM_LIBRARY_ENV_FILE`；新配置优先使用上面的 catalog 专用名称。配置只保存本机路径，不提交私密数据。

### 日志与完成回执

每次运行都会输出扫描范围、创建/更新/跳过/失败数量、输出类别和下一步建议。涉及 vault 的日志只报告泛化位置和资源类别，不打印密钥或不必要的本机绝对路径。结束时必须说明实际文件变化和验证方式。

## 能做什么

| 脚本 | 功能 | 何时运行 |
|---|---|---|
| `backfill_reading_records.py` | 为有书卡、无阅读记录的书批量创建“待读”记录 | 想让书卡与阅读记录对齐时 |
| `gen_library_md.py` | 按一级/二级分类生成图书馆总览 | 书卡变动后 |
| `gen_records_md.py` | 按书卡权威分类和 7 态状态生成阅读记录总览 | 阅读记录变动后 |
| `gen_genre_library_md.py` | 按单级类型生成图书馆总览 | 需要类型视图时 |

## 如何运行

以下命令从本技能的 `scripts/` 目录执行：

```bash
python3 backfill_reading_records.py --vault <vault-path>
python3 gen_library_md.py --vault <vault-path> --output <preview-path>
python3 gen_records_md.py --vault <vault-path> --output <preview-path>
python3 gen_genre_library_md.py --vault <vault-path> --base <vault-book-library-dir> --output <preview-path>
```

确认预览后，去掉 `--output` 写回 vault。所有脚本共享以下参数化约定：

- `--vault <path>` 或 `OBSIDIAN_VAULT`：vault 根目录，命令行优先。
- `--base <relpath>`：书库相对 vault 的路径；按实际书库显式传入，不依赖固定个人目录名。
- `--config <json>`：覆盖分类、状态、图标或字段透传设置（由具体脚本支持）。
- 私有配置使用 `SOIA_PKM_LIBRARY_BOOK_CATALOG_CONFIG_FILE`、兼容别名或默认配置路径加载；不会覆盖进程中已有的环境变量。

## 目录契约与上游关系

书库目录由 `--base` 决定，核心结构为：

```text
<base>/
├── 00_图书馆/
│   └── 书目/<分类目录>/<书名>.md
└── 阅读记录/
    ├── 想读/  待读/  计划读/  在读/
    ├── 暂停/  搁置/  完成/
    └── 阅读记录-总览.md
```

书卡的 `category`/`subcategory` 是分类权威源；阅读记录通过 `book: "[[书名]]"` 反查书卡。没有任何记录指向的书卡，就是 `backfill_reading_records.py` 的待补对象。生成脚本读本地 Markdown，不向远端请求数据。

`soia-pkm-library-weread-sync` 是可选上游：它可以先把微信读书数据落成书卡、阅读记录和机器段，本技能随后消费这些本地文件。catalog 也可以单独处理已有的本地数据，不安装上游同步 skill 仍能运行。

## 写盘与幂等边界

- Markdown 视图属于 vault 的产品特性文件，默认写回由 `--base` 定位的书库目录。
- 三个 `gen_*` 脚本支持 `--output <path>` 预览，避免直接覆盖总览文件。
- `backfill_reading_records.py` 只在目标记录不存在时创建，已有文件跳过，不覆盖用户记录。
- 脚本不创建网络缓存、不写外部状态、不调用 provider；临时预览路径由用户通过 `--output` 传入，临时文件由调用方自行管理。

## 边界与异常

| 场景 | 处理 |
|---|---|
| 未指定 vault | 退出并提示传 `--vault` 或设置 `OBSIDIAN_VAULT` |
| 书库目录不存在 | 输出可定位的缺失目录提示并退出，不伪造总览 |
| 目标待读记录已存在 | 跳过，不覆盖已有内容 |
| 书卡缺少标题或分类 | 按脚本默认值归类并在日志中提示 |
| 本地书名无法反查 | 跳过并打印警告，不中断批量整理 |
| 想确认生成内容 | 使用 `--output` 输出到临时预览文件 |

## 完成后回执

完成后必须回报：本次运行的脚本和范围、扫描/创建/更新/跳过/失败数量、实际写入的资源类别、预览或写回验证结果，以及任何需要用户处理的问题。不要把“命令返回 0”单独当作内容正确的证据；至少检查输出存在且包含预期标题或统计。
