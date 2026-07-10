---
name: soia-dev-agent-cli-dispatch
description: 调度外部编码 CLI（codex/claude/gemini/kimi/opencode/qwen，非宿主内置子代理）：显式指定执行器+模型+推理深度，或只给执行器家族按任务难度自动选型；调用后输出 Token/费用汇总、降级检测、额度预检与断点恢复。Triggers：「派活给 codex」「让 gemini 执行」「多 CLI 派发」等
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

调度外部编码 CLI（codex/claude/gemini/kimi/opencode/qwen，非宿主内置子代理，`qodercli` 也有命令模板但未纳入下方精简清单）进行受控派发：任务边界拆分、独立 workdir、防注入 prompt 写法、模型分级矩阵、Worktree 审批门、Anti-Fake-Fix 三步验证。在此之上，可显式指定执行器 + 模型 + 推理深度，或只给执行器家族由任务难度自动选型（见「自动路由」）；每次调用后输出 Token/费用汇总（见「调用总结回执」）、模型降级检测（见「Model Integrity Gate」）、额度预检（见「额度预检」）与断点续跑（见「可恢复执行」）。各执行器详细命令模板在 `references/` 子目录下按需加载。

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

## 自动路由 / Auto-routing

覆盖「客户或上游编排层只给了执行器家族，没给具体模型/推理深度」的场景。**显式指定始终绝对优先**——本节只在没有显式指定模型/推理深度时才生效；只要给了具体模型或推理深度，跳过本节，直接使用给定值。

### 判据（十项，用于把任务落到 easy / medium / hard）

| # | 判据 | easy 倾向 | hard 倾向 |
|---|------|-----------|-----------|
| 1 | 改动文件数 | 1-2 个 | 跨模块多文件 |
| 2 | 是否涉及并发 / 一致性 / 安全边界 | 否 | 是 |
| 3 | 是否需要新增架构决策 | 否，照抄既有模式 | 是，需要设计取舍 |
| 4 | 失败代价 | 可回退、易重试 | 不可逆或对外可见 |
| 5 | 上下文窗口需求 | 单文件 / 局部 | 跨仓库 / 长历史 |
| 6 | 是否需要多轮工具调用相互验证 | 一次编辑即可 | 需要反复读结果再改 |
| 7 | 是否涉及安全 / 权限 / 凭据代码 | 否 | 是 |
| 8 | 任务描述是否已给出精确 before/after | 是 | 否，需要探索式推理 |
| 9 | 是评审 / 证据核验类还是编写类 | 简单核对 | 复杂 diff review 倾向 hard |
| 10 | 预算 / 时间敏感度 | 需要快出结果 | 可以换更长运行时间 |

十项不要求全部满足；按整体倾向把任务落到三档之一。落到 easy/medium 但执行结果不达标时，按「⚡ Anti-Fake-Fix Gate」的处置规则升级重试，不要在同一档位反复重试期待不同结果。

### 推荐组合（P4 实证路由，2026-07-10 smoke matrix；部分家族仍是占位）

下表按执行器家族给出模型/推理深度组合。**codex 与 claude 两行已经过真实执行矩阵验证**（2026-07-10，codex 侧 35 case + claude 侧 15 case），标记为「实证」；**gemini / kimi / opencode / qwen 三行尚未测试**，继续如实标记 `pending_benchmark`，不得包装成已验证推荐。完整逐 case 证据、原始数字和已知缺口见 `references/benchmark-2026-07-10.md`。

| 执行器家族 | easy 候选 | medium 候选 | hard 候选 | 状态 |
|---|---|---|---|---|
| codex | `gpt-5.6-luna` @ low | `gpt-5.6-terra` @ medium（token 最省，实证） | `gpt-5.6-sol` @ high，穷尽才升到 xhigh（实证 xhigh 仅 sol 有质变） | **实证** — 依据：2026-07-10 smoke matrix（`references/benchmark-2026-07-10.md` §1） |
| claude | `claude-haiku-4-5`（比 opus 便宜约 18 倍，实证；未按 effort 拆分数据） | `claude-sonnet-5` @ medium | *(暂无实证推荐——见下方反模式警示)* | **实证**（hard 档除外）— 依据：2026-07-10 smoke matrix（`references/benchmark-2026-07-10.md` §2） |
| gemini | gemini-2.5-flash-lite | gemini-2.5-flash | gemini-2.5-pro / gemini-3.1-pro-preview | `pending_benchmark`（未测） |
| kimi | kimi-k2.6（默认档） | kimi-k2.6 --thinking | kimi-k2.6 --thinking（更长上下文/更多轮次） | `pending_benchmark`（未测） |
| opencode / qwen | 默认模型 | qwen-max 或等效中阶模型 | 项目已配置的最强可用模型 | `pending_benchmark`（未测） |

