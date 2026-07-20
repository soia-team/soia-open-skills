# Codex 执行规范 / Codex rules

## 模式选择

- **交互式编码会话**：使用 `codex`，放在 PTY 会话中运行。
- **一次性批处理**：使用 `codex exec`。
- **差异评审**：使用 `codex review`。
- **去沙箱全权限（常见默认候选）**：`--dangerously-bypass-approvals-and-sandbox`（注意：`--full-auto` 与此互斥，两者只能二选一，按你的编排约定选定后固定使用）。
- **多 Agent 并行**：`[features] multi_agent = true` 只适用于当前 Codex runtime 确实有可用 thread/collaboration 上下文的场景。外部 `codex exec` 不得仅因全局开关已启用就假设能 spawn；先做 capability probe。
- **去沙箱全权限模式**：`--dangerously-bypass-approvals-and-sandbox` — 仅在用户已明确同意（系统级或本次任务级授权）时使用；不要把它当成无需确认的默认状态。

## 模型分级

> ⚠️ 下表模型名称与版本号仅供参考，请以 `codex --version` 及 CLI 自身模型列表的实际输出为准；版本号会随时间推移而过期。

| 场景 | 模型（示例） | 使用规则 |
|------|------|----------|
| 新增 / 难任务 / 高风险变更 | 最新旗舰模型 + high reasoning | 复杂任务首选 |
| 复杂代码编辑（默认候选） | 编码专用模型 + high reasoning | 常见编码主力 |
| 代码审核 / diff review / evidence 验证 | 审查向模型 + high reasoning | 常见审查与证据验证主力 |

Codex CLI 支持 `-m/--model`；reasoning effort 通过 `-c model_reasoning_effort="high"` 指定。

## 推荐命令模板

### 1. 交互式会话（PTY）

```bash
codex
```

适用：

- 需要多轮交互。
- 需要 agent 在工作目录中持续探索和改动。

### 2. 一次性批处理

```bash
codex exec "Implement the approved patch and explain the changes"
```

适用：

- 单次任务。
- 需要脚本化收集最终结果。

### 3. 去沙箱全权限（常见默认候选）

```bash
codex exec -m <model> -c model_reasoning_effort="high" \
  --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
  "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")"
```

适用：

- 已明确授权，任务边界清晰、风险可控。
- ⚠️ `--full-auto` 与 `--dangerously-bypass-approvals-and-sandbox` 互斥，按你的编排约定二选一（多数场景选后者）。

### 4. 差异评审

```bash
codex review -m <model> -c model_reasoning_effort="high" --base main
```

适用：

- 评审当前分支相对基线的差异。
- 输出 pre-landing 风险意见。

### 5. 新增 / 难任务 / 高风险变更

```bash
codex exec -m <model> -c model_reasoning_effort="high" \
  --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
  "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")"
```

适用：

- 新增核心能力、跨模块重构、高风险修复。
- 需要更强复杂推理或更高一次通过率的任务。

## 非 git 目录

有些项目根目录本身不是 git repo（例如某些多仓库编排层的根目录，或临时工作区）。执行 `codex exec` 时，若报错 `Not inside a trusted directory`，可以加 `--skip-git-repo-check` 绕过检查：

```bash
codex exec -m <model> -c model_reasoning_effort="high" \
  --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
  "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")"
```

**但仍强烈建议在真实 git 仓库根目录（包括 `git worktree` 创建的工作树）内运行 codex**，不要把“加了 `--skip-git-repo-check` 就能在任意目录跑”当成默认做法：

- 实测发现，仅依赖这个参数在部分场景下表现并不符合预期（例如某些沙箱/权限组合下行为不一致）。建议自行复核实际产物，不要只看参数是否已加、退出码是否为 0。
- 优先做法：在真实 git 仓库（或其 worktree）内运行；只有确认目录不受信任检查影响、且已复核过实际行为时，才把 `--skip-git-repo-check` 当作退路使用。

## 退出码约定

`codex exec` 的退出码 **不能单独作为成功的证据**：

- 实测出现过“报错 `Not inside a trusted directory` 但退出码仍是 `0`”的假成功案例——如果只看 exit code，会误判任务已完成。
- 每次任务结束后，必须核对：
  1. stdout 实际内容是否包含预期的错误/警告文字（不要只看 exit code）。
  2. 产物是否真的产生：`git diff --stat`（代码类任务）或直接检查目标输出文件是否存在、内容是否符合预期。
- 只有“exit code 为 0 + stdout 无异常 + 产物核实存在”三者同时成立，才能判定本次执行成功。

