---
name: soia-dev-agent-cli-dispatch
description: 调用外部编码 CLI（codex/gemini/kimi/opencode/qwen 等，非 Claude Code 内置子代理）进行受控派发：任务边界拆分、独立 workdir、防注入 prompt 写法、模型分级矩阵、Worktree 审批门、Anti-Fake-Fix 三步验证。Triggers：「派活给 codex」「让 gemini 执行」「多 CLI 派发」「后台跑编码任务」等
---

# soia-dev-agent-cli-dispatch

Use this skill when you need to dispatch a coding, review, or analysis sub-task
to an external coding CLI — Codex, Gemini CLI, Kimi CLI, OpenCode, Qwen Code, or
even a separately-launched Claude Code process — instead of continuing the work
directly in the current agent session. This is about calling out to another
CLI process; it is **not** about Claude Code's own built-in sub-agents.

Do not use it when the current agent can just finish the task itself with no
external process involved, or when you only need a one-off local shell
command with no orchestration, monitoring, or prompt-injection concerns.

## 客户可读说明

### 这个技能可以做什么

调用外部编码 CLI（codex/gemini/kimi/opencode/qwen 等，非 Claude Code 内置子代理）进行受控派发：任务边界拆分、独立 workdir、防注入 prompt 写法、模型分级矩阵、Worktree 审批门、Anti-Fake-Fix 三步验证。各执行器详细命令模板在 `references/` 子目录下按需加载。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. Agent 先判断是否命中本技能，再检查依赖、配置、权限和风险动作。
3. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。
4. 执行后验证真实输出，不用“看起来成功”代替证据。
5. 最终回复必须给客户可见总结：做了什么、日志摘要、文件变化、问题和下一步。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-agent-cli-dispatch -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-agent-cli-dispatch/config.yml
SOIA_DEV_AGENT_CLI_DISPATCH_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- 强依赖、可选依赖和第三方 skill 关系必须以本 `SKILL.md` 后续的“依赖 / 前置 / 资源 / 边界”说明为准；没有写清楚时，先补说明或询问客户，不要猜。
- 第三方 skill 只能声明依赖和安装方式，不直接修改第三方 skill 文件。
- 本技能不硬绑定任何具体编排系统；文中出现的“你的编排层”指调用本技能的上层 Agent/系统，不是某个特定产品。

### 日志与完成回执

每次执行都要让客户看见过程和结果。最低回执格式：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <检查到的输入/配置/依赖，不打印秘密值>
- processed: <数量或范围>
- created/updated: <数量或路径>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <运行过的检查、命令或人工核对点>

