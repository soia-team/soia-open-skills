---
name: soia-dev-agent-cli-dispatch
description: 通用外部 AI 模型/CLI 调度器（codex/claude/agy/gemini/kimi/opencode/qwen，非宿主内置子代理），可由任意宿主 AI 用于编码、审查、分析、研究、文档和内容任务：支持显式模型+推理深度或按难度自动选型，并输出 Token/费用、模型完整性、额度与恢复回执。Triggers：「派活给 codex」「让 claude 分析」「调用 agy」「调用外部 AI」「多 CLI 派发」等
dependencies:
  optional: [soia-dev-sync-skills]
version: 1.1.0
created_at: 2026-07-10 11:28:32
updated_at: 2026-07-20 15:18:33
created_by: claude opus 4.6
updated_by: Claude Fable 5
---

# soia-dev-agent-cli-dispatch

Use this skill when any host AI needs to dispatch coding, review, analysis,
research, documentation, or content work to an external AI model/CLI — Codex,
Antigravity CLI, Gemini CLI, Kimi CLI, OpenCode, Qwen Code, or a
separately-launched Claude Code process — instead of continuing directly in the
current agent session. This is about calling an external AI process; it is
**not** about a host's built-in sub-agents.

Do not use it when the current agent can just finish the task itself with no
external process involved, or when you only need a one-off local shell
command with no orchestration, monitoring, or prompt-injection concerns.

## 客户可读说明

### 这个技能可以做什么

调度外部 AI 模型/CLI（codex/claude/agy/gemini/kimi/opencode/qwen，非宿主内置子代理，`qodercli` 也有命令模板但未纳入下方精简清单）进行受控派发，覆盖编码、审查、分析、研究、文档和内容任务：任务边界拆分、独立 workdir、防注入 prompt 写法、模型分级矩阵、Worktree 审批门、Anti-Fake-Fix 三步验证。在此之上，可显式指定执行器 + 模型 + 推理深度，或只给执行器家族由任务难度自动选型（见「自动路由」）；每次调用后输出 Token/费用汇总（见「调用总结回执」）、模型完整性检测（见「Model Integrity Gate」）、额度预检（见「额度预检」）与断点续跑（见「可恢复执行」）。各执行器详细命令模板在 `references/` 子目录下按需加载。

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

`npx skills` 会更新 `~/.agents/skills` 共享源，但不管理所有自定义目标。已安装开源 `soia-dev-sync-skills` 的环境可在明确指定目标后执行单项同步：

```bash
python3 ~/.agents/skills/soia-dev-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets soia,workbuddy \
  --skills soia-dev-agent-cli-dispatch
```

最终验收应确认 `~/.soia/skills/soia-dev-agent-cli-dispatch` 与 `~/.workbuddy/skills/soia-dev-agent-cli-dispatch` 都是指向 `~/.agents/skills/soia-dev-agent-cli-dispatch` 的软链接；不要把本地源码 checkout 当成 npx 安装结果。

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

满足任一即调用本技能（自然语言里常见的说法包括但不限于「派活给 codex」「让 claude 分析」「调用外部 AI」「多 CLI 派发」「后台跑任务」）：

| 条件 | 说明 |
|------|------|
| 需要把编码、审查、分析、研究、文档或内容子任务交给外部 AI CLI 执行 | 当前 host AI 不直接做，而是派给另一个外部 AI 进程 |
| 为子 agent 生成 prompt | 需要防注入的 temp 文件写法 |
| 后台启动长任务 | 需要受控 workdir + 进度监控 |
| 多 agent 并行 | 需要制定依赖 / 分配矩阵 / 派发计划 |

**不需要调用**：自己直接执行代码任务（无派发动作）。

## 如何自查你的外部 AI CLI 可用性

不要假设某个 CLI 一定可服务。派发前按下面顺序自查，把结果记在你自己的可用性记录里，而不是照抄本文档里的任何示例状态（示例会过期）：

1. **CLI 是否已安装**：`which <command>` 或 `<command> --version`；版本号以实际输出为准。
2. **认证 / 套餐是否有效**：优先使用官方的本地状态命令。若 CLI 没有不调用模型的 auth-status 命令（当前 `agy` 即如此），不得把 `<command> -p "ping"` 伪装成“零额度只读检查”；模型调用可能消耗额度，必须先获客户确认。需要浏览器登录时在 PTY 启动，状态记为 `blocked_user_action`，由客户本人完成账号选择与授权。
3. **上一次派发是否失败**：如果最近一次该执行器的任务返回非预期错误或反复超时，先记为暂不可服务，等你验证修复后再恢复派发。
4. **维护你自己的可用性表**：建议自建一张「执行器 / CLI 可用 / 套餐-Key 状态 / 可服务 / 备注」的表格，随你的编排层状态变化更新。

