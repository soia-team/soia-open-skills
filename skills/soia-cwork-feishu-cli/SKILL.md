---
name: soia-cwork-feishu-cli
description: 通过飞书官方 lark-cli 以应用凭证（bot）方式读取和分析企业工作场景中的飞书云文档、云盘、知识库、评论、权限与元数据；先按机器可读权限目录提醒最小 tenant scope、应用数据权限和版本发布流程，再完成只读调研。当用户要求调研飞书工作知识库、盘点知识库/云盘、读取飞书文档或配置飞书 CLI 时使用。
---

# soia-cwork-feishu-cli

使用飞书官方 `lark-cli` 连接用户明确授权的飞书应用，以 bot 身份优先执行只读盘点、搜索和文档分析。默认不修改飞书远端内容；写入、移动、删除、权限变更、发送消息和导出个人数据都必须单独确认。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 调研飞书云盘和知识库使用情况 | 检查应用身份、可见空间、节点树、文档类型、文件与权限元数据 | 结构化盘点、已访问范围、不可见范围和证据命令 |
| 读取、总结或比较飞书文档 | 先识别 URL 类型，再按 `lark-doc` 规则读取正文和大纲 | 文档摘要、引用位置、格式和权限限制 |
| 搜索飞书知识库、文档和云盘 | 使用 Drive Search 或 Wiki 节点查询，不猜 token 和参数 | 命中文档、标题、类型、空间和下一步读取范围 |
| 安装或修复飞书 CLI | 安装官方 CLI，配置应用凭证，检查 token、身份、scope 和连通性 | 命令输出摘要；绝不打印 App Secret 或 access token |

### 客户如何使用

可以直接说：

- “用飞书 CLI 盘点我可见的知识库层级和云盘文档类型。”
- “读取这个飞书 Wiki 页面，判断它更适合迁移到哪个开源本地部署产品。”
- “检查飞书应用当前能看到哪些知识空间和文档，不要修改任何内容。”

执行前解析 `source`、`target`、`scope`、`as` 和 `output`。对本技能的调研任务，默认 `as=bot`、`read_only=true`、`dry_run=true`（涉及写操作时）；不要因为 bot 看不到用户个人资源就静默改用用户 OAuth。

### 依赖与安装

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| Node.js/npm 或可运行 npx 的环境 | 强依赖 | 安装 Node.js 后运行 `npx @larksuite/cli@latest install` | 停止并说明需要安装 Node.js/npm |
| 官方 `lark-cli` | 强依赖 | `npx @larksuite/cli@latest install`；按需安装官方配套 skills：`npx skills add larksuite/cli -g -y` | 只可做公开资料调研，不能声称已读取用户飞书 |
| 飞书应用凭证 | 强依赖 | 使用 `profile add` 或本技能脚本写入 provider-owned CLI 配置 | 停止远端调研；不要要求用户把 Secret 发到聊天里 |
| 飞书应用已开通的 API 权限 | 强依赖 | 在飞书开放平台开通所需 scope；优先只读权限 | 记录缺少的 scope 和官方控制台链接 |

安装后先运行：

```bash
lark-cli doctor
lark-cli profile list
lark-cli auth status --json --verify
lark-cli whoami
```

### 权限开通与应用发布

在首次调研前，或 CLI 返回 `missing_scopes` 时，先读取[机器可读权限目录](references/permissions.yml)，再按[权限开通指南](references/permissions.md)向客户解释申请流程。应用凭证模式只申请 tenant scope；不要把 user OAuth scope 当成 bot 权限，也不要为了读取而申请写入、删除、上传或成员管理权限。

开放平台入口按私有配置中的 `LARK_APP_ID` 拼接：

```text
https://open.feishu.cn/app/<APP_ID>/auth
```

必须完成完整闭环：在“开发配置 → 权限管理”按目标 API 的权限要求开通并保存 → 检查 tenant 应用数据权限和资源可见范围 → 对需审核权限创建版本并提交线上发布 → 等企业管理员审核通过 → 重新运行 `setup_app_credentials.py --use`、`auth status --json --verify` 和代表性只读命令。免审权限可直接测试；“审核中”不视为权限已正式生效。

每次向客户回执权限时，分成“必需”“可选”“不要默认开通”三类，并列出缺失 scope、官方控制台入口和发布步骤；不要把客户的真实 App ID 写进公共技能文件。

### 应用凭证登录（bot 模式）

本技能采用用户指定的应用凭证方式，不调用 `lark-cli auth login` 的用户 OAuth 流程。应用凭证只获得 bot 身份：它只能读取应用可见、被授予应用访问权或租户策略允许访问的资源；它不能自动代表用户读取个人知识库、个人云盘或私有文档。

推荐把凭证放在技能专属私有配置，不提交仓库、不写入 vault：

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-feishu-cli/config.yml
SOIA_CWORK_FEISHU_CONFIG_FILE=<custom-config-path>
```

配置示例见 [assets/config.example.yml](assets/config.example.yml)。配置只允许出现占位符或用户自己的本地值：

```yaml
version: 1
env:
  LARK_APP_ID: "<YOUR_APP_ID>"
  LARK_APP_SECRET: "<YOUR_APP_SECRET>"
  LARK_PROFILE: "feishu-reader"
  LARK_BRAND: "feishu"