#### 反模式警示（实证，依据：2026-07-10 smoke matrix）

- **`claude-opus-4-8` 在简单任务上对 effort 无响应**：同一 fixture 上五档 effort（low/medium/high/xhigh/max）的 output token 数和 cost 完全相同（22 tokens / $0.0677）——五档都被 CLI 接受（非 unsupported），只是没有测量到差异。**这只在本次简单固定算术任务上成立**，难任务未测试，不要泛化成"opus 的 effort 参数整体无用"。因此本表 hard 档没有给 claude 侧推荐。依据：2026-07-10 smoke matrix。
- **`gpt-5.6-luna` 的 `xhigh` 档烧钱不产出**：旧的「同题 8 跑深度调研」对照里，`xhigh` 档烧到 933k tokens（terra 的约 4.6 倍），产出体积却没有相应变大，因此 luna 只推荐 easy 档 + low 效力，不建议升到高档。依据：2026-07-10 同题 8 跑深度调研（见下文「codex 5.6 系实测分级」节）。
- **结论：高 effort 是否有回报，取决于「这个模型」和「这个任务难度」两个变量共同作用，不是只看任务难度。** 同一个简单任务上，`claude-sonnet-5` 的 output 随 effort 单调增长（low 22 tokens → max 410 tokens），说明它确实在用 effort 换更多思考；`claude-opus-4-8` 完全不为所动——两个模型对同一个 effort 旋钮的反应可以截然不同。不要无脑对所有模型都开最高档，先确认该模型在类似任务上是否已有「effort 有效」的实证。依据：2026-07-10 smoke matrix。

### 与 model-catalog.yml 的关系

`references/model-catalog.yml` 每个模型条目预留了 `routing_profile`、`discovered_at`、`discovery_evidence` 三个字段。P4（2026-07-10）已把参与本轮 smoke matrix 的模型回填：`gpt-5.6-sol`/`gpt-5.6-terra`/`gpt-5.6-luna`/`claude-sonnet-5`/`claude-sonnet-5-2026-09-01`/`claude-opus-4-8`/`claude-haiku-4-5` 的 `routing_profile` 从 `null` 回填为实证的三档归属（`claude-opus-4-8` 回填为 `[]`——已测试、但当前证据不支持任何一档推荐，即上面的反模式）；`gpt-5.5`/`gpt-5.4`/`gpt-5.4-mini` 的 `discovered_at`/`discovery_evidence` 回填，但 `routing_profile` 保持 `[]`（已测试，"另需实测"缺口未补齐前不给路由推荐）。未参与本轮矩阵的模型（gemini/kimi/opencode/qwen 全家族、deepseek、其余 claude/openai 型号）保持 `null` 不变，仍是未知状态。**不得把仍是 `pending_benchmark` 的组合（gemini/kimi/opencode/qwen）包装成"已验证推荐"讲给客户听**；如实说明这是候选，不是结论。

## codex 5.6 系实测分级（2026-07-10，同题对照 8 跑）

> **本节地位（P4 更新，2026-07-10）**：「自动路由」表格中的 `pending_benchmark` 已被同一天跑出的 35+15 case smoke matrix 结果替换为实证路由（codex 与 claude 两个家族；gemini/kimi/opencode/qwen 仍是占位，见上文「推荐组合」表）。本节收录的是**另一批、更早**的「同题 8 跑深度调研」数据，回答的是"深度调研任务上哪个模型/档位物有所值"，与 smoke matrix 回答的"能不能正常跑、模型回显是否可信、effort 是否真的影响输出"是不同维度——两者互为补充、交叉引用，不重复摘录，也不互相替代。完整交叉引用与两批数据的关系说明见 `references/benchmark-2026-07-10.md` §3。
>
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

## 统一调用契约 / Unified invocation contract

本节定义每一次外部 CLI 调度的输入/输出字段，供你自己的编排层和 `scripts/` 下的脚本共用。术语先对齐：

