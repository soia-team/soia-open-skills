# NotebookLM Prompt Router

用于 NotebookLM grounded artifacts 的路由页。使用前必须按 [providers.md](providers.md) 完成 CLI、auth check 和 notebook/source/artifact 记录；然后按 artifact 类型读取具体 prompt，不要共用一个 NotebookLM 总提示词。

## 路由

| NotebookLM artifact | 读取 |
|---------------------|------|
| slide-deck / ppt | [prompt-notebooklm-ppt.md](prompt-notebooklm-ppt.md) |
| infographic / image | [prompt-notebooklm-image.md](prompt-notebooklm-image.md) |
| quiz | [prompt-notebooklm-quiz.md](prompt-notebooklm-quiz.md) |
| flashcards | [prompt-notebooklm-flashcards.md](prompt-notebooklm-flashcards.md) |
| mind-map | [prompt-notebooklm-mindmap.md](prompt-notebooklm-mindmap.md) |
| audio / podcast | [prompt-notebooklm-podcast.md](prompt-notebooklm-podcast.md) |
| report | [prompt-notebooklm-report.md](prompt-notebooklm-report.md) |

## QA Gate

- 回执记录 notebook_id、source_id、task_id/artifact_id、下载路径。
- 认证未通过时不能声称调用了 NotebookLM。
- 下载失败时保留 task/artifact 信息和可重跑命令。
