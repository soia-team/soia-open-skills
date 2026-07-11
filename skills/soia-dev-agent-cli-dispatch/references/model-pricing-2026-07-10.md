# 模型价格资料（2026-07-10 快照）/ Model pricing snapshot (2026-07-10)

> **来源与用途**：本文件是 2026-07-10 版模型价格调研原文的**原样收录**存档，未做任何数字改写。
> 运行时定价查询、脚本计算（`scripts/estimate_cost.py`、`scripts/run_matrix.py`）一律读取
> **`references/model-catalog.yml`**（从本文件规范化提取的结构化数据），不要让脚本直接解析本
> Markdown 文件。
>
> **正式预算、采购或生产上线前，请以各厂商官方定价页为准**（见下文「11. 官方来源」），本文件与
> `model-catalog.yml` 仅供派发决策和成本估算参考，可能滞后于官方页面的实时调整。
>
> 与 `model-catalog.yml` 的已知计数差异：本文件标题声明覆盖 **29 个模型**；直接清点本文件得到
> OpenAI 10 / Anthropic 10（不同型号；Sonnet 5 因推广价/标准价两个时间段被记为 2 个价格条目，
> 使 Anthropic 在 `model-catalog.yml` 中呈现为 11 行）/ Google 7（3.5-flash、3.1-flash-lite、
> 3.1-pro-preview、3-flash-preview、2.5-pro、2.5-flash、2.5-flash-lite）/ DeepSeek 2，
> 10+10+7+2=29，与标题一致。若你在别处看到「Google 8」的说法，那是一个未经复核的概述数字，
> 以本文件实际表格清点结果（7）和 `model-catalog.yml` 为准。

---

# AI 模型 API 价格完整对比

> **更新时间：2026-07-10**  
> **货币：美元（USD）**  
> **Token 单位：每 100 万 Token（MTok），除非表格另有说明。**

## 1. 范围与计价口径

本文件覆盖 OpenAI、Anthropic、Google Gemini 和 DeepSeek 当前重点的**通用、推理与编程文本模型**，并包含：

- 标准实时 API；
- 缓存输入、缓存写入与缓存存储；
- Batch、Flex、Priority、Fast 等服务档；
- 长上下文阶梯价格；
- 推理/思考 Token 的计费方式；
- 联网搜索、文件搜索和代码执行等常见工具附加费。

本文件**不把 ChatGPT、Claude Code、Gemini App 等月度订阅额度混入 API 价格**。Antigravity CLI 的套餐额度、账号级模型可用性和 AI credit overage 也不在本表范围内；不得用这里的 Gemini/Claude API 单价推导 `agy` 实际扣费。也不完整展开专用图像、视频、实时语音和 TTS 模型，因为它们使用不同的模态或按秒/分钟计价。

### 统一计算公式

```text
API 总费用
= 普通输入 Token × 输入单价
+ 缓存写入 Token × 缓存写入单价
+ 缓存读取 Token × 缓存读取单价
+ 可见回答与隐藏推理 Token × 输出单价
+ 工具调用费用
+ 缓存存储费用
+ 地域/优先级等附加倍率
```

“**1M 输入 + 1M 输出**”列仅用于直观比较，假设：

- 输入全部为普通、未缓存输入；
- 计费输出合计为 100 万 Token；
- 不含工具费、存储费、税费和地域溢价；
- 对 Gemini Pro 使用不超过 200K 的标准档；
- 对 OpenAI 使用短上下文标准档；
- Claude Sonnet 5 使用截至 2026-08-31 的当前推广价。

---

## 2. 统一标准 API 总表

