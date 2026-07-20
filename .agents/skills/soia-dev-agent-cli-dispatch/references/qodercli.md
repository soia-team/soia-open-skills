# qodercli 执行规范 / qodercli rules

> **注意**：实际命令是 `qodercli`（安装路径 `~/.local/bin/qodercli`），不是 `qoder` 或 `qoder chat`。

## 模式选择

- **自动化编码任务（跳过权限）**：`qodercli -p '<prompt>' --dangerously-skip-permissions`
- **极简无确认**：`qodercli -p '<prompt>' --yolo`
- **指定模型**：`--model auto | efficient | performance | ultimate`（⚠️ 具体档位名请以 `qodercli --help` 或官方文档实际支持列表为准）
- **限制 turn 数**：`--max-turns N`（防止无限循环）

## 推荐命令模板

### 1. 标准自动化执行

```bash
cd /path/to/project
qodercli -p "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")" --dangerously-skip-permissions
```

适用：

- 自动化编码任务，无需人工确认每步。
- 已明确接受工作目录内的改动风险。

### 2. 指定模型与 turn 限制

```bash
qodercli -p "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")" --dangerously-skip-permissions \
  --model performance --max-turns 20
```

适用：

- 需要更强推理能力的任务（用 performance / ultimate）。
- 需要防止任务超时无限循环（用 --max-turns）。

### 3. 极简 yolo 模式

```bash
qodercli -p "简单删除/写文件任务" --yolo
```

适用：

- 简单低风险任务（删除文件、写配置）。
- 需要最低摩擦的执行。

## 关键约束

- `qodercli` 是 headless CLI agent，不是 GUI 编辑器入口。
- 必须先 `cd` 到目标工作目录，或在 prompt 中明确指明路径。
- 含特殊字符的 prompt 必须通过 temp 文件传入（见 Prompt 注入防护）。
- 不要把你的 AI 工具配置目录（如 `~/.claude/`、`~/.codex/` 等）作为工作目录。