不可服务的执行器不得派发；等状态恢复、你自己验证通过后再更新记录、再派发。

**Google 认证通道不得混用**：Gemini CLI 的消费者 Google OAuth 自
2026-06-18 起已停止服务，应迁移到独立命令 `agy`；Gemini Code Assist
Standard/Enterprise、Gemini API Key 和 Vertex AI 通道仍保留在 `gemini`
执行器中。禁止 alias、静默替换命令、复制 OAuth 文件或把一个通道的
套餐/计费结论套到另一个通道。详见 `references/antigravity-cli.md` 与
`references/gemini-cli.md`。

### 全量 benchmark 覆盖闭环

声称“全模型 × 全推理档位已测试”前，必须同时具备：当前 CLI/账号的模型发现快照、每个模型支持档位的发现证据、完整笛卡尔积 case 清单、逐 case 原始 `manifest.json` 和聚合报告。缺少任一项，统一标记 `partial_coverage`，不得只凭聚合转述或 exit code 报告“全量完成”。价格目录中的 `availability` 只表示价格资料列出该模型，不等于当前账号/CLI 已验证可调用；实际执行能力以 `discovered_at`、`discovery_evidence` 和原始 manifest 为准。

## 适用 / 不适用

**适用**：
- 把一个工程任务拆给其他编码代理并行执行
- 把简单但需要外部 AI 执行、复核或留痕的任务受控派发出去
- 在受控工作目录中启动长时间运行的编码任务
- 对子任务执行结果做收集、汇总和复核

**不适用**：
- 不发生外部 AI 派发、只由当前 host 或本地工具直接完成的动作
- 需要立刻得到结果，无法承受异步后台执行
- 还没有明确子任务范围、工作目录和验收标准

任务简单不是排除条件：只要需要由外部 AI CLI 执行，就按风险、输入范围和验收要求选择最小充分的派发方式。

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
├── 简单且非破坏性任务（写配置/简单脚本；删除、覆盖等破坏性动作不得归入此类）
│   └── opencode run "..."  或  kimi -w <wt> --plan -p "..."（确认后改 --print）
│       详见 references/opencode-qwen.md / references/kimi-cli.md / references/qodercli.md
│
├── 中等任务（rsync/build/verify/小范围重构）
│   └── opencode run "..."  或  kimi -w <wt> -m kimi-k2.6 --thinking --print -p "..."
│       详见 references/opencode-qwen.md / references/kimi-cli.md / references/qodercli.md
│
├── 文档/内容写作
│   ├── 消费者 Google 账号：agy -p "..."（需先确认额度；显式派发）
│   ├── Gemini 企业/API Key/Vertex：gemini -p "..."
│   └── qwen "..." / qwen -m qwen-max "..."
│       详见 references/antigravity-cli.md / references/gemini-cli.md / references/opencode-qwen.md
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
│   ├── 消费者 Google 账号：agy --model "<agy models 显示名>" -p "..."
│   ├── Gemini 非消费者通道：gemini -p "..." --output-format json
│   ├── Gemini 非消费者通道：gemini -p "..." --output-format stream-json
│   └── claude --permission-mode bypassPermissions --print --output-format json
│       详见 references/antigravity-cli.md / references/gemini-cli.md / references/claude-code.md
│
├── 高隔离分析（沙箱）
│   ├── 消费者 Google 账号：agy --sandbox --mode plan -p "..."
│   └── Gemini 非消费者通道：gemini --sandbox -y -p "..."
│       详见 references/antigravity-cli.md / references/gemini-cli.md
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
| Antigravity 消费者账号 | agy | 显式派发；当前不自动选模 | `references/antigravity-cli.md` |
| 文档/内容 | agy（消费者）/ gemini（非消费者）/ qwen | agy 显式运行时显示名 / `gemini -p --yolo` / `qwen-max` | `references/antigravity-cli.md` / `references/gemini-cli.md` / `references/opencode-qwen.md` |
| 复杂代码（常见默认） | codex | high reasoning | `references/codex.md` |
| 代码审核 | codex | high reasoning | `references/codex.md` |
| 新增/高风险 | codex | high reasoning | `references/codex.md` |
| 调度 / 审查 / 规划 / 复杂推理 | Claude Code | 高阶推理档（thinking=high） | `references/claude-code.md` |
| 代码编写 / 中等任务 | Claude Code | 中阶档 | `references/claude-code.md` |
| 轻量 Edit / Read / Grep | Claude Code | 轻量档 | `references/claude-code.md` |
| 大上下文分析 | agy（消费者）/ gemini（非消费者）/ claude | agy 显式派发 / Gemini JSON 或 stream-json | `references/antigravity-cli.md` / `references/gemini-cli.md` / `references/claude-code.md` |
| 高隔离沙箱 | agy（消费者）/ gemini（非消费者） | `agy --sandbox --mode plan -p` / `gemini --sandbox -y -p` | `references/antigravity-cli.md` / `references/gemini-cli.md` |
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

