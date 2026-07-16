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
| video / cinematic-video | [prompt-notebooklm-podcast.md](prompt-notebooklm-podcast.md) |
| report | [prompt-notebooklm-report.md](prompt-notebooklm-report.md) |
| data-table | [prompt-notebooklm-report.md](prompt-notebooklm-report.md) |

NotebookLM CLI 还支持 `generate revise-slide`、`artifact list|get|get-prompt|rename|delete|export|poll|wait|retry|suggestions`、`download <type> --all` 等操作。需要覆盖验证时读取 [notebooklm-test-matrix.md](notebooklm-test-matrix.md)，默认先 dry-run，不要直接跑全量生成。

## QA Gate

- 回执记录 notebook_id、source_id、task_id/artifact_id、下载路径。
- 认证未通过时不能声称调用了 NotebookLM。
- 下载失败时保留 task/artifact 信息和可重跑命令。
- 全量 artifact 测试会消耗 NotebookLM 账号队列；只有用户明确确认后才使用 `scripts/notebooklm_artifact_matrix.py --run`。
