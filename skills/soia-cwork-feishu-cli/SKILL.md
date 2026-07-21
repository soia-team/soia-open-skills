---
name: soia-cwork-feishu-cli
description: 通过飞书官方 lark-cli 分开调研飞书知识库/Wiki与云盘/Drive，按应用身份（bot）或用户 OAuth 身份执行最小权限只读操作；先按机器可读权限目录提醒两类身份的 scope、应用数据权限、资源授权和版本发布流程。当用户要求调研飞书知识库、云盘、个人云盘、读取飞书文档或配置飞书 CLI 时使用。
version: 1.0.0
created_at: 2026-07-14 15:26:13
updated_at: 2026-07-21 09:40:25
created_by: claude opus 4.6
updated_by: Claude Fable 5
---

# soia-cwork-feishu-cli

使用飞书官方 `lark-cli` 连接用户明确授权的飞书应用，按“知识库/Wiki”和“云盘/Drive”分开执行只读盘点、搜索和文档分析。默认使用应用身份 bot；只有用户明确要求访问个人云盘、个人知识库或私有资源时，才走用户 OAuth。默认不修改飞书远端内容；写入、移动、删除、权限变更、发送消息和导出个人数据都必须单独确认。

## 场景分流：知识库与云盘不能混用

| 场景 | 默认身份 | 主要对象 | 用户 OAuth 何时使用 | 详细规则 |
|---|---|---|---|---|
| 知识库 / Wiki | bot | 知识空间、Wiki 节点、Wiki 文档 | 用户明确要求个人知识库或 bot 不可见的私有知识库 | [wiki-workflow.md](references/wiki-workflow.md) |
| 云盘 / Drive | bot | 共享文件夹、应用可见文档、文件元数据 | 用户明确要求“我的云盘 / 我的文件夹 / 个人文档” | [drive-workflow.md](references/drive-workflow.md) |

不要把 Wiki 的空间/节点接口当作云盘目录，也不要把 bot 的空搜索结果解释为用户个人云盘为空。

## 两种权限类型：是否需要同时申请

飞书对同一个 API 能力按调用身份分别管理权限：

- **应用身份权限**：`tenant_access_token`，运行时是 `bot`。在“应用身份权限”页签申请；还要配置应用数据权限、可用范围或把应用加入目标知识库/文件夹。
- **用户身份权限**：`user_access_token`，运行时是 `user`。在“用户身份权限”页签申请；再由用户执行 `lark-cli auth login` 完成 OAuth，访问范围跟随登录用户。

如果目标是“Bot 读取企业知识库 + 用户 OAuth 读取个人云盘”，需要在两个页签分别申请对应的最小只读 scope。只使用其中一种身份时，不要重复申请另一种权限。具体清单以 [permissions.yml](references/permissions.yml) 的 `identity_modes` 为准。

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

在首次调研前，或 CLI 返回错误时，先读取[机器可读权限目录](references/permissions.yml)和[错误目录](references/errors.yml)，再按[权限开通指南](references/permissions.md)向客户解释申请流程。先判断目标是知识库还是云盘，再判断使用 bot 还是 user OAuth；不要把 user OAuth scope 当成 bot 权限，也不要为了读取而申请写入、删除、上传或成员管理权限。

开放平台入口按私有配置中的 `LARK_APP_ID` 拼接：

```text
https://open.feishu.cn/app/<APP_ID>/auth
```

必须完成完整闭环：在“开发配置 → 权限管理”按目标 API 的权限要求开通并保存 → 检查 tenant 应用数据权限和资源可见范围 → 对需审核权限创建版本并提交线上发布 → 等企业管理员审核通过 → 重新运行 `setup_app_credentials.py --use`、`auth status --json --verify` 和代表性只读命令。免审权限可直接测试；“审核中”不视为权限已正式生效。

每次向客户回执权限时，分成“必需”“可选”“不要默认开通”三类，并列出缺失 scope、官方控制台入口和发布步骤；不要把客户的真实 App ID 写进公共技能文件。

### 应用凭证登录（bot 模式）

应用凭证是本技能的默认登录方式，不调用 `lark-cli auth login` 作为默认流程。应用凭证只获得 bot 身份：它只能读取应用可见、被授予应用访问权或租户策略允许访问的资源；它不能自动代表用户读取个人知识库、个人云盘或私有文档。

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

首次初始化或本机 profile 不存在时，使用 `--use` 让它成为当前 profile：

```bash
python3 <skill-path>/scripts/setup_app_credentials.py --use
```

刷新已有 profile 的 App Secret、App ID 或 brand 时，必须由用户明确发起，再使用：

```bash
python3 <skill-path>/scripts/setup_app_credentials.py --replace --use
```

由于 lark-cli 不允许同一个 App ID 同时存在于两个 profile，刷新会先删除旧 profile，再写入新 profile；因此只有在私有配置已确认无误、且用户明确要求刷新时才执行。若写入失败，需要检查私有配置后重新运行初始化。完成后验证：

```bash
lark-cli profile list
lark-cli auth status --json --verify
lark-cli whoami
lark-cli doctor
```

若出现 `invalid_client`、错误码 `20140` 或 “The auth method is not supported.”，这属于 profile/应用凭证认证失败，不是缺少 scope；先按 [errors.yml](references/errors.yml) 修复 profile，再检查权限。

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

