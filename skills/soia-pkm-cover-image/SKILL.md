---
name: soia-pkm-cover-image
description: 为公众号/X/小红书文章生成封面图。五维参数（type/palette/rendering/text/mood），默认 2.35:1 微信头图比例，产出接 soia-pkm-publish --cover。后端仅用 codex CLI 内置生图，探测不到就询问客户，绝不静默降级、绝不用代码渲染冒充位图。Triggers：「生成封面」「做个封面图」「配一张公众号头图」「做张小红书封面」「cover image」
---

# soia-pkm-cover-image

PKM 发布链（`compose -> publish`）里的**封面生成环节**：给已经写好或即将发布的文章生成一张位图封面，产出直接喂给 `soia-pkm-publish` 的 `--cover` 参数。本技能只产出**一张封面位图**（文中配图/插画属于 v2 路线图，见文末），不做排版、不做发布、不碰账号凭据。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 给一篇公众号/X/小红书文章配一张封面 | 分析内容 → 推荐五维参数（type/palette/rendering/text/mood）与比例 → 确认 → 解析生成后端 → 落盘 prompt → 生成 | 确认清单、最终 prompt 文件、`cover.png`、完成回执 |
| 换一种风格重新生成 | 保留旧版本、写新 prompt 文件、只重生成，不在旧图上描字改字 | 新旧两个版本的产物路径对比 |
| 后端不可用（没装 codex / 未登录） | 停止生成，明确告知缺什么、如何补齐，绝不降级成代码画图冒充位图 | 缺失说明 + 安装/登录指引 |

### 客户如何使用

1. 提供：文章的**确切标题**（不可由本技能编造或改写）、主题/要点、目标发布渠道（公众号 / X / 小红书，决定默认比例）。
2. Agent 分析内容后推荐五维参数与比例，连同"确认闸门"一起交给客户确认——除非客户在**当前这句话**里已明说"直接生成"/`--quick`。
3. 后端解析（见"后端解析"一节）：当前消息指定后端就用它；否则探测 codex CLI；都不满足就停止并询问客户，不静默降级。
4. 生成前把最终 prompt 落盘到 `prompts/NN-cover-<slug>.md`；生成后的 `cover.png` 可直接作为下游 `soia-pkm-publish` 的 `scripts/publish.py --article <md> --cover <output-dir>/cover.png` 输入（`soia-pkm-publish` 是独立的下游 skill，按其自身安装说明配置，本技能不修改它）。
5. 最终回复给出完成回执（见"日志与完成回执"）。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-cover-image -y
```

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| codex CLI（`codex exec`） | 强依赖（v1 唯一生图后端） | 安装 codex CLI 并完成登录，具体命令以官方文档当前版本为准 | PATH 上探测不到，或登录态检查未通过：**停止生成**，告知客户缺什么、如何安装/登录，并询问下一步；不得静默换成代码渲染或其它未声明的工具 |
| `soia-pkm-publish` | 下游衔接（非本技能依赖） | 见该 skill 自身的安装说明 | 本技能只负责产出 `cover.png`；是否安装、何时调用 publish 由客户决定，本技能不代为安装或修改它 |

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-cover-image/config.yml
SOIA_PKM_COVER_IMAGE_CONFIG_FILE=<custom-config-path>
```

- 本技能**不需要**任何账号凭据、cookie、token——`config.yml` 只保存生成偏好（默认 type/palette/aspect、是否跳过确认），不放秘密值。
- 如果客户不想要私有偏好，可以不创建 `config.yml`，本技能按内置默认值（`auto` 推荐 + 2.35:1 + 需要确认）运行。
- 样例见本技能目录下的 `config.example.yml`。

### 日志与完成回执

每次执行都要让客户看见判断、确认和产出全过程。最低回执格式：

