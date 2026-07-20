# Gemini CLI 执行规范 / Gemini CLI rules

## 认证通道边界

- 自 2026-06-18 起，Gemini CLI 的消费者 Google OAuth 已停止服务；浏览器
  显示认证成功后仍可能被产品服务端拒绝。消费者账号改用独立的 `agy`，见
  `antigravity-cli.md`。
- Gemini Code Assist Standard/Enterprise、Gemini API Key 和 Vertex AI 仍是
  受支持路径，继续使用 `gemini`。不得因为消费者迁移而卸载 CLI、删除配置、
  alias 到 `agy`，或改写这些通道。
- 诊断时只报告 auth 类型与状态，不读取或输出 token、API Key、OAuth URL/state
  或完整认证文件。

以下所有 `gemini` 命令模板只适用于已确认的 Standard/Enterprise、API Key
或 Vertex AI 通道；不得把它们作为消费者 Google 登录失败后的重试路径。

## 模式选择

- **交互式探索 / 长任务协作**：使用 `gemini`，并放在 PTY 会话中运行。
- **一次性批处理 / 可脚本化任务**：使用 `gemini -p`。
- **需要结构化解析**：优先 `--output-format json` 或 `--output-format stream-json`。
- **需要更强隔离**：优先 `gemini --sandbox -y -p ...`。

## 推荐命令模板

### 1. 交互式会话（PTY）

```bash
gemini
```

适用：

- 需要持续追问、反复修正 prompt。
- 需要让代理在较长周期内保持交互上下文。

约束：

- 必须放在独立 `workdir` 中运行。
- 不要在用户家目录或大而杂的根目录启动。

### 2. 一次性批处理（只读分析）

```bash
gemini -p "Analyze this codebase and propose a refactor plan"
```

适用：

- 只需要单次回答，不需要修改文件。
- 需要在后台跑、抓最终结果、减少人工介入。

### 2b. 一次性编码任务（需要写文件时的推荐做法）

```bash
gemini -p "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")" --yolo
```

适用：

- 需要修改/创建文件的编码任务。
- `--yolo` 自动批准所有工具调用（包括文件写入），等同于 Codex 的 `--dangerously-bypass-approvals-and-sandbox`。

**⚠️ 关键区别**：不带 `--yolo` 时，Gemini 需要用户确认每次工具调用。在非 PTY 管道模式下，没有 TTY 可以接收确认，导致进程卡死零输出。**编码任务必须加 `--yolo`。**

### 3. 结构化 JSON 输出

```bash
gemini -p "Summarize risks in this diff" --output-format json
```

适用：

- 需要由主代理解析结果并继续自动化处理。
- 需要稳定提取 `response / stats / error` 字段。

### 4. 流式 JSON 输出

```bash
gemini -p "Run tests and explain failures" --output-format stream-json
```

适用：

- 长任务。
- 需要流式观察进度、工具调用和最终结果。

### 5. 沙箱批处理

```bash
gemini --sandbox -y -p "Inspect the repository and report build issues"
```

适用：

- 对隔离要求更高的分析任务。
- 需要限制副作用。

约束：

- 除非任务明确需要修改文件，否则优先用沙箱模式。
- 如果任务依赖本地未挂载环境、私有工具链或交互式授权，沙箱模式可能失败。

## 退出码约定

Gemini CLI headless 执行至少要按以下退出码判断：

- `0`：成功
- `1`：一般错误或 API 失败
- `42`：输入参数错误
- `53`：turn limit exceeded

若不是 `0`：

1. 先记录命令、工作目录和退出码。
2. 判断是否属于 prompt 问题、环境问题、认证问题或任务规模过大。
3. 不要直接把失败归因为"模型不稳定"。

## 推荐使用法（仅受支持的非消费者通道）

- **Gemini 交互式任务**：走 PTY，会话可持续观察。
- **Gemini 批量分析任务**：优先 `-p` + `--output-format json`
- **Gemini 长任务监控**：优先 `-p` + `--output-format stream-json`
- **Gemini 高隔离分析**：优先 `--sandbox -y -p`

## 当前不建议的用法

- 不要在未指定 `workdir` 的情况下直接执行 `gemini`
- 不要把 Gemini 交互会话直接开在 `~`、仓库根总目录或凭据目录
- 不要把需要持续人工交互的问题误当成 `-p` 一次性任务
- 不要在需要稳定结构化消费结果时只取纯文本输出
- **不要在编码任务中省略 `--yolo`**：非 PTY 管道模式下不带 `--yolo` 会卡死（无法确认工具调用）