### 可执行路由与固定回执

不要只在自然语言里临时拍板。确定 easy/medium/hard 后调用 `scripts/route_model.py`；自动路由只选择同时具备 `routing_profile`、`discovered_at`、`discovery_evidence` 和已验证 reasoning levels 的模型。显式指定模型/档位始终优先，但未验证组合必须标记 `explicit_unverified`。

```bash
python3 scripts/route_model.py --executor codex --complexity hard
python3 scripts/route_model.py --executor claude --complexity medium --model claude-sonnet-5 --reasoning high
```

每次路由必须输出 `selected_model`、`selected_reasoning_effort`、`task_complexity`、`selection_reason`、`estimated_cost_range`、`catalog_version` 和 `selection_status`，再把结果写入统一调用契约；没有 verified candidate 时返回阻断状态，不得从 `pending_benchmark` 候选中静默挑一个。

### 推荐组合（P4 部分实证路由，2026-07-10 smoke matrix）

下表按执行器家族给出模型/推理深度组合。Codex 6 个型号的 35-case 与 Claude 3 个型号的 15-case 已有真实 smoke 聚合记录，但原始 manifest 未随交接提供，且未覆盖 catalog 中全部型号，因此统一标记 `partial_coverage`；表内推荐只对已覆盖组合有效。Gemini 本轮为 `blocked_auth`，Antigravity 未获准运行付费/额度模型评测，Kimi/OpenCode/Qwen 仍是 `pending_benchmark`。不得把部分实证包装成全量完成，证据边界见 `references/benchmark-2026-07-10.md`。

| 执行器家族 | easy 候选 | medium 候选 | hard 候选 | 状态 |
|---|---|---|---|---|
| codex | `gpt-5.6-luna` @ low | `gpt-5.6-terra` @ medium（token 最省，已覆盖组合内实证） | `gpt-5.6-sol` @ high，穷尽才升到 xhigh（已覆盖组合内实证） | `partial_coverage` — 6 个型号有聚合记录，缺全 catalog 覆盖与原始 manifest |
| claude | `claude-haiku-4-5`（比 opus 便宜约 18 倍；未按 effort 拆分数据） | `claude-sonnet-5` @ medium | *(暂无 hard 档实证推荐，见下方反模式警示)* | `partial_coverage` — 3 个型号有聚合记录，缺全 catalog 覆盖与原始 manifest |
| agy | — | — | — | `availability_discovered`（`agy models` 已无 prompt 验证；账号级显示名见 `references/antigravity-cli.md`，但未做真实模型 benchmark，禁止自动路由） |
| gemini | gemini-2.5-flash-lite | gemini-2.5-flash | gemini-2.5-pro / gemini-3.1-pro-preview | `blocked_auth`（2026-07-10 实测：消费者 OAuth 浏览器回调成功后被服务端以弃用策略拒绝；Standard/Enterprise、API Key、Vertex AI 仍是受支持的独立通道，本轮未测） |
| kimi | kimi-k2.6（默认档） | kimi-k2.6 --thinking | kimi-k2.6 --thinking（更长上下文/更多轮次） | `pending_benchmark`（未测） |
| opencode / qwen | 默认模型 | qwen-max 或等效中阶模型 | 项目已配置的最强可用模型 | `pending_benchmark`（未测） |

### 大型远端文件 / 云盘语义路由（操作策略，非 benchmark）