| 厂商 | 模型 | 标准输入 | 缓存输入/命中 | 标准输出 | 1M 输入+1M 输出 | Batch/Flex 输入/输出 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | `gpt-5.6-sol` | $5 | $0.5 | $30 | $35 | $2.5 / $15 | 短上下文；长上下文另见后表 |
| OpenAI | `gpt-5.6-terra` | $2.5 | $0.25 | $15 | $17.5 | $1.25 / $7.5 | 短上下文；长上下文另见后表 |
| OpenAI | `gpt-5.6-luna` | $1 | $0.1 | $6 | $7 | $0.5 / $3 | 短上下文；长上下文另见后表 |
| OpenAI | `gpt-5.5` | $5 | $0.5 | $30 | $35 | $2.5 / $15 | 短上下文；长上下文另见后表 |
| OpenAI | `gpt-5.5-pro` | $30 | — | $180 | $210 | $15 / $90 | 短上下文；高价 Pro 档 |
| OpenAI | `gpt-5.4` | $2.5 | $0.25 | $15 | $17.5 | $1.25 / $7.5 | 短上下文；长上下文另见后表 |
| OpenAI | `gpt-5.4-mini` | $0.75 | $0.075 | $4.5 | $5.25 | $0.375 / $2.25 | 未列长上下文阶梯价 |
| OpenAI | `gpt-5.4-nano` | $0.2 | $0.02 | $1.25 | $1.45 | $0.1 / $0.625 | 未列长上下文阶梯价 |
| OpenAI | `gpt-5.4-pro` | $30 | — | $180 | $210 | $15 / $90 | 短上下文；高价 Pro 档 |
| OpenAI | `gpt-5.3-codex` | $1.75 | $0.175 | $14 | $15.75 | — | Codex 专用；支持 Priority |
| Anthropic | Claude Fable 5 | $10 | $1 | $50 | $60 | $5 / $25 | 1M 上下文，标准价无长上下文附加费 |
| Anthropic | Claude Mythos 5 | $10 | $1 | $50 | $60 | $5 / $25 | 限量开放；1M 上下文 |
| Anthropic | Claude Opus 4.8 | $5 | $0.5 | $25 | $30 | $2.5 / $12.5 | 1M 上下文；另有 Fast mode |
| Anthropic | Claude Opus 4.7 | $5 | $0.5 | $25 | $30 | $2.5 / $12.5 | 1M 上下文；Fast mode 将于 2026-07-24 移除 |
| Anthropic | Claude Opus 4.6 | $5 | $0.5 | $25 | $30 | $2.5 / $12.5 | 1M 上下文 |
| Anthropic | Claude Opus 4.5 | $5 | $0.5 | $25 | $30 | $2.5 / $12.5 | 当前标准价格 |
| Anthropic | Claude Sonnet 5 | $2 | $0.2 | $10 | $12 | $1 / $5 | 推广价至 2026-08-31；之后为 $3/$15 |
| Anthropic | Claude Sonnet 4.6 | $3 | $0.3 | $15 | $18 | $1.5 / $7.5 | 1M 上下文 |
| Anthropic | Claude Sonnet 4.5 | $3 | $0.3 | $15 | $18 | $1.5 / $7.5 | 当前标准价格 |
| Anthropic | Claude Haiku 4.5 | $1 | $0.1 | $5 | $6 | $0.5 / $2.5 | 低成本 Claude |
| Google | `gemini-3.5-flash` | $1.5 | $0.15 | $9 | $10.5 | $0.75 / $4.5 | 输出价包含 thinking tokens |
| Google | `gemini-3.1-flash-lite` | $0.25 | $0.025 | $1.5 | $1.75 | $0.125 / $0.75 | 文本/图片/视频输入价 |
| Google | `gemini-3.1-pro-preview` ≤200K | $2 | $0.2 | $12 | $14 | $1 / $6 | 超过 200K 进入高价档 |
| Google | `gemini-3-flash-preview` | $0.5 | $0.05 | $3 | $3.5 | $0.25 / $1.5 | 输出价包含 thinking tokens |
| Google | `gemini-2.5-pro` ≤200K | $1.25 | $0.125 | $10 | $11.25 | $0.625 / $5 | 超过 200K 进入高价档 |
| Google | `gemini-2.5-flash` | $0.3 | $0.03 | $2.5 | $2.8 | $0.15 / $1.25 | 文本/图片/视频输入价 |
| Google | `gemini-2.5-flash-lite` | $0.1 | $0.01 | $0.4 | $0.5 | $0.05 / $0.2 | 文本/图片/视频输入价 |
| DeepSeek | `deepseek-v4-flash` | $0.14 | $0.0028 | $0.28 | $0.42 | — | 输入列为缓存未命中；1M 上下文 |
| DeepSeek | `deepseek-v4-pro` | $0.435 | $0.003625 | $0.87 | $1.305 | — | 输入列为缓存未命中；1M 上下文 |