问题与下一步：
- <缺 key / 缺依赖 / 需要客户确认 / 建议下一条命令；没有则写“无”>
```

## ⚡ 触发条件

满足任一即调用本技能（自然语言里常见的说法包括但不限于「派活给 codex」「让 gemini 执行」「多 CLI 派发」「后台跑编码任务」）：

| 条件 | 说明 |
|------|------|
| 需要把子任务交给 codex/gemini/kimi/claude/opencode/qwen 等外部 CLI 执行 | 当前 agent 不直接做，而是派给另一个编码 CLI 进程 |
| 为子 agent 生成 prompt | 需要防注入的 temp 文件写法 |
| 后台启动长任务 | 需要受控 workdir + 进度监控 |
| 多 agent 并行 | 需要制定依赖 / 分配矩阵 / 派发计划 |

**不需要调用**：自己直接执行代码任务（无派发动作）。

## 如何自查你的编码 CLI 可用性

不要假设某个 CLI 一定可服务。派发前按下面顺序自查，把结果记在你自己的可用性记录里，而不是照抄本文档里的任何示例状态（示例会过期）：

1. **CLI 是否已安装**：`which <command>` 或 `<command> --version`；版本号以实际输出为准。
2. **认证 / 套餐是否有效**：跑一次最小只读命令（如 `<command> -p "ping"` 或 `<command> auth status`），观察是否报登录失效、套餐到期或 quota 错误。
3. **上一次派发是否失败**：如果最近一次该执行器的任务返回非预期错误或反复超时，先记为暂不可服务，等你验证修复后再恢复派发。
4. **维护你自己的可用性表**：建议自建一张「执行器 / CLI 可用 / 套餐-Key 状态 / 可服务 / 备注」的表格，随你的编排层状态变化更新。

不可服务的执行器不得派发；等状态恢复、你自己验证通过后再更新记录、再派发。

## 适用 / 不适用

**适用**：
- 把一个工程任务拆给其他编码代理并行执行
- 在受控工作目录中启动长时间运行的编码任务
- 对子任务执行结果做收集、汇总和复核

**不适用**：
- 当前任务只需要一次性本地命令
- 需要立刻得到结果，无法承受异步后台执行
- 还没有明确子任务范围、工作目录和验收标准

## 核心原则

1. 先定义任务边界，再启动代理
2. 每个代理必须有独立 `workdir`
3. 长任务默认后台运行，并定期汇报进度
4. **`git worktree` 必须事先获得用户明确批准才能开**（与 commit/push/merge 同级不可逆操作门）；未经批准不得执行 `git worktree add`
5. 禁止在凭据目录、用户配置目录或未知目录直接启动编码代理
6. **所有源代码文件必须携带元数据头** → 详见 `references/metadata-header.md`
7. 未经批准的高风险操作一旦发生，必须记录在你自己的治理/审计追踪里（工单、变更日志、违规记录文档等）——记录这一步不能省略

## 执行器派发决策树

> ⚠️ 下面的模型名称、版本号和档位命名仅供参考。请以各 CLI 的 `--version` / `models` / `--help` 实际输出为准；版本号会随时间推移而过期。

```
任务类型判断
├── 简单任务（删除/写配置/简单脚本）
│   └── opencode run "..."  或  kimi -w <wt> --plan -p "..."（确认后改 --print）
│       详见 references/opencode-qwen.md / references/kimi-cli.md / references/qodercli.md
│
├── 中等任务（rsync/build/verify/小范围重构）
│   └── opencode run "..."  或  kimi -w <wt> -m kimi-k2.6 --thinking --print -p "..."
│       详见 references/opencode-qwen.md / references/kimi-cli.md / references/qodercli.md
│
├── 文档/内容写作
│   ├── gemini -p "..." (只读)
│   ├── gemini -p "..." --yolo (需要写文件)
│   └── qwen "..." / qwen -m qwen-max "..."
│       详见 references/gemini-cli.md / references/opencode-qwen.md
│
├── 中等复杂度编码 / 快速迭代
│   └── kimi -w <wt> -m kimi-k2.6 --thinking --skills-dir <your-skills-dir> --print -p "..."
│       详见 references/kimi-cli.md
│
├── 复杂代码编辑（常见默认候选）
│   └── codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check
│       详见 references/codex.md
│
├── 代码审核 / diff review / evidence 验证
│   └── codex exec ...
│       详见 references/codex.md
│
├── 新增/难任务/高风险变更
│   └── codex exec -m <model> -c model_reasoning_effort="high" ...
│       详见 references/codex.md
│
├── 调度 / 代码审查 / 计划拆分 / 复杂推理
│   └── Claude Code — 高阶推理档（thinking=high）
│       适用：派发子 agent / 审 PR / 规划提案 / 复杂 bug 定位
│       详见 references/claude-code.md
│
├── 代码编写 / 中等任务（高阶档节流替代）
│   └── Claude Code — 中阶档
│       适用：UI 编辑 / 文档改写 / 中型重构
│       详见 references/claude-code.md
│
├── 轻量 Edit / Read / Grep（超轻量）
│   └── Claude Code — 轻量档
│       适用：一次性小改 / 快速查阅
│       详见 references/claude-code.md
│
├── 大上下文分析 / 结构化输出
│   ├── gemini -p "..." --output-format json
│   ├── gemini -p "..." --output-format stream-json
│   └── claude --permission-mode bypassPermissions --print --output-format json
│       详见 references/gemini-cli.md / references/claude-code.md
│
├── 高隔离分析（沙箱）
│   └── gemini --sandbox -y -p "..."
│       详见 references/gemini-cli.md
│
└── Qwen 生态编码/评审
    └── qwen / qwen -i / qwen -m qwen-max
        详见 references/opencode-qwen.md