下表根据操作语义选择 easy / medium / hard 路径，用于远端文件、对象存储、共享盘或云盘等大型资料集。它不是模型能力、价格、速度或正确率的 benchmark，也不替代执行器可用性检查、用户授权、权限校验、dry-run、备份与恢复方案。实际执行器、存储服务、账号和运行环境均由当前任务上下文决定，不在此写死。

| 路径 | 典型任务 | 允许的核心动作 | 必须交付的证据 | 升级条件 |
|------|----------|----------------|----------------|----------|
| Luna / easy | 只读枚举、目录/元数据盘点、格式与命名核对 | 只读列举、抽样读取、格式检测、生成清单或差异报告；不改远端状态 | 范围、枚举时间、数量、抽样规则、异常项与未读项 | 遇到跨目录关联、需改写分类或迁移设计时升至 Terra |
| Terra / medium | 跨文件实现、分类整合、迁移方案 | 分析关联关系，生成或执行可回退的分批方案；先预览目标映射和冲突处理 | 源/目标映射、冲突清单、批次计划、dry-run 或等价预览、回滚路径 | 涉及删除、覆盖、不可逆替换，或需要确认最终状态时升至 Sol |
| Sol / hard | 删除前红队、终态验收 | 先反证删除范围、依赖和恢复路径；在获授权后复核实际终态，不以任务退出码代替验收 | 删除前范围对账、反例/依赖检查、授权记录、删除后枚举对账、抽样可读性与残留/误删检查 | 任一对账不一致、恢复路径未证实或权限边界不清时停止并回报 |

对远端写入、移动、覆盖、删除或发布，先遵守本技能的确认门和统一调用契约；Luna 不得越权写入，Terra 不得把迁移方案当作已完成迁移，Sol 不得在缺少终态证据时宣布完成。

#### 反模式警示（实证，依据：2026-07-10 smoke matrix）

- **`claude-opus-4-8` 在简单任务上对 effort 无响应**：同一 fixture 上五档 effort（low/medium/high/xhigh/max）的 output token 数和 cost 完全相同（22 tokens / $0.0677）——五档都被 CLI 接受（非 unsupported），只是没有测量到差异。**这只在本次简单固定算术任务上成立**，难任务未测试，不要泛化成"opus 的 effort 参数整体无用"。因此本表 hard 档没有给 claude 侧推荐。依据：2026-07-10 smoke matrix。
- **`gpt-5.6-luna` 的 `xhigh` 档烧钱不产出**：旧的「同题 8 跑深度调研」对照里，`xhigh` 档烧到 933k tokens（terra 的约 4.6 倍），产出体积却没有相应变大，因此 luna 只推荐 easy 档 + low 效力，不建议升到高档。依据：2026-07-10 同题 8 跑深度调研（见下文「codex 5.6 系实测分级」节）。
- **结论：高 effort 是否有回报，取决于「这个模型」和「这个任务难度」两个变量共同作用，不是只看任务难度。** 同一个简单任务上，`claude-sonnet-5` 的 output 随 effort 单调增长（low 22 tokens → max 410 tokens），说明它确实在用 effort 换更多思考；`claude-opus-4-8` 完全不为所动——两个模型对同一个 effort 旋钮的反应可以截然不同。不要无脑对所有模型都开最高档，先确认该模型在类似任务上是否已有「effort 有效」的实证。依据：2026-07-10 smoke matrix。

### 与 model-catalog.yml 的关系

`references/model-catalog.yml` 每个模型条目预留了 `routing_profile`、`discovered_at`、`discovery_evidence` 三个字段。P4（2026-07-10）只回填参与 smoke matrix 的真实可调用型号：`gpt-5.6-sol`/`gpt-5.6-terra`/`gpt-5.6-luna`/`claude-sonnet-5`/`claude-opus-4-8`/`claude-haiku-4-5`；未来价格时期只作为同一模型的 `future_pricing`，不得伪装成第二个 model ID。`gpt-5.5`/`gpt-5.4`/`gpt-5.4-mini` 有运行记录但仍缺 reasoning 生效证据，`routing_profile` 保持 `[]`。未参与矩阵的型号保持未知，不得包装成已验证推荐。

## codex 5.6 系实测分级（2026-07-10，同题对照 8 跑）

