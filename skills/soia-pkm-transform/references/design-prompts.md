# Design Prompts

用于 PPT、长图、信息图、海报、封面图、插画和视觉报告。目标是把文章转换成可读、好看、信息密度足够的产物，而不是把原文压缩成几张低质摘要卡。

## Prompt 路由

不同设计产物必须使用不同 prompt，不要共用一个「把文章转换成视觉」的大提示词。

| 目标产物 | 首选 prompt | 首选 provider | 关键边界 |
|----------|-------------|---------------|----------|
| PPT / 课件 | [PPT / 课件 Prompt](#ppt--课件-prompt) | 当前 agent presentations / HTML deck | 8-12 页、叙事结构、版式轮廓变化、可渲染检查 |
| 高密度长图 / 信息图 / 海报 | [高密度信息图 Prompt](#高密度信息图-prompt) | local_visual HTML/CSS screenshot | 中文密集文字必须排版在 HTML/CSS，不优先生图 |
| 封面图 / 头图 / 背景图 | [Imagegen / 封面图 Prompt](#imagegen--封面图-prompt) | Codex imagegen / gpt-image-2 / image provider | 少字或无字；最终标题建议后期叠加 |
| 插画 / 图标 / 视觉隐喻 | [Imagegen / 封面图 Prompt](#imagegen--封面图-prompt) | Codex imagegen / gpt-image-2 / image provider | 生成视觉资产，不承载事实密集信息 |
| 视觉报告 / PDF report | [视觉报告 Prompt](#视觉报告-prompt) | Markdown/HTML/PDF provider | 结构化综合，不冒充全文 PDF |
| NotebookLM artifact | [NotebookLM 产物 Prompt](#notebooklm-产物-prompt) | NotebookLM | source-grounded；必须记录 Notebook/artifact id |

Codex image2 / imagegen 的定位：生成**视觉素材**，不是中文密集排版引擎。若用户要「一张图讲清楚」且包含大量中文、数字、表格或引用，先用 HTML/CSS 排版；可以把 imagegen 生成的背景、插画、纹理、图标作为素材再叠加文字。

## 通用视觉合同

每次视觉转化先写一份 brief，再生成产物：

```yaml
source:
  title: ""
  author: ""
  type: X article | wechat | web | markdown
  sections: []
audience: ""
job_to_be_done: ""       # 看完之后要理解/判断/行动什么
content_mode: visual_dense | learning | synthesize
information_architecture:
  main_verdict: ""
  blocks: []             # 8-15 个信息块，每个有 claim + detail
  flows: []              # 流程/因果/层级/对比关系
  tables_or_charts: []   # 有数据用真实数据；无数据只做 labeled illustrative chart
  risks_or_limits: []
visual_direction:
  format: poster | long_image | deck | report
  canvas: "900x1600 | 1080x1920 | 16:9"
  style_reference: ""    # 用户给的参考图/模板/品牌方向
  typography: ""
  palette: ""
negative_constraints: []
qa:
  render_check: true
  overlap_check: true
  readability_check: true
```

负向约束默认包含：

- 不做只有标题、大色块、渐变背景和 3 条 bullet 的低信息图。
- 不把长文压成 3-5 个空泛观点，除非用户明确要求摘要。
- 不使用单一色相铺满全图；至少有背景色、主强调色、风险/支持语义色。
- 不让图表、卡片、文字互相覆盖；必须渲染后抽查。
- 中文长文优先 HTML/CSS 截图，不优先生图，避免文字乱码和不可控拼写。
- 没有真实量化数据时，图表必须标注「示意」，不能伪造统计。

## 高密度信息图 Prompt

用于「转成高密度图 / 信息图 / 海报 / 一张图讲清楚」。

```text
你是资深中文信息设计师和编辑。请把下面文章转换成一张高密度中文信息图。

目标读者：{audience}
画幅：{900x1600 或 1080x1920}
信息模式：visual_dense，不是摘要卡。

内容要求：
1. 严格基于原文，不引入原文外事实数据。
2. 提取 1 个主判断、8-15 个信息块、1 条主流程或关系链、1 个对比表或示意图、支持点、风险点、继续追问。
3. 每个信息块必须有「短标题 + 具体解释」，避免空泛名词。
4. 如果使用图表但原文没有数字，必须标注「教学示意」。

版式要求：
1. 顶部：大标题 + 来源 + verdict 横幅。
2. 中上部：6-9 个编号卡片，形成主信息矩阵。
3. 中部：流程图 / 层级图 / 对比表 / 示意图至少 2 种。
4. 底部：支持使用的点、必须警惕的点、继续追问。
5. 视觉密度接近财经/研究海报，而不是社交媒体标题图。

视觉要求：
1. 字体层级清楚：标题、分区标题、卡片标题、正文、注释至少 4 级。
2. 使用深浅对比、边框、语义色区分普通信息/支持/风险。
3. 控制留白，避免大片空区；但文字不能拥挤到不可读。
4. 禁止图表或文字覆盖其他模块。

输出：
- 先给信息架构 JSON/YAML。
- 再给完整 HTML/CSS。
- 渲染成 PNG 后检查：尺寸、可读性、重叠、截断。
```

## Imagegen / 封面图 Prompt

用于「生成封面图 / 头图 / 文章配图 / 背景图 / 插画 / 视觉隐喻」。可调用 Codex imagegen / gpt-image-2 / 其他 image provider。

不要用它直接生成中文密集信息图；图片模型对长中文、表格、精确数字和小字不稳定。需要文字时，先生成无字或少字视觉资产，再用 HTML/PPT/图片编辑叠加文字。

```text
你是资深视觉创意总监。请为下面文章生成一张 {用途：封面图/头图/插画/背景图}。

目标读者：{audience}
画幅：{16:9 / 4:3 / 1:1 / 3:4 / 9:16}
视觉目标：让读者在 2 秒内感到 {情绪/主题/冲突}
文章主判断：{main_verdict}

内容要求：
1. 只表达文章的核心主题、情绪和视觉隐喻，不承载密集事实。
2. 不生成长段中文文字、表格、小字、真实统计数字。
3. 如果必须有文字，只允许 1 个短中文标题或留出标题区，最终文字由后期排版叠加。
4. 不伪造品牌 logo、人物肖像、真实机构标识，除非用户提供素材和授权。

视觉要求：
1. 明确主体、前景、中景、背景和留白区域。
2. 指定风格：{editorial / cinematic / isometric / 3D / collage / minimal / research poster background}。
3. 指定色彩：{palette}，避免单色糊满。
4. 为后期叠加中文标题预留干净区域。

输出：
- 生成图像。
- 如果还要成品封面，后续用 HTML/PPT/图片编辑把标题、来源、作者叠加上去。
```

## PPT / 课件 Prompt

用于「转成 PPT / 课件 / workshop deck」。

```text
你是课程设计师和演示文稿设计师。请把下面文章转换成 8-12 页中文教学 PPT。

目标读者：{audience}
学习目标：看完能解释 {3-5 个具体能力}
内容模式：learning / preserve。不要只做摘要。

叙事结构：
1. 题名页：一句话说明这篇文章解决什么问题。
2. 文章地图：保留原文章节和逻辑，不只列观点。
3. 真实案例：把文章案例拆成任务、资料、工具、交付、验收。
4. 概念层级：用图解释术语关系。
5. 关键辨析：用表格或对照卡解释易混概念。
6. 工作流：用流程图落到真实执行。
7. 风险与边界：幻觉、资料质量、验证责任。
8. 自测 / 行动清单 / 来源。

设计要求：
1. 每页一个明确判断，不写「背景介绍」「核心观点」这类空标题。
2. 版式轮廓要变化：封面、地图、流程、对比、表格、检查清单、自测，不要每页同一种卡片网格。
3. 中文正文少而准；长内容进表格、流程或讲稿，不堆 bullet。
4. 输出 PPTX 时必须渲染全部页面并检查溢出、重叠、空白页。
5. 如果用 HTML deck，要保留导航和导出路径；如果用 PPTX，要保证可编辑。
```

## 视觉报告 Prompt

用于「把文章生成视觉报告 / report PDF / 研究简报」，不是全文 PDF。

```text
你是研究编辑和信息设计师。请把下面文章转换成一份中文视觉报告。

内容模式：synthesize，不是全文 preserve，也不是 TL;DR 摘要。
目标读者：{audience}

结构要求：
1. 摘要：3-5 条，不超过 1 页。
2. 文章地图：保留原文主要章节。
3. 核心判断：每条都对应原文依据。
4. 关键证据 / 案例：用表格、流程或卡片呈现。
5. 风险与边界：哪些结论需要验证，哪些是作者观点。
6. 行动建议 / 继续追问。
7. 来源与生成说明。

设计要求：
1. 报告可以比 PPT 信息更密，但必须有清楚层级。
2. 图表只使用原文数据；没有数据时标注示意。
3. 不把 report 当作「转 PDF」的默认替代品。
```

## NotebookLM 产物 Prompt

NotebookLM 适合 grounded synthesis，但也需要明确产物类型和保真度。

```text
请严格基于已上传 source 生成 {artifact_type}。

语言：中文。
目标读者：{audience}
保真要求：保留原文主要章节、例子、术语关系和风险边界；不要把长文压成泛泛摘要。

如果生成 slide deck：
- 生成 8-12 页。
- 每页标题必须是一个明确判断。
- 包含：文章地图、案例拆解、概念层级、流程图、易混概念对照、风险边界、自测题、来源页。

如果生成 quiz / flashcards：
- 所有题目只考 source 中出现的概念。
- 答案区必须包含解释和 source-grounded依据。

如果生成 infographic：
- 采用高密度信息图结构：verdict、编号卡片、流程/表格、支持点/风险点/继续追问。
```

## QA Gate

视觉产物完成前必须过关：

- **内容保真**：能对应回原文结构和例子；没有把全文误做成摘要。
- **信息密度**：长图至少 8 个信息块；PPT 至少 8 页（除非用户指定更短）。
- **版式质量**：没有孤零零大标题、大片空白、重复卡片模板。
- **视觉语义**：支持/风险/流程/注释有清楚的颜色或版式区分。
- **渲染验证**：PNG/PDF/PPTX 已实际渲染；检查重叠、截断、乱码。
- **诚实回执**：如果 NotebookLM 未登录、Open Design 不可用或发生降级，必须写明真实 provider。
