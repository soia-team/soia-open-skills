# NotebookLM Report Prompt

用于 NotebookLM `generate report`。它是 grounded report，不是全文 PDF，也不是短摘要。

NotebookLM report 的格式选择：

- `custom / Create Your Own`：默认用于 transform report。适合深度报告、结构可控、避免 briefing 过短。
- `briefing-doc`：只在用户明确要 brief / briefing / 快速简报时用。
- `study-guide`：用于学习指南、考试准备、课程化资料。
- `blog-post`：用于改写成博客文章，不等于研究报告。

```text
请严格基于已上传 source 生成中文深度 grounded report。使用 Create Your Own / custom 格式，不要用短 briefing。

目标读者：{params.audience}
语言：中文
内容模式：synthesize + preserve structure。必须保留 source 的章节结构、概念清单、案例链和关键判断。

结构：
1. 执行摘要：3-5 条，只占报告开头，不要吞掉正文。
2. Source 地图：主要章节、论证路径、案例链。
3. 概念覆盖矩阵：模块、术语、解释、与案例的关系、易混对象。
4. 逐模块解释：按 source 章节展开，不漏掉主体概念。
5. 案例拆解：任务、输入资料、关键能力、工具/资源连接、执行流程、验收。
6. 易混概念表：从 source 中选最容易混淆的 4-8 组概念；不要套用某个样例文章的固定概念对。
7. 风险与边界：来源、误读风险、工具/数据限制、责任归属、验证方式。
8. 行动清单：读者下一步如何搭一个可验证流程。
9. 继续追问：3-5 个可以深挖的问题。
10. 来源说明。

约束：
- 不引入 source 外事实。
- 不把 report 当作全文 PDF。
- 不生成只有 1-2 页的摘要；如果 source 是中长文，报告应覆盖主要章节和概念。
```

## QA Gate

- 记录 notebook_id、source_id、artifact_id、下载路径。
- 若用户要「转 PDF」，应走 PDF preserve recipe，而不是 NotebookLM report。
- 若 NotebookLM 只生成短 briefing，改用 `--format custom` 和上述 prompt 重跑，或本地重排。
