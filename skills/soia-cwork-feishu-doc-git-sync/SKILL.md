---
name: soia-cwork-feishu-doc-git-sync
description: 将飞书知识库或云文档以应用身份只读同步为本地 Markdown，保留目录、来源和同步元数据，并可接入 Git、Obsidian 与 VitePress；当用户要求同步飞书知识库、备份到 Git、在本地查看或规划双向同步时使用。
dependencies:
  hard: [soia-cwork-feishu-cli]
version: 1.5.0
created_at: 2026-07-14 23:24:26
updated_at: 2026-07-20 11:30:00
created_by: claude opus 4.6
updated_by: gpt-5.6-sol
---

# soia-cwork-feishu-doc-git-sync

把飞书知识库的内容镜像到一个本地 Markdown 知识库。默认方向是 Feishu → local/Git/Obsidian/VitePress；本技能不默认向飞书写入，双向同步必须先建立文档归属、冲突策略和写权限。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 同步飞书知识库到本地 | 遍历知识空间节点，读取可读文档并生成 Markdown | 本地镜像目录、目录层级、来源链接、同步清单 |
| 备份到 Git | 将生成内容放入客户指定的 Git 仓库并检查差异 | commit/push 回执、文件变更和失败清单 |
| 用 Obsidian 查看 | 在独立 vault 中保存规则、镜像和本地补录 | 可直接用 Obsidian 打开的 vault |
| 用 VitePress 展示 | 生成站点侧边栏并构建静态站点 | 本地开发服务或构建产物 |
| 检查表格/多维表格导出能力 | 解析真实资源类型、权限和可用导出格式 | 只读探查结果；不会默认生成 Excel 文件 |
| 同步指定 Sheet 范围 | 用 `lark-cli sheets` 读取已明确配置的工作表和 A1 范围，并生成 Markdown 表格 | 范围受限的表格值镜像；默认不读取任何 Sheet 单元格 |
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
6. 同步写入后会自动校验 manifest、文件存在性、frontmatter、失败占位、侧边栏覆盖范围和资源引用；发现 `failed`/`stale` 时返回非零结果，不能把旧正文当作最新成功。
7. 如需检查表格导出，先做 `drive +inspect`/帮助/schema 探查；能力探查不等于授权导出。
8. 只有客户明确确认导出范围、格式、文件数和本地目录后，才调用 `drive +export` 或 `drive +export-download`。
9. 如需镜像 Sheet 单元格，先在私有配置的 `sync.sheets.selections` 中逐项指定 `node_token`、稳定 `sheet_id` 与有界 A1 `range`，再启用 `sync.sheets.enabled` 或传入 `--sync-sheets`。若需要公式、样式、批注、布局、图表、透视、筛选、条件格式或迷你图元数据，再单独开启 `sync.sheets.preserve` 的对应开关。
10. 如需镜像多维表格，逐项指定 `sync.bitables.selections` 的 `node_token`、`table_id` 和 `max_records`，再开启 `sync.bitables.enabled` 或传入 `--sync-bitables`；附件二进制还需要单独开启 `download_attachments`，仪表盘/报表元数据需要 `include_dashboards`。
11. 只有用户明确确认来源、格式、文件数、输出目录和 Git 策略后，才能执行完整初始化：Sheet 设置 `sync.sheets.workbook_exports.enabled=true` 与 `all_nodes=true`，Base 设置 `sync.bitables.base_exports.enabled=true` 与 `all_nodes=true`，Wiki 文件设置 `sync.files.downloads.enabled=true` 与 `all_nodes=true`。每项必须配置 `batch_size`，重复执行至 deferred 为零。
12. 如需离线资源、文档间本地跳转、子页面导航或变更台账，先在私有配置中逐项启用 `download_assets`、`localize_internal_links`、`render_sub_page_navigation`、`change_ledger`；它们默认关闭以兼容已有镜像。
13. 批量初始化前先以一份代表性范围试点，确认资源数量、失败类别和本地渲染；同步完成后再运行 Git diff、站点构建和必要的人工抽查。

推荐命令：

