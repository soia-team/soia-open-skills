---
name: soia-pkm-translate
description: 三模式翻译技能——quick 直译、normal（默认）先分析文体术语受众再译、refined 在此基础上加审校+润色出版级流程。长文用机械分块脚本按标题/段落切块保术语一致，产出独立的“原文件名-中文版.md”落原文件同目录，绝不覆盖原文。典型用于翻译 clip-x/clip-web 归档的英文文章。Triggers：「翻译这篇」「translate this」「精翻」「快翻」「把这篇文章翻成中文」「校对翻译」「继续润色」
---

# soia-pkm-translate

> 属 SOIA 个人知识管理域（`soia-pkm-*`）的"加工"环节：把 `soia-pkm-clip-x` / `soia-pkm-clip-web` 等归档产物里的外文文章，翻译成目标语言，落地为独立文件，不改动原文。

## 客户可读说明

### 这个技能可以做什么

三种模式覆盖从"先看看大概意思"到"要发布级质量"的完整翻译需求；长文自动分块并跨块保持术语一致；产出永远是原文旁边的一个新文件，不覆盖、不污染原文。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 快速看懂一篇外文文章大意（quick） | 直接翻译，不做额外分析 | 一份直译版全文 |
| 一篇普通文章的可读译文（normal，默认） | 先分析文体/术语/受众，再据此翻译 | 一份自然流畅的译文全文 |
| 出版级质量的重要文章（refined） | 分析 → 翻译 → 审校（只诊断）→ 润色（应用修正） | 诊断说明 + 最终润色版全文 |
| 长文（超过分块阈值） | 用机械脚本按标题/段落切块，术语表贯穿所有块 | 分块数量、术语表命中数，最终仍是一份合并后的完整译文 |
| 翻译 vault 里已归档的英文文章 | 继承原 frontmatter，加 `translated_from` 等字段 | `<原文件名>-<目标语言>版.md`，与原文件同目录，原文件保持不变 |

### 客户如何使用