> 注意：DeepSeek 的“标准输入”是**缓存未命中**价格；它的缓存命中价格非常低。  
> Gemini 的输出价格明确包含 thinking tokens。OpenAI、Claude 和 DeepSeek 的推理/思考输出也会计入相应输出用量。

---

## 3. 按“1M 普通输入 + 1M 计费输出”排序

| 排名 | 厂商 | 模型 | 1M 输入+1M 输出 |
| --- | --- | --- | --- |
| 1 | DeepSeek | `deepseek-v4-flash` | $0.42 |
| 2 | Google | `gemini-2.5-flash-lite` | $0.5 |
| 3 | DeepSeek | `deepseek-v4-pro` | $1.305 |
| 4 | OpenAI | `gpt-5.4-nano` | $1.45 |
| 5 | Google | `gemini-3.1-flash-lite` | $1.75 |
| 6 | Google | `gemini-2.5-flash` | $2.8 |
| 7 | Google | `gemini-3-flash-preview` | $3.5 |
| 8 | OpenAI | `gpt-5.4-mini` | $5.25 |
| 9 | Anthropic | Claude Haiku 4.5 | $6 |
| 10 | OpenAI | `gpt-5.6-luna` | $7 |
| 11 | Google | `gemini-3.5-flash` | $10.5 |
| 12 | Google | `gemini-2.5-pro` ≤200K | $11.25 |
| 13 | Anthropic | Claude Sonnet 5 | $12 |
| 14 | Google | `gemini-3.1-pro-preview` ≤200K | $14 |
| 15 | OpenAI | `gpt-5.3-codex` | $15.75 |
| 16 | OpenAI | `gpt-5.6-terra` | $17.5 |
| 17 | OpenAI | `gpt-5.4` | $17.5 |
| 18 | Anthropic | Claude Sonnet 4.6 | $18 |
| 19 | Anthropic | Claude Sonnet 4.5 | $18 |
| 20 | Anthropic | Claude Opus 4.8 | $30 |
| 21 | Anthropic | Claude Opus 4.7 | $30 |
| 22 | Anthropic | Claude Opus 4.6 | $30 |
| 23 | Anthropic | Claude Opus 4.5 | $30 |
| 24 | OpenAI | `gpt-5.6-sol` | $35 |
| 25 | OpenAI | `gpt-5.5` | $35 |
| 26 | Anthropic | Claude Fable 5 | $60 |
| 27 | Anthropic | Claude Mythos 5 | $60 |
| 28 | OpenAI | `gpt-5.5-pro` | $210 |
| 29 | OpenAI | `gpt-5.4-pro` | $210 |

这个排序只表示 Token 单价，不表示完成同一任务的真实总成本。高成功率模型可能减少返工、工具调用和上下文往返；低价模型也可能因为重复尝试而扩大实际 Token 消耗。

---

# 4. OpenAI 详细价格

## 4.1 标准短上下文、Batch/Flex 与 Priority

单位均为 USD / MTok。Batch 和 Flex 在当前表中价格相同。