```bash
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --dry-run
# 试点只写所选节点到独立目录；仍会核验它是否属于当前知识库
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --output-dir <pilot-output-dir> \
  --pilot-node-token <node_token> --incremental
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental
# 没有事件订阅时，按 wiki +node-get 的远端更新时间判断正文是否变化
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental --probe-remote-metadata
# 如果上次清单已有失败项，复用成功正文，只退避重试失败项
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
# 下载图片到本地镜像并把正文中的远程 URL 改成相对路径
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --download-assets
# 将私有配置中明确选择的 Sheet 范围渲染为 Markdown 表格
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --sync-sheets
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
- `--only-node-token` 是单文档修复开关；与 `--rebuild-tree-only` 一起使用时只从已有 manifest 定位节点，不重新遍历飞书树，也不会因为其他节点历史失败而重试它们。
- 首次同步建立完整基线，记录 `obj_edit_time`/`remote_updated_at` 和 `docs +fetch` 返回的 `revision_id`。
- 后续 `--incremental` 仍会先按 `parent_node_token` 重建树，但只读取新增、失败、事件命中或远端编辑时间变化的文档正文；未变化节点复用本地 Markdown。
- 兄弟节点顺序直接保留 `wiki +node-list` 返回的飞书顺序，不按标题重新排序；因此 VitePress/Obsidian 目录应与飞书知识库的手工排序一致。
- 没有事件目标时，默认用 `wiki +node-get` 做元数据探测；这会产生较多轻量元数据请求，但避免重复下载正文。大型空间可改用官方事件订阅并传 `--event-file`。
- 事件只提供“哪个对象可能变了”的提示，不能替代 Wiki 树对账；创建、删除、标题变化和未识别事件仍需重新对账节点树。
- 官方事件订阅、权限和 `drive.file.*` 覆盖边界见 [references/events.yml](references/events.yml)。当前 `lark-cli event list` 未暴露云文档 `drive.file.*` 事件，因此本脚本不声称已经在 CLI 内常驻监听；外部长连接/webhook 适配器可以把 JSON/NDJSON 交给 `--event-file`。

## 依赖与安装

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| `soia-cwork-feishu-cli` | 强依赖 | 安装并配置飞书官方 `lark-cli` 应用凭证 | 停止，先完成 bot 登录和权限检查 |
| `lark-cli` | 强依赖 | 参见 `soia-cwork-feishu-cli` 的安装说明 | 停止并报告安装命令 |
| Python 3.10+ | 强依赖 | 使用系统 Python 或项目 Python | 停止 |
| PyYAML | 强依赖 | `python3 -m pip install pyyaml` | 停止并报告依赖缺失 |
| Git | 可选增强 | 安装 Git | 仍可生成本地镜像，但不能提交/推送 |
| VitePress | 可选增强 | 由目标文档仓库提供 | 仍可同步到 Obsidian |
| Obsidian | 可选增强 | 用户本机安装 | 仍可生成普通 Markdown |

私有配置默认位置：

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-feishu-doc-git-sync/config.yml
```

也可以使用 `SOIA_CWORK_FEISHU_DOC_GIT_SYNC_CONFIG_FILE` 指定配置文件。参考 [assets/config.example.yml](assets/config.example.yml)。

最小配置示例：

```yaml
version: 1
provider:
  cli: lark-cli
  profile: <configured-cli-profile>
  brand: feishu
  identity: bot
space:
  id: <wiki-space-id>
  source_url_template: https://<tenant>.feishu.cn/wiki/{node_token}
paths:
  output_dir: <git-repository>/docs/feishu-knowledge
  generated_dir: 10_<knowledge-base-name>
sync:
  mode: mirror
  prune: false
```

权限建议：首轮只申请知识库、文档与 Sheet 只读权限。图片和附件下载是可选增强，涉及云盘/导出权限时单独申请；双向写入权限永不作为默认权限。

## 同步规则

