# Kimi CLI 执行规范 / Kimi CLI rules

## 基本信息

- 本机路径：`~/.local/bin/kimi`
- 版本与推荐模型：⚠️ 请以 `kimi --version` 及 CLI 自身模型列表为准；下方模型代号仅供参考，会随时间推移而过期。
- 临时定位：编码能力大致对标中阶 Claude 模型一档；具体表现请以你自己项目的基准测试为准，不要照抄本文档的定位描述。

## 模式选择

- **交互式协作**：使用 `kimi -w <workdir>`，适合需要连续追问或人工确认的任务。
- **批处理写入**：使用 `kimi -w <workdir> --print`，仅允许在独立 worktree + 明确任务边界内用于写入任务。
- **plan-only 只读评审**：使用 `kimi -w <workdir> --plan`，适合 review、方案拆分、风险检查。
- **ACP 集成**：使用 `kimi acp`，供支持 ACP 的上层编排器接入。

## 推荐命令模板

### 1. 批处理写入（常见默认候选）

```bash
kimi -w <workdir> -m kimi-k2.6 --thinking --skills-dir <your-skills-dir> \
     --print --final-message-only \
     -p "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")"
```

适用：

- 中等复杂度编码任务。
- 独立 worktree 内的明确文件范围写入。
- 已在 prompt 中列明验证命令和回写目标。

### 2. plan-only 只读评审

```bash
kimi -w <workdir> -m kimi-k2.6 --thinking --skills-dir <your-skills-dir> \
     --plan \
     -p "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/review-prompt.txt")"
```

适用：

- 只读 diff review。
- 方案拆分、风险点枚举、验收标准补齐。
- 不允许写文件的审查任务。

### 3. 显式指定 kimi-k2.6 交互模式

```bash
kimi -w <workdir> -m kimi-k2.6 --thinking --skills-dir <your-skills-dir>
```

适用：

- 需要人工持续确认的编码协作。
- 需要观察工具调用和中间判断的任务。

### 4. ACP 模式

```bash
kimi acp
```

适用：

- 由支持 ACP 的宿主编排器接管上下文和工具授权。
- 不直接用于普通批处理派发。

## 关键约束

- `kimi --print` 隐式 `--yolo`，会自动批准写入类操作。
- `--print` 只允许在独立 worktree + 明确任务边界内用于写入任务。
- 只读评审必须使用 `--plan` 或交互模式，不要用 `--print`。
- 每个写入任务必须在 prompt 中限定可改路径、不可改路径、验证命令和失败回写方式。
- prompt 必须走 `${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt`，不要把长 prompt 直接拼进 shell 字符串。

## 安全底线

- 不要在主分支、共享工作树、你自己的 AI 工具配置目录（如 `~/.ssh/`、`~/.config/`）或凭据目录运行写入任务。
- 不要把 `--print` 用作只读审查。
- 不要让 Kimi 直接 commit、push、merge；Git 确认门仍由主 agent 控制。
- 任务失败时保留 worktree 和日志，不要自动清理证据。