| 模型 | 输入 | 缓存输入 | 缓存写入 | 输出 | Batch/Flex：输入/缓存/写入/输出 | Priority：输入/缓存/写入/输出 |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-5.6-sol` | $5 | $0.50 | $6.25 | $30 | $2.50 / $0.25 / $3.125 / $15 | $10 / $1 / $12.50 / $60 |
| `gpt-5.6-terra` | $2.50 | $0.25 | $3.125 | $15 | $1.25 / $0.125 / $1.5625 / $7.50 | $5 / $0.50 / $6.25 / $30 |
| `gpt-5.6-luna` | $1 | $0.10 | $1.25 | $6 | $0.50 / $0.05 / $0.625 / $3 | $2 / $0.20 / $2.50 / $12 |
| `gpt-5.5` | $5 | $0.50 | — | $30 | $2.50 / $0.25 / — / $15 | $12.50 / $1.25 / — / $75 |
| `gpt-5.5-pro` | $30 | — | — | $180 | $15 / — / — / $90 | — |
| `gpt-5.4` | $2.50 | $0.25 | — | $15 | $1.25 / $0.13 / — / $7.50 | $5 / $0.50 / — / $30 |
| `gpt-5.4-mini` | $0.75 | $0.075 | — | $4.50 | $0.375 / $0.0375 / — / $2.25 | $1.50 / $0.15 / — / $9 |
| `gpt-5.4-nano` | $0.20 | $0.02 | — | $1.25 | $0.10 / $0.01 / — / $0.625 | — |
| `gpt-5.4-pro` | $30 | — | — | $180 | $15 / — / — / $90 | — |
| `gpt-5.3-codex` | $1.75 | $0.175 | — | $14 | 官方未列 | $3.50 / $0.35 / — / $28 |

## 4.2 OpenAI 长上下文价格

当支持阶梯计价的请求进入长上下文档时，使用以下价格。GPT-5.6 和 GPT-5.5 的官方模型说明将长上下文触发点描述为**整次请求输入超过 272K Token**；定价页也为 GPT-5.4 系列列出了对应长上下文档。

| 模型 | 长上下文输入 | 缓存输入 | 缓存写入 | 输出 | 1M 输入+1M 输出 |
| --- | --- | --- | --- | --- | --- |
| `gpt-5.6-sol` | $10 | $1 | $12.50 | $45 | $55 |
| `gpt-5.6-terra` | $5 | $0.50 | $6.25 | $22.50 | $27.50 |
| `gpt-5.6-luna` | $2 | $0.20 | $2.50 | $9 | $11 |
| `gpt-5.5` | $10 | $1 | — | $45 | $55 |
| `gpt-5.5-pro` | $60 | — | — | $270 | $330 |
| `gpt-5.4` | $5 | $0.50 | — | $22.50 | $27.50 |
| `gpt-5.4-pro` | $60 | — | — | $270 | $330 |

### OpenAI 特别说明

1. `gpt-5.4-mini` 和 `gpt-5.4-nano` 的当前定价表没有列出单独的长上下文阶梯价格。
2. OpenAI 对 2026-03-05 及以后发布、支持数据驻留的模型，区域处理端点可能加收 **10%**。
3. `gpt-5.3-codex` 的标准价格为 $1.75 输入、$0.175 缓存输入、$14 输出；Priority 为 $3.50、$0.35、$28。
4. 推理 Token 属于输出用量的一部分，高 reasoning effort 通常增加输出侧的计费 Token。

---

# 5. Anthropic Claude 详细价格

| 模型 | 基础输入 | 5分钟写缓存 | 1小时写缓存 | 缓存命中/刷新 | 输出 | Batch 输入/输出 | 长上下文/Fast |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Fable 5 | $10 | $12.50 | $20 | $1 | $50 | $5 / $25 | 1M，无附加价 |
| Claude Mythos 5 | $10 | $12.50 | $20 | $1 | $50 | $5 / $25 | 限量开放；1M |
| Claude Opus 4.8 | $5 | $6.25 | $10 | $0.50 | $25 | $2.50 / $12.50 | 1M；Fast $10/$50 |
| Claude Opus 4.7 | $5 | $6.25 | $10 | $0.50 | $25 | $2.50 / $12.50 | 1M；Fast $30/$150，2026-07-24 移除 |
| Claude Opus 4.6 | $5 | $6.25 | $10 | $0.50 | $25 | $2.50 / $12.50 | 1M；Fast 已不可用 |
| Claude Opus 4.5 | $5 | $6.25 | $10 | $0.50 | $25 | $2.50 / $12.50 | 标准价 |
| Claude Sonnet 5（至 2026-08-31） | $2 | $2.50 | $4 | $0.20 | $10 | $1 / $5 | 推广价；1M |
| Claude Sonnet 5（自 2026-09-01） | $3 | $3.75 | $6 | $0.30 | $15 | $1.50 / $7.50 | 恢复标准价；1M |
| Claude Sonnet 4.6 | $3 | $3.75 | $6 | $0.30 | $15 | $1.50 / $7.50 | 1M，无附加价 |
| Claude Sonnet 4.5 | $3 | $3.75 | $6 | $0.30 | $15 | $1.50 / $7.50 | 标准价 |
| Claude Haiku 4.5 | $1 | $1.25 | $2 | $0.10 | $5 | $0.50 / $2.50 | 低成本档 |

## 5.1 Claude 缓存规则

Claude 的 Prompt Caching 相对基础输入价格采用固定倍率：

| 缓存操作 | 相对基础输入价格 | 有效期 |
| --- | ---: | --- |
| 5 分钟写缓存 | 1.25× | 5 分钟 |
| 1 小时写缓存 | 2× | 1 小时 |
| 缓存命中/刷新 | 0.1× | 延续前一次写入的有效期 |

## 5.2 Claude 长上下文与地域费用

- Fable 5、Mythos 5、Opus 4.8/4.7/4.6、Sonnet 5 和 Sonnet 4.6 的完整 1M 上下文按标准单价计费，不收额外长上下文阶梯费。
- 对 Opus 4.6、Sonnet 4.6 及更新型号，使用 `inference_geo: "us"` 会在输入、输出、缓存写入和缓存读取价格上乘以 **1.1**；默认全球路由使用标准价。
- Opus 4.7 及更新 Opus、Fable 5、Mythos 5 和 Sonnet 5 使用新 tokenizer。同一文本可能比 Sonnet 4.6 及更早型号产生约 **30% 更多 Token**；实际增幅依内容而变，因此不能只比较每 MTok 单价。
- Claude 的 extended/adaptive thinking Token 按输出 Token 价格计费，并受 `max_tokens` 等输出预算约束。

---

# 6. Google Gemini 详细价格

Google 将模型可见输出和 thinking tokens 合并到输出计费中。表中的音频输入列仅在官方为该模型列出不同音频单价时单独显示。

| 模型 | 服务档 | 文本/图像/视频输入 | 音频输入 | 输出（含思考） | 缓存读取 | 缓存存储 | 1M文本输入+1M输出 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemini-3.5-flash` | Standard | $1.50 | — | $9 | $0.15 | $1/MTok/小时 | $10.50 |
| `gemini-3.5-flash` | Batch | $0.75 | — | $4.50 | $0.075 | $1/MTok/小时 | $5.25 |
| `gemini-3.5-flash` | Flex | $0.75 | — | $4.50 | $0.08 | $1/MTok/小时 | $5.25 |
| `gemini-3.5-flash` | Priority | $2.70 | — | $16.20 | $0.27 | $1/MTok/小时 | $18.90 |
| `gemini-3.1-flash-lite` | Standard | $0.25 | $0.50 | $1.50 | $0.025 / $0.05 | $1/MTok/小时 | $1.75 |
| `gemini-3.1-flash-lite` | Batch / Flex | $0.125 | $0.25 | $0.75 | $0.0125 / $0.025 | $0.50/MTok/小时 | $0.875 |
| `gemini-3.1-flash-lite` | Priority | $0.45 | $0.90 | $2.70 | $0.045 / $0.09 | $1.80/MTok/小时 | $3.15 |
| `gemini-3.1-pro-preview` ≤200K | Standard | $2 | 同价/按官方模态 | $12 | $0.20 | $4.50/MTok/小时 | $14 |
| `gemini-3.1-pro-preview` >200K | Standard | $4 | 同价/按官方模态 | $18 | $0.40 | $4.50/MTok/小时 | $22 |
| `gemini-3.1-pro-preview` ≤200K | Batch / Flex | $1 | 同价/按官方模态 | $6 | $0.20 | $4.50/MTok/小时 | $7 |
| `gemini-3.1-pro-preview` >200K | Batch / Flex | $2 | 同价/按官方模态 | $9 | $0.40 | $4.50/MTok/小时 | $11 |
| `gemini-3.1-pro-preview` ≤200K | Priority | $3.60 | 同价/按官方模态 | $21.60 | $0.36 | $8.10/MTok/小时 | $25.20 |
| `gemini-3.1-pro-preview` >200K | Priority | $7.20 | 同价/按官方模态 | $32.40 | $0.72 | $8.10/MTok/小时 | $39.60 |
| `gemini-3-flash-preview` | Standard | $0.50 | $1 | $3 | $0.05 / $0.10 | $1/MTok/小时 | $3.50 |
| `gemini-3-flash-preview` | Batch / Flex | $0.25 | $0.50 | $1.50 | $0.05 / $0.10 | $1/MTok/小时 | $1.75 |
| `gemini-3-flash-preview` | Priority | $0.90 | $1.80 | $5.40 | $0.09 / $0.18 | $1.80/MTok/小时 | $6.30 |
| `gemini-2.5-pro` ≤200K | Standard | $1.25 | 同价/按官方模态 | $10 | $0.125 | $4.50/MTok/小时 | $11.25 |
| `gemini-2.5-pro` >200K | Standard | $2.50 | 同价/按官方模态 | $15 | $0.25 | $4.50/MTok/小时 | $17.50 |
| `gemini-2.5-pro` ≤200K | Batch / Flex | $0.625 | 同价/按官方模态 | $5 | $0.125 | $4.50/MTok/小时 | $5.625 |
| `gemini-2.5-pro` >200K | Batch / Flex | $1.25 | 同价/按官方模态 | $7.50 | $0.25 | $4.50/MTok/小时 | $8.75 |
| `gemini-2.5-pro` ≤200K | Priority | $2.25 | 同价/按官方模态 | $18 | $0.225 | $8.10/MTok/小时 | $20.25 |
| `gemini-2.5-pro` >200K | Priority | $4.50 | 同价/按官方模态 | $27 | $0.45 | $8.10/MTok/小时 | $31.50 |
| `gemini-2.5-flash` | Standard | $0.30 | $1 | $2.50 | $0.03 / $0.10 | $1/MTok/小时 | $2.80 |
| `gemini-2.5-flash` | Batch / Flex | $0.15 | $0.50 | $1.25 | $0.03 / $0.10 | $1/MTok/小时 | $1.40 |
| `gemini-2.5-flash` | Priority | $0.54 | $1.80 | $4.50 | $0.054 / $0.18 | $1.80/MTok/小时 | $5.04 |
| `gemini-2.5-flash-lite` | Standard | $0.10 | $0.30 | $0.40 | $0.01 / $0.03 | $1/MTok/小时 | $0.50 |
| `gemini-2.5-flash-lite` | Batch / Flex | $0.05 | $0.15 | $0.20 | $0.01 / $0.03 | $1/MTok/小时 | $0.25 |
| `gemini-2.5-flash-lite` | Priority | $0.18 | $0.54 | $0.72 | $0.018 / $0.054 | $1.80/MTok/小时 | $0.90 |

