# 外部 CLI 调度契约参考

这是 `soia-dev-agent-cli-dispatch` 的详细调用契约。正文只保留选择和执行主流程；需要编排外部 CLI、恢复批量任务、核对模型或执行收尾门禁时再加载本文件。

## 内容导航

- 统一调用契约、输入输出字段与未知值处理
- 预检、模型完整性、断点恢复与完成回执
- 危险目录与反虚假修复门禁

## 统一调用契约 / Unified invocation contract

本节定义每一次外部 CLI 调度的输入/输出字段，供你自己的编排层和 `scripts/` 下的脚本共用。术语先对齐：

| 术语 | 含义 |
|---|---|
| `host_ai` | 调用本技能的宿主（任意兼容 Agent；可以是 Claude Code，也可以不是——本技能不绑定单一宿主） |
| `executor_cli` | 被调度的外部 CLI 进程：`codex` / `claude` / `agy` / `gemini` / `kimi` / `opencode` / `qwen`（`qodercli` 有独立命令模板，见 `references/qodercli.md`；`agy` 有账号级运行时模型发现，但没有 API catalog 路由候选） |
| `requested_model` | 本次调用要求使用的模型标识（可以是别名，见 `scripts/catalog_lib.py::find_model` 的宽松匹配规则） |
| `actual_model` | 执行器实际使用的模型标识；只有执行器自己在输出里回显时才能拿到，拿不到就是 `null`，不得编造 |
| `requested_reasoning_effort` | 请求的推理深度/强度参数（不同执行器命名不同） |
| `actual_reasoning_effort` | 执行器实际回显的推理档位；无法可靠读取时为 `null`，不得用请求值冒充 |
| `billing_mode` | `api`（按 token 计费）\| `subscription`（订阅额度）\| `unknown`。决定 `scripts/estimate_cost.py` 的输出是否等于真实扣费——订阅制下永远不等于 |

