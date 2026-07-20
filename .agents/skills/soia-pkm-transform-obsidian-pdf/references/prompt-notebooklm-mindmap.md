# NotebookLM Mindmap Prompt

用于 NotebookLM `generate mind-map`。

```text
请严格基于已上传 source 生成中文 mind map。

目标读者：{params.audience}
语言：中文

结构要求：
1. 根节点是文章标题或核心问题。
2. 一级节点保留原文主要章节或论证模块。
3. 二级节点放关键概念、案例、流程、风险。
4. 三级节点放必要解释，避免过长句。
5. 不要把长文压成 3 个空泛分支。
6. 不引入 source 外事实。
```

## QA Gate

- 记录 notebook_id、source_id、artifact_id。
- 层级不超过 4 层。
- 下载后若节点过空泛，改用本地 Mermaid mindmap 重排。
