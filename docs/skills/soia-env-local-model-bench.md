# soia-env-local-model-bench

> 在 Apple Silicon 上评测本地 LLM：先环境检查与引擎选型（mlx-lm/llama.cpp 等），确认后才下载部署；跑题库判定、吞吐 TTFT 与硬件采样，产出可横比的口径化报告

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-local-model-bench) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「评测本地模型」「本地模型跑分」「装个本地模型」「mlx 测速」。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 不知道这台机器能不能跑本地模型 | 只读探测芯片/内存/磁盘/OS/已装引擎 | 事实清单 + 引擎选型对比与场景推荐 |
| 下载模型又慢又卡死 | aria2c 16 连接方案 + 完整性验证 | 稳定的下载速率与验证结果 |
| 部署起来跑一轮评测 | mlx-lm / llama.cpp 双引擎启动模板 + 题库自动判定 | 每题 PASS/FAIL/待人工 + 速度数字 |
| 想知道并发能到多少 | TTFT 冷/热 + 1/2/4/8 并发聚合吞吐 | 带口径声明的吞吐结果 JSON |
| 跑的时候占多少资源 | 进程 RSS/CPU/GPU 采样与汇总 | 峰值与活跃均值 |
| 接进 pi/dsh/opencode 干活 | Agent 挂本地端点跑沙盒真实任务 | 测试通过与否 + 耗时 + 改动范围 |
| 结果沉淀下来以后对比 | 按报告契约出回执、横比列、口径声明 | 可跨模型、跨社区对比的报告 |

**不做清单**（显式边界）：不做模型训练/微调；不做云端 API 评测；首版不支持非 macOS 平台（脚本在其他平台只报事实不给推荐）；**不自动删除模型文件**（收尾清单只提醒，删除由客户自己执行）。

### 客户如何使用

1. 客户说出目标（评测某个模型 / 想装个本地模型 / 对比两个引擎），不需要先准备命令。
2. Agent **必须先跑第 0 步环境检查**并给出引擎选型表——客户确认引擎与模型后才进入下载安装，不跳步。
3. 下载、装引擎、启停服务都属于改机动作：先展示计划（装什么、放哪、占多少磁盘）再执行。
4. 评测执行中 Agent 边跑边报每题结果；结束按「日志与完成回执」格式收口。
5. 涉及把结论写入客户知识库或发布 Artifact 时，先确认落点再写。

### 两个入口场景

本技能的本质：评测开源 LLM 是否适合本地机器——有无合适配型、能否当日常辅助、能否为了安全（隐私）把数据留在本机处理。客户最常见的两种进门方式：

**场景一 · 「帮我找适合本机的开源模型」（如：日常编码助手）**

1. 第 0 步 env_check 探测机器（芯片/内存/磁盘/已装引擎）。
2. 需求访谈四问——**问在下载之前，不是之后**：
   - 用途：编码 / 写作 / 翻译 / agent？
   - 主语言：中文还是英文？——投机解码加速比强依赖语言，中文用户不能拿英文数字做决定（见 [methodology.md](references/methodology.md)）。
   - 速度优先还是质量优先？
   - 隐私敏感度：哪些数据不出本机？
3. 按带宽物理学给简单结论（见 [engines.md](references/engines.md) 带宽谱系）：本机能跑的档位与预期速度区间。配置不符合就到此为止，如实说不适合，不硬推。
4. 市场发现（见 [model-discovery.md](references/model-discovery.md)）给候选清单：模型 x 量化版本 x 预检结果 x 预期速度。
5. 客户确认候选后进入既有 下载 → 部署 → 评测 → 报告 流程（第 1-6 步）。

**场景二 · 「我要安装 xxx 模型，帮我找合适的版本」**

1. 同样先第 0 步 env_check。
2. 按 [model-discovery.md](references/model-discovery.md) 在市场上找该模型的各量化/格式版本（HF / ModelScope 同名仓、mlx-community / unsloth 打包——注意 ModelScope 多为 lmstudio-community 打包，核对格式），并做本机架构支持预检。
3. 按内存门槛公式 + 需求推荐具体版本，引擎 x 量化选型对照 [engines.md](references/engines.md)。
4. 客户确认后安装评测。

两个场景共同纪律：**反问需求在下载之前**；结论先答「能不能日常用」，再给性能数字——真的可以使用 > 速度跑分。

## 安装

客户明确选择安装整个 `soia-env` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-env@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-env@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-local-model-bench -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
