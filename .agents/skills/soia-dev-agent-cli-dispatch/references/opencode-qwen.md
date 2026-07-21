# OpenCode & Qwen Code 执行规范

## OpenCode 执行规范 / OpenCode rules

### 模式选择

- **交互式本地工作台**：使用 `opencode`。
- **一次性批处理**：使用 `opencode run "<prompt>"`。
- **Headless server**：使用 `opencode serve`，留给你后续要接入的 provider 层。
- **浏览器工作台**：使用 `opencode web`，适合人工观察会话与状态。
- **Provider / model 管理**：使用 `opencode providers`、`opencode models`。

### 推荐命令模板

#### 1. 一次性批处理

```bash
cd /path/to/project
opencode run "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")"
```

适用：

- 单次编码/分析任务。
- 需要脚本化收集最终结果。

#### 2. 指定 provider / model

```bash
cd /path/to/project
opencode run --model openai/gpt-5 "Review this diff and list the top 5 risks"
```

适用：

- 需要强制模型来源。
- 你的编排层要显式控制路由时。

#### 3. 起 headless server

```bash
cd /path/to/project
opencode serve --hostname 127.0.0.1 --port 4096
```

适用：

- 后续把 OpenCode 接入为外层调度器的执行面。
- 需要长期会话和外部控制时。

#### 4. 起 web 界面

```bash
cd /path/to/project
opencode web
```

适用：

- 人工观察会话、模型状态和导出内容。
- 临时 UI 调试，不适合作为自动化主链。

### 关键约束

- `opencode` 默认更像工作台/服务壳，不要把它误当成纯 CLI 批处理器。
- 建议默认只用 `opencode run`，`serve/web` 作为后续 provider 能力预留，不要默认开启。
- 需要结构化会话资产时，优先配合 `opencode export` / `opencode import`。
- `opencode` 的工作目录必须指向真实项目根，不要在配置目录、家目录运行。

---

## Qwen Code 执行规范 / Qwen Code rules

> **注意**：实际命令是 `qwen`，不是 `qwencode`。

### 模式选择

- **交互式会话**：使用 `qwen`。
- **一次性 headless 任务**：使用 `qwen "<prompt>"`。
- **交互式启动并预注入 prompt**：使用 `qwen -i "<prompt>"`。
- **Qwen 认证管理**：使用 `qwen auth`。
- **MCP / hooks / channels 扩展**：使用 `qwen mcp`、`qwen hooks`、`qwen channel`。

### 推荐命令模板

#### 1. 一次性批处理

```bash
cd /path/to/project
qwen "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")"
```

适用：

- 中短任务。
- 希望直接走 Qwen 模型栈。

#### 2. 指定模型

```bash
cd /path/to/project
qwen -m qwen-max "Summarize this module and propose refactor steps"
```

适用：

- 需要绑定 Qwen 侧模型档位（⚠️ 具体模型名请以 `qwen models` 或官方文档实际支持列表为准）。
- 需要让你自己的 `qwen-cli` provider 显式指定模型。

#### 3. 带初始 prompt 的交互式会话

```bash
cd /path/to/project
qwen -i "Read the current workspace and prepare a review plan"
```

适用：

- 先注入任务，再进入持续交互。
- 需要人工介入追问时。

### 关键约束

- `qwen` 更适合做 Qwen 模型族入口，不适合作为你工作流状态的真源。
- 需要认证前先跑 `qwen auth`，不要把认证问题误判为模型问题。
- 当前默认把 `qwen` 视为 coding/review agent，不把它当系统级调度器。
- 涉及 messaging channel 的能力时，你的编排层只接其执行面，不接其状态真源。
