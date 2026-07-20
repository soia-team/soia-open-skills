# 家庭导航 Excel 生产说明

本说明对应 `scripts/gen_family_nav_xlsx.mjs`。它面向单个学习分区或课程合集，帮助家长先理解资源是什么、适合谁、怎么用，再按分类筛选并点击进入具体云盘课程。

## 目录

- [适用边界](#适用边界)
- [工作簿结构](#工作簿结构)
- [输入 JSON](#输入-json)
- [从扫描构建输入 JSON](#从扫描构建输入-json)
- [运行命令](#运行命令)
- [生成前后的正确顺序](#生成前后的正确顺序)
- [链接与云端上传](#链接与云端上传)
- [完成定义](#完成定义)

## 适用边界

| 需求 | 是否适用 |
|---|---|
| 一个分区的家庭说明、课程筛选、课程直达 | 是 |
| 全盘逐文件检索 | 否，使用 `gen_catalog_xlsx.py` |
| 修改云盘实体结构 | 否，先走 inventory/organize |
| 自动编造适龄、学习节奏 | 否，字段必须来自实际资源盘点或用户确认 |

脚本只生产 Excel，不读取或修改云盘。输入 JSON 由 agent 根据终态扫描、课程说明和用户确认生成。

## 工作簿结构

输出固定两张表：

1. `01_先看这里`
   - 一句话总说明；
   - 收录资源数、分类数、生成日期和分区名；
   - 最多六条家庭使用建议；
   - 分类统计。
2. `02_资源导航`
   - 可按分类、适合谁/阶段、资源形态筛选；
   - 展示怎么用、建议节奏和完整云盘路径；
   - “资源名称”和“打开云盘”两列均可点击；
   - 保留完整 URL，便于复制到浏览器。

脚本不创建一堆空工作表。需要更详细的教学说明时，应先提炼成简洁字段；长篇原文放在单独文档或新增明确命名的工作表生成器中，不手工破坏模板。

## 输入 JSON

所有字段都必须是非空字符串；`rows` 至少一项。可直接复制 `assets/family-navigation.example.json` 后替换占位内容，也可按下面模板创建。示例里的 `<40位file_id>` 故意不能通过校验，避免忘记换成真实链接后误交付。

```json
{
  "title": "<分区名> 家庭学习导航",
  "summary": "<一句话说明这批资源是什么、最适合怎样使用>",
  "generatedAt": "YYYY-MM-DD",
  "partition": "<云盘分区名>",
  "guidance": [
    {
      "label": "先选主线",
      "text": "一次只选一套主资源，连续使用一段时间再评估。"
    },
    {
      "label": "短时高频",
      "text": "低龄资源优先每天短时间接触，不追求一次学完。"
    }
  ],
  "rows": [
    {
      "category": "10_语言启蒙",
      "name": "<课程名称>",
      "audience": "<适合谁/阶段>",
      "type": "视频+音频",
      "usage": "<建议怎么用>",
      "pace": "<建议频率与单次时长>",
      "path": "/<云盘内完整路径>",
      "url": "https://www.alipan.com/drive/file/all/backup/<40位file_id>"
    }
  ]
}
```

字段来源：

- `name/path/url`：终态云盘扫描；不能从旧索引复制后不核验。
- `audience/type`：目录内容、文件类型和官方说明；判断不了写“待家长确认”，不要编年龄。
- `usage/pace`：实际体量与用户目标；视频按集数与时长估算，歌曲/绘本按短时高频原则。
- `summary/guidance`：面向家长写人话，不把目录结构原样复述成说明。

URL 只接受阿里云盘直达格式：

```text
https://www.alipan.com/drive/file/all/backup/<40位file_id>
https://www.aliyundrive.com/drive/file/all/backup/<40位file_id>
```

## 从扫描构建输入 JSON

`build_family_nav_inputs.py` 从新鲜的文件级 `scan_drive.py` JSONL 选择目录资源并生成上述输入 JSON。每个 guide 可选配置两个排除字段：

```json
{
  "selection_mode": "explicit_roots",
  "resource_roots": [
    {"path": "/Learning/Language/Complete course", "category": "Courses"}
  ],
  "exclude_paths": ["/Learning/Language/01_先看这里"],
  "exclude_name_patterns": ["^说明(?:-|_).+$", "^临时"]
}
```

- `selection_mode` 未填写时默认为 `explicit_roots`：必须提供至少一个 `resource_roots`，且只选择这些明确声明的业务资源包根；空数组会失败，不会自动扫描叶目录。
- `selection_mode: "deepest_leaves"` 是显式 opt-in 的兼容模式：按扫描结果自动选择排除项之外的最深目录。只有在确实要使用这种自动选择时才填写该值；`resource_roots` 在此模式下仍可作为额外的明确资源根。
- `selection_mode` 只接受 `explicit_roots` 或 `deepest_leaves`；未知值直接失败。
- `exclude_paths` 是 scope 内的绝对目录路径；该目录及其所有子目录均不作为资源行。
- `exclude_name_patterns` 是 Python 正则，使用 `search` 匹配目录名；命中的目录及其子目录均不作为资源行。需要精确名称时使用 `^...$`。
- 每个 guide 默认追加 `^01_先看这里$`，以排除导航 guide 自身；这是通用目录名规则，不包含任何用户私有路径，也不能通过传入空数组关闭。
- `resource_roots` 与排除规则命中同一目录会报错，避免同时“选择”和“排除”的静默冲突。

排除是可审计的：每个 `<guide-id>.json` 都带有 `excluded_directories`，其中逐项记录 `path`、`name` 与 `matched_by`（字段、规则值、默认/用户来源和实际命中的祖先目录）；命令打印的 JSON 状态在对应 `outputs[]` 中重复这份列表。未命中的配置规则不会虚报为匹配。

例如，以下命令只读取本地扫描和 guide spec，不访问云盘：

```bash
python3 '<skill-dir>/scripts/build_family_nav_inputs.py' \
  --scan '<run-dir>/fresh-scan.jsonl' \
  --guide-spec '<run-dir>/family-guides.json' \
  --out-dir '<run-dir>/family-navigation-inputs' \
  --url-prefix 'https://www.alipan.com/drive/file/all/backup/'
```

## 运行命令

查看自说明：

```bash
node '<skill-dir>/scripts/gen_family_nav_xlsx.mjs' --help
```

正式生成：

```bash
node '<skill-dir>/scripts/gen_family_nav_xlsx.mjs' \
  --input '<run-dir>/navigation.json' \
  [--output-dir '<absolute-output-dir>'] \
  --artifact-runtime '<runtime-with-node_modules>' \
  --qa-dir '<cache-or-run-dir>/qa' \
  --soffice '<soffice-path>'
```

依赖规则与总索引相同：必须使用 `@oai/artifact-tool`，不临时换 Excel 库。`navigation.json` 和 QA 图片属于运行中间物，放用户缓存或临时目录；正式 `.xlsx` 放用户指定交付目录，未指定时按 curator 的三级输出目录优先级落到默认 Downloads 目录。

脚本返回 JSON，至少包含：

```json
{
  "status": "updated",
  "output": "<absolute-output-path>",
  "rows": 12,
  "recalculated": true,
  "verified": true,
  "previews": ["<qa-preview-1>", "<qa-preview-2>"]
}
```

## 生成前后的正确顺序

家庭导航本身也是云盘文件，因此顺序会影响最终统计：

1. 完成云盘结构整理并独立复核终态。
2. 从终态扫描生成 `navigation.json`。
3. 生成并验证家庭导航 Excel。脚本会在写入两列 `HYPERLINK` 公式、导出（以及可选 `soffice` 重算）后，重新打开最终 `.xlsx`：只接受恰有 `01_先看这里` / `02_资源导航` 两张表、数据行数与输入一致、名称列和“打开云盘”列公式均引用该行输入 URL，且无公式错误的工作簿。
4. 获得上传/覆盖授权后，把 Excel 上传到目标 `01_先看这里`。
5. 独立复核云端 bytes、SHA1、`file_id` 和无重名副本。
6. 再做分区终态扫描、OB 资源地图、全文检索与总索引 Excel。

如果在第 6 步之后才上传导航表，刚生成的索引会少 1 个文件。

## 链接与云端上传

- 每一行的资源名称本身必须可点击，不能只依赖“🔗 打开”图标。
- URL 必须指向具体课程目录，而不是只指向上级分区。
- 同盘移动/改名通常保留 `file_id`；覆盖上传文件可能生成新 `file_id`。
- 覆盖前记录旧 ID/SHA1/bytes，覆盖后记录新 ID/SHA1/bytes，并更新所有消费端。
- 若用户只要求本地生成，不得擅自上传。

在线预览只显示公式时，使用 `--soffice` 重算后重新上传。不要把公式字符串改成普通文本来掩盖问题。

## 完成定义

- JSON 每个资源均来自终态盘点，名称、路径和 URL 对应同一实体。
- `01_先看这里` 能在一分钟内回答“是什么、适合谁、怎么用、什么节奏”。
- `02_资源导航` 可筛选，资源名称与打开列都可直达具体课程。
- 导出后的最终 `.xlsx` 已重新打开验证：工作表恰为 `01_先看这里` / `02_资源导航`，数据行数匹配输入，名称列和“打开云盘”列均保留引用输入 URL 的 `HYPERLINK` 公式，公式错误扫描为 0；两张表均已渲染目检，长文本没有严重截断。
- XLSX ZIP 完整性通过，`.inspect.ndjson` 未进入交付目录。
- 使用 `soffice` 时，在线预览显示友好链接文字而不是公式源码。
- 若已上传，远端 bytes/SHA1 与本地一致，目标目录无重名副本。
- 上传后完成终态重扫，OB 资源地图与总索引包含该导航文件。
