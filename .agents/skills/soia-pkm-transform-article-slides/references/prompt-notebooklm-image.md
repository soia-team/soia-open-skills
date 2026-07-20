# NotebookLM Image Prompt

用于 NotebookLM `generate infographic` 或 image-like artifact。NotebookLM 适合 source-grounded 信息组织；中文密集最终成图仍需要下载后检查，可必要时交给本地 HTML/CSS 重排。

```text
请严格基于已上传 source 生成一张中文高密度 infographic。

目标读者：{params.audience}
语言：中文
信息模式：visual_dense，不是摘要卡。

结构要求：
1. 顶部：文章标题、来源、一个主判断。
2. 中部：8-15 个信息块，每块有短标题和具体解释。
3. 至少包含 1 条流程/因果链、1 个对比表或关系矩阵。
4. 底部：支持点、风险点、继续追问。
5. 不引入 source 外事实；没有数据时不要伪造统计图。

输出后下载 infographic artifact，并检查中文是否可读、是否有截断或错字。
```

## QA Gate

- 记录 notebook_id、source_id、artifact_id、下载路径。
- 若中文小字不可读或信息块不足，改用 [prompt-infographic.md](prompt-infographic.md) 做本地 HTML/CSS 版。
