# Antigravity CLI 执行规范 / Antigravity CLI rules

## 通道边界

- Antigravity CLI 的命令是 `agy`，用于承接 Gemini CLI 的消费者 Google
  OAuth 用户；它不是 `gemini` 的 alias，也不是 npm 包。
- 保留 `gemini`：Gemini Code Assist Standard/Enterprise、Gemini API Key
  和 Vertex AI 仍是独立支持通道。不得静默改变供应商、账号、模型或计费。
- 不读取、复制或打印 Gemini/Antigravity 的 token、cookie、OAuth URL/state、
  keyring 条目或完整认证文件。

官方入口：

- 消费者账号弃用：<https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals>
- 迁移指南：<https://antigravity.google/docs/gcli-migration>
- CLI 文档：<https://antigravity.google/docs/cli-overview>
- 模型与套餐：<https://antigravity.google/docs/models>、<https://antigravity.google/docs/plans>
- 官方仓库：<https://github.com/google-antigravity/antigravity-cli>

执行时重新读取这些官方资料和 `agy --help`；不要把本文的版本、参数或路径
当成永远不变的事实。

## 安装、版本与升级

```bash
command -v agy
agy --version
agy update
```

- macOS/Linux 的官方安装器来自
  `https://antigravity.google/cli/install.sh`，默认二进制为
  `~/.local/bin/agy`。
- 官方安装器可能配置 shell PATH/alias。通用自动化不得直接运行后声称
  “未改 profile”；需要无 profile 副作用时，使用
  `soia-dev-ai-cli-upgrade` 的隔离安装流程。
- 已安装版本使用 `agy update`。重新运行 bootstrap installer 可能只报告
  已存在，并不等于执行了升级。

## 登录与首次迁移

首次运行必须使用 PTY：

```bash
agy
```

可能出现的用户动作：

1. 系统浏览器账号选择和 Google 授权；
2. 旧 Gemini 配置/扩展/技能迁移清单；
3. 企业用户的 GCP project 连接。

遇到这些步骤时返回 `blocked_user_action`，让客户本人确认。不要代选账号，
不要把授权 URL/code 写进日志。首次迁移可能写入系统 keyring 和新配置目录，
必须以 CLI 的实际提示为准。

显式导入旧扩展的命令为：

```bash
agy plugin import gemini
```

该命令会写配置；只有客户明确批准导入范围后才能运行。不要手工复制认证文件。

## 技能与配置路径

- 全局 skills：`~/.gemini/antigravity-cli/skills/`
- workspace skills：`.agents/skills/`
- 继续读取 workspace 的 `AGENTS.md` / `GEMINI.md`；无需改名。
- MCP 全局配置：`~/.gemini/config/mcp_config.json`
- MCP workspace 配置：`.agents/mcp_config.json`

旧 workspace `.gemini/skills/` 需要由客户确认后迁到 `.agents/skills/`。
不要删除旧目录来“消除警告”。

## 模型发现与套餐边界

先运行只读发现，不要靠静态清单猜账号可用模型：

```bash
agy models
```

- `agy models` 不发送模型 prompt，但会使用当前登录态访问服务。需要登录、
  浏览器确认或账号选择时返回 `blocked_user_action`，不要把授权 URL/code 写进
  日志。
- 输出是账号、套餐和服务端状态范围内的**显示名称**。当前 CLI 没有承诺 JSON、
  稳定 alias 或固定顺序；不要把显示名自行转换成 API model id。
- 官方当前列出的基础模型是 Gemini 3.5 Flash、Gemini 3.1 Pro、Claude Sonnet
  4.6 (thinking)、Claude Opus 4.6 (thinking) 和 GPT-OSS-120b。Gemini 两个模型
  面向 Standard、Google AI Pro、Google AI Ultra 和 Enterprise；三个第三方
  模型仅列为 Google AI Ultra。以执行时官方页面和 `agy models` 为准。
- 2026-07-11 在一个已登录账号上只读观察到以下显示名称；这是回归样本，
  **不是永久全量清单，也不代表其他账号套餐**：

```text
Gemini 3.5 Flash (Medium)
Gemini 3.5 Flash (High)
Gemini 3.5 Flash (Low)
Gemini 3.1 Pro (Low)
Gemini 3.1 Pro (High)
Claude Sonnet 4.6 (Thinking)
Claude Opus 4.6 (Thinking)
GPT-OSS 120B (Medium)
```

`references/model-catalog.yml` 是 API 每 Token 价格目录，不是 Antigravity
套餐目录。不得把其中的 Gemini/Claude API 价格或 model id 复用成 `agy`
的实际扣费、稳定 alias 或自动路由候选。未做真实 prompt benchmark 前，
只能报告 `model_source=runtime_account_scoped`、原始显示名和
`billing=unknown`。

## 显式派发

当前已验证的基础命令形状：

```bash
agy -p "<prompt>"
agy --model "<exact-display-name-from-agy-models>" -p "<prompt>"
agy --sandbox --mode plan -p "<prompt>"
```

边界：

- `-p` / `--print` 是真实模型调用，可能消耗套餐额度或产生费用；运行前确认。
- `--dangerously-skip-permissions` 会自动批准工具动作，只能在客户明确授权写入
  且 workdir 隔离后使用；不得作为默认参数。
- 本技能尚未验证 `agy` 的结构化 usage、实际模型回显或价格映射。回执中
  `actual_model`、Token 和实际扣费拿不到时写 `unknown/unavailable`，不得把
  Gemini API 等价价格冒充 Antigravity 实际账单。
- 未完成付费/额度 benchmark 前，`agy` 只能显式派发，不能进入自动路由。

## 诊断回执

至少报告：

- `command_path`、`cli_version`、`update_status`；
- `auth_status`（`unknown` / `blocked_user_action` / `ok`）；
- `model_source=runtime_account_scoped`、`models_status` 和本次 `agy models`
  返回的显示名称（若已获授权并成功发现）；
- 是否发生浏览器登录、迁移提示或 PATH shadowing；
- `actual_model`、Token、费用的证据强度；
- `gemini` 旧 CLI 与非消费者认证通道是否保持不变。
