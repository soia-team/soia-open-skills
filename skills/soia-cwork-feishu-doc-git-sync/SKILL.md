---
name: soia-cwork-feishu-doc-git-sync
description: 将飞书知识库或云文档以应用身份只读同步为本地 Markdown，保留目录、来源和同步元数据，并可接入 Git、Obsidian 与 VitePress；当用户要求同步飞书知识库、备份到 Git、在本地查看或规划双向同步时使用。
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
| 规划双向同步 | 区分只读镜像、托管文档和本地补录 | 冲突/权限风险说明，不自动覆盖飞书 |

### 客户如何使用

1. 确认 `soia-cwork-feishu-cli` 已完成飞书应用凭证登录，并且机器人可以读取目标知识空间。
2. 在本机私有配置中填写知识空间 ID、输出目录和来源 URL 模板；不要把 App Secret、token 或企业私有路径提交到公开技能仓库。
3. 首次使用先执行 dry-run，核对空间、节点数量和目标目录。
4. 执行镜像同步。默认只写本地文件和同步元数据，不修改飞书内容，也不删除本地历史文件。
5. 如需检查表格导出，先做 `drive +inspect`/帮助/schema 探查；能力探查不等于授权导出。
6. 只有客户明确确认导出范围、格式、文件数和本地目录后，才调用 `drive +export` 或 `drive +export-download`。
7. 同步完成后再运行 Git diff、站点构建和必要的人工抽查。

推荐命令：

```bash
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --dry-run
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
# 如果只需要修复本地目录层级、暂时不请求飞书
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --rebuild-tree --rebuild-tree-only
# 从飞书刷新最新目录层级和兄弟节点顺序，但复用现有本地正文
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --rebuild-tree --refresh-tree-only
# 下载图片到本地镜像并把正文中的远程 URL 改成相对路径
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --incremental \
  --download-assets
```

### 三种工作模式

- `mirror`：默认模式。飞书是来源，本地生成的 `10_飞书镜像/` 不应手工编辑。
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
sync:
  mode: mirror
  prune: false