```

## 派发矩阵（快速查表）

| 场景 | 执行器 | 模式 | 详细规则 |
|------|-------|------|---------|
| 简单任务 | opencode / kimi | `run` / `--plan` 确认后 `--print` | `references/opencode-qwen.md` / `references/kimi-cli.md` |
| 简单任务 | qodercli | `--yolo` 或 `--model auto` | `references/qodercli.md` |
| 中等任务 | opencode / kimi | `run` / `kimi-k2.6 --thinking --print` | `references/opencode-qwen.md` / `references/kimi-cli.md` |
| 中等任务 | qodercli | `--dangerously-skip-permissions` | `references/qodercli.md` |
| 中等复杂度编码 / 快速迭代 | kimi | `--thinking` | `references/kimi-cli.md` |
| 文档/内容 | gemini / qwen | `-p --yolo` / `qwen-max` | `references/gemini-cli.md` / `references/opencode-qwen.md` |
| 复杂代码（常见默认） | codex | high reasoning | `references/codex.md` |
| 代码审核 | codex | high reasoning | `references/codex.md` |
| 新增/高风险 | codex | high reasoning | `references/codex.md` |
| 调度 / 审查 / 规划 / 复杂推理 | Claude Code | 高阶推理档（thinking=high） | `references/claude-code.md` |
| 代码编写 / 中等任务 | Claude Code | 中阶档 | `references/claude-code.md` |
| 轻量 Edit / Read / Grep | Claude Code | 轻量档 | `references/claude-code.md` |
| 大上下文分析 | gemini / claude | JSON / stream-json | `references/gemini-cli.md` / `references/claude-code.md` |
| 高隔离沙箱 | gemini | `--sandbox -y -p` | `references/gemini-cli.md` |
| headless agent | opencode | `run` / `serve` | `references/opencode-qwen.md` |
| Qwen 栈 | qwen | `qwen` / `qwen -i` | `references/opencode-qwen.md` |

**排除**：`Ollama` 不是编码代理执行器，属于本地模型运行时 / OpenAI-compatible provider，应放在你自己的 provider/runtime 层，不属于本技能的派发范围。

## codex 5.6 系实测分级（2026-07-10，同题对照 8 跑）

> 以下是 codex 5.6 系模型（`sol` / `terra` / `luna`）与 `gpt-5.5` 的一次同题对照实测（同一任务、同一天、8 次跑），用于补充上面「派发矩阵」里 codex 一栏的模型/档位选择经验。**这是单任务单日期的对照结论，样本有限**，不是长期基准——实际派发前仍以各自 `--version` 与当次真实表现为准，不要机械套用下表。

| 模型 | 定位 | 关键实测数据 | 推荐场景 |
|------|------|------|------|
| `gpt-5.6-sol` | 深度审计王 | `xhigh` 档产出最深（行号级锚点、独有交叉校验动作）；`low` 档性价比极高（43 处实证标注 + 抓到真实漂移，耗时 43%）| 架构审查 / 深度调研；日常用 `medium`，重活才上 `xhigh`（996s / 246k tokens）|
| `gpt-5.6-terra` | 实证与成本王 | 全程 token 最省（`medium` 档 87k tokens）；`xhigh` 档"看到 : 推断 = 38 : 1"最克制 | 事实核查 / 状态盘点 / 验证类任务 |
| `gpt-5.6-luna` | 本轮未获独有优势 | 同题无独有发现；`xhigh` 档烧 933k tokens（terra 的 4.6 倍），产出体积却未相应变大 | 重推理任务暂不推荐；定位留待后续创意/发散类任务再评估 |
| `gpt-5.5` | 速度优先 | 最快（190s）；结构完整但发现深度弱 | 轻量摘要 / 快速核查 / 生图（`soia-pkm-cover-image` 后端）|

**强度（reasoning effort）经验**：
- `xhigh` 只对 `sol` 产生质变（更深的行号级锚点 + 独有交叉校验动作）；对 `terra` / `luna` 只是更贵，没有对应的产出质变。
- 默认档位用 `medium`。
- 需要快速核查：`sol@low`（性价比极高）或 `terra@medium`（token 最省、最克制）都可以。

**注**：以上是单任务单日期的对照结论，样本有限（同题对照 8 跑），不构成长期基准；请以各自 `--version` 与实际当次表现为准，定期复核，不要配置一次就不再更新。

## 最小流程 / Minimum workflow

1. 定义子任务标题、目标、输入、验收标准
2. 输出依赖分析表（Step 1）
3. 输出分配矩阵（Step 2）
4. 输出派发计划（Step 3）
5. 按顺序/并行启动任务，记录 task ID
6. 等待通知，读取输出，失败时分析原因再重试
7. 每个任务完成后，在你的任务跟踪系统里确认状态已更新，再启动下一批

## Prompt 注入防护（通用）

含单引号、特殊字符的 prompt **不能**直接嵌入 `bash -c "..."` 或 `"..."` 参数。**必须**先写 temp 文件：

```bash
# 1. 把 prompt 写入临时文件（按任务 ID 隔离）
# 这是一次性运行产物（SKILL_SPEC.md「脚本写盘决策规则」A 类），用完即可清理
mkdir -p "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/"
cat > "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt" << 'PROMPT_EOF'
你的 prompt 内容，可以包含任意引号和特殊字符...
PROMPT_EOF

