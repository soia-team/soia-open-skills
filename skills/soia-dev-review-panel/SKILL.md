---
name: soia-dev-review-panel
description: Multi-lens, adversarially-verified review of a code diff or skill package. Never edits/merges/publishes. Triggers：「多角度审一下这个改动」「用几个视角复查」「对抗式复核一下」「审一下这个技能包」
version: 1.0.0
created_at: 2026-07-21 19:04:05
updated_at: 2026-07-21 19:04:05
created_by: claude fable 5
updated_by: claude fable 5
dependencies:
  hard: [soia-dev-coding-protocol]
---

# soia-dev-review-panel

A single reviewer has blind spots — that is the entire premise of this skill.
It structures a review into independent lenses that each look for a different
failure mode, then makes every candidate finding survive an adversarial
"try to refute this" pass before it's allowed into the report. Findings that
don't survive verification are dropped, not softened.

Do not use this for the mechanics of fetching a GitHub PR's diff or finding a
target repo's own rule files — that's `soia-dev-github-ops`'s Pre-Merge Rule
Review. This skill is the review methodology that procedure calls into once
it has a diff in hand; it also works standalone on a local diff or a skill
package with no GitHub involvement at all.

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 多角度、不漏判地审一次代码改动 | 拆成独立视角逐个过（能并行就并行），每条候选发现再经一轮对抗式复核，只保留经得住反驳的 | 分档发现清单（阻断/应改/提示）+ 每条的证据等级 |
| 审一个技能包（SKILL.md/scripts/references） | 换一套技能包专属视角（宿主无关性、安全门完整性、跨文件描述一致性等） | 同上 |
| 只想知道审了哪些方面、有没有漏检 | 报告里明确列出"检查过、没问题"的部分，不是只报问题 | 覆盖范围说明 |

### 客户如何使用

1. 说明审查目标：本地未提交的改动、一段已经拿到手的 diff 文本、或一个技能目录路径（如 `skills/<name>/`）。
2. 如果目标类型不明确（代码改动 vs 技能包 vs 两者都有），先问一句再往下走，不要自己猜。
3. 如果对严格程度有要求（比如"再严一点""这次要快"），据此增减视角数量和复核轮数；默认是下面列出的基础视角集。
4. 报告只包含"经复核确认成立"的发现，不自动改代码、不自动提交、不自动合并、不自动发布——这些都是使用者自己的下一步。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-review-panel -y
```

强依赖 `soia-dev-coding-protocol`：本技能的"测试覆盖与反面模式"视角直接复用它的 Anti-Fake-Fix Gate 和提交前自审清单，不重复维护第二份。安装本技能会自动带上这个依赖。

本技能不需要私有配置。

### 私密信息与中间数据

本技能不持久化任何数据，不需要凭据、cookie 或 API key。审查材料（diff 内容、技能目录内容）只在当前对话/子任务上下文中使用，不写入任何文件、日志或第三方服务；如果和 `soia-dev-github-ops` 组合使用，凭据与网络请求边界由那个技能负责，不在本技能范围内。

### 日志与完成回执

```markdown
完成：<一句话说明审了什么、结论是什么>。

