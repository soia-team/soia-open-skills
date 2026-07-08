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
  style: auto                    # course_module | technical_sharing | knowledge_blueprint | editorial_magazine | xhs_cards | executive | workshop
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
- 长文或概念数 >=12：14-18 页；中等文章：10-14 页；短文：8-10 页。用户指定页数时服从用户并记录降级。
- 概念入门 / 教程类：`style: course_module`，`content_mode: learning`。
- 技术方法 / 工具链文章：`style: technical_sharing`，加入架构、流程、操作清单和验证页。
- 知识库 / 系统结构 / 方法论：`style: knowledge_blueprint`，加入关系图、输入输出、MOC/流程。
- 观点文章：`style: editorial_magazine` 或 `executive`，加入论点、证据、反例和行动建议。
- 小红书 / 社交轮播：`style: xhs_cards`，每页一个任务，标题短而具体。
- 用户只说「转 PPT」时，默认保留文章结构和关键例子，不做短摘要。

## 样式预设

| style | 页数 | 必须出现的页面角色 | 适合文章 |
|-------|------|--------------------|----------|
| `course_module` | 14-18 | 封面、学习地图、概念覆盖、案例拆解、流程、术语速查、练习、自测、来源 | 小白教程、概念入门 |
| `technical_sharing` | 14-18 | 封面、系统图、pipeline、命令/工具表、QA gate、风险矩阵、检查清单、来源 | 技术方法、AI workflow |
| `knowledge_blueprint` | 8-12 | 封面、知识地图、层级图、输入输出、操作模型、MOC、下一步、来源 | 知识库、方法论 |
| `editorial_magazine` | 8-12 | 强标题封面、判断页、证据网格、反例/边界、影响、行动建议、来源 | 观点文章、趋势解读 |
| `xhs_cards` | 6-9 | Hook、概念卡、步骤卡、对照卡、坑点卡、复盘卡 | 社交卡片和轮播 |

如果用户没有指定 style，先根据文章类型自动选一个；不要让 `auto` 直接进入生成。

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
2. 先抽 source coverage：章节清单、概念清单、案例链、关键判断、风险词。
3. 先判断文章类型并选择 style preset；如果 style=auto，必须写明自动选择依据。
4. 生成 1 份 slide plan，列出每页：页标题、页面任务、核心内容、原文依据、视觉形式、讲稿/备注、覆盖的概念。
5. 再生成 PPTX 或 HTML deck。每页标题必须是一个明确判断，不要写「背景介绍」「核心观点」这类空标题。

推荐结构：
1. 题名页：文章标题 + 一句话说明它解决的问题。
2. 文章地图：把原文结构和概念覆盖可视化，不只列观点。
3. 问题场景：读者为什么需要这篇文章。
4. 核心概念：术语关系、层级或知识图谱。
5. 案例拆解：任务、资料、工具、交付、验收。
6. 工作流：真实执行步骤、输入输出、检查点。
7. 术语速查：覆盖主要术语，不遗漏主体概念。
8. 关键辨析：易混概念对照表或判断矩阵。
9. 风险边界：原文提醒、幻觉/误读风险、验证责任。
10. 自测/讨论/行动清单。
11. 来源页：来源链接、作者、生成说明。

设计要求：
1. 版式轮廓至少 4 种：封面、地图、流程、对比、表格、检查清单、自测、来源。
2. 避免每页重复卡片网格；避免大标题 + 三个 bullet 的低密度页面。
3. 中文正文少而准；长内容进入表格、流程、备注或讲稿。
4. 有数据只使用原文数据；没有数据时不要伪造图表。
5. 输出后必须渲染全部页面，检查文字溢出、重叠、乱码、空白页。
6. 每页最多一个主判断；多个事实用表格/分组/时间线，不堆散 bullet。
7. 封面和结尾不能占掉主要信息量；正文页要让读者学到具体结构、流程或判断。
8. 不使用单一色相铺满整套 deck；至少区分背景、主强调、风险/反例、支持/行动四类语义。
```

## QA Gate

- 中长文至少 14 页；短文至少 8 页；用户明确指定更短时记录降级。
- 每页都有页面任务，不是自动摘要卡。
- 能对应回原文结构、例子和关键清单。
- 概念/术语覆盖率达到主要概念的 80% 以上；概念教程不允许只讲 3-5 个词。
- 至少 4 种版式轮廓。
- PPTX 能打开并渲染；HTML deck 保留导航和导出路径。
- 逐页截图或预览抽查：无文字重叠、越界、乱码、空白页。
- 如果输出像“几张摘要卡”，必须回到 slide plan 重做，不算完成。