## 6.1 Gemini 长上下文规则

| 模型 | 普通档 | 长上下文档 |
| --- | --- | --- |
| Gemini 3.1 Pro Preview | Prompt ≤200K：输入 $2、输出 $12 | Prompt >200K：输入 $4、输出 $18 |
| Gemini 2.5 Pro | Prompt ≤200K：输入 $1.25、输出 $10 | Prompt >200K：输入 $2.50、输出 $15 |
| Gemini 3.5 Flash、3.1 Flash-Lite、3 Flash、2.5 Flash、2.5 Flash-Lite | 当前价格页只列统一单价 | 没有单独列出的长上下文阶梯价 |

## 6.2 Gemini Batch、Flex 与缓存注意事项

- Batch 通常降低输入和输出价格，但**缓存读取价格并不一定同步减半**。
- 例如 Gemini 2.5 Flash：Standard 输入/输出为 $0.30/$2.50，Batch/Flex 为 $0.15/$1.25，但文本缓存读取仍为 $0.03。
- Gemini 3.1 Pro 和 2.5 Pro 的 Batch/Flex 缓存读取价与 Standard 相同。
- 缓存存储按照“每 100 万缓存 Token × 每小时”持续计费。
- Priority 主要购买更高优先级/吞吐能力，价格显著高于 Standard。