**输入字段：**

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` | 是 | 本次调用在批次内的唯一标识 |
| `provider` | 是 | `openai` / `anthropic` / `google` / `deepseek` / `antigravity` / 其他；`agy` 使用 `antigravity`，不要按底层模型厂商套 API 价 |
| `executor` | 是 | 见上文 `executor_cli` |
| `model` | 是 | `requested_model`；未显式指定时按「自动路由」选型后再填入 |
| `reasoning` | 否 | `requested_reasoning_effort`；未指定时参考 catalog 的 `default_reasoning_level` |
| `cmd_template` | 是 | 实际执行的 shell 命令（已按「Prompt 注入防护」写好 temp 文件引用） |
| `timeout_seconds` | 否 | 默认 600 秒（见 `scripts/run_matrix.py --timeout-seconds`） |

**输出字段：**

| 字段 | 说明 |
|---|---|
| `status` | 见下方状态枚举 |
| `exit_code` | 子进程退出码；超时未取到时为 `null` |
| `input_tokens` / `cached_input_tokens` / `cache_write_tokens` / `output_tokens` | 分项 Token；执行器不提供时为 `null` |
| `total_tokens` | 已知分项之和；只有总量时可单独填写总量并把 `usage_status` 标为 `partial` |
| `usage_status` / `usage_source` | `measured` / `partial` / `unavailable`，以及数据来自哪个 CLI JSON/stdout |
| `actual_model` | 见上文；解析不到为 `null` |
| `requested_reasoning_effort` / `actual_reasoning_effort` | 请求档位与实际回显档位分开记录 |
| `estimated_api_equivalent_usd` | 由结构化价格和分项 Token 计算；缺少 input/output 拆分时为 `null`，不能把总 Token 全算成 output |
| `provider_reported_cost_usd` | CLI JSON 自报成本，仅作观测值，不自动等同真实账单扣费 |
| `actual_charge_usd` | 只有可靠账单证据时填写；订阅制通常为 `null` |
| `pricing_source` / `pricing_date` | catalog 来源和生效日期 |
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
| `auth_status` | `ok` / `expired` / `unknown` / `blocked_user_action`；优先本地 auth-status。没有该命令时，不得未经确认用模型调用代替 |
| `last_known_quota_state` | 上一次派发记录里的额度状态；没有记录就是 `"unknown"` |
| `recommendation` | `proceed` / `hold` / `skip`，附一句理由 |

预检默认不消耗真实模型调用额度（只做版本探测与官方本地状态检查）。浏览器登录、账号选择或任何 `-p` 模型调用不属于默认预检；前者进入 `blocked_user_action`，后者必须先确认可能的额度/费用。`recommendation` 为 `hold` 或 `skip` 时，不得继续派发，除非客户明确批准。

`scripts/run_matrix.py` 在每次运行开始时会对本批次涉及的 executor 做只读版本探测（`<executor> --version`）并写入 manifest 的 `cli_versions` 字段；`--resume` 时会重新探测并在版本变化时打印警告。**当前脚本不做认证状态检查**——`auth_status` 仍需派发者在预检报告里人工核实或另行探测，脚本本身不会为了验证登录态而发起真实模型调用。

## Model Integrity Gate

保证"客户以为用的模型"和"实际用的模型"一致；出现偏差必须如实报告，不能包装成"任务成功"。

1. **requested vs actual**：每次调用后比对 `requested_model` 与 `actual_model`。
2. **降级判定**：
   - `codex`：stdout 头部若有 `model: xxx` 行，与 `requested_model` 不一致时，状态标记为 `fallback_or_downgrade`（`scripts/run_matrix.py::detect_actual_model` 已实现，只扫描 stdout 前 2000 字符内的 `model:` 行）。
   - `claude`：**P4（2026-07-10）更新**——纯文本模式（`cmd_template` 不含 `--output-format json`）下 headless 输出仍然**没有**可靠的模型回显机制，任何成功调用一律标记 `actual_model_unverified`，**不允许**因为"看起来跑成功了"就报告为 `passed`。但当 `cmd_template` 显式带 `--output-format json`（或 `--output-format=json`）时，`scripts/run_matrix.py::detect_actual_model` 会解析 stdout JSON 的 `modelUsage`（键名即模型 id）或顶层 `model` 字段作为 `actual_model`，与 `requested_model` 比对后可以正常判定 `passed` / `fallback_or_downgrade`，不再一律 `actual_model_unverified`。比对前会先剥离两种已在真实 CLI（2.1.206，2026-07-10 实测验证，非猜测）上观察到的修饰后缀：不带 `--model` 时回显可能带方括号执行模式后缀（如 `claude-opus-4-8[1m]`）；用短别名（如 `haiku`）请求时回显可能带日期后缀（如 `claude-haiku-4-5-20251001`）；显式传完整 catalog `model_id`（如 `claude-haiku-4-5`）时回显通常精确匹配、无后缀。stdout 不是合法 JSON 时仍然回退到 `actual_model_unverified`，不假装已验证。细节与原始验证 payload 见 `references/benchmark-2026-07-10.md`。
   - 其他执行器（agy/gemini/kimi/opencode/qwen）：Phase 1 未实现模型回显检测，`notes` 会如实写明"model-echo verification is not implemented for this executor"，不假装已覆盖。
3. **宿主模型变化**：`host_ai` 自身运行在哪个底层模型上，属于**仅可观测、不可控**的信息——本技能不能对宿主自己的模型完整性做强制门禁。如果宿主环境暴露了自身模型标识，记录下来即可；拿不到就写 `unknown`，不要推断。
4. **能力限制声明**：任何一次 Model Integrity Gate 判定为 `actual_model_unverified` 或 `fallback_or_downgrade` 的调用，最终回执必须包含这次判定，不能只在内部日志里留痕、对客户只报"完成"。
5. **严格版本别名**：方括号执行模式后缀可以剥离；日期版模型标识不得通用截断，只能通过 catalog 的 `actual_model_aliases` 显式映射。未登记的日期版本必须判为 mismatch，防止真实换模被归一化掩盖。

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
- requested_reasoning_effort: <请求档位，或 "unknown">
- actual_reasoning_effort: <实际回显档位，或 "unverified">

Token 与费用：
- input_tokens: <数字，或 "unknown">
- cached_input_tokens: <数字，或 "unknown">
- cache_write_tokens: <数字，或 "unknown">
- output_tokens: <数字，或 "unknown">
- total_tokens: <数字，或 "unknown">
- usage_status: <measured | partial | unavailable>
- usage_source: <CLI JSON/stdout 来源，或 "unavailable">
- estimated_api_equivalent_usd: <金额，或 "unavailable">
- provider_reported_cost_usd: <金额，或 "unavailable">
- actual_charge_usd: <可靠账单值，或 "unknown">
- pricing_source: <catalog source，或 "unknown">
- pricing_date: <价格生效日期，或 "unknown">
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

**组合验收防假绿（2026-07-11 实测）**：同一 shell 中连续跑多条检查时，必须使用 `set -e`（需要管道时用 `set -euo pipefail`）或逐条保存并核对退出码。否则前面的 unit test 失败可能被最后一条成功命令覆盖，整个组合命令仍返回 0；此类结果一律作废并按 fail-fast 方式重跑。

---
