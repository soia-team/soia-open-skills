# NotebookLM PPT Prompt

用于 NotebookLM `generate slide-deck`，输出 `.pptx` 或 PDF deck。它和本地 PPT prompt 不同：NotebookLM 优势是 source-grounded synthesis，短板是版式可控性较弱，所以 prompt 要强调结构、页标题和下载记录。

```text
请严格基于已上传 source 生成一份中文 slide deck。

目标读者：{params.audience}
页数：{params.slide_count 或 8-12}
推荐风格：{params.style 或 course_module / technical_sharing / knowledge_blueprint / editorial_magazine}
语言：中文
内容模式：learning / preserve，不能压成泛泛摘要。

Deck 要求：
1. 每页标题必须是一个明确判断，不要写「背景介绍」「核心观点」。
2. 保留原文主要章节、例子、术语关系、工作流和风险边界。
3. 必须包含：题名页、文章地图、问题场景、案例拆解、概念层级、流程图、易混概念对照、风险边界、自测/讨论、来源页。
4. 所有关键判断必须能回到 source，不引入 source 外事实。
5. 如果 source 没有真实数据，不要伪造图表或统计。
6. 不要生成“几页摘要卡”。每页要承担不同任务：map / flow / table / case / quiz / source 等。
7. 如果文章是教程或概念入门，加入学习目标、术语速查、练习题；如果是技术工具文，加入执行步骤、命令/工具、验收检查；如果是观点文，加入论点、证据、反例和边界。

输出后下载 slide-deck，优先 pptx；不支持 pptx 时下载 PDF，并记录 artifact id。
```

## QA Gate

- 记录 notebook_id、source_id、artifact_id、下载路径。
- 至少 8 页，除非用户指定更短。
- 若 NotebookLM 输出低密度或缺页，本地再按 [prompt-ppt.md](prompt-ppt.md) 重排，不声称 NotebookLM 已完成高质量设计。
