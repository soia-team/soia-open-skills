# Output Recipes

按目标产物读取对应小节。所有 recipe 都从标准 article packet 开始，不直接操作原 URL。

## PDF

默认：vault 内 Markdown -> Obsidian 原生导出，内容模式为 `preserve`。

PDF 的默认语义是**全文转换**，不是摘要报告。除非用户明确说「总结成 PDF」或「briefing PDF」，不得把一篇长文压缩成几页观点。

步骤：

1. 确认源文件在 Obsidian vault 内。
2. 使用 Obsidian 自带「导出 PDF」或等价自动化，保留标题、frontmatter 可读信息、正文层级、引用、图片和链接。
3. 保存到源 Markdown 同目录同名 stem；如果生成派生版，文件名明确标注 `full` / `summary` / `report`。
4. 检查 PDF 存在、页数合理、中文不乱码；页数应与原文长度大致匹配，不能明显少到只剩摘要。
5. 回写 `## 转化产物` 链接。

降级：

- 源不在 vault：使用 agent PDF 能力生成。
- Obsidian 不可用：告知降级，并用程序化 PDF 或浏览器打印生成全文版；如果只能生成摘要，必须先说明并征求确认。

## PPT / PPTX

开始前先读取 [design-prompts.md](design-prompts.md) 的路由规则，再读取 [prompt-ppt.md](prompt-ppt.md)。PPT 的失败形态通常不是文件打不开，而是低密度、无叙事、每页重复卡片、看起来像自动摘要。

输入默认来自 article packet / Markdown 正文。用户没有提供大纲时，agent 应从标题层级、段落结构、例子、术语和清单自动推断；用户给了参数时优先服从参数。

常用参数：

```yaml
params:
  slide_count: auto
  audience: auto
  style: auto
  aspect_ratio: "16:9"
  output_format: pptx
  provider: auto
  include_speaker_notes: auto
```

默认分两种：

- 普通公共环境：优先用当前 agent 的 presentation provider 或本地自包含 HTML deck。
- 用户明确要求或配置指定 Open Design：读取 [provider-open-design.md](provider-open-design.md) 和 [prompt-open-design.md](prompt-open-design.md)，再用 Open Design / html-ppt 模板。
- 需要快速 grounded deck 或多源资料：用 NotebookLM `slide-deck`，先读取 [prompt-notebooklm-ppt.md](prompt-notebooklm-ppt.md)，优先下载 `.pptx`，不行再下载 PDF。

选型：

- 教学/概念入门：`style: course_module`；若 Open Design 可用，可参考 `html-ppt-course-module` 或 `presenter-mode-reveal`。
- 系统结构/术语关系/工作流：`style: knowledge_blueprint`；若 Open Design 可用，可参考 `html-ppt-knowledge-arch-blueprint`。
- 技术分享：`style: technical_sharing`；若 Open Design 可用，可参考 `html-ppt-tech-sharing`。
- AI 工具/知识图谱/流程：`style: graph_dark`；若 Open Design 可用，可参考 `html-ppt-graphify-dark-graph`。
- 小红书图文：`style: xhs_cards`；若 Open Design 可用，可参考 `html-ppt-xhs-white-editorial` 或 `social-carousel`。

内容结构至少 14-18 页（中长文 / 概念数 >=12），除非用户要求短 deck：

1. 题名页：文章标题、来源、作者。
2. 文章地图：保留原文主要章节，不只列 3-5 个观点。
3. 案例/任务拆解。
4. 概念层级和关键辨析。
5. 流程 / 架构 / 关系图。
6. 术语速查或表格。
7. 行动建议 / 讨论问题 / 自测。
8. 来源页。

验证：

- PPTX 能打开。
- 渲染预览全部页。
- 无明显文字重叠、越界、空白页。
- 版式轮廓至少包含 4 种：封面 / 地图 / 流程 / 对比 / 表格 / 自测 / 来源，不能每页同一种卡片模板。
- 若使用 HTML deck，必须保留键盘导航和导出路径；不要只交一个不可编辑截图。
- 若文章含多个概念，先列 coverage matrix；主要概念覆盖率低于 80% 时不算完成。

## 图片 / 长图 / 信息图

先判断用户说的「图片」是哪一种：

| 子类型 | 例子 | Prompt | Provider |
|--------|------|--------|----------|
| `cover_image` | 封面图、头图、文章配图、PPT 背景 | [prompt-codex-image.md](prompt-codex-image.md) | Codex imagegen / gpt-image-2 / image provider |
| `illustration` | 插画、图标、视觉隐喻、装饰图 | [prompt-codex-image.md](prompt-codex-image.md) | Codex imagegen / gpt-image-2 / image provider |
| `long_image` | 长图、图文卡、竖版总结图 | [prompt-infographic.md](prompt-infographic.md) | local_visual HTML/CSS screenshot |
| `infographic` | 一张图讲清楚、信息图、研究海报 | [prompt-infographic.md](prompt-infographic.md) | local_visual HTML/CSS screenshot |

长图/信息图开始前先读取 [prompt-infographic.md](prompt-infographic.md) 和 QA Gate。信息图必须先做信息架构，再做视觉；不要从「帮我总结」直接跳到 HTML。