```

使用配置初始化应用 profile 时，脚本通过 stdin 传递 Secret，不把 Secret 放进进程参数或日志：

```bash
python3 <skill-path>/scripts/setup_app_credentials.py
```

如需将新 profile 切换为默认 profile，必须显式使用：

```bash
python3 <skill-path>/scripts/setup_app_credentials.py --use
```

等价的手工方式是：

```bash
printf '%s' '<YOUR_APP_SECRET>' | lark-cli profile add \
  --name feishu-reader \
  --app-id '<YOUR_APP_ID>' \
  --app-secret-stdin \
  --brand feishu
```

不要把 `LARK_APP_SECRET` 放进 shell 历史、命令行参数、日志、提交记录或飞书文档。`auth login` 是用户 OAuth 授权，不是本技能的应用凭证登录方式。

### 只读调研工作流

1. **检查身份和范围**：先读取[机器可读权限目录](references/permissions.yml)，必要时读取[权限开通指南](references/permissions.md)；运行 `lark-cli auth status --json --verify`、`lark-cli whoami`；记录 identity、profile、token 状态和非敏感 scope，不输出密钥。
2. **读取匹配的官方嵌入技能**：运行 `lark-cli skills read lark-shared`；涉及云盘、Wiki 或正文时，再分别读取 `lark-drive`、`lark-wiki`、`lark-doc` 的对应说明。不要凭 `--help` 猜参数。
3. **盘点知识库**：确认应用已开启机器人能力，并且知识库管理员已授权应用；优先运行 `lark-cli wiki +space-list --as bot --page-all --format json`；对返回的每个 `space_id` 运行 `lark-cli wiki +node-list --as bot --space-id <SPACE_ID> --page-all --format json`。个人库 `my_library` 只能用 user 身份，bot 看到它不可见是预期行为。
4. **盘点云盘和文档**：用 `lark-cli drive +search --as bot --query '' --doc-types doc,docx,sheet,bitable,file,folder,wiki,slides --format json`，必要时按空间、文件夹、时间或类型缩小范围。
5. **读取文档**：先用 `lark-cli drive +inspect --as bot --url '<URL>' --format json` 解析真实类型和 token；再按 `lark-doc` 说明使用 `lark-cli docs +fetch --as bot --doc '<URL-or-token>' --scope outline|full --doc-format markdown --format json`。
6. **分析迁移需求**：只基于已读到的结构、类型、附件、权限和协作痕迹判断目标产品；把“看到的”“推断的”“未验证的”分开写。
7. **验证**：对关键数量重新分页核对；抽取代表性文档；检查 bot 不可见的个人资源并单列为缺口；若 API 要求应用数据权限，单独核对其数据范围。不要把一次搜索结果当成全量清单。

详细命令和产品边界见 [references/cli-workflows.md](references/cli-workflows.md)。

### 写操作与风险边界

- 默认只读：搜索、列空间、列节点、读取正文、查看元数据、查看评论和权限。
- 创建、编辑、评论、上传、移动、复制、导出、下载、公开分享、成员管理、删除、回滚和发送消息都属于写入或敏感数据动作；先展示目标、范围、命令和影响，等待用户明确确认。
- 遇到 CLI 返回 `confirmation_required`，不要静默追加 `--yes`；把高风险动作交给用户确认。
- 遇到缺 scope，优先按错误中的 `console_url` 和缺失 scope 处理；不要为了绕过 bot 限制切换用户 OAuth。
- 不读取浏览器 Cookie、密码、浏览器 profile、keychain 原始内容或未由用户提供的 token 存储。

### 日志与完成回执

每次运行至少报告：

- `started`：CLI 版本、profile 名称、bot/user 身份、非敏感 scope 和调研范围；不打印 Secret。
- `processed`：空间、节点、文件或文档数量，以及分页是否完整。
- `created/updated`：默认写“未改动远端”；若有用户确认的写入，列出实际对象和结果。
- `skipped/failed`：权限不足、bot 不可见、分页上限、解析失败和原因。
- `verification`：运行过的 status、schema、分页、抽样读取和备份/导出检查。

推荐回执：

```markdown
完成：<一句话说明本次飞书调研或配置结果>。

日志摘要：
- started: <profile / identity / 非敏感范围>
- processed: <空间、节点、文档或文件数量>
- created/updated: 未改动远端 / <已确认的写入结果>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <运行过的 CLI 检查、分页核对、抽样读取>

问题与下一步：
- <缺 scope、bot 不可见资源、需要用户授权或无>
```

## 资源

- 配置示例：[assets/config.example.yml](assets/config.example.yml)
- CLI 工作流：[references/cli-workflows.md](references/cli-workflows.md)
- Provider 选择和凭证边界：[references/providers.md](references/providers.md)
- 权限事实源：[references/permissions.yml](references/permissions.yml)
- 权限申请流程：[references/permissions.md](references/permissions.md)
- 应用凭证初始化脚本：`scripts/setup_app_credentials.py`

## 验证

```bash
python3 <skill-path>/scripts/setup_app_credentials.py --help
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py <skill-path>
```

仓库级验证由 `soia-open-skills/AGENTS.md` 规定，至少运行单元测试、技能目录生成检查、技能审计和 `git diff --check`。

### 前向测试

复杂调研或权限变更前，先用脱敏 fixture 或客户明确授权的代表性只读对象执行一次前向测试：核对权限提示、bot 身份、数量分页、失败分类和最终回执；不得把命令成功退出当成内容完整性的证据。