发现清单：<按阻断/应改/提示分档，每条给位置和证据等级>
覆盖范围：<用了哪些视角，核实过没问题的部分>
决定权：<交还使用者——建议合并/建议先改/建议不合并，不代为执行>
```

## Step 0 — 确定目标类型与视角组

- 目标是代码 diff（本地 `git diff`、别人已经拿到手的 diff 文本、`soia-dev-github-ops` 交过来的 PR diff）→ 用"代码视角组"。
- 目标是技能包（`skills/<name>/` 目录，或改动主要落在某个技能的 `SKILL.md`/`scripts`/`references`）→ 用"技能包视角组"；如果技能包里也有 `scripts/*.py` 之类的代码，两组都要用。
- 目标类型或范围边界不确定，先问，不要猜。

## Step 1 — 视角清单

每个视角独立执行、独立读原始材料，不共享上一个视角的结论——避免锚定，这是多视角审查的核心价值所在，跳过这一条就是把成本花了但没拿到收益。

### 代码视角组

| 视角 | 关注点 |
|---|---|
| 正确性与自证 | 改动是否真的做到了它声称做的事——去读被改动的文件原文核实，不能只看 diff 片段（diff 只显示改动行+少量上下文，容易漏看完整签名/分支） |
| 安全 | 外部输入（URL/路径/用户数据）有没有校验；有没有硬编码密钥/token；凭据或隐私数据有没有落进日志或提交历史 |
| 测试覆盖与反面模式 | 套用 `soia-dev-coding-protocol` 的 Anti-Fake-Fix Gate 逐条核对：有没有测试但断言过松（"跑起来不报错"不算验证）；描述里的数字声称（"N 个测试通过""处理了 M 条记录"）有没有独立复现过，不要直接采信 |
| 范围与一致性 | 改动是否超出标题/描述声称的范围；文档（README/SKILL.md/CHANGELOG）有没有跟着行为改动同步；依赖方向有没有反向 |

### 技能包视角组

| 视角 | 关注点 |
|---|---|
| 命令/接口正确性 | 技能正文里出现的每条命令（`gh` CLI、脚本调用等）语法是否真的对——不要凭经验判断字段名和参数存不存在。只用无副作用、免登录的方式核实（`--help`、`--dry-run`、纯查询类调用）；命令本身需要凭据或有副作用（创建/合并/删除/发送/授权变更类），改成对照官方文档核对参数，不要真的执行——这条硬性限制优先于"私密信息与中间数据"段的"不需要凭据"声明，是它的具体落地方式，不是例外 |
| 安全门完整性 | 高影响操作（删除、覆盖、发送、发布、授权变更）是否都有对应的显式确认要求；grant 类操作有没有对称的 verify/revoke 核实步骤 |
| 宿主无关性 | 有没有依赖某个特定 AI CLI 专有工具（如 Claude Code 的 `computer`/`claude-in-chrome`/内置 slash command）；正文必须能被其他 host（Codex、Gemini CLI 等）独立读懂并跑起来 |
| 一致性与同步 | frontmatter description / `agents/openai.yaml` / 顶层 README 对应行 / 自动生成目录，这几处对能力的描述是否互相同步；`version` 是否跟着这次改动 bump；技能名是否和已有技能（尤其跨仓库）撞名——本机 `~/.agents/.skill-lock.json` 按名字单一 key 存储，不分来源仓库，撞名会互相覆盖装机文件 |

需要更严格的审查时，在基础视角之外按需要加视角（比如涉及并发的改动加"并发语义"视角），不要为了凑数硬加不相关的视角。

## Step 2 — 派发

当前环境如果支持派生独立子任务（比如 Claude Code 的 Agent/Workflow 工具，或其他 host 提供的等价并行机制），把选中的视角分给独立子任务并行执行，每个子任务只给它自己那个视角的说明和原始材料，不要把其他视角的结论一起喂给它。

当前环境不支持派生子任务时，在同一个上下文里按顺序逐个视角过一遍：每切换一个视角前明确"现在只用视角 X 的标准看，忘掉刚才那个视角的结论"，用书面形式把这句话写出来再继续，防止视角之间互相污染判断。两种方式产出的候选发现格式一致，选哪种取决于环境能力，不取决于严格程度。

## Step 3 — 候选发现的格式

每条候选发现固定四要素：

1. 一句话标题
2. 具体位置（文件路径 + 行号，或章节名——不要只说"某处"）
3. 证据等级：看到的（引用原文）/ 推断的（给推理链）/ 不确定（明说，并给出验证路径）
4. 严重度候选：阻断（违反硬性规则/安全问题/明显 bug）/ 应改（不阻断但值得处理）/ 提示（检查过没问题，或次要观察）

## Step 4 — 对抗式复核（不可省略）

派发方式沿用 Step 2 的同一套降级规则：能派生独立子任务就派生；不能就在同一上下文里做，但必须先写一句书面切换语（例如"现在只负责尝试推翻这条发现，忽略我刚才作为原视角时的判断"）再继续——复核面对的锚定风险和 Step 2 视角之间互相污染是同一类问题，同一套规则处理。

每条"阻断"或"应改"级的候选发现，换一个独立视角重新审视，专门尝试推翻它：

- 重新去读原始材料本身，不是读上一步的转述——转述会放大或稀释原始信息，必须回到源头。
- 默认倾向"不成立"，只有真的复现、核实过之后才判定"成立"。
- 检查：引用的证据是否真的存在于原文；严重度有没有被夸大或低估；有没有一个反例能推翻结论；复核过程中如果发现了更准确的问题描述（比如原发现的行号引用有偏差），用修正后的版本，不要因为细节有偏差就整条丢弃。
- "提示"级（检查过没问题）的候选不需要对抗式复核，直接进最终报告的覆盖范围说明。

只有复核判定"成立"的发现才进入最终报告。

## Step 5 — 输出

最终回复必须包含：

1. **一句话结论**：这次改动整体上是"建议通过""建议先改""建议拒绝"之一，放在最前面。
2. **发现清单**：按阻断/应改分档，每条给位置、证据等级、简要说明。
3. **覆盖范围**：用了哪些视角、核实过但没发现问题的部分（不要只报问题，让读者知道审查边界在哪）。
4. **决定权明确交还**：这是审查建议，不是自动执行的许可——本技能不改代码、不提交、不合并、不发布；那是使用者看完报告后自己的下一步。

## 与其他技能的关系

| 技能 | 关系 |
|---|---|
| `soia-dev-coding-protocol` | 强依赖。"测试覆盖与反面模式"视角直接复用它的 Anti-Fake-Fix Gate 和提交前自审清单，不重复维护 |
| `soia-dev-github-ops` | 单向依赖，方向与本表其他行相反：它的 Pre-Merge Rule Review hard-依赖本技能（装不了就停下，不会退化成自己维护一份清单），负责"拉 PR diff + 找目标仓库自己的规则文件"，把结果交给本技能做 Step 1-4 的视角审查和对抗式复核。本技能不反向依赖它，也不知道怎么用 `gh` CLI 拉 PR，那部分留给它 |
| `soia-private-skills` 的 `soia-dev-code-review` | 不是同一个技能的开源版，两者可以同时安装（名字不同，不冲突）。那个技能专门服务已确认的 SOIA 产品 workspace 内 proposal/Wave/fix 治理评审，6 维度按团队内部经验把具体模型绑定到具体维度；本技能是通用方法论，不含任何产品/团队专属信息，也不假设特定模型分工。vault、`soia-open-skills`、`soia-private-skills` 与普通仓库的评审用本技能，已确认的 SOIA 产品治理评审用那个 |
