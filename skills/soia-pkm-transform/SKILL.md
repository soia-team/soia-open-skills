---
name: soia-pkm-transform
version: 0.1.0
description: 把 X/公众号/网页/Markdown 文章转换为 PDF、PPT、图片/长图、试卷、脑图、播客、闪卡、报告等产物的公共路由 skill。配置外置，可调用 Obsidian、NotebookLM、Codex 文件能力与 publish。Triggers：「转换文章为」「归档并转成」「生成 PPT/脑图/试卷/图片/播客」
---

# soia-pkm-transform

把一篇文章变成不同产物的**公共路由层**：PDF、PPT、图片/长图、信息图、试卷、脑图、播客、闪卡、报告、公众号 HTML、小红书卡片等。

它不替代 `clip-*` / `publish` / NotebookLM / Codex 内置文件能力，而是把它们编排成一句话可触发的流程：

```
clip-*(收) -> organize(可选) -> transform(转成产物) -> publish/maintain(可选)
```

## 公共工具原则

- 不写死个人 vault 路径、家庭信息、账号、token、key、cookie、公众号凭据。
- 路径、provider 偏好、输出目录只来自用户指令、配置文件或环境变量。
- 秘钥只放 provider 自己的私有认证位置，例如 NotebookLM 的本地 profile、微信公众号私有 env；不要写进 vault 或本开源 skill。
- 不读取 `私有数据.md`、浏览器 cookie、账号配置文件，除非用户明确要求且该 provider 官方/工具流程需要。
- 文章正文可以来自 vault、URL 或用户给的本地文件；不要扫描无关目录来猜来源。

## 触发词

| 用户说 | 行为 |
|--------|------|
| 「转换文章为 PDF：<文章路径或 URL>」 | 先取文章，再按 PDF recipe 输出 |
| 「把这篇 X 转成 PPT」 | 若是 URL 先交给 `soia-pkm-clip-x` 归档，再生成 PPT |
| 「转成高密度图 / 信息图 / 海报」 | 保留文章关键结构，优先走视觉模板或 HTML 截图，不要做低密度摘要卡 |
| 「归档并转成脑图：<URL>」 | 先 clip，再生成 mind map |
| 「这篇文章生成一套试卷」 | 生成 quiz / exam markdown，可选 PDF |
| 「转换成播客 / 闪卡 / 报告」 | 优先用 NotebookLM provider；不可用时说明降级 |
| 「把这篇转成公众号 / 小红书卡片 / X thread」 | 交给 `soia-pkm-publish` |

如果用户没有给文章来源，先问一句要转换哪篇；如果只缺风格偏好，使用通用默认，不阻塞。默认目标是**转换**，不是总结；只有用户明确说「总结 / 摘要 / briefing」时才压缩内容。

## 内容保真模式

先判断用户要的是哪一种，不要混用：

| 模式 | 触发 | 要求 |
|------|------|------|
| `preserve` | 转 PDF、导出 PDF、转成全文报告、转成课件 | 尽量保留原文结构、章节、例子、清单和关键表述；允许排版重组，但不能把长文压成几条观点 |
| `synthesize` | 做报告、NotebookLM grounded report、研究简报 | 基于原文综合提炼，同时保留来源和局限 |
| `summarize` | 用户明确说总结、摘要、TL;DR | 才输出短摘要 |
| `visual_dense` | 高密度图、信息图、海报、一张图讲清楚 | 信息密度优先，保留 8-15 个信息块、数字/关系/判断，不要做空洞大标题卡 |
| `learning` | 试卷、闪卡、课程模块、教学 PPT | 围绕学习目标、概念辨析、练习和答案组织 |

例如「转换文章为 PDF」不能输出 2 页摘要；应输出可读的全文 PDF 或明确说明当前 provider 只能生成摘要并请求确认。

## 配置发现

配置是可选的。没有配置时按本 skill 默认路由走。

优先级：

1. 用户本轮明确指定的 provider / 输出目录 / 格式
2. `SOIA_PKM_TRANSFORM_CONFIG`
3. `~/.config/soia-pkm/transform.yml` 或 `transform.json`
4. `~/.soia-pkm/transform.yml` 或 `transform.json`
5. vault / 项目内的 `.soia/transform.yml` 或 `transform.json`（只放非敏感偏好）

需要样例时读取 [assets/transform.config.example.yml](assets/transform.config.example.yml)。只想定位配置时可运行：

```bash
python3 scripts/resolve_config.py
```

## 标准文章包

任何输入先规整成一个 article packet，再选择输出 recipe。article packet 不一定要落盘，但内部判断必须具备这些字段：