- 只使用 `--as bot` 的应用身份读取，默认不需要用户身份 token。
- 通过 node token 遍历知识空间，使用文档 token 读取 `docx` 内容。
- `paths.generated_dir` 必须使用目标知识库的真实名称或稳定英文名称；例如 `10_后端技术支持库`，不要再嵌套一个泛化的 `feishu-knowledge` 目录。
- 如果已有输出目录中只有一个 `10_*` 生成目录而配置未填写 `paths.generated_dir`，技能会复用它；如果发现多个候选目录，会停止并要求先明确配置，避免自动制造重复目录。
- 每个生成 Markdown 写入来源 URL、space ID、node token、object token、父节点和内容 hash。
- 使用 `sync-state.json` 保留 node token 到本地路径的映射；标题变化时尽量保持稳定路径，树位置由最新 `parent_node_token` 重新计算。
- `manifest.json` 和 `sync-state.json` 记录 `obj_edit_time`、`remote_updated_at`、`revision_id`，用于增量选择和审计。
- 本地单个路径组件最多 48 个字符；超长标题会保留完整标题在 frontmatter/侧边栏，并在文件夹或文件名中追加 node ID 短后缀，避免 Obsidian、macOS 和 VitePress/Rollup 路径过长。
- 同步器会把飞书导出的自定义 `figure/source/grid/callout`、媒体 token 和 XML 片段转换为可被 Markdown/VitePress 解析的形式；这只改变本地渲染，不写回飞书。
- 飞书文档引用会按 `node_token` 优先、`obj_token` 兜底解析为可点击的飞书 Wiki 链接；用户引用会保留为 `@显示名`。静态 Markdown 不复制飞书的悬浮卡片和成员头像交互，但不再错误降级为代码样式。
- 有子节点的飞书节点必须生成一个同名目录，并把正文放在目录内的同名 index Markdown：`父目录/节点名/节点名.md`；叶子节点才直接生成 `节点名.md`。不要生成同级的“同名文件 + 同名文件夹”。
- 如果飞书本身存在同名叶子与可展开节点、父子同名或同级重复可展开节点，目录/文件会追加稳定的 node ID 短后缀；这是为了避免本地文件系统发生同级冲突，manifest 仍以 `node_token` 区分真实节点。
- `--retry-failed` 会复用上次 `sync_status: ok` 的本地正文，只读取上次失败的文档；适合遇到飞书接口限流后继续补齐。
- `--retry-batch-size N` 仅与 `--retry-failed` 配合使用，每次最多补偿 N 个失败节点；大型空间应重复执行，并以 `--validate-only` 的 `failed_records=0` 作为结束条件。
- `--retry-failed` 使用上一次 manifest 作为节点清单，不再先对全量文档做元数据探测；这样补偿运行只消耗失败正文请求，并继续受全局节流保护。
- 同一输出目录同时只允许一个同步进程；如果上一轮仍在退出或用户重复启动，后续进程会停止并报告，不会并发覆盖 manifest。
- 全局请求节流和指数退避会跨同步 worker 生效；`sync.min_request_interval_seconds` 默认 0.5 秒，避免大知识库并发触发 `99991400` 限流。
- 正文读取失败但本地已有旧正文时，节点会标记为 `stale` 并保留旧正文；下一次增量同步会继续重试，校验不会将其视为成功。
- 每次非 dry-run 同步结束都会运行本地验收；`--validate-only` 可单独复核最近一次结果。验收失败时退出码为 2，并在 manifest 的 `validation` 节点保留机器可读摘要。
- `prune: false` 时不删除已消失节点对应的本地文件；节点会在 manifest 中标记为 deleted，避免一次权限或网络异常造成数据丢失。
- `20_本地补录/` 与 `90_同步元数据/` 不会被知识库同步覆盖。
- `--rebuild-tree` 只迁移 `paths.generated_dir` 内由同步器生成的旧扁平文件，不触碰 `20_本地补录/`。
- `--rebuild-tree-only` 仅复用已有 manifest 和生成文件做目录迁移，不发起飞书正文请求；如果同时启用资源本地化，仍可能只为刷新过期媒体 URL 读取含资源的文档。
- `--refresh-tree-only` 会重新读取飞书节点树和兄弟顺序，按最新 `parent_node_token` 重建本地目录和侧边栏，但复用已有本地正文；启用资源本地化时，会额外刷新仍含未本地化资源的文档；必须与 `--rebuild-tree` 一起使用。
- `manifest.json`/`sync-state.json` 的 `tree_order: feishu_node_list` 表示目录顺序来源于飞书节点列表，不是标题排序。
- 图片默认保留远程 URL；设置 `sync.download_assets: true` 或传入 `--download-assets` 后，技能会把正文中的远程图片及 `<source token="...">` 媒体块下载到 `paths.generated_dir/_assets/`，并把 Markdown/HTML 引用改写为相对路径。已下载的飞书附件卡片必须进一步改写为标准 Markdown 本地链接；若该链接被单独的 `<p>` 包裹，必须同时移除该 HTML 容器，确保 Obsidian 和 VitePress 都能点击打开。未下载的卡片仍保留原远程引用并报告失败。
- 下载资源时，优先按飞书媒体 token 去重；同一附件或图片即使带有不同的短期签名 URL，也只保留一份本地资源。无 token 的资源仍按 URL 内容寻址。
- `sync.localize_internal_links: true` 时，已同步的 Wiki/文档引用会改为相对本地 Markdown 链接；`sync.render_sub_page_navigation: true` 时，飞书导出的 `<sub-page-list>` 会改为本地 Markdown 子页面导航。两项均默认关闭，不影响已有外链行为。
- `sync.change_ledger: true` 时，会在同步元数据下按运行生成新增、修改、移动和远端删除的变更台账；修改项只保留受 `change_ledger_max_diff_lines` 限制的 diff，不复制文档全文，也不改变生成镜像或本地补录目录。
- `sheet` 默认只生成元数据 stub。设置 `sync.sheets.enabled: true` 后，仍必须在 `sync.sheets.selections` 中逐项声明 Wiki `node_token`、由 `sheets +workbook-info` 确认的 `sheet_id`、以及有界 A1 `range`；同步器再用 `sheets +csv-get` 读取显示值并生成 Markdown 表格。范围、最大单元格数和最大返回字符数的完整契约见 [references/sheet-mirroring.yml](references/sheet-mirroring.yml)。
- `sync.sheets.preserve.enabled: true` 会在同一选定范围另存单元格值、公式、样式、批注，以及工作表布局、图表和浮动图片元数据的 JSON 快照；可额外开启透视、筛选、条件格式和迷你图元数据。它不把图表或图片伪装成原生 Markdown。完整工作簿需在用户明确批准后同时设置 `sync.sheets.workbook_exports.enabled: true` 和 `all_nodes: true`，同步器会用 `drive +export` 分批生成 `.xlsx` 并在 Sheet 索引中链接。
- 异步 Sheet 导出未在首轮轮询完成时，会把导出任务票据保存在生成目录的私有快照中；后续批次只轮询同一任务，并在就绪后使用 `drive +export-download` 下载，不会反复创建相同工作簿导出任务。`manifest.stats.sheet_workbooks_pending` 表示仍在飞书端处理的数量。
- 图片/附件本地化是显式 opt-in 的本地数据下载；不能因为用户只要求“检查图片”就下载全部素材。持久化配置中的 `sync.download_assets: true` 只能视为用户此前对该资源范围的明确授权，不得扩展为表格或多维表格导出授权。若先执行 Sheet/Base/文件的结构初始化并使用 `--skip-assets` 避免输出锁冲突，必须在初始化结束后单独执行资源本地化批次；`--skip-assets` 不会把图片或附件标记为已下载。
- `bitable` 与未明确选择的 `sheet` 默认只生成元数据 stub，不读取表内数据。设置 `sync.bitables.enabled: true` 后，必须逐项声明 `node_token`、`table_id` 与 `max_records`；同步器以 `base +field-list`、`base +record-list` 和可选的 `base +view-list`/`base +dashboard-list`/`base +dashboard-block-list` 生成 Markdown 与 JSON 快照。`sync.bitables.download_attachments: true` 是独立的二进制下载授权，使用 `base +record-download-attachment` 并只处理已选表的已读记录附件。完整 Base 导出仍须在用户明确批准后同时设置 `sync.bitables.base_exports.enabled: true` 和 `all_nodes: true`，同步器用 `drive +export` 分批生成 `.base`。
- Wiki `file` 节点默认只生成元数据 stub；用户明确确认完整初始化后，同时设置 `sync.files.downloads.enabled: true` 与 `all_nodes: true`，同步器才会分批调用 `drive +download`。文件以原始二进制保存，不会执行、挂载、解压或解析 ZIP、DMG、EXE 等格式。
- 飞书 Markdown 导出的图片 URL 可能是短期鉴权地址；启用本地化与资源刷新后，技能会先重读关联文档取得新 URL，再下载资源，避免对已过期的 Feishu drive/stream 链接反复等待；不会无条件重拉所有正文。可用 `--refresh-asset-urls` 显式打开该行为。
- 图片下载使用 URL 内容寻址文件名，重复同步会复用已有资源；Markdown 的普通 URL 与 `(<https://…>)` 尖括号 URL 都会进入同一下载队列。可通过 `asset_workers`、`asset_timeout_seconds`、`max_asset_bytes` 限制并发、超时和单文件大小。大型存量镜像可设置正整数 `asset_batch_size`：每次只请求该数量的尚未落盘资源，已下载资源仍会被本地化改写；`asset_refreshed_batch_size` 可限制同一批已刷新文档的新链接下载量。重复执行并以 `--validate-only` 确认完成。manifest 会报告本轮 `assets_deferred`。下载失败只保留原 URL，并在 manifest 的 `assets_failed` 计数中报告，不把鉴权 URL 写入日志或清单。
- `<source token="...">` 或无 URL 的 `<img token="...">` 会调用官方 `docs +media-download`；远程 URL 不可直接读取时，需要按权限清单补充 `docs:document.media:download` 或 `drive:file:download`，并在私有配置中启用本地资源下载。没有下载权限时不得猜测本地资源已经完整。

