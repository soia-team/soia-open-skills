# 云盘馆藏 Excel 增量索引

本说明对应正式入口 `scripts/gen_catalog_xlsx.py`，用于把 Obsidian 中的馆藏总览与全文检索 Markdown 生产成可筛选、可点击、可增量刷新的 Excel。它是“全盘或多分区索引”，不是单个课程区的家庭说明表；后者见 [family-navigation-excel.md](family-navigation-excel.md)。

## 目录

- [什么时候用](#什么时候用)
- [输入与输出](#输入与输出)
- [增量原理](#增量原理)
- [运行依赖](#运行依赖)
- [正式运行](#正式运行)
- [数据口径](#数据口径)
- [云盘上传与链接更新](#云盘上传与链接更新)
- [故障处理](#故障处理)
- [完成定义](#完成定义)

## 什么时候用

| 需求 | 使用入口 |
|---|---|
| 全盘/多分区按目录、类型、扩展名和文件名检索 | `gen_catalog_xlsx.py` |
| 只刷新发生变化的分区 | `gen_catalog_xlsx.py`，普通运行，不加 `--force` |
| 给家长看一个学习分区怎么用、点击进入具体课程 | `gen_family_nav_xlsx.mjs` |

禁止在 vault、平台临时目录或对话产物目录另写一次性 Excel builder。生成规则只维护在 skill 内，用户目录只放输入与交付物。

## 输入与输出

输入：

1. `00_馆藏总览.md`：目录浏览、分区统计与目录云盘链接。
2. `_全文检索/*.md`：每个分区一份，提供逐文件明细。

`--output-dir` 可显式指定 `<absolute-output-dir>`；未指定时脚本按 `ALIPAN_CURATOR_OUTPUT_DIR`、私有 `config.yml`、`<用户家目录>/Downloads/soia-pkm-alipan-curator/` 三级优先级选择绝对输出目录，并在其中写入 `00_阿里云盘馆藏总索引.xlsx`，输出为：

```text
<output-dir>/
├── 00_阿里云盘馆藏总索引.xlsx
└── 00_阿里云盘馆藏总索引-分区明细/
    ├── <分区A>.xlsx
    ├── <分区B>.xlsx
    └── ...
```

分区数由 `_全文检索/*.md` 动态决定，不写死为六个。

- 总入口：使用说明、目录索引、类型统计、分区统计、扩展名统计、分区工作簿入口。
- 分区明细：使用说明、文件明细、类型统计、扩展名统计。
- `01_目录索引` 的课程/目录名称本身可点击；不要只放一个难发现的小图标。
- 总入口使用相对路径链接分区明细，整套目录一起移动后仍可用。

## 增量原理

1. 对每份 `_全文检索/*.md` 计算 SHA-256。
2. 按数据源指纹缓存解析结果到平台用户缓存目录（Linux/macOS 读取 `$XDG_CACHE_HOME` 或 `Path.home() / '.cache'`；Windows 使用 `%LOCALAPPDATA%`）。
3. 普通运行只重建源 SHA-256 已变化或输出缺失的分区工作簿。
4. 任一分区或 `00_馆藏总览.md` 变化时，额外重建轻量总入口。
5. 分区改名或删除时，只有在新工作簿成功生成并提交 manifest 后，才清理已从 `_全文检索` 消失的旧分区工作簿与缓存，避免新旧名称并存。
6. 全部输入不变时返回 `status=unchanged`、`changedPartitions=[]`、`rebuilt=[]`。
7. 生成失败时不提交新 manifest，防止半成品被误判为最新。

只有首次生成、缓存丢失或生成规则/样式整体升级时使用 `--force`。日常刷新无理由加 `--force` 会退化为每次全量生成。

## 运行依赖

Excel 作者层强制使用宿主提供的 `@oai/artifact-tool`，不切换到 `openpyxl`、`xlsxwriter` 或 `pandas.ExcelWriter`。

需要：

- Python 3.10+；
- Node.js；
- 含 `node_modules/@oai/artifact-tool` 的运行目录；
- 可选 LibreOffice `soffice`，用于预计算 `HYPERLINK` 的友好显示值。

在支持 workspace dependency loader 的宿主中，先读取它返回的 Node、`node_modules` 和 `soffice` 路径。若缺少 `@oai/artifact-tool`，停止并说明，不猜路径、不临时安装替代库。

## 正式运行

先创建一次性的运行目录，只用于连接宿主依赖：

```bash
RUNTIME_DIR="$(mktemp -d)"
ln -s '<loader-node-modules>' "$RUNTIME_DIR/node_modules"
```

交付运行：

```bash
python3 '<skill-dir>/scripts/gen_catalog_xlsx.py' \
  --catalog '<vault>/path/to/00_馆藏总览.md' \
  --search-dir '<vault>/path/to/_全文检索' \
  --output-dir '<absolute-output-dir>' \
  --node '<loader-node>' \
  --artifact-runtime "$RUNTIME_DIR" \
  --soffice '<loader-soffice>' \
  --verify \
  --json
```

常用模式：

- 日常刷新：不加 `--force`。
- 首次生成/生成规则升级：加 `--force`。
- 交付验收：加 `--verify`，只渲染总入口和本次变化分区的所有工作表。
- 自定义缓存：`--cache-dir <cache-dir>`，仍须放在用户缓存区而不是 vault。

运行完成后再用完全相同参数复跑一次。第二次必须进入 unchanged 快路径；否则增量缓存、输出缺失判断或 manifest 提交存在问题。

## 数据口径

“馆藏总文件数”和“Excel 已展开文件明细数”不一定相等：

- 总文件数来自 `00_馆藏总览.md` 的物理扫描统计。
- 已展开明细来自 `_全文检索/*.md` 的实际数据行。
- 某些历史分区可能只保留聚合统计，或主动排除无检索价值的模板碎片。

Excel 首页必须同时显示两种口径及覆盖率，不能把已展开行数冒充全盘总数。每份全文检索 Markdown 的数据行数必须与其头部声明一致；不一致时生成器应失败，不带病交付。

工作簿只写数据源文件名和用途，不写输入 Markdown、缓存或运行目录的绝对本机路径。上传前应机械扫描 XLSX 内部 XML，确认不存在 `/Users/`、`/home/`、`/Volumes/`、用户名等本地标识。

同一逻辑路径可能对应多个物理实体。目录大纲可按路径去重以便阅读，但全盘统计与全文检索必须以扫描记录为准，不能因为路径相同少算实体。

生成时间默认使用宿主系统时区；需要固定时区时显式设置 `SOIA_CATALOG_TIME_ZONE`。需要调整 Node 内存参数时显式设置 `SOIA_ARTIFACT_NODE_OPTIONS`，公共 skill 不注入机器相关默认值。

## 云盘上传与链接更新

Excel 本地生成成功不等于云端已更新。需要上传时按以下顺序：

1. 记录远端旧文件的 `file_id`、字节数、SHA1 和所在目录。
2. 获得用户对覆盖动作的明确授权。
3. 使用原子层上传；若使用覆盖参数，明确知道旧文件会进入回收站且新文件可能取得新 `file_id`。
4. 独立 `ll` 复核远端新文件的名称、字节数、SHA1 和 `file_id`。
5. 把关键 Excel 的最终完整路径、字节数、SHA1 和可选 `file_id` 写入 `audit_structure.py` 的 `required_artifacts` 合同；资源地图的最终链接写入 `resource_maps`，让终态审计机械复核，而不是只在回执里抄一遍。
6. 更新 Obsidian 回执、资源地图和其他消费端中的旧链接；全库检索旧 `file_id` 应为 0，历史审计记录除外。
7. 上传完成后再做终态扫描和索引刷新；否则刚上传的 Excel 会天然少算一项。

云盘目录深链使用：

```text
https://www.alipan.com/drive/file/all/backup/<40位file_id>
```

不要使用 `drive/folder/<id>`。

## 故障处理

| 现象 | 常见原因 | 安全处理 |
|---|---|---|
| 在线预览显示 `=HYPERLINK(...)` | 工作簿没有公式缓存值 | 提供 `--soffice` 重算后再上传 |
| 每次都重建全部分区 | 日常误用了 `--force`，或缓存目录不可持久 | 去掉 `--force`，确认缓存位于 XDG cache 且 manifest 可写 |
| unchanged 但文件缺失 | 输出被外部移动/删除，或旧 manifest 异常 | 生成器应把缺失输出视为 changed；若仍未重建，删除该数据源缓存后用 `--force` 一次 |
| 分区头部数量与明细不一致 | Markdown 拼接漏行、重复行或头部未更新 | 回到 `gen_catalog.py`/扫描源修正，不在 Excel 层硬改数字 |
| 总文件数大于明细数 | 历史分区只做聚合或排除了碎片 | 在首页显示覆盖率；需要逐文件检索时重扫对应分区 |
| Excel 能打开但链接不可点 | 名称列没有公式，或 URL 不是直达格式 | 检查 `HYPERLINK` 数量，并抽查 `file/all/backup/<file_id>` |
| 交付目录出现 `.inspect.ndjson` | 调试 sidecar 未清理 | 生成器应自动清理；交付前再次确认目录只含正式产物 |
| 云端还是旧版本 | 只更新了本地，或覆盖后仍引用旧 `file_id` | 比较远端 SHA1/bytes，并更新所有消费端链接 |

更广泛的云盘扫描、删除、路径异常和并发问题见 [operations-troubleshooting.md](operations-troubleshooting.md)。

## 完成定义

- 所有全文检索文件的声明数与实际数据行一致。
- 总入口的物理总数、已展开明细数和覆盖率均有明确标签。
- 本次变化分区已重建；未变化分区文件的修改时间/哈希保持不变。
- `--verify` 公式错误扫描为 0，变化工作簿的全部工作表均完成渲染检查。
- `unzip -t` 或等价 ZIP 完整性检查通过。
- 提供 `soffice` 时，链接显示为友好文字；名称列和“打开云盘”列均可点击。
- 同参数第二次运行返回 `status=unchanged` 且 `rebuilt=[]`。
- 若已上传，远端字节数与 SHA1 和本地一致，旧 `file_id` 的消费端引用已更新；关键产物与资源地图分别通过 `required_artifacts`、`resource_maps` 合同审计。
- 缓存和 QA 预览不进入 vault/仓库，交付目录无调试 sidecar。