> **本节地位（P4 更新，2026-07-10）**：35+15 case smoke matrix 为 Codex/Claude 的**部分覆盖实证**，不能替代全 catalog 矩阵；Gemini/Kimi/OpenCode/Qwen 仍是 blocked/pending。本节收录的是另一批更早的「同题 8 跑深度调研」数据，回答的是“深度调研任务上哪个模型/档位物有所值”，与 smoke matrix 的可调用性/回显维度互为补充，不互相替代。
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

含单引号、特殊字符或 YAML frontmatter 的 prompt **不能**直接嵌入 `bash -c "..."`，也不能不加参数终止符就作为位置参数传入。prompt 以 `-` / `---` 开头时，CLI 可能把正文误判成命令选项。**必须**先写独立文件，并优先通过 stdin 传入：

```bash
# 1. 把 prompt 写入临时文件（按任务 ID 隔离）
# 这是一次性运行产物（SKILL_SPEC.md「脚本写盘决策规则」A 类），用完即可清理
mkdir -p "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/"
cat > "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt" << 'PROMPT_EOF'
你的 prompt 内容，可以包含任意引号和特殊字符...
PROMPT_EOF

# 2a. Codex：用 `-` 明确从 stdin 读取
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check - \
  < "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt"

# 2b. Claude：用本技能脚本从 stdin 读取，prompt 不进入 argv / ps 输出
python3 scripts/run_claude_prompt.py \
  --prompt-file "${TMPDIR:-/tmp}/soia-dev-agent-cli-dispatch/<task-id>/prompt.txt" \
  --model <model-id> --effort high --permission-mode dontAsk \
  --tools Read,Grep,Glob --output-format json
```

如果某个 CLI 不支持 stdin、只能接收位置参数，必须写成 `command [options] -- "$(< "$PROMPT_FILE")"`；其中 `--` 不得省略。长 prompt 仍优先 stdin，避免命令行长度上限和正文暴露在进程列表中。

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

统一调用的字段、状态、预检、模型完整性、断点恢复、回执、危险目录和反虚假修复门禁集中在 [references/dispatch-contract.md](references/dispatch-contract.md)。

调用前只保留这条主流程：

1. 先做 CLI 版本和认证/额度预检，结果为 `hold` 或 `skip` 时停止并说明原因。
2. 固定 `requested_model` 与 `actual_model` 两个字段；无法从执行器输出验证时写 `unknown`，不能用请求值冒充实际值。codex 的 actual_model 以会话头 `model:` 行为唯一权威（models cache 损坏时其自报身份不可信，详见 `references/codex.md`「实战控制规程」）。
3. 批量任务使用可恢复 manifest；每个 case 完成后原子写入状态，失败、降级、超时和未测试不得伪装成通过。
4. 完成回执必须同时给出执行器、模型、用量状态、异常/降级、问题和下一步；未知值保持未知。
5. 涉及危险目录、外部写入或代码代理任务时，先执行参考文件中的安全门禁和真实输出验证。

## 🔴 Codex Prompt 卫生规则（防止 CLI 读治理文件而非写代码）

**多数编码 CLI 在启动时会扫描工作目录**。无关的治理/技能文件会占用 context，但目标仓的适用规则和目标文件不能因此被删掉。

**禁止在代码修复 prompt 里出现以下无关内容**：
- 与目标任务无关的产品 workspace、board、proposal、`AGENTS.md` 或其他 skill 路径
- 与目标无关的技能/子代理调用指令（如 `@xxx-skill`、内部技能前缀名）
- 不适用于目标仓的产品治理流程说明（阶段编号、门禁名称等内部术语）
- 回写指令（可选：需要回写时简化为单行命令）

若目标本身就是 skill package 或 AGENTS 配置，prompt **必须**包含目标仓适用的 `AGENTS.md` 规则和精确 `skills/<skill-name>/...` / 配置文件路径；只排除无关的 SOIA 产品 board/proposal 上下文，不能因路径名含 `skills/` 或 `AGENTS.md` 就删除任务必要输入。

**代码修复 prompt 应只包含**：
1. 工作目录
2. 要修改的文件路径 + 行号
3. 要执行的编辑操作（精确的 before/after）
4. 验证命令（如 `cargo check` / `npm test` / 对应项目的测试命令）
5. 简单回写（可选，一行命令）