| 术语 | 含义 |
|---|---|
| `host_ai` | 调用本技能的宿主（任意兼容 Agent；可以是 Claude Code，也可以不是——本技能不绑定单一宿主） |
| `executor_cli` | 被调度的外部 CLI 进程：`codex` / `claude` / `gemini` / `kimi` / `opencode` / `qwen`（`qodercli` 有独立命令模板，见 `references/qodercli.md`，但 `model-catalog.yml` 未把它作为一个 provider 分组） |
| `requested_model` | 本次调用要求使用的模型标识（可以是别名，见 `scripts/catalog_lib.py::find_model` 的宽松匹配规则） |
| `actual_model` | 执行器实际使用的模型标识；只有执行器自己在输出里回显时才能拿到，拿不到就是 `null`，不得编造 |
| `reasoning_or_effort` | 推理深度/强度参数（不同执行器命名不同：`model_reasoning_effort`、`--thinking`、`thinking=high` 等） |
| `billing_mode` | `api`（按 token 计费）\| `subscription`（订阅额度）\| `unknown`。决定 `scripts/estimate_cost.py` 的输出是否等于真实扣费——订阅制下永远不等于 |

**输入字段：**

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` | 是 | 本次调用在批次内的唯一标识 |
| `provider` | 是 | `openai` / `anthropic` / `google` / `deepseek` / 其他 |
| `executor` | 是 | 见上文 `executor_cli` |
| `model` | 是 | `requested_model`；未显式指定时按「自动路由」选型后再填入 |
| `reasoning` | 否 | 未指定时参考 `references/model-catalog.yml` 对应模型的 `default_reasoning_level`（可能为 `null`，即未知） |
| `cmd_template` | 是 | 实际执行的 shell 命令（已按「Prompt 注入防护」写好 temp 文件引用） |
| `timeout_seconds` | 否 | 默认 600 秒（见 `scripts/run_matrix.py --timeout-seconds`） |

**输出字段：**

| 字段 | 说明 |
|---|---|
| `status` | 见下方状态枚举 |
| `exit_code` | 子进程退出码；超时未取到时为 `null` |
| `tokens_used` | 整数，或字符串 `"unknown"`（解析不到时，不得编造数字） |
| `actual_model` | 见上文；解析不到为 `null` |
| `api_equivalent_cost` | 由 `scripts/estimate_cost.py` 计算的 API 等价费用估算，含 `confidence` |
| `notes` | 字符串数组，记录本次调用的例外情况（降级、无法解析、计费 tier 回退等） |

**状态枚举全集**（与 `scripts/run_matrix.py` 的 `ALL_STATUSES` 一致）：

`pending` / `running` / `passed` / `failed` / `unsupported` / `blocked_auth` / `blocked_quota` / `blocked_paid_api` / `pending_quota` / `timeout` / `fallback_or_downgrade` / `actual_model_unverified` / `interrupted` / `not_tested`

**unknown / unsupported 约定：**

- 解析不到的字段一律写 `null`（JSON）或字符串 `"unknown"`，**禁止用 0、空字符串或猜测值填充**——那会被下游误读成"确实是 0"或"确实是这个值"。
- `unsupported` 专指执行器明确表示"不支持该模型/参数"（stdout/stderr 命中 `not supported` / `invalid model` / `unknown model`），不要和"我们没测过"的 `not_tested` 混用。
- 任何标记为 `unknown` / `unsupported` / `unavailable` 的字段，禁止在客户可见的总结文字里被复述成确定结论（不能说"token 用量为 0"，只能说"token 用量未知，原因是 xxx"）。

## 额度预检 / Quota precheck

对某个 executor 发起**第一次真实调用**之前（尤其是新会话、或距上次调用较久之后），先跑一次预检并向客户展示报告，字段固定：

| 字段 | 说明 |
|---|---|
| `executor` | 目标执行器 |
| `cli_installed` | `true` / `false`（`which <command>` 或等效检测） |
| `cli_version` | 实际探测到的版本字符串，或 `"unavailable"` |
| `auth_status` | `ok` / `expired` / `unknown`（跑一次最小只读命令观察，例如对应 CLI 的 `auth status` 或 `-p "ping"`） |
| `last_known_quota_state` | 上一次派发记录里的额度状态；没有记录就是 `"unknown"` |
| `recommendation` | `proceed` / `hold` / `skip`，附一句理由 |

预检报告本身不消耗真实模型调用额度（只读版本探测 + 认证状态检查）。`recommendation` 为 `hold` 或 `skip` 时，不得继续派发，除非客户明确批准。

`scripts/run_matrix.py` 在每次运行开始时会对本批次涉及的 executor 做只读版本探测（`<executor> --version`）并写入 manifest 的 `cli_versions` 字段；`--resume` 时会重新探测并在版本变化时打印警告。**当前脚本不做认证状态检查**——`auth_status` 仍需派发者在预检报告里人工核实或另行探测，脚本本身不会为了验证登录态而发起真实模型调用。

## Model Integrity Gate

保证"客户以为用的模型"和"实际用的模型"一致；出现偏差必须如实报告，不能包装成"任务成功"。

1. **requested vs actual**：每次调用后比对 `requested_model` 与 `actual_model`。
2. **降级判定**：
   - `codex`：stdout 头部若有 `model: xxx` 行，与 `requested_model` 不一致时，状态标记为 `fallback_or_downgrade`（`scripts/run_matrix.py::detect_actual_model` 已实现，只扫描 stdout 前 2000 字符内的 `model:` 行）。
   - `claude`：**P4（2026-07-10）更新**——纯文本模式（`cmd_template` 不含 `--output-format json`）下 headless 输出仍然**没有**可靠的模型回显机制，任何成功调用一律标记 `actual_model_unverified`，**不允许**因为"看起来跑成功了"就报告为 `passed`。但当 `cmd_template` 显式带 `--output-format json`（或 `--output-format=json`）时，`scripts/run_matrix.py::detect_actual_model` 会解析 stdout JSON 的 `modelUsage`（键名即模型 id）或顶层 `model` 字段作为 `actual_model`，与 `requested_model` 比对后可以正常判定 `passed` / `fallback_or_downgrade`，不再一律 `actual_model_unverified`。比对前会先剥离两种已在真实 CLI（2.1.206，2026-07-10 实测验证，非猜测）上观察到的修饰后缀：不带 `--model` 时回显可能带方括号执行模式后缀（如 `claude-opus-4-8[1m]`）；用短别名（如 `haiku`）请求时回显可能带日期后缀（如 `claude-haiku-4-5-20251001`）；显式传完整 catalog `model_id`（如 `claude-haiku-4-5`）时回显通常精确匹配、无后缀。stdout 不是合法 JSON 时仍然回退到 `actual_model_unverified`，不假装已验证。细节与原始验证 payload 见 `references/benchmark-2026-07-10.md`。
   - 其他执行器（gemini/kimi/opencode/qwen）：Phase 1 未实现模型回显检测，`notes` 会如实写明"model-echo verification is not implemented for this executor"，不假装已覆盖。
3. **宿主模型变化**：`host_ai` 自身运行在哪个底层模型上，属于**仅可观测、不可控**的信息——本技能不能对宿主自己的模型完整性做强制门禁。如果宿主环境暴露了自身模型标识，记录下来即可；拿不到就写 `unknown`，不要推断。
4. **能力限制声明**：任何一次 Model Integrity Gate 判定为 `actual_model_unverified` 或 `fallback_or_downgrade` 的调用，最终回执必须包含这次判定，不能只在内部日志里留痕、对客户只报"完成"。

## 可恢复执行 / Resumable execution

面向需要跑一批（多 case、多 executor、多模型）派发矩阵的场景，使用 `scripts/run_matrix.py`（严格串行，一次只跑一个 case，不并发）。

**Manifest 位置**（遵循 `SKILL_SPEC.md`「脚本写盘决策规则」B 类——可追溯、记录状态变化的审计记录，不是一次性临时文件）：

```text
${XDG_STATE_HOME:-~/.local/state}/soia-dev-agent-cli-dispatch/runs/<run_id>/manifest.json
```

**首次运行：**

```bash
python3 scripts/run_matrix.py --cases cases.json --run-id <run_id> \
  --manifest-dir "${XDG_STATE_HOME:-$HOME/.local/state}/soia-dev-agent-cli-dispatch/runs/<run_id>"
