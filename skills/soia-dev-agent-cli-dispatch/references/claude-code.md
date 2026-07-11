# Claude Code 执行规范 / Claude Code rules

## 模式选择

- **批处理 / 自动化**：优先 `claude --print`
- **结构化结果**：优先 `--output-format json` 或 `stream-json`
- **最小权限控制**：显式设置 `--permission-mode`
- **交互式会话**：仅在确需人工连续交互时才直接进入 TUI

## 模型分级

> ⚠️ 下表模型名称仅供参考，具体可用档位请以 `claude --help` / 你账号可用的模型列表为准；模型代号会随时间推移而变化。

| 场景 | 模型（示例档位） | 定位 |
|------|------|------|
| 调度 / 代码审查 / 计划拆分 / 复杂推理 | 高阶推理档（thinking=high） | 派发子 agent、审 PR、规划提案、复杂 bug 定位 |
| 代码编写 / 中等任务 | 中阶档 | UI 编辑、文档改写、中型重构，作为高阶档的节流替代 |
| 轻量 Edit / Read / Grep | 轻量档 | 一次性小改、快速查阅 |

## 推荐命令模板

### 1. 一次性批处理

```bash
claude --permission-mode bypassPermissions --print "Summarize the refactor plan for this module"
```

适用：

- 单轮任务。
- 需要避免 PTY/TUI 交互。

### 2. 结构化 JSON 输出

```bash
claude --permission-mode bypassPermissions --print --output-format json "Review this diff and return findings"
```

### 2.1 从文件安全传入长 prompt（推荐）

```bash
python3 scripts/run_claude_prompt.py \
  --prompt-file <prompt-file> \
  --permission-mode dontAsk \
  --tools Read,Grep,Glob \
  --model <model-id> \
  --effort high \
  --output-format json
```

脚本通过 stdin 传 prompt，正文不会进入 shell 插值、命令行参数或进程列表。若不用脚本而把文件内容作为位置参数传给 Claude，必须加参数终止符：

```bash
claude --permission-mode dontAsk --print --output-format json -- \
  "$(< "<prompt-file>")"
```

prompt 可能以 YAML `---` 或单个 `-` 开头；省略 `--` 会被 Claude CLI 当成未知选项。长 prompt 优先使用 stdin 脚本，不用位置参数方案。

### 3. 流式 JSON 输出

```bash
claude --permission-mode bypassPermissions --print --output-format stream-json "Run the tests and explain failures"
```

### 4. 继续当前目录最近会话

```bash
claude --continue
```

适用：

- 需要在同目录续接最近一次 Claude Code 会话。

## 关键约束

- 默认推荐 `--print`，因为它更适合自动化编排、减少 PTY/TUI 交互开销。
- `--permission-mode bypassPermissions` 只在你已经明确接受该工作目录的改动风险时使用。
- 若任务只需要分析，不应默认放大到可编辑会话。
- 若要结构化消费输出，必须显式带 `--output-format`。
- 从文件传入 prompt 时优先用 `scripts/run_claude_prompt.py`；不得用缺少 `--` 的 `"$(cat prompt.txt)"` 位置参数写法。
- `--output-format json` 会在长任务结束时一次性返回结果，数分钟无 stdout 不等于卡死。设置足够的 timeout（脚本默认 900 秒），并用进程存活/CPU/最终 exit code 判断，不要仅因暂时无输出重复派发。
- `--tools Read,Grep,Glob` 只限制模型可调用的工具，不能禁用 Claude Code 本机 hooks。hooks 仍可能写会话日志；要求“文件系统零写入”时，应先检查 hooks，在中性工作目录运行，并对调用前后 `git status` 做差分，不能只凭 tool allowlist 声称完全只读。
