# 云盘馆藏 Excel 增量索引

## 目标

把 `00_馆藏总览.md` 与 `_全文检索/*.md` 生成成可筛选 Excel，同时避免每次把全部文件明细重新写入同一个大工作簿。

正式入口只有一个：

```text
scripts/gen_catalog_xlsx.py
```

不要在 vault、`/tmp` 或对话产物目录另写临时生成脚本。

## 输出结构

假设 `--output` 是 `<输出目录>/00_阿里云盘馆藏总索引.xlsx`，生成结果为：

```text
<输出目录>/
├── 00_阿里云盘馆藏总索引.xlsx          # 轻量总入口：目录、分区、类型、扩展名、明细入口
└── 00_阿里云盘馆藏总索引-分区明细/
    ├── 10_孩子学习库.xlsx
    ├── 20_个人阅读.xlsx
    ├── 30_技术成长.xlsx
    ├── 40_影视.xlsx
    ├── 50_书籍文化.xlsx
    └── 90_存档.xlsx
```

总入口使用相对路径链接各分区明细；整套目录移动后仍能一起使用。`01_目录索引` 的课程/目录名称本身可点击直达阿里云盘；每个分区工作簿含使用说明、文件明细、类型统计、扩展名统计，并保留阿里云盘直达链接。

## 增量原理

1. 对每份 `_全文检索/*.md` 计算 SHA-256。
2. 按分区缓存解析结果，默认位于 `${XDG_CACHE_HOME:-~/.cache}/soia-pkm-alipan-curator/catalog-xlsx/<数据源指纹>/`。
3. 普通运行只重建 SHA-256 发生变化或输出缺失的分区工作簿。
4. 任一分区或 `00_馆藏总览.md` 变化时，重建轻量总入口；未变化的分区明细直接复用。
5. 只有生成规则/样式整体变化时才使用 `--force`。

缓存不进入 vault，也不进入 skill 仓库。生成失败时不提交新 manifest，下次运行会继续重建，不会把半成品误判为最新。

## 运行依赖

Excel 作者层强制使用宿主提供的 `@oai/artifact-tool`，不安装或切换到 `openpyxl`、`xlsxwriter`、`pandas.ExcelWriter`。

宿主需要提供：

- Node.js 可执行文件；
- 包含 `@oai/artifact-tool` 的 `node_modules`；
- Python 3.10+；
- 可选 `soffice`，用于预计算 `HYPERLINK` 的友好显示文字。

在 Codex 中先调用 workspace dependency loader，然后在用户可写的临时运行目录创建 `node_modules` 软链：

```bash
RUNTIME_DIR="$(mktemp -d)"
ln -s '<loader 返回的 node_modules 路径>' "$RUNTIME_DIR/node_modules"

python3 '<skill目录>/scripts/gen_catalog_xlsx.py' \
  --catalog '<vault>/40_图书视频馆/50_云盘馆藏/00_馆藏总览.md' \
  --search-dir '<vault>/40_图书视频馆/50_云盘馆藏/20_云盘地图/_全文检索' \
  --output '<vault>/outputs/<任务目录>/00_阿里云盘馆藏总索引.xlsx' \
  --node '<loader 返回的 Node.js 路径>' \
  --artifact-runtime "$RUNTIME_DIR" \
  --soffice '<loader 返回的 soffice 路径>' \
  --json
```

若宿主没有 `@oai/artifact-tool`，停止并说明缺失依赖，不猜路径、不临时安装替代库。

## 常用模式

### 日常刷新（推荐）

不加 `--force`。未变化分区会跳过；若所有源都没变化，整个任务直接返回 `status=unchanged`。

### 首次生成或生成规则升级

```text
--force
```

首次需要建立 6 份分区工作簿，因此仍会全量生成一次。之后才进入增量路径。

### 交付前视觉验收

```text
--verify
```

只渲染总入口和本次实际变化分区的全部工作表，预览写到缓存目录的 `qa/`，不污染 vault。

### 自定义缓存位置

```text
--cache-dir <用户可写缓存目录>
```

## 完成检查

- 6 份 Markdown 解析行数分别与头部声明一致；不一致立即失败。
- 馆藏总览各分区文件数之和等于全盘文件数。
- 总入口的已展开明细数等于 6 个分区缓存文件数之和。
- 本次变化分区工作簿存在，未变化分区工作簿未被改写。
- `--verify` 的公式错误扫描为 0，全部工作表视觉可读。
- 提供 `soffice` 时，抽查云盘与本地明细链接显示为友好可点击文字。