```

**断点续跑**（进程被杀、额度耗尽、或手动中断后）：

```bash
python3 scripts/run_matrix.py --cases cases.json --run-id <run_id> \
  --manifest-dir "${XDG_STATE_HOME:-$HOME/.local/state}/soia-dev-agent-cli-dispatch/runs/<run_id>" \
  --resume
```

manifest 里的 `resume_command` 字段会给出这条命令的现成版本，直接复制运行即可。

行为约定：

- 每个 case 跑完后立即原子写 manifest（临时文件 + `os.replace`），中途被杀不会破坏 manifest 文件本身。
- 某个 provider 的某个 case 命中 `blocked_quota` 后，同一 provider 剩余的 case 立即标记 `pending_quota`（不再实际执行子进程），其他 provider 的 case 不受影响、按串行顺序继续跑。
- `--resume` 时，已是终态（`passed` / `unsupported` / `blocked_paid_api` / `fallback_or_downgrade` / `actual_model_unverified`）的 case 直接跳过；残留 `running`（上次进程被杀留下的）会先标记 `interrupted`（证据保留在该 case 记录的 `previous_attempt` 字段里，不丢弃），再重新尝试一次。
- `--resume` 时会重新探测本批次涉及执行器的 CLI 版本，和上次 manifest 里记录的版本不一致会打印警告（结果可能不可比较，但不会阻止运行）。

## 调用总结回执 / Call summary receipt

每次调用（无论成功、失败、超时、额度不足还是降级）结束后，必须输出以下最低回执格式：

```text
完成：<一句话说明本次调用做了什么>

