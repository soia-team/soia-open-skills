# NotebookLM Prompt

用于 NotebookLM grounded artifacts：slide deck、quiz、flashcards、mind map、podcast、report、infographic。使用前必须按 [providers.md](providers.md) 完成 CLI、auth check 和 notebook/source/artifact 记录。

## 参数

```yaml
params:
  provider: notebooklm
  artifact_type: slide-deck       # audio | video | slide-deck | quiz | flashcards | mind-map | report | infographic
  audience: auto
  language: zh-Hans
  content_mode: preserve | synthesize | learning | visual_dense
  output_format: auto
```

## Prompt 模板

```text
请严格基于已上传 source 生成 {params.artifact_type}。

语言：中文。
目标读者：{params.audience}
保真要求：保留原文主要章节、例子、术语关系和风险边界；不要把长文压成泛泛摘要。

如果生成 slide deck：
- 生成 8-12 页，除非用户指定页数。
- 每页标题必须是一个明确判断。
- 包含：文章地图、案例拆解、概念层级、流程图、易混概念对照、风险边界、自测题、来源页。

如果生成 quiz / flashcards：
- 所有题目只考 source 中出现的概念。
- 答案区必须包含解释和 source-grounded 依据。

如果生成 infographic：
- 采用高密度信息图结构：verdict、编号卡片、流程/表格、支持点/风险点/继续追问。
```

## QA Gate

- 回执记录 notebook_id、source_id、task_id/artifact_id、下载路径。
- 认证未通过时不能声称调用了 NotebookLM。
- 下载失败时保留 task/artifact 信息和可重跑命令。
