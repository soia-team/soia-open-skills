# soia-cwork-feishu-doc-git-sync

> 将飞书知识库或云文档以应用身份只读同步为本地 Markdown，保留目录、来源和同步元数据，并可接入 Git、Obsidian 与 VitePress；当用户要求同步飞书知识库、备份到 Git、在本地查看或规划双向同步时使用

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-cwork-feishu-doc-git-sync) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 同步飞书知识库到本地 | 遍历知识空间节点，读取可读文档并生成 Markdown | 本地镜像目录、目录层级、来源链接、同步清单 |
| 排除指定知识库子树 | 按稳定节点 ID 或精确标题跳过根节点及全部后代 | 不读取该子树正文、表格、图片或附件，也不加入侧边栏和重试队列 |
| 备份到 Git | 将生成内容放入客户指定的 Git 仓库并检查差异 | commit/push 回执、文件变更和失败清单 |
| 用 Obsidian 查看 | 在独立 vault 中保存规则、镜像和本地补录 | 可直接用 Obsidian 打开的 vault |
| 用 VitePress 展示 | 生成站点侧边栏并构建静态站点 | 本地开发服务或构建产物 |
| 检查表格/多维表格导出能力 | 解析真实资源类型、权限和可用导出格式 | 只读探查结果；不会默认生成 Excel 文件 |
| 同步独立或内嵌 Sheet | 对私有配置明确授权的范围读取 Sheet；可自动覆盖全部独立 Sheet 节点，内嵌 Sheet 从文档 XML 中识别后再读取 | 有边界的 Markdown 表格快照；不再把已授权的 Sheet 节点写成正文占位 |
| 保留 Sheet 公式、样式、批注与图表信息 | 对已选范围保存单元格、布局、图表和浮动图片元数据快照 | Markdown 表格旁的本地保真 JSON；不伪装为可编辑工作簿 |
| 初始化完整 Sheet 与报表 | 经确认后分批导出整个 Sheet 工作簿 | `.xlsx` 保真副本，保留公式、样式、批注、图表、透视和单元格图片 |
| 镜像指定多维表格 | 读取指定 Base 表的字段、限量记录和可选视图，生成 Markdown 与快照 | 有上限的表格内容、schema/记录快照；默认不读取任何 Base 数据 |
| 初始化多维表、多人报表 | 经确认后分批导出完整 Base；选定表也可读取仪表盘与报表块元数据 | `.base` 保真副本；仪表盘快照写入 JSON，不伪装成交互式网页 |
| 本地化资源与导航 | 经确认后下载文档图片/附件，或下载所选多维表格记录附件，并把文档内部链接和子页面列表改为本地导航 | 本地资源、相对链接和可选子页面导航 |
| 初始化知识库文件 | 经确认后分批下载 Wiki `file` 节点的原始二进制 | 本地链接；ZIP、DMG、EXE 等只保存，绝不执行、挂载或解压 |
| 查看同步变更 | 经配置后生成新增、修改、移动和远端删除的本地变更台账与受限 diff | 本次同步的统计、变更清单和差异详情 |
| 规划双向同步 | 区分只读镜像、托管文档和本地补录 | 冲突/权限风险说明，不自动覆盖飞书 |

### 客户如何使用