1. 提供要翻译的文件路径（典型是 `soia-pkm-clip-x` / `soia-pkm-clip-web` 归档在 vault 里的外文文章），或直接粘贴文本；顺手说明目标语言 / 模式 / 受众（不说就用 config 默认或本技能内置默认：`zh-CN` / `normal` / `general`）。
2. **首次对某个文件执行翻译前**，Agent 必须先报告"将翻译 `<文件>` 到 `<目标语言>`，模式 `<quick/normal/refined>`"，等待客户确认，除非客户已经明确说"直接翻""不用确认"。目标语言/模式/受众只要有一项来自 config 默认值而非客户本次显式指定，都算"推荐输入"，同样需要走这一步确认。
3. Agent 判定或使用客户指定的模式（quick / normal / refined），按 [三种模式](#三种模式) 执行。
4. 长文（超过 `chunk_threshold`，默认 4000 词）先跑 `scripts/chunk_markdown.py` 机械分块，术语表贯穿所有块保持一致；短文直接在当前上下文整篇翻译。细节见 [references/chunk-workflow.md](references/chunk-workflow.md)。
5. **clip 归档双语模板注意（实测教训 2026-07-10）**：clip-x/clip-web 归档笔记是「摘要+原文+中文译文+我的看法」多段模板，整篇喂分块脚本会把已有中文译文一并计词——词数虚胖（实测 4431 vs 真实待译 1517），更长的文章会被误判切块且边界可能横跨"原文"与"已有译文"两个语义区。对这类文件：先只截取 `## 原文` 小节（到下一个 `##` 标题为止）存临时文件再喂脚本；是否触发分块以**待译段**词数为准，不以整篇为准。
5. 翻译永远**先落盘、后汇报**：产出 `<原文件名>-<目标语言>版.md` 落在原文件同目录，frontmatter 继承原文并追加 `translated_from` 等字段，绝不覆盖原文件。
6. 最终回复必须给客户完整回执：模式、块数、术语表命中数、产出文件路径、剩余风险。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-translate -y
```

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| Python 3（stdlib） | 强依赖 | 系统自带或 `brew install python3` | 没有 Python 3 就无法跑 `scripts/chunk_markdown.py`，退化为不分块、整篇在上下文内翻译（长文质量会下降，需提醒客户） |
| PyYAML | 可选增强 | `pip install pyyaml` | 缺失时 `scripts/resolve_config.py` 仍能定位到 `config.yml` 路径，只是不能结构化解析；Agent 改为直接读文件文本内容 |
| Obsidian vault（任意结构） | 方法参考，非强依赖 | 不需要单独安装 | 本技能可以翻译任意 Markdown/纯文本文件，不要求文件必须在 vault 内；只有涉及 vault frontmatter 和归位约定时才参考 vault 上下文 |
| `soia-pkm-clip-x` / `soia-pkm-clip-web` | 上游来源，非强依赖 | 不需要安装，除非客户需要先归档再翻译 | 只是常见的输入来源，本技能不调用也不修改这两个 skill 的任何文件 |

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-translate/config.yml
SOIA_PKM_TRANSLATE_CONFIG_FILE=<custom-config-path>
```

- 样例见 [config.example.yml](config.example.yml)：`target_language` / `mode` / `audience` / `style` / `chunk_threshold` / `chunk_max_words` / `glossary`（内联术语表）都是明文偏好，不含任何秘密。
- 如果客户不需要自定义偏好，可以不创建 `config.yml`，本技能会用内置默认值（`zh-CN` / `normal` / `general` / `storytelling` / 4000 / 5000）。
- 优先级：CLI 参数（客户本次明确说的目标语言/模式/受众/术语）> 进程环境变量 > 私有 `config.yml` > 本技能内置默认值。
- 不需要、也不应该读取任何 API key、cookie、session、账号凭据——本技能只处理客户提供的文本文件。

### 日志与完成回执

每次执行都要让客户看见判定、确认、分块和产出全过程。最低回执格式：

```markdown
完成：<一句话说明本次翻译了什么文件、到什么语言、什么模式>。

日志摘要：
- 确认记录：<本次是否走了首次确认、客户确认内容；用户已明说跳过则写"客户已要求跳过确认">
- 模式：<quick / normal / refined，以及判定依据>
- 分块：<是否触发分块；触发则写块数与每块词数；未触发写"未触发分块，整篇在单次上下文内翻译">
- 术语表：<config 术语表命中次数 + 本次从原文抽取的会话术语数量；无术语表则写"未配置术语表，仅按上下文保持一致">
- 审校（仅 refined）：<跨块术语/人名/风格漂移检查结果；quick/normal 写"不适用">

文件变化：
- 新建：<绝对路径，`<原文件名>-<目标语言>版.md`>
- 未改动：<原文件路径，确认未被覆盖>

问题与下一步：
- <图片语言不匹配提醒 / 需要客户核对的译名或术语 / normal 模式可回复"继续润色"升级为 refined；没有则写"无，可直接使用产出">
```

## 三种模式

| 模式 | 步骤 | 适用场景 | 触发词 |
|---|---|---|---|
| **quick** | 直接翻译 | 短文本、非正式内容、想先看懂大意 | 「快翻」「quick」「直接翻译一下」 |
| **normal**（默认） | 分析（文体/术语/受众）→ 翻译 | 一般文章、博客、日常归档 | 未指定模式时的默认值 |
| **refined** | 分析 → 翻译 → 审校（只诊断）→ 润色（应用修正） | 出版级质量、重要文档、要对外发布的内容 | 「精翻」「refined」「校对翻译」「润色译文」 |

- quick 模式不分块——不论长短都直接整篇翻译，速度优先；长文走 quick 时提醒客户"quick 模式不做术语一致性处理，长文建议用 normal"。
- normal 完成后，如果客户回复"继续润色"，直接从 refined 的审校步骤开始，不用重新分析或重新翻译。
- refined 模式审校/润色的详细检查项见 [references/refined-review-checklist.md](references/refined-review-checklist.md)。

## 长文机械分块

`scripts/chunk_markdown.py` 是纯 Python stdlib 脚本，只做机械活——按标题层级和段落边界切块，不做任何翻译判断：

```bash
python3 scripts/chunk_markdown.py --file <path.md> --json
python3 scripts/chunk_markdown.py --file <path.md> --threshold 4000 --max-words 5000 --json
python3 scripts/chunk_markdown.py --selftest
```

- 默认阈值 **4000 词**触发分块；未触发时整篇作为一个块返回，直接在当前上下文翻译。
- 触发后单块上限 **5000 词**，按标题分组、超限小节再按段落/行边界继续拆分；代码块永远整体保留，不会被从中间切开。
- `--json` 输出块清单（每块的 index / words / heading）；需要物理文件时加 `--output-dir <临时目录>`，会在 `<目录>/chunks/` 下写 `chunk-NN.md`（和 `frontmatter.md`，如果原文有 frontmatter）。
- 翻译本身永远在调用本技能的 Agent 的 LLM 上下文里完成，脚本不调用任何翻译 API。
- 完整工作流（术语抽取、会话术语表、逐块翻译、合并、中间文件清理）见 [references/chunk-workflow.md](references/chunk-workflow.md)。

## 术语一致性

- config 里的 `glossary`（原文 → 固定译法）是本技能的第一层术语依据；长文分块翻译时，先通读全文抽取专有名词和反复出现的术语，与 config 术语表合并成本次的**会话术语表**，贯穿翻译所有块，不逐块各自决定译法。
- refined 模式的审校步骤专门检查跨块术语、人名、风格漂移——这是分块翻译最容易出问题的地方，检查清单见 [references/refined-review-checklist.md](references/refined-review-checklist.md)。
- quick 模式不做术语表合并（追求速度），normal 模式做术语合并但不做专门的跨块审校（除非客户之后要求"继续润色"升级为 refined）。

## 与 vault 衔接

- 典型场景：翻译 `soia-pkm-clip-x` / `soia-pkm-clip-web` 已归档到 vault 的英文文章，但本技能不要求输入文件必须在 vault 内，任意 Markdown/纯文本文件都可以翻译。
- 产出文件名：`<原文件名>-<目标语言版>.md`，落在原文件**同目录**。目标语言到文件名后缀的映射：`zh-CN`/`zh`/`zh-Hans` → `中文版`；`en` → `英文版`；`ja` → `日文版`；`ko` → `韩文版`；其他语言用 `<目标语言代码>版`（如 `fr版`）。
- **绝不覆盖原文件**——产出永远是新文件；如果同名译文文件已存在，先告知客户，等待确认是否覆盖旧译文（这属于覆盖类风险动作，必须先确认）。
- frontmatter 规则：完整保留原文件的全部 frontmatter 字段，在末尾追加：

```yaml
translated_from: <原文件名或相对路径>
translated_language: <目标语言代码，如 zh-CN>
translated_at: <YYYY-MM-DD>
```

  不重命名或删除原有字段；如果正文已有一级标题（H1）且原 frontmatter 有 `title`，`title` 字段按原样保留，不强制同步成译文标题。

## 交付顺序

### 前向测试

首次处理新格式或长文前，先用小范围或 fixture 输入验证分块边界、frontmatter 保留、术语一致性、非覆盖产出和空正文失败处理；命令返回 0 不等于译文质量已验证。

先落盘，后汇报：产出文件必须先写入磁盘并通过内容核对（文件确实存在、frontmatter 字段完整、正文非空），再向客户发出完成回执。不允许先描述"已完成"再补写文件。

## 边界与限制

- 本技能不调用任何外部翻译 API 或网络服务；分块脚本是纯本地机械处理，翻译由调用本技能的 Agent 在自己的上下文里完成。
- 本技能不处理账号、cookie、session 等凭据——只处理客户提供的文件路径或文本内容。
- 图片本身的文字（封面、截图、图表）不在本技能翻译范围内；完成翻译后按惯例做一次轻量提醒：列出可能仍是原文语言、需要客户自行判断是否要本地化的图片，不擅自处理图片。
- 术语表和会话上下文只保证"同一次翻译任务内"一致，不跨文件、跨任务自动累积记忆；需要长期维护的术语表应该由客户写进 `config.yml` 的 `glossary`。

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结本次翻译的文件、目标语言、模式，以及是否触发了分块。
2. **文件变更** — 新建的译文文件完整路径；明确说明原文件未被改动。
3. **下一步** — normal 模式提醒客户可回复"继续润色"升级为 refined；refined 模式提醒客户核对审校清单里标出的存疑译名/术语；有图片语言不匹配提醒时一并列出。