## 安全规则

- 不在公开 skill、Obsidian vault、Markdown、Git 提交、终端输出或最终回复中写入 App Secret、access token、cookie。
- 终端日志、进度回执和最终回复不得输出本地绝对路径、具体本地文件名、操作系统用户名、用户名、密码、App Secret、access token 或私有下载 URL；统一使用脱敏占位符，只报告状态、数量和错误类别。详见 [references/output-redaction.yml](references/output-redaction.yml)。
- 不默认调用飞书创建、更新、删除接口。
- `drive +export`、`drive +export-download`、`docs +media-download` 和附件下载均属于数据导出/下载动作；用户说“看下能否导出”时只做 inspect、help、schema 或 dry-run，不得直接创建本地文件。
- Sheet 与 Base 值镜像都属于敏感数据落盘：只有用户明确确认需要将选定范围/表同步到本地工作区，并在私有配置中写入有界 `sync.sheets.selections` 或受限 `sync.bitables.selections` 后才可启用；该确认不授权任何工作簿导出、未选附件下载或自动 Git 提交。
- 真实导出前必须明确回执来源、类型、格式、预计文件数、输出目录和 Git 追踪策略；“检查能力”不等于“授权导出”。
- 导出文件默认放在临时目录或用户明确指定的目录；只有经用户明确确认的完整镜像初始化才能写入生成目录下的 `_exports/` 或 `_assets/`，并且不得自动提交 Git、自动推送远程或写回飞书。
- bot 无权访问的个人云盘或私有资源必须报告为不可见，不得切换 user OAuth 代为读取。
- 不默认覆盖本地补录、删除历史文件或推送远程 Git；这些属于需要明确确认的写入/发布动作。
- 执行前检查目标仓库、当前分支和远程地址；发现与预期不符时停止并报告。