```markdown
完成：<一句话说明本次生成了什么封面，或说明因何未生成>。

日志摘要：
- 五维参数：type=<值> palette=<值> rendering=<值> text=<值> mood=<值>（各值标注"客户指定"或"AI 推荐"）
- 比例：<aspect>（默认 2.35:1，或客户/用途指定值）
- 确认记录：<确认清单的客户答复摘要，或"客户已用 --quick / 明确说直接生成，跳过确认，本次沿用的假设是：…">
- 后端：<codex-exec 或客户指定的其它后端；不可用时写"探测失败，已停止并询问客户">

产出：
- prompt 文件：<prompts/NN-cover-<slug>.md 路径>
- 封面图：<output-dir>/cover.png（或未生成时写"无，原因见上"）

文件变化：
- <本次新建/覆盖的绝对路径列表；未生成时写"未改动文件">

问题与下一步：
- <后端缺失 / 标题与原文不一致需要客户核对 / 建议客户下一步把 cover.png 交给 soia-pkm-publish；没有则写"无，可直接使用产出">
```

## 五维参数（精选，非上游全集）

| 维度 | 可选值 | 默认 | 一句话说明 |
|---|---|---|---|
| **type** | hero / conceptual / typography / metaphor / scene / minimal | auto（按内容判断） | 构图母题：主视觉大图 hero、抽象概念隐喻 conceptual、大字排版 typography、单一隐喻符号 metaphor、场景插画 scene、极简留白 minimal |
| **palette** | warm / elegant / cool / dark / vivid / mono | auto | 配色基调：暖色调 warm、高级灰 elegant、冷色调 cool、深色底 dark、高饱和 vivid、黑白 mono |
| **rendering** | flat-vector / hand-drawn / painterly / digital | auto | 渲染质感：扁平矢量 flat-vector、手绘感 hand-drawn、绘画质感 painterly、数字插画 digital |
| **text** | none / title-only / title-subtitle | **title-only** | 文字层级：不放字 none、只放标题 title-only（默认）、标题+副标题 title-subtitle |
| **mood** | subtle / balanced / bold | balanced | 情绪强度：低对比 subtle、适中 balanced（默认）、高对比 bold |

## 比例（aspect）与发布链衔接

| aspect | 用途 | 尺寸参考 |
|---|---|---|
| **2.35:1（默认）** | 微信公众号头图 | 900×383 |
| 16:9 | 通用横版 / X 配图 | — |
| 1:1 | 小红书方图 | — |

本技能不指定发布渠道时默认按公众号场景出图（2.35:1）；客户提到 X 或小红书就切到对应比例。产出的 `cover.png` 路径设计为可直接作为下游衔接：

```bash
python3 scripts/publish.py --article <文章md> --cover <output-dir>/cover.png
```

这条命令属于 `soia-pkm-publish` 自己的脚本，客户需先按该 skill 的安装说明配置好凭据；本技能只负责把 `cover.png` 生成到约定路径，不代替 publish 执行发布。

## 确认闸门（生成前必须走）

生成前必须让客户确认以下四项——它们决定图能不能直接用：**type、palette、text（文字层级）、aspect（比例）**。rendering 与 mood 一并展示方便客户一次看全，但硬性确认门槛以前四项为准。

- 内容分析出的推荐值、`config.yml` 里的偏好默认值，都只算**推荐输入**，不构成跳过确认的理由。
- 唯一的跳过条件：客户在**当前这句话**里明确说"直接生成"/`--quick`/等价表述，或私有 `config.yml` 设置了 `quick_mode: true`。
- 跳过确认后，必须在完成回执里说明本次沿用了哪些假设（用了哪个默认 type/palette/aspect）。

## 后端解析

生图后端解析顺序（两级，v1 只有一个真实后端）：

