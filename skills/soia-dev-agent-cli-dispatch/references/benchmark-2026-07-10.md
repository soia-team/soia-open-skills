# 2026-07-10 同题 smoke 矩阵实测记录 / 2026-07-10 same-fixture smoke matrix

> **用途**：本文件是「自动路由 / Auto-routing」表格从 `pending_benchmark` 占位升级为实证推荐（P4）
> 的证据来源，收录两个独立 run 的聚合结果：codex 侧 35 case（`run_id: smoke-20260710`）与
> claude 侧 15 case（`run_id: smoke-claude-json-20260710`）。两个 run 同一天（2026-07-10）跑同一类
> fixture：固定算术 + model 回显任务（要求模型做一次简单计算并让执行器把实际使用的模型/token/成本
> 回显出来，用于核验 Model Integrity Gate，而不是测试模型的推理深度）。
>
> **诚实边界（务必先读）**：本文件转述的是任务交接时给出的**聚合结论**，不是 `scripts/run_matrix.py`
> 产出的原始 `manifest.json` 逐 case dump——那份原始文件本身未随交接提供。凡是交接材料给出了具体数字
> 的地方，以下如实照抄；凡是只给出聚合结论、没有给出逐 case 明细的地方，本文件明确写"未单独报告"，
> **不做插值或推测填充**。若需要逐 case 复核，请重新用 `scripts/run_matrix.py` 生成 `cases.json` 并
> 实际跑一次，或索取对应 `run_id` 的原始 `manifest.json`。
>
> 与 SKILL.md 现有「codex 5.6 系实测分级」节的关系：那一节收录的是**另一批、更早**的「同题 8 跑深度
> 调研」对照数据（sol/terra/luna/gpt-5.5 在同一个复杂调研任务上的产出深度/成本对比），维度是"这个模型
> 在深度调研任务上的表现"；本文件的 35+15 case smoke 矩阵维度是"这个模型/推理档在一个简单固定任务上
> 能不能正常跑、模型回显是否可信、effort 参数是否真的影响输出"。两者互为补充，不重复摘录，SKILL.md
> 保留原节不变。

## 1. codex 侧：35-case exit-code smoke 矩阵（`run_id: smoke-20260710`）

**Fixture**：固定算术 + model 回显任务，覆盖 6 个模型：`gpt-5.6-sol`、`gpt-5.6-terra`、
`gpt-5.6-luna`、`gpt-5.4`、`gpt-5.4-mini`、`gpt-5.5`。

**顶层结果**：35 个 case 中，29 个 exit 0 通过，6 个是以下明确例外（35 − 6 = 29，已核算）：

| 模型 | 推理档 | 结果 | 说明 |
|---|---|---|---|
| gpt-5.6-sol | minimal | `unsupported` | codex 5.6 系明确不支持 minimal 档（拒绝式失败，不是运行时报错） |
| gpt-5.6-terra | minimal | `unsupported` | 同上 |
| gpt-5.6-luna | minimal | `unsupported` | 同上 |
| gpt-5.4 | minimal | `failed` | 报错退出（非 unsupported 的拒绝式失败，是运行时错误） |
| gpt-5.4-mini | minimal | `failed` | 同上 |
| gpt-5.5 | minimal | `failed` | 同上 |

**按模型汇总的推理档结论**（这是聚合结论的原文转述，刻意区分"已确认可用"与"本次未报错但未确认"两类，
不要混为一谈）：