## 外部 exec 的多 Agent 降级边界（2026-07-11 实测）

- 外部 `codex exec` 即使读到 `multi_agent=true`，也可能没有可派生的 thread；实测表现为 spawn 返回 `no thread`，随后模型仍尝试等待，最终形成“对 0 个 agent 等待”的空转。
- 需要 SOL/Codex 只做 leader 裁决而不依赖子 agent 时，显式加 `--disable multi_agent`，并在 prompt 里写明“禁止 spawn/wait”。这不是能力降级伪装，而是把本轮角色固定为单 leader。
- 确实需要多 Agent 时先探针：必须拿到至少一个成功的 spawn receipt 与非空 agent id；spawn 失败或 agent 集合为空时立即返回 `blocked_subagent_unverified`，禁止调用 wait。
- 只读沙箱可能禁止 `mktemp`/临时测试写入；这种环境失败只能标为 `environment_blocked`，不能推断代码测试失败。由宿主在正常可写环境重新跑并单独出回执。

## Prompt 注入防护

含单引号、特殊字符的 prompt **不能**直接嵌入 `bash -c "..."` 或 `"..."` 参数，否则 shell 解析会崩溃。
**必须**先写 temp 文件，再用命令替换传入：

```bash
# 1. 把 prompt 写入临时文件（按任务 ID 隔离，避免多任务冲突）
mkdir -p "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/task-01/"
cat > "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/task-01/prompt.txt" << 'PROMPT_EOF'
你的 prompt 内容，可以包含任意引号和特殊字符...
PROMPT_EOF

# 2. 用 $() 传入 codex
codex exec -m <model> -c model_reasoning_effort="high" \
  --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
  "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/task-01/prompt.txt")"
```

**prompt 文件命名规范**：`${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt`
- 不同任务放不同子目录，避免并行派发之间 task ID 冲突
- 必须先 `mkdir -p "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<目录>/"`

## 关键约束

- 一律显式指定工作目录；如果由宿主工具支持，优先传 `-C/--cd` 或外层 `workdir`。
- 不要把 `dangerously-bypass-approvals-and-sandbox` 当默认模式。
- 需要 scratch 任务时，优先临时 git repo 或 `git worktree`。
- 若用于 review，不要在 live 主工作目录切分支污染现场。

## 实战控制规程（2026-07 云盘战役校准，七条全部有实证）

1. **actual_model 的唯一权威是会话头 `model:` 行**。codex v0.144.x 在 models cache 损坏时（症状：stderr 出现 `ERROR codex_models_manager…failed to load models cache`）自报身份失灵：五次实跑 sol/terra，回执分别自称 gpt-5.6-luna（四次）与 gpt-5（一次）；任务书写明"以会话头为准"也拦不住。主控必须自己 grep 输出中的 `model:` 行定 actual_model，并核验/修正 codex 写进产物的署名（SKILL.md `updated_by`、commit `Co-Authored-By`）。
2. **长执行进程禁止由 codex 启动**。codex exec 会话结束会杀死其子进程（四次实证：扫描器/预检器随会话退出被杀）。耗时执行（全盘扫描、批量写入、构建）一律由主控 `nohup … &` 直跑并用监控哨看护；codex 只做规划、编码、审计。
3. **完成以证据文件为准，不信叙述**。codex 曾两次以"正在运行"结束会话而进程已死。任务书要求前台同步等待+产物落盘；主控验收看文件与退出码，不看回执的过程描述。
4. **派发前主控做基线核验**。建分支前确认目标仓工作树目标文件无未提交改动、且 main 与 origin/main 对齐。实证：本地 main 曾挂着一个未推 commit，codex 基于污染基线建分支，PR 卷入无关变更，需 cherry-pick 重建。注意口径：无关的他人未提交文件**不构成阻塞**（见下条），不要把本条放大为"工作树必须全净"。
5. **无关未提交文件：列明、不 add、回执申明**。任务书写明"工作树可能存在无关未提交文件（列出或描述特征），不得 add，只提交本任务文件"；codex 完成后在回执申明"无关文件未纳入 commit"。同一脏工作树上四次派发零误提交的正面模式。
6. **heredoc 写 prompt 前必 `mkdir -p`**（两次踩坑）：目标目录不存在时 `cat > $DIR/prompt.txt` 静默失败，codex 收到空输入照样开跑。
7. **回执模板增补两行**：①原文引用会话头 `model:` 行；②"无关未提交文件未纳入 commit"申明。
