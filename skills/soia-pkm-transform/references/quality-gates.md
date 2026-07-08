# Quality Gates

用于判断「转换文章为 X」是否真的完成。文件存在不是完成；能打开也只是第一层。

## 先抽覆盖清单

生成前先从 source 提取：

- `sections`：原文章节 / 小标题 / 逻辑路径。
- `concepts`：术语、工具、角色、流程节点、风险词。
- `case_chain`：文章使用的案例、任务、输入、动作、输出。
- `source_claims`：需要保留的关键判断。

所有产物都要覆盖这张清单的大部分内容。若长文含 12 个以上概念，PPT、报告、播客、试卷、闪卡不能只覆盖 3-5 个词。

## 最低标准

| 产物 | 不合格信号 | 最低可交付标准 |
|------|------------|----------------|
| PPT / deck | 6 页以内、每页三 bullet、漏掉主体概念 | 中长文 14-18 页；至少 4 种版式；包含文章地图、案例、概念层级、流程/表格、易混点、风险、自测、来源 |
| report | 只有执行摘要或几段总结 | 结构化报告；包含 source 地图、概念覆盖矩阵、证据/案例、风险边界、行动清单；不是全文 PDF，也不是 TL;DR |
| PDF | 页数明显少于正文容量 | 默认全文保真转换；若是 report/summary，文件名和回执必须标明 |
| infographic / long image | 大标题 + 少量卡片、大片空白 | 至少 12 个信息块；至少 2 种结构化表达；支持/风险/流程有语义区分 |
| podcast/audio | 1 分钟浅聊，只讲几个词 | 中长文默认 8-12 分钟 deep-dive；按章节覆盖概念、例子、易混点、行动清单 |
| video | 只做概念广告片 | explainer 默认 6-8 分钟；必须有分镜、字幕要点、视觉元素和 source-grounded 内容 |
| cinematic-video | 把事实塞进小字画面 | 60-90 秒视觉隐喻 + 旁白，事实来自 source；密集解释交给脚本或 deck |
| quiz | 答案混在题目后，题目少 | 选择题、简答题、应用题分区；`答案与解析` 单独成区；题号一致 |
| flashcards | 只做几个泛泛卡片 | 一个概念一张卡；覆盖术语、流程、易混点和风险边界 |
| data-table | 只有术语和定义两列 | 至少包含术语、模块、解释、案例关系、易混对象、风险/边界、适合产物 |

## NotebookLM 特别规则

- Report 弹窗有 `Create Your Own`、`Briefing Doc`、`Study Guide`、`Blog Post`。普通 `report` 默认用 `custom / Create Your Own`，不要误用短 briefing。
- 教程文章的 slide deck 要在 prompt 中写明目标页数和覆盖矩阵；NotebookLM 版式不可控，若输出低密度，必须本地重排。
- Audio 默认 `deep-dive + long`；用户明确要短音频时才用 `brief / short`。
- Cinematic video 走 `generate video --format cinematic`；不是 `generate cinematic-video`。

## Open Design 特别规则

- 先选模板和 style preset，再写设计 brief。不要手写低质白底 bullet deck 后声称用了 Open Design。
- `plugin apply`、`artifact create`、`export` 是三件事：只完成前两步不能说导出成功。
- `od export` 依赖 desktop renderer；缺 Electron/desktop.sock 时必须记录真实失败，不许把本地截图冒充 Open Design export。

## 回执

回执必须列：

- 生成方式：local / NotebookLM / Open Design / Obsidian。
- 覆盖结果：页数、信息块数、概念数、题目数、卡片数、时长目标。
- 验证结果：渲染、打开、解析、质量门是否通过。
- 失败或降级：真实错误、可重跑命令、未生成的目标。