```yaml
title: ""
source_type: X | 公众号 | web | markdown | pdf | unknown
source_url: ""
source_note_path: ""
author: ""
published_at: ""
body: ""
summary: ""
target_output: pdf | ppt | image | long_image | quiz | mindmap | podcast | flashcards | report | wechat | x_thread | xhs
content_mode: preserve | synthesize | summarize | visual_dense | learning
audience: ""
constraints: []
```

取源规则：

- X URL：先触发 `soia-pkm-clip-x`；归档完成后用生成的 Markdown。
- 公众号 URL：先触发 `soia-pkm-clip-wechat`。
- 普通网页 URL：先触发 `soia-pkm-clip-web`。
- 本地 Markdown / vault 笔记：直接读取该文件。
- PDF / Word / PPT 等本地文件：先触发 `soia-pkm-clip-drive` 或使用当前 agent 的文档提取能力生成 Markdown packet。

## Provider 选择

先按用户明确要求，其次按配置，最后按默认：

| 目标 | 默认 provider | 常见降级 |
|------|---------------|----------|
| PDF | Obsidian 原生导出（vault 内 Markdown，`preserve`） | agent PDF 工具 / 浏览器打印；不得默认总结 |
| PPT / PPTX | Open Design / html-ppt 或 Codex presentations | NotebookLM slide-deck / PDF deck |
| 图片 / 长图 / 信息图 | Open Design / HTML screenshot（高密度中文优先） | imagegen / NotebookLM infographic |
| 试卷 / 测验 | NotebookLM quiz 或本地 Markdown quiz | 手写 Markdown + 答案 |
| 脑图 | NotebookLM mind-map JSON 或 Mermaid mindmap | mindmap-ppt / Markdown outline |
| 播客 / 视频 / 闪卡 | NotebookLM | 不可用时说明需要 provider |
| 报告 | NotebookLM report 或本地 Markdown report | `soia-pkm-compose` |
| 公众号 / X / 小红书 | `soia-pkm-publish` | 只生成本地 HTML / 文案 |

使用 NotebookLM、Obsidian、Open Design、Codex 内置文件能力或发布链路前，按需读取 [references/providers.md](references/providers.md)。

## 工作流

1. **解析请求**：识别文章来源、目标产物、格式、受众、是否需要先归档。
2. **获取文章**：URL 走对应 `clip-*`，本地文件直接读取，形成 article packet。
3. **选择模式和 recipe**：先定 `content_mode`，再按目标产物读取 [references/output-recipes.md](references/output-recipes.md)，选择 provider。
4. **确认 provider 可用性**：NotebookLM、Open Design、Obsidian、发布链路都必须先跑只读/健康检查；不可用就记录真实缺口，不得把降级产物说成已调用该 provider。
5. **生成产物**：只在当前 vault / 项目 / 用户指定目录写文件。
6. **验证**：
   - PDF：能打开，页数合理；需要视觉时渲染抽查。
   - PPT：能打开并渲染预览；检查文字溢出和重叠。
   - 图片/长图：文件存在、尺寸合理、文字可读。
   - 试卷/闪卡：题目、答案、解析数量一致。
   - 脑图：JSON / Mermaid / Markdown 语法可解析。
   - NotebookLM 产物：记录 notebook id、artifact id、下载路径。
7. **回写链接**：如果源文章在 vault 内且配置允许，新增或更新 `## 转化产物` 段，只追加产物链接，不改原文。
8. **回执**：列出来源、content_mode、provider、输出文件、验证结果和下一步。

## 输出位置

默认规则：

- 原样导出类（PDF）：和源 Markdown 放同目录同名 stem。
- 派生产物（PPT、图片、试卷、脑图等）：放到配置的 `outputs.root`。
- 如果没有配置且在 Obsidian vault 内：`outputs/transform/<YYYY>/<文章stem>/`。
- 如果不在 vault 内：`outputs/transform/<文章stem>/`。

不要为了输出文件创建新的个人化目录名；公共默认必须通用。

## 与其他 PKM skill 的关系

- 上游：`soia-pkm-clip-x` / `clip-wechat` / `clip-web` / `clip-drive`
- 可选整理：`soia-pkm-organize`
- 内容再写作：`soia-pkm-distill` / `soia-pkm-compose`
- 平台发布：`soia-pkm-publish`
- 维护：`soia-pkm-maintain`

## 完成后回执

执行完必须输出：

1. **做了什么**：来源文章 -> 目标产物。
2. **使用 provider**：例如 Obsidian / NotebookLM / Codex presentations / imagegen。
3. **内容模式**：preserve / synthesize / summarize / visual_dense / learning；如果发生降级，说明原因。
4. **文件变更**：新建 / 修改文件完整路径。
5. **验证结果**：实际跑过的检查。
6. **下一步**：可选，如「配置 NotebookLM 后重跑播客」或「用 Open Design 高密度模板重出信息图」。
