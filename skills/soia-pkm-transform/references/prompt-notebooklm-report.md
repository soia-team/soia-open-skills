# NotebookLM Report Prompt

用于 NotebookLM `generate report`。它是 grounded report，不是全文 PDF，也不是短摘要。

```text
请严格基于已上传 source 生成中文 grounded report。

目标读者：{params.audience}
语言：中文
内容模式：synthesize，但必须保留 source 结构和证据。

结构：
1. 执行摘要：3-5 条。
2. Source 地图：主要章节和论证路径。
3. 核心判断：每条判断都对应 source 依据。
4. 关键证据 / 案例 / 流程：用表格或清单呈现。
5. 风险与边界：哪些是作者观点，哪些需要外部验证。
6. 行动建议 / 继续追问。
7. 来源说明。

约束：
- 不引入 source 外事实。
- 不把 report 当作全文 PDF。
```

## QA Gate

- 记录 notebook_id、source_id、artifact_id、下载路径。
- 若用户要「转 PDF」，应走 PDF preserve recipe，而不是 NotebookLM report。
