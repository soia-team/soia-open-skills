# Design Prompts

用于 PPT、长图、信息图、海报、封面图、插画和视觉报告。目标是把文章转换成可读、好看、信息密度足够的产物，而不是把原文压缩成几张低质摘要卡。

## Prompt 路由

不同设计产物必须使用不同 prompt，不要共用一个「把文章转换成视觉」的大提示词。

| 目标产物 | 首选 prompt | 首选 provider | 关键边界 |
|----------|-------------|---------------|----------|
| PPT / 课件 | [prompt-ppt.md](prompt-ppt.md) | 当前 agent presentations / HTML deck | 8-12 页、叙事结构、版式轮廓变化、可渲染检查 |
| 高密度长图 / 信息图 / 海报 | [prompt-infographic.md](prompt-infographic.md) | local_visual HTML/CSS screenshot | 中文密集文字必须排版在 HTML/CSS，不优先生图 |
| 封面图 / 头图 / 背景图 | [prompt-codex-image.md](prompt-codex-image.md) | Codex imagegen / gpt-image-2 / image provider | 少字或无字；最终标题建议后期叠加 |
| 插画 / 图标 / 视觉隐喻 | [prompt-codex-image.md](prompt-codex-image.md) | Codex imagegen / gpt-image-2 / image provider | 生成视觉资产，不承载事实密集信息 |
| 视觉报告 / PDF report | [prompt-report.md](prompt-report.md) | Markdown/HTML/PDF provider | 结构化综合，不冒充全文 PDF |
| Open Design PPT / 长图 / 动效 | [prompt-open-design.md](prompt-open-design.md) | Open Design / template-guided local render | 必须说明 handoff 还是模板指导本地生成 |
| NotebookLM slide deck | [prompt-notebooklm-ppt.md](prompt-notebooklm-ppt.md) | NotebookLM | source-grounded deck；记录 Notebook/artifact id |
| NotebookLM image / infographic | [prompt-notebooklm-image.md](prompt-notebooklm-image.md) | NotebookLM | source-grounded image artifact；密集中文仍需人工/截图验收 |
| NotebookLM quiz / flashcards / mindmap / podcast / report | [prompt-notebooklm.md](prompt-notebooklm.md) 路由到具体文件 | NotebookLM | source-grounded；必须记录 Notebook/artifact id |

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
  coverage: []           # 原文章节、概念清单、案例链、关键判断
  blocks: []             # 12-18 个信息块，每个有 claim + detail
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

## 目标 Prompt 文件

- PPT / 课件：读取 [prompt-ppt.md](prompt-ppt.md)，它支持 `slide_count`、`audience`、`style`、`aspect_ratio`、`provider` 等参数。
- 高密度长图 / 信息图：读取 [prompt-infographic.md](prompt-infographic.md)，它默认走 HTML/CSS 截图并强调信息块密度。
- Codex image / imagegen：读取 [prompt-codex-image.md](prompt-codex-image.md)，它约束 imagegen 只做视觉素材，不做密集中文排版。
- Open Design：读取 [prompt-open-design.md](prompt-open-design.md)，它区分 `handoff` 和 `template_guided_local_render`，并按 PPT、长图、视频选不同模板。
- 视觉报告：读取 [prompt-report.md](prompt-report.md)，它区分 report 和全文 PDF。
- NotebookLM artifact：先读取 [prompt-notebooklm.md](prompt-notebooklm.md)，再按产物读取 [prompt-notebooklm-ppt.md](prompt-notebooklm-ppt.md)、[prompt-notebooklm-image.md](prompt-notebooklm-image.md)、[prompt-notebooklm-quiz.md](prompt-notebooklm-quiz.md)、[prompt-notebooklm-flashcards.md](prompt-notebooklm-flashcards.md)、[prompt-notebooklm-mindmap.md](prompt-notebooklm-mindmap.md)、[prompt-notebooklm-podcast.md](prompt-notebooklm-podcast.md) 或 [prompt-notebooklm-report.md](prompt-notebooklm-report.md)。

## QA Gate

视觉产物完成前必须过关：

- **内容保真**：能对应回原文结构和例子；没有把全文误做成摘要。
- **信息密度**：长图至少 12 个信息块；中长文 PPT 至少 14 页（除非用户指定更短）。
- **概念覆盖**：概念教程、工具教程、方法论文章要覆盖主要概念的 80% 以上，不能只挑几个词做摘要。
- **版式质量**：没有孤零零大标题、大片空白、重复卡片模板。
- **视觉语义**：支持/风险/流程/注释有清楚的颜色或版式区分。
- **渲染验证**：PNG/PDF/PPTX 已实际渲染；检查重叠、截断、乱码。
- **诚实回执**：如果 NotebookLM 未登录、Open Design 不可用或发生降级，必须写明真实 provider。