不要把 `LARK_APP_SECRET` 放进 shell 历史、命令行参数、日志、提交记录或飞书文档。`auth login` 是用户 OAuth 授权，只能在用户明确要求个人资源或明确指定 `--as user` 时使用。

### 用户 OAuth 登录（仅个人资源）

用户明确要求个人云盘、个人知识库或私有资源时，先读取对应的 [wiki-workflow.md](references/wiki-workflow.md) 或 [drive-workflow.md](references/drive-workflow.md)，确认用户身份 scope，再使用 split-flow：

```bash
mkdir -p "${TMPDIR:-/tmp}/soia-cwork-feishu-cli"
lark-cli auth login --scope "<minimal-user-scopes>" --no-wait --json
lark-cli auth qrcode '<verification_url>' --output "${TMPDIR:-/tmp}/soia-cwork-feishu-cli/feishu-user-oauth.png"
```

把授权链接和二维码交给用户后结束本轮；用户确认完成后，由 agent 执行 `lark-cli auth login --device-code <device_code>`，再检查 `auth status --json --verify` 是否为 `user: ready`。不要把用户 OAuth 当成 bot 修复手段，也不要在用户未明确要求时静默切换身份。

认证链路必须区分：

- `lark-cli auth login`：官方 CLI 的用户身份 OAuth/device flow，完成后才会出现 `user: ready`。
- `https://accounts.feishu.cn/oauth/v1/device/verify?...`：CLI device flow 的验证入口。若它跳转到 `open.feishu.cn/page/scope-authorization` 并显示“已提交申请，正在审核中”，表示应用的用户身份 scope 或应用版本尚未生效；这不是用户已经完成登录。
- `https://open.feishu.cn/open-apis/authen/v1/user_info`：登录完成后的“获取用户信息” API，需要已有 `user_access_token`，不能当作登录入口。
- 自建网页应用若自行实现 OAuth，使用官方授权码接口 `/open-apis/authen/v1/authorize`，配置 `redirect_uri` 后交换 `user_access_token`；不要为了 CLI 任务手工拼接该 URL，CLI 已经用 device flow 封装。

同一个 App ID 既可以产生 Bot 的 `tenant_access_token`，也可以作为 OAuth 客户端产生用户的 `user_access_token`；页面显示应用名称相同不能证明当前是 Bot 或 User。以 `auth status --json --verify` 的 `identities.bot` / `identities.user` 和命令的 `--as` 为准。

### 只读调研工作流

1. **检查身份和范围**：先读取[机器可读权限目录](references/permissions.yml)，必要时读取[错误目录](references/errors.yml)和[权限开通指南](references/permissions.md)；运行 `lark-cli auth status --json --verify`、`lark-cli whoami`；记录 identity、profile、token 状态和非敏感 scope，不输出密钥。
2. **读取匹配的官方嵌入技能**：运行 `lark-cli skills read lark-shared`；知识库任务读取 `lark-wiki`，云盘任务读取 `lark-drive`，正文任务再读取 `lark-doc`。不要凭 `--help` 猜参数。
3. **盘点知识库/Wiki**：按 [wiki-workflow.md](references/wiki-workflow.md) 选择身份；bot 运行 `wiki +space-list` / `wiki +node-list`，user 仅在用户明确授权后运行对应的 `--as user` 命令。个人库 `my_library` 只能用 user 身份。
4. **盘点云盘/Drive**：按 [drive-workflow.md](references/drive-workflow.md) 选择身份；bot 运行 Drive 搜索只能覆盖应用可见资源，个人云盘必须明确 OAuth 后运行 `--as user`。
5. **读取文档**：先用对应身份运行 `lark-cli drive +inspect --as <bot|user> --url '<URL>' --format json` 解析真实类型和 token；再按 `lark-doc` 说明使用对应身份的 `docs +fetch`。
6. **分析迁移需求**：只基于已读到的结构、类型、附件、权限和协作痕迹判断目标产品；把“看到的”“推断的”“未验证的”分开写。
7. **验证**：对关键数量重新分页核对；抽取代表性文档；检查 bot 不可见的个人资源并单列为缺口；若 API 要求应用数据权限，单独核对其数据范围。不要把一次搜索结果当成全量清单。

详细命令和产品边界见 [references/cli-workflows.md](references/cli-workflows.md)。

### 写操作与风险边界

- 默认只读：搜索、列空间、列节点、读取正文、查看元数据、查看评论和权限。
- 创建、编辑、评论、上传、移动、复制、导出、下载、公开分享、成员管理、删除、回滚和发送消息都属于写入或敏感数据动作；先展示目标、范围、命令和影响，等待用户明确确认。
- 遇到 CLI 返回 `confirmation_required`，不要静默追加 `--yes`；把高风险动作交给用户确认。
- 遇到 `invalid_client` / `20140`，不要把它归类为缺 scope，也不要先申请权限；先修复应用凭证 profile。
- 遇到缺 scope，优先按错误中的 `console_url` 和缺失 scope 处理；不要静默切换用户 OAuth，只有用户明确要求个人资源或明确指定 `--as user` 时才启动 OAuth。
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
- 知识库/Wiki 工作流：[references/wiki-workflow.md](references/wiki-workflow.md)
- 云盘/Drive 工作流：[references/drive-workflow.md](references/drive-workflow.md)
- 常见错误事实源：[references/errors.yml](references/errors.yml)
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
