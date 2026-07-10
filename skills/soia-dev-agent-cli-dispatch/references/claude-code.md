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
