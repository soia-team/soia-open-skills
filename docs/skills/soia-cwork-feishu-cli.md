# soia-cwork-feishu-cli

> 通过飞书官方 lark-cli 以最小权限只读调研 Wiki、Drive 与文档

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-cwork-feishu-cli) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「调研飞书知识库」「读取飞书云盘」「配置飞书 CLI」

## 能力与用法

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
~/.config/soia-skills/soia-cwork-feishu-cli/config.yml
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

## 安装

本技能随 `soia-cwork-office` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-cwork-office@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-cwork-office@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-cwork-office-skills -g -a '*' -s soia-cwork-feishu-cli -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