---

# 7. DeepSeek 详细价格

| API 模型名 | 版本 | 缓存命中输入 | 缓存未命中输入 | 输出 | 1M未命中输入+1M输出 | 上下文 | 最大输出 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `deepseek-v4-flash` | DeepSeek-V4-Flash | $0.0028 | $0.14 | $0.28 | $0.42 | 1M | 384K |
| `deepseek-v4-pro` | DeepSeek-V4-Pro | $0.003625 | $0.435 | $0.87 | $1.305 | 1M | 384K |

## 7.1 DeepSeek 特别说明

- 两个 V4 模型都支持非思考和思考模式，默认是思考模式。
- `deepseek-chat` 与 `deepseek-reasoner` 将于 **2026-07-24 15:59 UTC** 弃用；兼容期内分别映射到 V4 Flash 的非思考与思考模式。
- 官方价格页没有单独列 Batch、Priority 或长上下文加价。
- 实际费用直接从充值余额或赠送余额中扣除。
- 推理模式通常会产生更多输出 Token，因此虽然单 Token 价格不变，总费用可能增加。

---

# 8. 推理深度如何影响价格

## 8.1 API 按量计费

推理深度一般不会改变同一模型的单 Token 单价，但会改变模型使用的推理 Token 数量：

```text
计费输出 Token
= 用户看见的回答 Token
+ 模型内部/返回的推理或思考 Token
```

