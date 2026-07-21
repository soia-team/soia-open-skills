# NotebookLM Quiz Prompt

用于 NotebookLM `generate quiz`。

```text
请严格基于已上传 source 生成一套中文测验。

目标读者：{params.audience}
难度：{params.difficulty 或 mixed}
语言：中文

题目结构：
1. 选择题 5-10 道，覆盖关键概念和易混点。
2. 简答题 3-5 道，要求解释因果、流程或判断依据。
3. 应用题 / 讨论题 1-3 道，要求把文章方法用于一个小场景。
4. 单独生成「答案与解析」区，每题都要解释为什么。

约束：
- 所有题目只考 source 中出现的内容。
- 不考 source 外事实。
- 答案必须有 source-grounded 依据。
```

## QA Gate

- 题号连续，答案区题号一致。
- 选择题答案唯一，除非题干明确多选。
- 下载 Markdown/JSON 后检查题目数量和答案数量一致。
