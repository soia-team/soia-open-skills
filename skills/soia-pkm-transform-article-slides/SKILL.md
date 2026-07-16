---
name: soia-pkm-transform-article-slides
description: 把文章转换为 PPT / PPTX / HTML 演示文稿或课件。本地 HTML deck 优先，可选 Open Design 或 NotebookLM PPT。Triggers：「做成PPT」「转成幻灯片」「生成课件」「转PPT」「export slides」「生成演示文稿」「make slides」
version: 1.0.0
created_at: 2026-07-16 10:58:46
updated_at: 2026-07-16 13:25:56
created_by: zp / claude opus 4.6
updated_by: zp / claude opus 4.6
---

# soia-pkm-transform-article-slides

把已归档或指定文章转换为可演示的 PPT / PPTX / HTML deck 或课件，按 `preserve`（完整保留） 或 `learning`（学习向） 模式生成。

## 客户可读说明

### 这个技能可以做什么

把 Markdown / vault 文章或 URL 转换为演示产物：

- **本地 HTML deck**：纯本地生成，无需外部账号，默认方案
- **PPTX**：python-pptx 生成，可直接用 PowerPoint / Keynote 打开
- **Open Design**：可选增强，生成设计级幻灯片
- **NotebookLM PPT**：可选，基于 NotebookLM 生成课件框架

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 转成 PPT | 生成 PPTX 或 HTML deck，prompt 落盘可重跑 | 输出路径、页数/张数、可打开确认 |
| 指定 provider | 走对应 provider 流程 | provider 日志 |
| 执行完成 | 验收文件可打开、无空白页、无文字溢出 | 完成回执 |

### 客户如何使用

1. 说明来源（URL / vault 路径 / 本地 Markdown）和受众/风格（可选）。
2. 可选：指定 provider（`local` / `open-design` / `notebooklm`）。
3. URL 来源先 clip 归档再转换。

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-transform-article-slides -y
```

- 本地方案：`pip install python-pptx`
- Open Design（可选）：见 [references/provider-open-design.md](references/provider-open-design.md)
- NotebookLM（可选）：见 [references/provider-notebooklm.md](references/provider-notebooklm.md)

### 日志与完成回执

```markdown
完成：<一句话>。

日志摘要：
- source: <路径或 URL>
- provider: local | open-design | notebooklm
- content_mode: preserve | learning
- prompt: <落盘路径>
- output: <文件路径>
- slides: <张数>

验证：
- 文件可打开
- 无空白页、无明显文字溢出
- prompt 已落盘可重跑

问题与下一步：
- <无 / provider 降级原因>
```

## 边界

- 不做内容总结，只做格式映射；`learning` 模式允许结构重组但不压缩核心要点。
- 图片错误（文字溢出、重叠）唯一修复方式：改 prompt 重新生成，禁止直接修改位图。
- prompt 必须落盘到 `outputs/transform/<YYYY>/<stem>/prompts/` 保证可重跑。
- Open Design / NotebookLM 是可选 provider，缺失时走本地降级，不停止任务。

## 工作流

1. 确认来源 → URL 先 clip。
2. 确定 `content_mode`：默认 `preserve`；用户说「课件/学习材料」改 `learning`。
3. 选 provider：用户指定 > 配置 > 本地 HTML deck。
4. 读 [references/prompt-ppt.md](references/prompt-ppt.md) 生成 prompt，落盘。
5. 生成产物到 `outputs/transform/<YYYY>/<stem>/`。
6. 验收：可打开、张数合理、无溢出、无空白页。
7. 回执。

详见 [references/prompt-ppt.md](references/prompt-ppt.md)、[references/provider-open-design.md](references/provider-open-design.md)、[references/quality-gates.md](references/quality-gates.md)。