| 模型 | 已确认可用（low/medium/high/xhigh 全部 exit 0，且与旧 8 跑深度调研交叉印证） | 已确认失败 | 状态 |
|---|---|---|---|
| gpt-5.6-sol | low, medium, high, xhigh | minimal（unsupported） | **实证收敛**：`supported_reasoning_levels` 已回填为 `[low, medium, high, xhigh]` |
| gpt-5.6-terra | low, medium, high, xhigh | minimal（unsupported） | 同上 |
| gpt-5.6-luna | low, medium, high, xhigh | minimal（unsupported） | 同上 |
| gpt-5.4 | 无（"另需实测"，见下） | minimal（failed，报错） | 本次 minimal 之外的档位不在明确例外清单里（因此技术上 exit 0），但交接材料明确标注"另需实测"，**不构成"已确认可用"的结论**，只表示"本次没报错" |
| gpt-5.4-mini | 无（"另需实测"） | minimal（failed，报错） | 同上 |
| gpt-5.5 | 无（"另需实测"） | minimal（failed，报错） | 同上；另有旧 8 跑深度调研数据（见 §3），但那是不同维度的任务 |

**为什么 gpt-5.4/5.4-mini/5.5 的 low/medium/high/xhigh 不直接标"已确认可用"**：顶层结果明确说
"全部 exit 0 通过除以下 6 个例外"，也就是说这三个模型在非 minimal 档位上确实 exit 0 了；但交接材料
额外加了一句"5.4 系另需实测"，这是一个比"exit 0"更谨慎的判断——很可能是因为本 fixture 是一个极简单的
固定算术任务，"exit 0"不足以证明 reasoning 参数被真正采纳/生效（不像 5.6 系那样有旧 8 跑深度调研的
交叉印证）。本文件如实保留这个更谨慎的结论，不因为"技术上没报错"就升级为"确认支持"。

## 2. claude 侧：15-case `--output-format json` smoke 矩阵（`run_id: smoke-claude-json-20260710`）

**Fixture**：同一固定算术 + model 回显任务，通过 `claude --print --output-format json --model <model>
--effort <level>` 调用，从返回的 JSON 里的 `modelUsage`（键即模型 id）读取真实 model/usage/cost；
覆盖 3 个模型 × 5 个 effort 档（`low`/`medium`/`high`/`xhigh`/`max`）= 15 case，与 case 总数精确吻合。

**顶层结果**：15/15 exit 0；**零降级**——15/15 requested model == actual model（比对 JSON 的
`modelUsage` 键）；15/15 固定算术题计算正确；`--effort` 的 5 个档位全部被 CLI 接受（无一个报
invalid/unsupported）。

| 模型 | effort | 输出 tokens | 单次成本 (USD) | 说明 |
|---|---|---|---|---|
| claude-sonnet-5 | low | 22 | $0.0445 | |
| claude-sonnet-5 | medium | 未单独报告 | 未单独报告 | 交接材料只给出 low/max 两个端点，未给中间档具体数字，此处不插值 |
| claude-sonnet-5 | high | 未单独报告 | 未单独报告 | 同上 |
| claude-sonnet-5 | xhigh | 未单独报告 | 未单独报告 | 同上 |
| claude-sonnet-5 | max | 410 | $0.0503 | output 变为 low 的约 18.6 倍（410/22 ≈ 18.6，即增长约 17.6 倍：(410-22)/22 ≈ 17.6），cost 只增长约 13%（(0.0503-0.0445)/0.0445 ≈ 13.0%，均为本文件自行核算，注意"变为 N 倍"与"增长 N 倍"是两个不同的数，不要混用） |
| claude-opus-4-8 | low | 22 | $0.0677 | 五档数值完全相同（见下） |
| claude-opus-4-8 | medium | 22 | $0.0677 | 同上 |
| claude-opus-4-8 | high | 22 | $0.0677 | 同上 |
| claude-opus-4-8 | xhigh | 22 | $0.0677 | 同上 |
| claude-opus-4-8 | max | 22 | $0.0677 | 同上；**反模式**：effort 对本任务无测量得到的效果 |
| claude-haiku-4-5 | low/medium/high/xhigh/max（聚合） | 未单独报告 | 聚合 $0.0037/call | 交接材料只给出跨 5 档的聚合成本，未按档位拆分；比 opus 便宜约 18.3 倍（0.0677/0.0037 ≈ 18.30，本文件自行核算，与交接材料"约 18 倍"的说法一致） |