1. 确认 `soia-cwork-feishu-cli` 已完成飞书应用凭证登录，并且机器人可以读取目标知识空间。
2. 在本机私有配置中填写知识空间 ID、输出目录和来源 URL 模板；不要把 App Secret、token 或企业私有路径提交到公开技能仓库。
3. 首次使用先执行 dry-run，核对空间、节点数量和目标目录。
4. 先用单节点隔离试点核对表格、资源和样式快照；`--pilot-node-token` 只写明确选择的节点到单独试点目录，不会给空目录补齐其他节点占位文件。
5. 执行镜像同步。默认只写本地文件和同步元数据，不修改飞书内容，也不删除本地历史文件。
6. 如需排除完整目录树，在私有配置设置 `sync.exclude_subtrees.enabled: true`，并在 `roots` 中优先填写稳定 `node_token`；首次清理既有 Markdown、完整导出和已下载附件时显式运行一次 `--rebuild-tree`，本地补录目录永不受影响。
7. 同步写入后会自动校验 manifest、文件存在性、frontmatter、失败占位、侧边栏覆盖范围、排除子树残留、资源引用、未归档的嵌入式 Sheet、未归档的 Sheet 内嵌 Base、`all_docx` 模式下尚未完成 XML 语义扫描的历史文档，以及 `all_nodes` 模式下仍未生成真实表格的独立 Sheet；发现 `failed`/`stale` 或语义缺口时返回非零结果，不能把空白占位或局部内容当作完整成功。
8. 如需检查表格导出，先做 `drive +inspect`/帮助/schema 探查；能力探查不等于授权导出。
9. 只有客户明确确认导出范围、格式、文件数和本地目录后，才调用 `drive +export` 或 `drive +export-download`。
10. 如需镜像 Sheet，先在私有配置明确范围：全部独立 Sheet 使用 `sync.sheets.enabled: true` 与 `all_nodes: true` 自动发现每个网格子表，或在 `selections` 中逐项指定 `node_token`、稳定 `sheet_id` 和有界 A1 `range`；两种方式都必须设置行列、单元格和返回字符上限。响应达到 `max_chars` 时必须按 `actual_range` 下一行续读，不能把截断当成整表失败。混合工作簿还需显式设置 `include_bitable_tabs: true` 与记录上限，随后把 Base 子表路由到多维表格读取。文档内嵌 Sheet 启用 `sync.embedded_sheets.enabled` 后，还须选择 `all_docx: true` 或 `node_tokens`。按需开启 `sync.sheets.preserve` 保存公式、样式、批注、布局和图表等元数据。未启用时必须显示并校验语义缺口，不得静默删除 `<sheet>` 或把独立 Sheet 占位当成完整归档。
11. 如需镜像多维表格，逐项指定 `sync.bitables.selections` 的 `node_token`、`table_id` 和 `max_records`，再开启 `sync.bitables.enabled` 或传入 `--sync-bitables`；附件二进制还需要单独开启 `download_attachments`，仪表盘/报表元数据需要 `include_dashboards`。
12. 只有用户明确确认来源、格式、文件数、输出目录和 Git 策略后，才能执行完整初始化：Sheet 设置 `sync.sheets.workbook_exports.enabled=true` 与 `all_nodes=true`，Base 设置 `sync.bitables.base_exports.enabled=true` 与 `all_nodes=true`，Wiki 文件设置 `sync.files.downloads.enabled=true` 与 `all_nodes=true`。每项必须配置 `batch_size`，重复执行至 deferred 为零。
13. 如需离线资源、文档间本地跳转、子页面导航或变更台账，先在私有配置中逐项启用 `download_assets`、`localize_internal_links`、`render_sub_page_navigation`、`change_ledger`；它们默认关闭以兼容已有镜像。
14. 批量初始化前先以一份代表性范围试点，确认资源数量、失败类别和本地渲染；同步完成后再运行 Git diff、站点构建和必要的人工抽查。

推荐命令：

