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
  include_sources: true
```

## Prompt 模板

```text
你是研究编辑和信息设计师。请把下面文章转换成一份中文视觉报告。

内容模式：synthesize，不是全文 preserve，也不是 TL;DR 摘要。
目标读者：{params.audience}

结构要求：
1. 执行摘要：3-5 条，不超过 1 页。
2. 文章地图：保留原文主要章节和逻辑。
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

## QA Gate

- 结构可追溯到原文。
- 关键判断有依据，不编造外部事实。
- 明确标注 report 与全文 PDF 的区别。