封面图/插画开始前先读取 [prompt-codex-image.md](prompt-codex-image.md)。不要要求 imagegen 直接生成大量中文文字；最终文字用 HTML/PPT/图片编辑叠加。

默认：

- 高密度中文长图/信息图：优先本地 HTML/CSS 排版后截图。
- 用户明确要求或配置指定 Open Design：读取 [provider-open-design.md](provider-open-design.md) 和 [prompt-open-design.md](prompt-open-design.md)，再用 Open Design / template-guided local render。
- 封面图/插画/背景素材：可用 imagegen / gpt-image-2。
- NotebookLM 可用且用户要「信息图」时，可选 `generate infographic`，先读取 [prompt-notebooklm-image.md](prompt-notebooklm-image.md)。

要求：

- 先从文章提取 1 个主题、8-15 个信息块、目标读者、关键关系、风险/边界/结论。
- 中文密集内容优先用 HTML 截图，避免生图文字不稳定。
- 参考结构：顶部 verdict / 一句话结论；中部 6-9 张编号卡片；下部流程图、对比表、趋势/关系图；底部支持点、风险点、继续追问。
- 信息密度优先于装饰，避免空洞大标题、低信息量渐变卡、单色大留白。
- 生成图要保存为 PNG。

验证：

- 图片存在、尺寸合理。
- 文字在目标尺寸下可读。
- 不出现明显乱码、截断、错别字。
- 至少人工或截图抽查一次，不得只检查文件存在。
- 抽查时若出现遮挡、过度留白、信息块不足、层级不清，必须迭代版式后再交付。
- imagegen 产物如果包含错误文字、乱码、伪造 logo 或错误数字，必须重做或改成无字素材。

## Quiz / Exam

默认：

- NotebookLM 可用：`generate quiz`，下载 Markdown 或 JSON。
- 本地降级：生成 `quiz.md`。

使用 NotebookLM 时先读取 [prompt-notebooklm-quiz.md](prompt-notebooklm-quiz.md)；本地降级时按 `learning` 模式保留原文概念、例子和易错点。

题型建议：

- 选择题 5-10 道。
- 简答题 3-5 道。
- 应用题 / 讨论题 1-3 道。
- 单独 `## 答案与解析`，不要把答案混在题目后。

验证：

- 题目编号连续。
- 每道选择题有且只有一个标准答案，除非明确是多选。
- 答案区题号与题目区一致。
- 不编造原文没有的事实。

## Mindmap

默认：

- NotebookLM 可用：`generate mind-map`，下载 JSON。
- 本地降级：生成 Mermaid mindmap 或缩进 Markdown。
- 用户要演示效果：可接 mindmap-ppt 类 provider 或当前 agent presentation provider。

使用 NotebookLM 时先读取 [prompt-notebooklm-mindmap.md](prompt-notebooklm-mindmap.md)；本地降级时保留文章标题层级和概念关系，不把长文压成 3 层空泛树。

本地 Mermaid 形态：

```mermaid
mindmap
  root((文章标题))
    核心观点
      证据
      例子
    方法步骤
      Step 1
      Step 2
```

验证：

- 层级不超过 4 层，避免过密。
- 每个节点短句化。
- Mermaid 代码块语法完整。

## Podcast / Audio

默认：NotebookLM `generate audio`。

开始前读取 [prompt-notebooklm-podcast.md](prompt-notebooklm-podcast.md)，明确语言、时长、听众和内容保真度。

要求：

- 说明语言、时长和风格。
- 等待完成后下载 MP3。
- 回执里标注 NotebookLM 生成，不说成本地音频模型。

不可用时：

- 不伪造音频。可以先生成播客脚本 Markdown，等待用户配置 provider。

## Flashcards

默认：

- NotebookLM `generate flashcards` 下载 Markdown/JSON。
- 本地降级：生成问答卡 Markdown 表格。

使用 NotebookLM 时先读取 [prompt-notebooklm-flashcards.md](prompt-notebooklm-flashcards.md)；本地降级时按「一个概念一张卡」生成。

验证：

- 每张卡只考一个点。
- 正面是问题，背面是答案和必要解释。
- 避免过长答案。

## Report

默认：

- NotebookLM `generate report` 适合 grounded 资料报告。
- 本地 Markdown report 适合快速总结和轻量加工。
- 如果用户要原创文章而不是报告，转交 `soia-pkm-compose-article-draft`。

开始前读取 [prompt-report.md](prompt-report.md)。如果用户明确要求 NotebookLM grounded report，先读取 [prompt-notebooklm-report.md](prompt-notebooklm-report.md) 并按 provider bootstrap 检查。

注意：Report 是「综合报告」，不是 PDF 全文导出。用户说「转 PDF」时不要自动转成 report。

结构：

1. 摘要。
2. Source 地图和 coverage matrix。
3. 核心观点。
4. 关键证据 / 案例 / 概念矩阵。
5. 可执行建议。
6. 局限与待核实。
7. 来源。

中长文 report 不能短到只剩摘要；若用户要 brief，文件名和回执标注 `briefing`。

## WeChat / X / Xiaohongshu

按目标平台转交 `publish-*` 家族：

- 公众号：Markdown -> WeChat-ready HTML / 草稿箱。
- X：thread 拆条。
- 小红书：卡片式文案 + 配图建议。

发布链路必须遵守人工闸门：公众号只建草稿，不自动群发。
