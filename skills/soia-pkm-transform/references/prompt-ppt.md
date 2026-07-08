# PPT Prompt

用于「转成 PPT / 课件 / workshop deck / slide deck」。默认输入是一篇文章或 Markdown，不要求用户提前整理大纲；agent 应先从正文标题、段落结构、例子、术语和清单中推断 deck 结构。

## 参数

```yaml
target_output: ppt
source: article_packet | markdown_path | url
params:
  provider: auto                 # auto | local_presentation | html_deck | notebooklm | open_design
  output_format: pptx            # pptx | html | pdf
  audience: auto                 # 小白 | 专业读者 | 管理者 | 学生 | ...
  language: zh_Hans
  content_mode: learning         # learning | preserve | synthesize
  style: auto                    # course | technical | executive | workshop | xhs | magazine
  slide_count: auto              # auto | 6 | 8 | 10 | 12 | ...
  aspect_ratio: "16:9"
  density: dense                 # normal | dense | high
  include_speaker_notes: auto
  use_notebooklm: auto
  use_open_design: auto
```

参数优先级：用户本轮明确说出 > 调用方传入 `params` > 配置文件 > 自动推断。

## 默认推断

- Markdown 有清楚标题层级：把一级/二级标题作为 deck 的叙事骨架，不只提炼 3-5 个观点。
- 长文：10-14 页；中等文章：8-10 页；短文：6-8 页。用户指定页数时服从用户。
- 概念入门 / 教程类：`style: course`，`content_mode: learning`。
- 技术方法 / 工具链文章：`style: technical`，加入架构、流程、操作清单和验证页。
- 观点文章：`style: executive` 或 `magazine`，加入论点、证据、反例和行动建议。
- 用户只说「转 PPT」时，默认保留文章结构和关键例子，不做短摘要。

## Prompt 模板

```text
你是中文课程设计师、信息架构师和演示文稿设计师。请把下面文章转换成一份可编辑中文 PPT。

输入：
- 文章标题：{title}
- 来源/作者：{source_url_or_author}
- 目标读者：{params.audience}
- 页数：{params.slide_count}
- 风格：{params.style}
- 画幅：{params.aspect_ratio}
- 内容模式：{content_mode}

任务：
1. 先读取全文，保留原文章节、案例、清单、关键术语和因果关系。
2. 生成 1 份 slide plan，列出每页：页标题、页面任务、核心内容、视觉形式、备注。
3. 再生成 PPTX 或 HTML deck。每页标题必须是一个明确判断，不要写「背景介绍」「核心观点」这类空标题。

推荐结构：
1. 题名页：文章标题 + 一句话说明它解决的问题。
2. 文章地图：把原文结构可视化，不只列观点。
3. 问题场景：读者为什么需要这篇文章。
4. 核心概念：术语关系、层级或知识图谱。
5. 案例拆解：任务、资料、工具、交付、验收。
6. 工作流：真实执行步骤、输入输出、检查点。
7. 关键辨析：易混概念对照表或判断矩阵。
8. 风险边界：原文提醒、幻觉/误读风险、验证责任。
9. 自测/讨论/行动清单。
10. 来源页：来源链接、作者、生成说明。

设计要求：
1. 版式轮廓至少 4 种：封面、地图、流程、对比、表格、检查清单、自测、来源。
2. 避免每页重复卡片网格；避免大标题 + 三个 bullet 的低密度页面。
3. 中文正文少而准；长内容进入表格、流程、备注或讲稿。
4. 有数据只使用原文数据；没有数据时不要伪造图表。
5. 输出后必须渲染全部页面，检查文字溢出、重叠、乱码、空白页。
```

## QA Gate

- 至少 8 页，除非用户明确指定更短。
- 每页都有页面任务，不是自动摘要卡。
- 能对应回原文结构、例子和关键清单。
- 至少 4 种版式轮廓。
- PPTX 能打开并渲染；HTML deck 保留导航和导出路径。