**本文件自行核算的两条推论**（标注为推论，不是交接材料原文，供理解经济学含义参考）：
- sonnet-5 的 output token 从 22 增到 410（+约 17.6 倍新增部分：(410-22)/22 ≈ 17.6），但总成本只从
  $0.0445 涨到 $0.0503（+约 13%）——output 定价（$10/1M token）本身占比很小，多数成本来自输入侧的
  cache 读写（可参照本技能作者在实现阶段对 `claude --output-format json` 做的一次真实探测调用：单次
  ping 里 `cache_read_input_tokens` 上万，远超个位数的 `input_tokens`）。这解释了"output 涨很多、
  cost 涨很少"的现象，但**这条解释本身是推论，不是 smoke matrix 报告原文**。
- opus-4-8 五档完全同值，说明 CLI **接受**了全部 5 个 `--effort` 值（不是被拒绝/报错），只是这次
  fixture 任务上模型没有据此产出可测量的差异——"接受但无效果"和"不支持"是两个不同的结论，不要混淆。

## 3. 与既有「codex 5.6 系实测分级」节的关系（不重复摘录）

SKILL.md 的「codex 5.6 系实测分级」节收录了 2026-07-10 的另一批「同题 8 跑深度调研」数据：同一批模型
（`sol`/`terra`/`luna`/`gpt-5.5`）在一个复杂调研任务上跑 8 次的产出深度、token 用量和耗时对比
（例如 sol 在 `xhigh` 档 996s / 246k tokens、terra 在 `medium` 档全程最省 87k tokens、luna 在
`xhigh` 档烧到 933k tokens 但无独有发现、gpt-5.5 全场最快 190s）。那批数据回答的问题是"哪个模型/档位
在**深度调研任务**上物有所值"；本文件的 35+15 case smoke 矩阵回答的问题是"这个模型/推理档在一个
**简单固定任务**上能不能正常跑、模型回显是否可信"。两者结论方向一致（例如都认为 sol 的 `xhigh` 有
质变而 luna 的 `xhigh` 只烧钱），但样本和任务类型不同，不应互相替代或合并成一份表格。

## 4. 本次 P4 回填清单（去向）

以下字段/文档已根据本文件的实证结论回填，不再是 `pending_benchmark` 占位：

- `references/model-catalog.yml`：`gpt-5.6-sol`/`gpt-5.6-terra`/`gpt-5.6-luna`/`claude-sonnet-5`/
  `claude-sonnet-5-2026-09-01`/`claude-opus-4-8`/`claude-haiku-4-5` 的 `routing_profile` /
  `discovered_at` / `discovery_evidence` 从 `null` 回填为实证值；`gpt-5.5`/`gpt-5.4`/`gpt-5.4-mini`
  的 `discovered_at` / `discovery_evidence` 回填，但 `routing_profile` 保持 `[]`（已测试、暂无路由
  推荐，等待"另需实测"的缺口补齐）；claude 三个模型的 `supported_reasoning_levels` 回填为
  `[low, medium, high, xhigh, max]`。未出现在本文件矩阵里的模型（gemini/kimi/opencode/qwen 全家族、
  deepseek、其余 claude/openai 型号）保持原样不动，仍是未知状态，不得假装已验证。
- SKILL.md「自动路由 / Auto-routing」节的「推荐组合」表：codex 与 claude 两行升级为实证路由并注明
  依据；gemini/kimi/opencode/qwen 三行保持 `pending_benchmark`，如实标注"未测"。

## 5. 实现阶段的补充技术验证：`modelUsage` 键名修饰后缀（非 smoke matrix 原文）