举例：输出单价为 $10/MTok 时：

| 推理档 | 隐藏/显式推理 Token | 可见回答 Token | 计费输出合计 | 输出费用 |
| --- | ---: | ---: | ---: | ---: |
| Low | 2,000 | 1,000 | 3,000 | $0.03 |
| Medium | 7,000 | 1,000 | 8,000 | $0.08 |
| High | 15,000 | 1,000 | 16,000 | $0.16 |
| XHigh | 40,000 | 1,000 | 41,000 | $0.41 |

所以“回答看起来很短”并不代表输出侧用量一定很少。

## 8.2 编程 Agent 的真实费用

Claude Code、Codex、Gemini CLI 或其他 Agent 的真实成本通常由以下因素相乘：

```text
推理深度
× 每轮上下文大小
× 工具调用轮数
× 重试与验证次数
× 输出长度
```

对大型代码仓库而言，反复发送文件、终端输出、测试日志和历史对话，往往比最终回答本身更贵。

---

# 9. 常见工具与附加服务价格

| 厂商 | 项目 | 价格/规则 |
| --- | --- | --- |
| OpenAI | Web Search / Image Web Search | $10 / 1,000 次调用 + 搜索内容按所选模型输入 Token 计费 |
| OpenAI | Web Search Preview（推理模型） | $10 / 1,000 次调用 + 搜索内容按模型费率 |
| OpenAI | Web Search Preview（非推理模型） | $25 / 1,000 次调用；搜索内容 Token 免费 |
| OpenAI | File Search 存储 | $0.10 / GB / 天；每个账户 1GB 免费 |
| OpenAI | File Search 调用 | $2.50 / 1,000 次调用 |
| OpenAI | Hosted Shell / Code Interpreter 容器 | 1GB $0.03、4GB $0.12、16GB $0.48、64GB $1.92 / 20 分钟会话；符合条件时按分钟计，最低 5 分钟 |
| Anthropic | Web Search | $10 / 1,000 次搜索 + 搜索内容的标准 Token 费用 |
| Anthropic | Web Fetch | 无额外工具费；抓取内容按标准输入 Token 计费 |
| Anthropic | Code Execution（单独使用） | 每组织每月 1,550 小时免费；之后 $0.05 / 小时 / 容器；最低 5 分钟 |
| Anthropic | Code Execution（配合 Web Search/Fetch） | 无额外执行费，仅收标准 Token 费用 |
| Google | Gemini 3 系列 Google Search Grounding | 每月共享 5,000 prompts 免费；之后 $14 / 1,000 个实际搜索查询 |
| Google | Gemini 2.5 系列 Google Search Grounding | 付费层每日 1,500 grounded prompts 免费；之后 $35 / 1,000 grounded prompts |
| Google | Gemini 2.5 Pro/Flash Google Maps Grounding | 付费层免费额度依模型/服务档而异；超额通常 $25 / 1,000 grounded prompts |
| DeepSeek | 工具调用 | 官方价格页未列独立工具调用费；模型生成与工具上下文仍按 Token 计费 |