执行器与模型：
- executor: <executor_cli>
- requested_model: <requested_model>
- actual_model: <actual_model，或 "unverified"，或 "unknown">
- reasoning: <reasoning_or_effort，或 "unknown">

Token 与费用：
- tokens_used: <数字，或 "unknown">
- api_equivalent_cost: <金额 币种，或 "unavailable">
- confidence: <exact | estimated | unavailable>
- 订阅制下实际扣费≠此估算（api_equivalent_estimate）

状态：
- status: <见「统一调用契约」状态枚举全集>
- 降级/异常说明：<Model Integrity Gate 判定结果；没有异常写"无">

问题与下一步：
- <缺 key / 额度不足 / 需要客户确认 / resume_command；没有则写"无">
```

单次调用用这份回执；批量矩阵额外参考 manifest 的 `completed_cases` / `remaining_cases` / `stop_reason` 汇总整批状态。

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

## 价格资料说明 / Pricing reference

- `references/model-pricing-2026-07-10.md` 原样收录 2026-07-10 版模型价格调研原文（未改写数字），顶部注明来源与「正式预算以官方定价页为准」的声明。
- `references/model-catalog.yml` 是从上述原文规范化提取的**运行时单一事实源**：`scripts/estimate_cost.py`、`scripts/run_matrix.py` 只读取这个 YAML 文件，不解析 Markdown。人工核对价格时，请以 Markdown 原文为准；脚本计算以 YAML 为准；两者数字不一致时先修 YAML 再核对来源，不要各自为政。
- 更新价格时：先改 `model-pricing-2026-07-10.md`（或新增一份带日期的新快照文件），再同步改 `model-catalog.yml`，改完跑 `python3 scripts/catalog_lib.py --selftest` 确认结构仍然合法。
- 「codex 5.6 系实测分级」一节（见上文）是**初步单日样本**，与本节的官方/半官方价格资料性质不同，不要混用：分级节是"哪个模型/档位在这次测试里表现更好"，本节是"这个模型每 1M token 官方标价多少"。分级节待全矩阵覆盖（P3 `scripts/run_matrix.py` 批量结果）后需要更新。

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
| 模型价格资料原文（2026-07-10 快照） | `references/model-pricing-2026-07-10.md` | 需要人工核对官方定价、或价格资料更新时 |
| 模型价格/推理档运行时目录 | `references/model-catalog.yml` | `scripts/estimate_cost.py` / `scripts/run_matrix.py` 运行时读取；人工修改前后都跑一次 `scripts/catalog_lib.py --selftest` |
| P4 实证路由的证据来源（2026-07-10 smoke matrix 全量结果） | `references/benchmark-2026-07-10.md` | 需要查「自动路由」表格具体依据、逐 case 明细或已知缺口时 |

**加载原则**：派发决策确定执行器后，只加载对应执行器的 reference，不要全部加载。

## Scripts（按需调用）

| 脚本 | 用途 | 自检命令 |
|------|------|----------|
| `scripts/catalog_lib.py` | 受限 YAML 子集解析器 + `model-catalog.yml` schema 校验（重复 model_id / 缺字段 / 负价拒绝，未知 reasoning level 标记为 WARN） | `python3 scripts/catalog_lib.py --selftest` |
| `scripts/estimate_cost.py` | 给定 model + token 数，输出 API 等价费用估算（分项 + 总额 + `confidence`），未知模型给出近似候选并以 exit code 2 退出 | `python3 scripts/estimate_cost.py --selftest` |
| `scripts/run_matrix.py` | 可恢复的串行派发矩阵执行器（P3 用；本文档阶段只用 mock 命令自检，不真实调用任何模型） | `python3 scripts/run_matrix.py --selftest` |

三个脚本均为纯 Python 标准库实现，无第三方依赖。修改任意一个后，先跑对应 `--selftest`，再跑一遍其余两个确认没有连带破坏（`estimate_cost.py` 和 `run_matrix.py` 都从 `catalog_lib.py` 导入解析/校验逻辑）。