```bash
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --dry-run
# 试点只写所选节点到独立目录；仍会核验它是否属于当前知识库
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --output-dir <pilot-output-dir> \
  --pilot-node-token <node_token> --incremental
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental
# 没有事件订阅时，按 wiki +node-get 的远端更新时间判断正文是否变化
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental --probe-remote-metadata
# 复用已完整正文，优先补独立 Sheet stub、未扫描的内嵌 Sheet 文档，再退避重试失败项
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --retry-failed
# 事件适配器已经拿到变动 ID 时，只拉对应节点；可重复传入多个 ID
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --changed-node-token <node_token> --changed-obj-token <obj_token>
# 只修复指定节点的本地格式，复用 manifest 中的其他文档，不重试历史失败项
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --rebuild-tree --rebuild-tree-only --only-node-token <node_token> --skip-assets
# 官方 webhook/长连接适配器写入 JSON/NDJSON 后，按事件目标增量拉取
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --event-file <events.ndjson>
# 仅在确认历史生成目录曾经扁平化时执行一次结构迁移
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --retry-failed --rebuild-tree
# 大型知识库遇到限流时分批补偿；重复执行直到 --validate-only 通过
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> \
  --retry-failed --retry-batch-size 100 --skip-assets
# 如果只需要修复本地目录层级、暂时不请求飞书
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --rebuild-tree --rebuild-tree-only
# 从飞书刷新最新目录层级和兄弟节点顺序，但复用现有本地正文
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --rebuild-tree --refresh-tree-only
# 应用私有配置中的整棵子树排除，并清理该子树既有 Markdown、完整导出和已下载附件
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --rebuild-tree --refresh-tree-only --skip-assets
# 下载图片到本地镜像并把正文中的远程 URL 改成相对路径
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --download-assets
# 将私有配置中明确选择的 Sheet 范围渲染为 Markdown 表格
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --sync-sheets
# 将已授权文档中的嵌入式 Sheet 追加为有界 Markdown 表格快照
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --sync-embedded-sheets
# 将私有配置中明确选择的多维表格镜像为 Markdown 与 JSON 快照
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --sync-bitables
# 完整初始化仍使用同一同步命令；私有配置中 workbook_exports/base_exports/files.downloads
# 的 enabled 与 all_nodes 必须都为 true，并按 batch_size 分批重复执行
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --sync-sheets --sync-bitables
# 只校验最近一次同步生成的本地镜像，不访问飞书
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --validate-only
```

### 三种工作模式

- `mirror`：默认模式。知识库是来源，本地生成的 `10_knowledge-base/` 不应手工编辑。
- `local`：只维护本地 `20_本地补录/`，不会被镜像同步覆盖，也不会自动上传飞书。
- `managed`：未来用于明确指定的双向托管文档。必须逐文档确认写入权限、冲突规则和发布动作；当前脚本只提供只读镜像基础，不把它伪装成已经完成的双向同步。

### ID 增量同步与事件推送

- `node_token` 是同步主键，`obj_token` 是正文读取和事件映射的对象键；标题变化、移动和重名都不应改变这两个 ID。
- `sync.exclude_subtrees` 必须在私有配置中显式启用；优先按稳定 `node_token` 排除，`exact_title` 会排除所有精确同名根节点。同步器只在根节点的父级列表中识别它，不再枚举后代，并从正文、Sheet、Base、图片、附件、重试、活跃 manifest 和侧边栏中同时排除整棵子树。
- 已生成的排除子树内容不会被普通增量同步静默删除；用户明确要求清理后运行 `--rebuild-tree`，同步器把已知成员记录为 `excluded` 而不是误报为远端删除，并清理、校验对应 Markdown、目录、`_exports/` 完整导出和 `_assets/` 已下载附件均不残留；`20_本地补录/` 永不删除。
- `--only-node-token` 是单文档修复开关；与 `--rebuild-tree-only` 一起使用时只从已有 manifest 定位节点，不重新遍历飞书树，也不会因为其他节点历史失败而重试它们。
- 首次同步建立完整基线，记录 `obj_edit_time`/`remote_updated_at` 和 `docs +fetch` 返回的 `revision_id`。
- 后续 `--incremental` 仍会先按 `parent_node_token` 重建树，但只读取新增、失败、事件命中或远端编辑时间变化的文档正文；未变化节点复用本地 Markdown。
- 兄弟节点顺序直接保留 `wiki +node-list` 返回的飞书顺序，不按标题重新排序；因此 VitePress/Obsidian 目录应与飞书知识库的手工排序一致。
- 没有事件目标时，默认用 `wiki +node-get` 做元数据探测；这会产生较多轻量元数据请求，但避免重复下载正文。大型空间可改用官方事件订阅并传 `--event-file`。
- 事件只提供“哪个对象可能变了”的提示，不能替代 Wiki 树对账；创建、删除、标题变化和未识别事件仍需重新对账节点树。
- 官方事件订阅、权限和 `drive.file.*` 覆盖边界见 [references/events.yml](references/events.yml)。当前 `lark-cli event list` 未暴露云文档 `drive.file.*` 事件，因此本脚本不声称已经在 CLI 内常驻监听；外部长连接/webhook 适配器可以把 JSON/NDJSON 交给 `--event-file`。

## 安装

客户明确选择安装整个 `soia-cwork-office` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-cwork-office@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-cwork-office@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-cwork-feishu-doc-git-sync -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
