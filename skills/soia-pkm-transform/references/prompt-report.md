# Report Prompt

用于「视觉报告 / report PDF / 研究简报」。Report 是结构化综合，不是全文 PDF；用户说「转 PDF」时默认走全文保真 PDF recipe。

## 参数

```yaml
target_output: report
params:
  provider: auto                  # notebooklm | local_markdown | html_report
  output_format: markdown         # markdown | html | pdf
  audience: auto
  content_mode: synthesize
  density: dense
  report_type: deep_grounded      # deep_grounded | briefing | study_guide | blog_post | visual_report
  include_sources: true
```

## Report 类型

- `deep_grounded`：默认。深度 grounded report，覆盖 source 结构、概念、案例和边界。
- `briefing`：快速简报，只在用户明确要 brief 时使用。
- `study_guide`：学习指南，包含术语、练习、自测。
- `blog_post`：改写成博客文章，不等于研究报告。
- `visual_report`：HTML/PDF 视觉报告，适合阅读和转 PDF。

## Prompt 模板

```text
你是研究编辑和信息设计师。请把下面文章转换成一份中文视觉报告。

内容模式：synthesize，不是全文 preserve，也不是 TL;DR 摘要。
目标读者：{params.audience}

结构要求：
1. 执行摘要：3-5 条，不超过 1 页。
2. Source coverage：章节清单、概念清单、案例链、关键判断。
3. 文章地图：保留原文主要章节和逻辑。
4. 概念覆盖矩阵：模块、术语、解释、案例关系、易混对象。
5. 核心判断：每条都对应原文依据。
6. 关键证据 / 案例：用表格、流程或卡片呈现。
7. 风险与边界：哪些结论需要验证，哪些是作者观点。
8. 行动建议 / 继续追问。
9. 来源与生成说明。

设计要求：
1. 报告可以比 PPT 信息更密，但必须有清楚层级。
2. 图表只使用原文数据；没有数据时标注示意。
3. 不把 report 当作「转 PDF」的默认替代品。
```

## QA Gate

- 结构可追溯到原文。
- 关键判断有依据，不编造外部事实。
- 明确标注 report 与全文 PDF 的区别。
- 中长文 report 不得少到只剩摘要；应覆盖主要章节和概念。