> **来源区分（务必先读）**：本节内容不是交接材料给出的 15-case smoke matrix 原文，而是 P4 实现
> `scripts/run_matrix.py` 的 claude adapter 时，为了确认 JSON 解析逻辑对不对，对本机已安装的
> `claude` 2.1.206 CLI 额外做的 3 次真实探测调用（均为读一次 `2+2` 的极简任务，成本共约 $0.19）。
> 这是**本次实现的独立验证**，不是对 15-case smoke matrix 本身的重新执行或篡改——15-case 的聚合结论
> （零降级、15/15 correct）保持不变，照抄自交接材料。之所以收录在这里，是因为它解释了 P4 的
> `run_matrix.py` 为什么要做"剥离后缀再比较"这一步，而不是直接用 `==`。

探测 1——不带 `--model`（用会话默认模型）：

```
$ claude --print --output-format json --permission-mode bypassPermissions "what is 2+2? reply with only the number"
```

返回 JSON 的 `modelUsage` 键为 `"claude-opus-4-8[1m]"`（不是裸的 `claude-opus-4-8`）——带一个方括号修饰后缀，推测是 1M 上下文窗口的执行模式标记（`model-catalog.yml` 里 `claude-opus-4-8` 的 `context_window` 恰好是 `1000000`，与此吻合，但这只是推断，未找到官方文档逐字确认）。

探测 2——用短别名 `--model haiku`：

```
$ claude --print --output-format json --permission-mode bypassPermissions --model haiku --effort low "what is 2+2? reply with only the number"
```

返回 JSON 的 `modelUsage` 键为 `"claude-haiku-4-5-20251001"`——带一个日期后缀（`-20251001`），不等于 catalog 的 `model_id`（`claude-haiku-4-5`），也不等于请求时用的别名字符串（`haiku`）。若不做归一化，naive 字符串比较会把这次成功调用误判为 `fallback_or_downgrade`。

探测 3——用完整 catalog `model_id`：`--model claude-haiku-4-5`：

```
$ claude --print --output-format json --permission-mode bypassPermissions --model claude-haiku-4-5 --effort low "what is 2+2? reply with only the number"
```

返回 JSON 的 `modelUsage` 键精确等于 `"claude-haiku-4-5"`——与请求值完全一致，无任何修饰。

**结论**：`--model` 传完整 catalog `model_id`（而不是短别名，也不省略）时，`modelUsage` 键回显精确、无后缀；这与交接材料"15/15 requested == actual"的说法一致，说明当时的 15-case matrix 很可能也是用完整 `model_id` 发起调用的。但既然探测 1/2 证明了方括号后缀和日期后缀在这个 CLI 版本上是真实会出现的行为（不是假设），`run_matrix.py::_normalize_claude_model_id` 按这两种模式做剥离后再比较，比单纯 `==` 更稳健，不影响对已给出的"15/15"这个既有结论的转述。

## 6. 仍然未知、需要下一轮验证的缺口

- gpt-5.4 / gpt-5.4-mini / gpt-5.5 在 low/medium/high/xhigh 档位上的表现只确认"本次 exit 0"，未确认
  "reasoning 参数被真正采纳"（需要类似 5.6 系的深度调研交叉印证，或更细粒度的输出内容检查）。
- claude-sonnet-5 的 medium/high/xhigh 档具体 output token 数与成本未单独报告，只知道 low→max 单调
  递增的两个端点；如需精确的五档曲线，需要重新采集或索取原始 manifest。
- claude-haiku-4-5 未按 effort 档拆分数据，只有聚合成本；haiku 是否像 sonnet 一样对 effort 敏感、还是
  像 opus 一样不敏感，本次数据不足以判断。
- opus-4-8"对本任务 effort 无效"的结论只在这一个简单 fixture 上成立；本文件明确不把它泛化成"opus 的
  effort 参数整体无用"，硬任务上的表现需要专门测试。
- gemini / kimi / opencode / qwen 全家族在本轮完全未测试，路由表对应行继续标 `pending_benchmark`。