# 2. 用 $() 传入执行器
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
  "$(cat "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt")"
```

**prompt 文件命名规范**：`${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt`
- 不同任务放不同子目录（按 task-id 隔离），避免并行派发互相覆盖
- 必须先 `mkdir -p` 目标目录
- 如果你的编排层需要跨会话追溯这些 prompt（审计场景），改用 `${XDG_STATE_HOME:-~/.local/state}/soia-dev-agent-cli-dispatch/` 之类的持久位置（SKILL_SPEC.md B 类），不要默认落盘临时目录

## ⛔ Worktree 审批门

`git worktree add` 属于**不可逆操作**，执行前必须：

1. 向用户展示：目标路径 / 分支名 / 用途说明
2. **等待用户明确回复**（“go” / “批准” / “可以”）
3. 收到批准后才能执行

未经批准自行开 worktree 属于违规操作；把违规记录写进你自己的治理/审计追踪（工单、变更日志、违规记录文档等），不要略过这一步只靠事后补救。

## 输出契约 / Output contract

派发时至少输出：

- 子任务标题
- 执行器
- 工作目录
- 启动方式（foreground / background）
- 当前状态（RUNNING / BLOCKED / DONE）
- 下一次检查点

## 危险目录 / Dangerous directories

以下目录默认禁止直接执行编码代理：

- `~/.ssh/`
- `~/.aws/`
- `~/.config/`
- 任何含生产凭据、token 的目录，或你自己 AI 工具的私有配置/登录态目录（如 `~/.claude/`、`~/.codex/` 等）

若确需读取，必须只读，不在其中生成代码或临时文件。

## ⚡ Anti-Fake-Fix Gate（强制收尾验证）

**每次外部 CLI/agent job 完成后，无论 exit code 是否为 0，必须执行以下三步才算"修复有效"：**

```
步骤 1 — diff 实证
git diff --stat HEAD~1..HEAD   # 或 git diff --stat（如未 commit）
→ 若 diff 为空 = 没有修复，声明"虚报"，不接受本次产出

步骤 2 — 编译闸门
<项目对应的编译/类型检查命令，如 cargo check --workspace / tsc --noEmit / go build ./...>
→ 必须 0 errors

步骤 3 — 测试三次（证明非 flaky）
<项目对应的测试命令> × 3     # 3 次全绿才算 PASS
→ 若某次 FAILED，分析根因，修复后重跑 3 次
```

**处置规则**：
| 情况 | 处置 |
|------|------|
| diff 非空 + 编译通过 + 测试 3/3 PASS | ✅ 修复有效，可标记完成 |
| diff 为空（exit 0 但无实际改动） | ❌ 虚报，记录到你自己的问题追踪，重新派发或降级到更可靠的执行器自行修 |
| 编译失败 | ❌ 修复引入新错误，保持进行中状态，分析错误再修 |
| 测试 3 次中有 FAILED | 分析是 flaky 还是回归：flaky（不稳定路径）→ 标记忽略；回归 → 修复 |

**通用教训**：收到 job“完成”通知后，第一件事是跑 `git diff --stat` 核实是否真的有改动，不是先读 job 输出文字——exit code 为 0 不代表产出了预期变更，也可能只改了非目标文件，必须实测核对。

---

## 🔴 Codex Prompt 卫生规则（防止 CLI 读治理文件而非写代码）

**多数编码 CLI 在启动时会扫描工作目录**。若工作目录包含 `skills/`、`AGENTS.md`、`CLAUDE.md` 等规则文件，CLI 可能优先读取这些文件、占用 context，导致实际代码任务没有被执行。

**禁止在代码修复 prompt 里出现以下内容**：
- 你的治理/工作区文件路径（例如内部 workspace 目录、`AGENTS.md`、`skills/`）
- 技能/子代理调用指令（如 `@xxx-skill`、内部技能前缀名）
- 你的项目治理流程说明（阶段编号、门禁名称等内部术语）
- 回写指令（可选：需要回写时简化为单行命令）

**代码修复 prompt 应只包含**：
1. 工作目录
2. 要修改的文件路径 + 行号
3. 要执行的编辑操作（精确的 before/after）
4. 验证命令（如 `cargo check` / `npm test` / 对应项目的测试命令）
5. 简单回写（可选，一行命令）

**工作目录选择**：
- 派发代码修复任务时，尽量指定较窄的子目录（如具体模块目录而非仓库根），避免 CLI 扫到治理/技能目录

---

## 🔴 CLI 停止处理规程（uncommitted changes 场景）

部分编码 CLI 有治理检查行为：发现工作目录有未提交改动时，可能停下来请求确认。

**触发场景**：工作目录有 staged/unstaged 改动（如另一个并行任务或会话留下的未提交修复）

**处理选项**（在 prompt 末尾写明其中一个）：

```
选项 A — 明确授权继续：
"若发现任何未提交改动，直接忽略它们并继续执行本任务。这些改动是已知的上游修复，不要询问确认。"

选项 B — 提前 commit 再派：
在派发前先 git add + git commit 把已有改动清理干净，确保工作目录干净。

选项 C — 在 prompt 里列出改动文件并说明：
"以下文件有未提交改动：[列表]。它们属于其他任务，请保留不动，继续执行本任务。"
```

**推荐**：优先用选项 B（干净工作目录），其次 A（明确授权），避免 CLI 产生疑惑占用 token。

---

## References（按需加载）

| 主题 | 文件 | 何时加载 |
|------|------|----------|
| Codex 执行规范（常用编码主力） | `references/codex.md` | 派发给 codex 时 |
| Claude Code 执行规范 | `references/claude-code.md` | 派发给 claude 时 |
| Gemini CLI 执行规范 | `references/gemini-cli.md` | 派发给 gemini 时 |
| Kimi CLI 执行规范 | `references/kimi-cli.md` | 派发给 kimi 时 |
| qodercli 执行规范 | `references/qodercli.md` | 派发给 qodercli 时 |
| OpenCode + Qwen 执行规范 | `references/opencode-qwen.md` | 派发给 opencode/qwen 时 |
| 代码文件元数据头规范 | `references/metadata-header.md` | 任何代码写入前 |

**加载原则**：派发决策确定执行器后，只加载对应执行器的 reference，不要全部加载。