1. **当前消息指定** —— 客户在这一轮明确点名了要用的后端，直接使用。
2. **探测 codex CLI** —— 检查 `codex` 是否在 `PATH` 上可执行，且已完成登录（用官方提供的只读登录状态检查，具体子命令以当前 codex CLI 版本文档为准）。满足则委托它生成：以 `codex exec` 的形式调用，把落盘好的 prompt 文件内容、目标比例、输出路径一并交给 codex，由 codex 内部的 image_gen 能力完成实际生图，本技能只负责组织 prompt、传参和校验产物是否落地。
   - **落地路径注意**：codex exec 生成的图片默认落在 `~/.codex/generated_images/<session-id>/` 缓存目录下，**不会**自动出现在本技能约定的 `<output-dir>/cover.png`。调用后必须去该缓存目录定位刚生成的文件，再复制/移动到约定输出路径，然后才校验落地；不要只检查目标路径一次就判定"生成失败"。
3. **都不满足** —— 明确告知客户"codex CLI 不可用（未安装/未登录/探测失败，具体到哪一种）"，并询问客户要不要现在安装登录、换一台已装好的机器、或者暂缓生成。**绝不静默降级**成任何未声明的其它方式。

## ⛔ 两条红线（必须遵守）

1. **禁止用 SVG / HTML / canvas / 任何代码渲染冒充位图。** 只要客户要的是"封面图"，交付物必须是真实生成的位图（PNG/JPG），不能用矢量代码画一张图糊弄过去——哪怕内容看起来"像图"。生图后端不可用时，走上面"都不满足"的分支询问客户，不得退而求其次改用代码渲染。
2. **禁止在已生成的位图上描字、改字、贴补丁。** 文字错了、模糊了、排版挤了，唯一合法修复是**改 prompt 重新生成**，不得用 Pillow/Canvas/ImageMagick/OCR 覆盖等任何编程手段在原图上直接改动像素级文字。重新生成时新写一份 prompt 文件、新的输出文件名，**保留旧版本**供客户对比，不覆盖旧产物。

## Prompt 落盘（硬要求）

每次调用生图后端**之前**，必须把这次生成用的完整最终 prompt 写入产物目录下的 `prompts/NN-cover-<slug>.md`（`NN` 从 `01` 递增，`slug` 为 2–4 个英文单词的 kebab-case 短语，来自文章主题）。这个文件是可复现记录：换后端重跑、事后追溯这次为什么这样生成，都靠它，不依赖记忆。文字纠错重生成时新开一份编号更高的 prompt 文件，不覆盖旧的。

## 构图原则

- **留白 40–60%**：主体不要塞满画面，给标题文字留呼吸空间。
- **主元素居中或左偏**：视觉焦点放画面中央或偏左，右侧/下方留给文字排版。
- **人物只用简化剪影，禁止写实人脸**：涉及人物元素一律画成简化剪影或抽象形态，不生成可辨识的写实人脸。
- **标题必须用客户提供或原文的确切标题，禁止编造或改写**：`text` 不是 `none` 时，图上出现的标题文字必须逐字对应客户给出的标题；拿不准客户原话时先问，不替客户"优化措辞"。

## 输出目录结构

```
outputs/cover-image/<topic-slug>/
├── prompts/
│   └── 01-cover-<topic-slug>.md
└── cover.png
```

- `<topic-slug>` 与 `prompts/` 里的 `slug` 保持一致，方便对应查找。
- 客户指定了别的输出目录（如某个 vault 内的文章同级目录）时，以客户指定为准，只是仍然遵守"`prompts/` 子目录 + `cover.png`"这套内部结构。
- 文字纠错重生成：新版本用 `cover-v2.png`（依次递增）+ 对应编号更高的 prompt 文件，旧版本不删除，直到客户确认可以清理。

## 边界与限制

- 本技能不生成插画、多图长图、文中配图——这些属于其它转化产物（如 `soia-pkm-transform` 覆盖的信息图/长图），本技能只做单张封面。
- 本技能不做发布、不碰任何账号凭据或平台 API；把 `cover.png` 交给下游发布 skill 之后的动作由客户或对应 skill 自己完成。
- 本技能不保证生图后端一定成功产出满意结果——生图具备一定不确定性，效果不理想时走"重新生成"流程，不代表本技能本身失败。

## 路线图 v2

文中配图（article illustration，正文内多图插画而非单张封面）留待后续版本，本版只覆盖单张封面生成。
