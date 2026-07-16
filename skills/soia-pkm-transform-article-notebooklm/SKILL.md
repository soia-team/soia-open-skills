---
name: soia-pkm-transform-article-notebooklm
description: 用 NotebookLM 把文章转换为试卷、闪卡、脑图、播客、学习笔记等学习类产物，降级为本地 Markdown。Triggers：「生成试卷」「做成闪卡」「生成脑图」「做播客」「NotebookLM」「generate quiz」「make flashcards」「mindmap」「podcast」
version: 1.0.0
created_at: 2026-07-16
updated_at: 2026-07-16
created_by: zp
updated_by: zp
---

# soia-pkm-transform-article-notebooklm

把已归档或指定文章转换为学习类或互动类产物：试卷、闪卡、脑图、播客脚本、学习笔记，优先使用 NotebookLM，降级为本地 Markdown。

## 客户可读说明

### 这个技能可以做什么

把 Markdown / vault 文章或 URL 转换为学习产物：

- **试卷（quiz）**：选择题 + 简答题 + 答案解析
- **闪卡（flashcards）**：Anki 兼容双面卡片
- **脑图（mindmap）**：Mermaid / Markdown 层级结构
- **播客脚本（podcast）**：对话式音频脚本
- **学习笔记**：NotebookLM 综合摘要

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 生成试卷 | 本地 Markdown 或 NotebookLM quiz artifact | 题数、题型分布、文件路径 |
| 做闪卡 | Anki 兼容 Markdown 或 NotebookLM flashcards | 卡片数、文件路径 |
| 脑图 / 播客 | Mermaid 脑图 / 对话脚本 Markdown | 文件路径、节点数 / 字数 |
| 上传 NotebookLM | 上传源文件、记录 notebook id | notebook id / artifact 路径 |
| 执行完成 | 验收产物结构完整、题目答案数量一致 | 完成回执 |

### 客户如何使用

1. 说明来源（URL / vault 路径 / 本地 Markdown）和目标类型（试卷/闪卡/脑图/播客，可选）。
2. 可选：指定 provider（`local` / `notebooklm`）、题数、卡片数、难度。
3. URL 来源先 clip 归档再转换。

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-transform-article-notebooklm -y
```

- 本地方案：无额外依赖（生成 Markdown）
- NotebookLM（可选）：见 [references/provider-notebooklm.md](references/provider-notebooklm.md)

### 日志与完成回执

```markdown
完成：<一句话>。

日志摘要：
- source: <路径或 URL>
- artifact_type: quiz | flashcards | mindmap | podcast | notes
- provider: local | notebooklm
- content_mode: learning
- output: <文件路径或 notebook id>
- count: <题数 / 卡片数 / 节点数>

验证：
- 文件存在且可读
- 题目数 == 答案数（quiz/flashcards）
- 脑图 Mermaid 可解析（mindmap）
- prompt 已落盘可重跑

问题与下一步：
- <无 / provider 降级原因 / NotebookLM 失败目标列表>
```

## 边界

- 默认 `learning` 模式：结构重组，核心知识点提炼，不压缩核心要点。
- quiz/flashcards：题目数 == 答案数 == 解析数，验收必须三者一致。
- prompt 落盘到 `outputs/transform/<YYYY>/<stem>/prompts/`。
- NotebookLM 是可选 provider；缺失时走本地 Markdown 生成，不停止任务。
- NotebookLM 失败的 artifact 逐项记录（不能静默跳过）。

## 工作流

1. 确认来源 → URL 先 clip。
2. 确定 `artifact_type`：`quiz`（默认）/ `flashcards` / `mindmap` / `podcast` / `notes`。
3. 选 provider：用户指定 > 配置 > 本地 Markdown。
4. NotebookLM 路径：先跑健康检查（[references/provider-notebooklm.md](references/provider-notebooklm.md)），再上传源文件，记录 notebook id，生成对应 artifact。
5. 本地路径：读 [references/prompt-notebooklm.md](references/prompt-notebooklm.md) 对应章节生成 prompt，输出 Markdown。
6. 生成产物到 `outputs/transform/<YYYY>/<stem>/`，prompt 落盘。
7. 验收：结构完整、数量一致、Mermaid 可解析（如适用）。
8. 回执，NotebookLM 失败目标逐项列出。

详见 [references/prompt-notebooklm.md](references/prompt-notebooklm.md)、[references/notebooklm-test-matrix.md](references/notebooklm-test-matrix.md)、[references/quality-gates.md](references/quality-gates.md)。