---

# 10. 选择建议

| 场景 | 优先考虑 | 价格侧理由 |
| --- | --- | --- |
| 大批量分类、提取、翻译 | Gemini 2.5 Flash-Lite、DeepSeek V4 Flash、GPT-5.4 Nano | 标准输入输出成本最低 |
| 日常代码生成与简单修复 | DeepSeek V4 Pro、Gemini 2.5 Flash、GPT-5.4 Mini | 成本较低，适合高调用量 |
| 中高难度编码 | Gemini 2.5 Pro、Claude Sonnet 5、GPT-5.3 Codex、GPT-5.6 Terra | 性能与价格之间更均衡 |
| 超长上下文代码库 | Claude Sonnet 5/4.6、Opus 4.8；或 DeepSeek V4 | Claude 1M 不加长上下文阶梯价；DeepSeek 官方也只列统一价 |
| 最高难度推理/Agent | GPT-5.6 Sol、Claude Opus 4.8、Claude Fable 5 | 单价高，应限制在难题和升级路径中 |
| 离线批量任务 | 各家的 Batch/Flex | 通常比标准实时价格低约一半，但缓存规则需单独核算 |
| 低延迟关键请求 | OpenAI Priority、Gemini Priority、Claude Fast | 更快，但价格通常明显上升 |

一个常见的成本控制路由：

```text
低价模型处理初稿/分类
→ 中档模型处理主要开发
→ 旗舰模型只处理失败升级、复杂架构和最终验证
```

---

# 11. 官方来源

- [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)
- [Anthropic Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Google Gemini Developer API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)

---

# 12. 更新与使用声明

API 定价、推广期、模型状态和弃用日期可能随时调整。正式预算、采购或生产上线前，应再次检查上述官方价格页。第三方聚合平台、云厂商、虚拟卡、税费、汇率和渠道服务费可能使最终结算价高于或低于本表。