## 日志与完成回执

终端和最终回复至少报告：

- `started`：空间、身份、配置来源和目标目录（不打印秘密）。
- `processed`：节点、文档、跳过和失败数量。
- `created/updated`：生成或更新的 Markdown、manifest、sidebar 数量。
- `skipped/failed`：失败节点、原因和是否可重试。
- `verification`：Git diff、VitePress build、抽样文档和源链接检查结果。
- `next_step`：是否需要补权限、确认 Git push 或规划双向同步。
- 文件变化只报告数量和类别，不列本地路径或文件名；身份只报告 `bot identity` / `user identity` 等非敏感状态。

## Resources

- 权限与权限申请分层：[references/permissions.yml](references/permissions.yml)
- 飞书 CLI 命令与权限申请流程：同仓库 `soia-cwork-feishu-cli/references/cli-workflows.md` 和 `soia-cwork-feishu-cli/references/permissions.md`。
- 事件订阅与增量目标：[references/events.yml](references/events.yml)
- 同步策略：[references/sync-policy.yml](references/sync-policy.yml)
- 文档格式转换：[references/block-mapping.yml](references/block-mapping.yml)
- Sheet 范围镜像：[references/sheet-mirroring.yml](references/sheet-mirroring.yml)
- 富资源镜像能力与边界：[references/rich-resource-mirroring.yml](references/rich-resource-mirroring.yml)
- 表格/多维表格导出安全策略：[references/export-policy.yml](references/export-policy.yml)
- 日志与回复脱敏策略：[references/output-redaction.yml](references/output-redaction.yml)
- Git 与 VitePress 接入：[references/git-vitepress.yml](references/git-vitepress.yml)
- 私有配置模板：[assets/config.example.yml](assets/config.example.yml)

## Validation

```bash
python3 scripts/sync_feishu_wiki.py --help
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --dry-run
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --validate-only
git diff --check
```

### Forward test

Before a real sync, run a dry-run or a small authorized representative scope and verify the tree, stable node-ID mapping, ordering, incremental selection, asset references, and failure receipt. After every write, require the built-in validation gate to pass; a zero exit code alone is not evidence that the mirror is complete.