```

权限建议：首轮只申请知识库、文档只读权限。图片和附件下载是可选增强，涉及云盘/导出权限时单独申请；双向写入权限永不作为默认权限。

## 同步规则

- 只使用 `--as bot` 的应用身份读取，默认不需要用户身份 token。
- 通过 node token 遍历知识空间，使用文档 token 读取 `docx` 内容。
- 每个生成 Markdown 写入来源 URL、space ID、node token、object token、父节点和内容 hash。
- 使用 `sync-state.json` 保留 node token 到本地路径的映射；标题变化时尽量保持稳定路径，树位置由最新 `parent_node_token` 重新计算。
- `manifest.json` 和 `sync-state.json` 记录 `obj_edit_time`、`remote_updated_at`、`revision_id`，用于增量选择和审计。
- 本地单个路径组件最多 48 个字符；超长标题会保留完整标题在 frontmatter/侧边栏，并在文件夹或文件名中追加 node ID 短后缀，避免 Obsidian、macOS 和 VitePress/Rollup 路径过长。
- 同步器会把飞书导出的自定义 `figure/source/grid/callout`、媒体 token 和 XML 片段转换为可被 Markdown/VitePress 解析的形式；这只改变本地渲染，不写回飞书。
- 飞书文档引用会按 `node_token` 优先、`obj_token` 兜底解析为可点击的飞书 Wiki 链接；用户引用会保留为 `@显示名`。静态 Markdown 不复制飞书的悬浮卡片和成员头像交互，但不再错误降级为代码样式。
- 有子节点的飞书节点必须生成一个同名目录，并把正文放在目录内的同名 index Markdown：`父目录/节点名/节点名.md`；叶子节点才直接生成 `节点名.md`。不要生成同级的“同名文件 + 同名文件夹”。
- 如果飞书本身存在同名叶子与可展开节点、父子同名或同级重复可展开节点，目录/文件会追加稳定的 node ID 短后缀；这是为了避免本地文件系统发生同级冲突，manifest 仍以 `node_token` 区分真实节点。
- `--retry-failed` 会复用上次 `sync_status: ok` 的本地正文，只读取上次失败的文档；适合遇到飞书接口限流后继续补齐。
- `prune: false` 时不删除已消失节点对应的本地文件；节点会在 manifest 中标记为 deleted，避免一次权限或网络异常造成数据丢失。
- `20_本地补录/` 与 `90_同步元数据/` 不会被飞书镜像覆盖。
- `--rebuild-tree` 只迁移 `10_飞书镜像/` 内由同步器生成的旧扁平文件，不触碰 `20_本地补录/`。
- `--rebuild-tree-only` 仅复用已有 manifest 和生成文件做目录迁移，不发起飞书正文请求；如果同时启用资源本地化，仍可能只为刷新过期媒体 URL 读取含资源的文档。
- `--refresh-tree-only` 会重新读取飞书节点树和兄弟顺序，按最新 `parent_node_token` 重建本地目录和侧边栏，但复用已有本地正文；启用资源本地化时，会额外刷新仍含未本地化资源的文档；必须与 `--rebuild-tree` 一起使用。
- `manifest.json`/`sync-state.json` 的 `tree_order: feishu_node_list` 表示目录顺序来源于飞书节点列表，不是标题排序。
- 图片默认保留远程 URL；设置 `sync.download_assets: true` 或传入 `--download-assets` 后，技能会把正文中的远程图片及 `<source token="...">` 媒体块下载到 `10_飞书镜像/_assets/`，并把 Markdown/HTML/附件引用改写为相对路径，VitePress 和 Obsidian 可直接读取本地文件。
- 图片/附件本地化是显式 opt-in 的本地数据下载；不能因为用户只要求“检查图片”就下载全部素材。持久化配置中的 `sync.download_assets: true` 只能视为用户此前对该资源范围的明确授权，不得扩展为表格或多维表格导出授权。
- `sheet` 与 `bitable` 默认只生成元数据 stub，不读取表内数据。导出为 `xlsx`、`csv` 或 `base` 属于敏感数据导出，必须遵循 [references/export-policy.yml](references/export-policy.yml)：先解析和 dry-run，再展示范围并等待明确确认；不得自动写入生成镜像目录、提交 Git 或上传回飞书。
- 飞书 Markdown 导出的图片 URL 可能是短期鉴权地址；启用本地化时，默认只重新读取仍含远程图片的文档来刷新 URL，不会无条件重拉所有正文。可用 `--refresh-asset-urls` 显式打开该行为。
- 图片下载使用 URL 内容寻址文件名，重复同步会复用已有资源；可通过 `asset_workers`、`asset_timeout_seconds`、`max_asset_bytes` 限制并发、超时和单文件大小。下载失败只保留原 URL，并在 manifest 的 `assets_failed` 计数中报告，不把鉴权 URL 写入日志或清单。
- `<source token="...">` 或无 URL 的 `<img token="...">` 会调用官方 `docs +media-download`；远程 URL 不可直接读取时，需要按权限清单补充 `docs:document.media:download` 或 `drive:file:download`，并在私有配置中启用本地资源下载。没有下载权限时不得猜测本地资源已经完整。

## 安全规则

- 不在公开 skill、Obsidian vault、Markdown、Git 提交、终端输出或最终回复中写入 App Secret、access token、cookie。
- 终端日志、进度回执和最终回复不得输出本地绝对路径、具体本地文件名、操作系统用户名、用户名、密码、App Secret、access token 或私有下载 URL；统一使用脱敏占位符，只报告状态、数量和错误类别。详见 [references/output-redaction.yml](references/output-redaction.yml)。
- 不默认调用飞书创建、更新、删除接口。
- `drive +export`、`drive +export-download`、`docs +media-download` 和附件下载均属于数据导出/下载动作；用户说“看下能否导出”时只做 inspect、help、schema 或 dry-run，不得直接创建本地文件。
- 真实导出前必须明确回执来源、类型、格式、预计文件数、输出目录和 Git 追踪策略；“检查能力”不等于“授权导出”。
- 导出文件默认放在临时目录或用户明确指定的目录；不得自动落入 `10_飞书镜像/`、自动提交 Git、自动推送远程或写回飞书。
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
- 表格/多维表格导出安全策略：[references/export-policy.yml](references/export-policy.yml)
- 日志与回复脱敏策略：[references/output-redaction.yml](references/output-redaction.yml)
- Git 与 VitePress 接入：[references/git-vitepress.yml](references/git-vitepress.yml)
- 私有配置模板：[assets/config.example.yml](assets/config.example.yml)

## Validation

```bash
python3 scripts/sync_feishu_wiki.py --help
python3 scripts/sync_feishu_wiki.py --config <private-config.yml> --dry-run
git diff --check
```

### Forward test

Before a real sync, run a dry-run or a small authorized representative scope and verify the tree, stable node-ID mapping, ordering, incremental selection, asset references, and failure receipt. A zero exit code alone is not evidence that the mirror is complete.