**工作目录选择**：
- 派发代码修复任务时，尽量指定较窄的子目录（如具体模块目录而非仓库根），避免 CLI 扫到治理/技能目录
- 若目标是仓级规则、跨 skill 测试或 catalog，仓库根就是必要 workdir；用目标文件 allowlist 和明确禁区控制范围，不得伪造更窄目录

---

## 🔴 CLI 停止处理规程（uncommitted changes 场景）

部分编码 CLI 有治理检查行为：发现工作目录有未提交改动时，可能停下来请求确认。

**触发场景**：工作目录有 staged/unstaged 改动（如另一个并行任务或会话留下的未提交修复）

**处理选项**（在 prompt 末尾写明其中一个）：

```
选项 A — 明确授权继续：
"以下未提交改动是已知用户/上游工作：[列表]。全部保留；只修改本任务 allowlist。若发生文件重叠或基线不符，停止并回报。"

选项 B — 提前 commit 再派：
只有用户在当前任务明确授权 commit，且逐项确认已有改动均属于该提交时，才能在派发前精确 git add + git commit。禁止为了“清理工作目录”打包未知或他人的改动。

选项 C — 在 prompt 里列出改动文件并说明：
"以下文件有未提交改动：[列表]。它们属于其他任务，请保留不动，继续执行本任务。"
```

**推荐**：优先使用经用户批准的隔离 worktree/临时 clone；不能隔离时用选项 C 或带 allowlist 的 A。选项 B 不是默认清理手段，只在 commit 已被明确授权且提交边界已核实时使用。

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
| Antigravity CLI 执行规范 | `references/antigravity-cli.md` | 派发给 agy 或迁移消费者 Google 账号时 |
| Gemini CLI 执行规范 | `references/gemini-cli.md` | 派发给 gemini 时 |
| Kimi CLI 执行规范 | `references/kimi-cli.md` | 派发给 kimi 时 |
| qodercli 执行规范 | `references/qodercli.md` | 派发给 qodercli 时 |
| OpenCode + Qwen 执行规范 | `references/opencode-qwen.md` | 派发给 opencode/qwen 时 |
| 代码文件元数据头规范 | `references/metadata-header.md` | 任何代码写入前 |
| 模型价格资料原文（2026-07-10 快照） | `references/model-pricing-2026-07-10.md` | 需要人工核对官方定价、或价格资料更新时 |
| 模型价格/推理档运行时目录 | `references/model-catalog.yml` | `scripts/estimate_cost.py` / `scripts/run_matrix.py` 运行时读取；人工修改前后都跑一次 `scripts/catalog_lib.py --selftest` |
| P4 部分覆盖路由证据（2026-07-10 smoke matrix 聚合结果） | `references/benchmark-2026-07-10.md` | 需要查已覆盖组合、聚合数字、原始 manifest 缺口或下一轮范围时 |

**加载原则**：派发决策确定执行器后，只加载对应执行器的 reference，不要全部加载。

## Scripts（按需调用）

| 脚本 | 用途 | 自检命令 |
|------|------|----------|
| `scripts/catalog_lib.py` | 受限 YAML 子集解析器 + `model-catalog.yml` schema 校验（重复 model_id / 缺字段 / 负价拒绝，未知 reasoning level 标记为 WARN） | `python3 scripts/catalog_lib.py --selftest` |
| `scripts/estimate_cost.py` | 给定 model + token 数，输出 API 等价费用估算（分项 + 总额 + `confidence`），未知模型给出近似候选并以 exit code 2 退出 | `python3 scripts/estimate_cost.py --selftest` |
| `scripts/run_matrix.py` | 可恢复的串行派发矩阵执行器（P3 用；本文档阶段只用 mock 命令自检，不真实调用任何模型） | `python3 scripts/run_matrix.py --selftest` |
| `scripts/route_model.py` | 从已验证 catalog 记录机械选择模型/推理档并输出固定路由回执；显式指定优先 | `python3 scripts/route_model.py --selftest` |
| `scripts/run_claude_prompt.py` | 从 UTF-8 prompt 文件经 stdin 调用 Claude Code，防 YAML `---` 被误判为选项，并保留结构化 stdout | `python3 scripts/run_claude_prompt.py --selftest` |

所有脚本均为纯 Python 标准库实现，无第三方依赖。修改任意一个后，先跑对应 `--selftest`，再跑其余脚本的自检，确认没有连带破坏（`estimate_cost.py` 和 `run_matrix.py` 都从 `catalog_lib.py` 导入解析/校验逻辑）。
