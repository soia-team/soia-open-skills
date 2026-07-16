# Open Design Prompt

用于把文章交给 Open Design 或用 Open Design 模板指导本地生成 PPT、长图、信息图、HTML deck、HyperFrames。

先读 [provider-open-design.md](provider-open-design.md) 确认使用模式。若不是 Open Design handoff，而只是参考模板本地生成，回执写 `Template-guided local render`。

## 参数

```yaml
target_output: ppt | long_image | infographic | report | video
provider: open_design
params:
  mode: handoff | template_guided_local_render
  template: auto
  design_system: auto
  style: auto
  audience: auto
  density: dense
  aspect_ratio: "16:9"
  canvas: auto
  output_format: html | pptx | pdf | png | mp4
  mcp_agent: auto
```

## 样式预设

不同产物不要共用同一个视觉提示词。

| style | 适用 | 模板提示 | 视觉重点 |
|-------|------|----------|----------|
| `course_module` | 小白教程、知识讲解、训练营 | `html-ppt-course-module` | 章节化、例题、自测、讲稿 |
| `technical_sharing` | 技术文章、工具教程、AI workflow | `html-ppt-tech-sharing` | 架构图、流程、命令、检查点 |
| `knowledge_blueprint` | 知识库、系统结构、方法论 | `html-ppt-knowledge-arch-blueprint` | 层级、关系、地图、输入输出 |
| `graph_dark` | AI 工具、模型关系、复杂概念网络 | `html-ppt-graphify-dark-graph` | 图谱、节点、边、语义分组 |
| `editorial_magazine` | 观点文章、趋势解读、商业分析 | `guizang-ppt` / `html-ppt-taste-editorial` | 强标题、图文节奏、判断和证据 |
| `dense_research_poster` | 一张图讲清楚、研究海报 | `magazine-poster` / `finance-report` | 8-15 信息块、表格、风险/支持区 |
| `xhs_cards` | 小红书卡片 / 社交轮播 | `html-ppt-xhs-white-editorial` / `social-carousel` | 3-8 张卡、标题短、结论明确 |
| `hyperframes_explainer` | 短视频、动效解释 | `hyperframes` / `motion-frames` | 分镜、节奏、字幕、可导出 MP4 |

## Prompt 模板

```text
你是 Open Design 设计工作流编排者。请基于下面 article packet 生成一个可交给 Open Design 的设计 brief，或在 template-guided local render 模式下生成自包含 HTML/CSS/PPT 产物。

输入：
- 目标产物：{target_output}
- 使用模式：{params.mode}
- 推荐模板：{params.template}
- 设计系统：{params.design_system}
- 样式：{params.style}
- 受众：{params.audience}
- 内容密度：{params.density}
- 画幅/尺寸：{params.aspect_ratio_or_canvas}
- 文章标题：{title}
- 来源/作者：{source_url_or_author}

必须先输出设计 brief：
1. Job to be done：读者看完要理解、判断或行动什么。
2. Source coverage：列出原文章节、概念清单、案例链和关键判断；这是后续验收基线。
3. 信息架构：8-15 个信息块；每块包含 claim、evidence/detail、source anchor。
4. 视觉结构：封面/总览/流程/对比/表格/风险/行动/来源；PPT 至少 4 种版式轮廓。
5. 模板映射：说明为何选择该 Open Design template / style，不能只写“现代感/科技感”。
6. 负向约束：不要低密度摘要卡，不要单色大留白，不伪造数字，不把长文压成三点。

如果 target_output=ppt：
- 中长文生成 14-18 页 slide plan；短文至少 8 页；每页标题必须是明确判断，不是“背景介绍”。
- 每页指定 layout role：cover / map / flow / matrix / table / case / quiz / source 等。
- 必须有文章地图、概念覆盖矩阵、案例拆解、流程/架构、术语速查、对比表、风险边界、自测、来源页。
- 若文章介绍十几个概念，不允许只做“概念简介”几页；必须分模块覆盖。

如果 target_output=long_image 或 infographic：
- 使用 1080x1920 或用户指定 canvas。
- 顶部放 verdict / 主题判断；中部 8-15 个编号卡片；下部放流程、对比表或关系图；底部放支持点/风险点/继续追问。
- 中文密集文字使用 HTML/CSS 排版，不要求生图模型直接绘制文字。

如果 target_output=video：
- 先写 8-12 个镜头的 storyboard，再映射 HyperFrames / motion template。
- 每个镜头有字幕、画面元素、运动、时长。

完成后必须给 QA：
- render/export 命令或 Open Design handoff URL/项目 ID。
- 检查文字重叠、截断、乱码、空白页。
- 说明是否真正调用 Open Design，还是只使用 Open Design 模板指导本地生成。
```

## QA Gate

- 没有 `od` / daemon / project id 时，不写「Open Design 已生成」。
- 使用 MCP 安装命令前先 `--print`；真实写配置需要用户确认。
- 中长文 PPT 至少 14 页、至少 4 种版式轮廓。
- 信息图至少 12 个信息块，且能回到原文证据。
- 导出物必须实际渲染或下载检查。
