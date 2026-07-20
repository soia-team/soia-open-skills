# SOIA Local Providers

本文件覆盖不依赖外部 SaaS 的默认 provider：Obsidian、local visual、Codex/agent native、imagegen、publish 和 local markdown。

## Obsidian Provider

适用：vault 内 Markdown -> PDF。

- 源 Markdown 已在 Obsidian vault 内时，PDF 默认走 Obsidian 自带导出或等价 Obsidian 自动化。
- 目标是 `preserve`：保留正文层级、图片、链接、表格和 Obsidian 渲染，而不是生成摘要报告。
- 导出后检查 PDF 文件存在、页数合理，必要时用 `pdfinfo` / `pdftoppm` 抽查视觉。
- 不把 Obsidian 插件配置、主题路径或个人 vault 路径写进 skill。需要路径时走用户输入、`OBSIDIAN_VAULT` 或配置文件。

## Local Visual Provider

适用：没有 Open Design 的普通用户环境。它是 PPT、长图、信息图的公共默认路径。

能力：

- PPT / PPTX：使用当前 agent 的 presentations / PowerPoint 能力，或生成自包含 HTML deck 后导出。
- 长图 / 信息图：使用本地 HTML/CSS 生成页面，再用 Playwright / browser screenshot / 当前 agent 截图能力导出 PNG。
- 视觉报告：生成 Markdown/HTML，再按 PDF 或截图导出。

流程：

1. 读取 [design-prompts.md](design-prompts.md)，再按目标读取 [prompt-ppt.md](prompt-ppt.md)、[prompt-infographic.md](prompt-infographic.md)、[prompt-codex-image.md](prompt-codex-image.md) 或 [prompt-report.md](prompt-report.md)。
2. 先写 visual brief 和信息架构，再生成 HTML/PPTX。不要从「总结」直接跳到页面。
3. 渲染检查：尺寸、文字可读性、截断、重叠、乱码。
4. 若渲染失败，先修布局；不要把未验收产物交付。

降级边界：

- 若环境没有 Playwright，也可以用当前 agent 的浏览器截图能力、系统浏览器打印、或 PDF/PNG 工具。
- 若没有可编辑 PPT 能力，先交 HTML deck / PDF deck，并在回执说明不是 PPTX。

本地全量 smoke：

```bash
python3 scripts/local_artifact_smoke.py \
  --article <article.md> \
  --out-dir <out-dir> \
  --strict \
  --json
```

该脚本从同一篇 Markdown 生成 `report.md/html/pdf`、`deck.html/pptx`、`infographic.html/png`、`data-table.csv`、`quiz.md`、`flashcards.md/csv`、`mindmap.mmd`、`podcast-script.md`、`video-script.md`、`cinematic-video-shotlist.md`，并用 Playwright 渲染 PNG/PDF。`--strict` 会检查报告长度、概念覆盖、deck 页数、信息块数、题目/答案数量、音频/视频脚本长度等质量门；失败时不要交付。若 Playwright 自带浏览器缺失，脚本会优先使用系统 Chrome；不要要求用户为了普通本地导出先安装 Open Design。

依赖：

- `deck.pptx` 需要 Python 环境可 `import pptx`（包名通常是 `python-pptx`）。
- HTML 到 PDF/PNG 渲染需要 Node 可 `require("playwright")`。若当前 agent 提供 bundled runtime，优先用 `--node-bin <node>` 和 `--node-path <node_modules>` 注入；不要把某台机器的 runtime 路径写进 skill。
- 依赖缺失时先给安装/注入路径建议，再降级为 HTML deck / Markdown report；不要声称 PPTX、PDF 或 PNG 已导出。

质量门也可以单独跑，适用于 local、NotebookLM、Open Design 或人工重排后的同名产物目录：

```bash
python3 scripts/validate_artifact_quality.py \
  --article <article.md> \
  --out-dir <out-dir> \
  --strict \
  --json
```

`article_packet.py` 会从 source 动态抽章节和概念；不要在本地 provider 里维护某个领域或某篇文章的固定术语库。

## Codex / Agent Native Providers

适用：本地可编辑产物和强视觉校验。

- PPTX：使用当前 agent 的 presentation / PowerPoint 能力；生成后必须渲染预览，检查文字溢出和重叠。
- PDF：使用当前 agent 的 PDF 能力；适合非 Obsidian 源或需要程序化版式的试卷/报告。
- 图片：使用 image generation 或 HTML screenshot；生成后检查尺寸和可读性。
- 文档：Word / DOCX 类产物使用当前 agent 的 documents 能力。

这些 provider 不需要在 skill 里写模型 key。若某个 agent 需要 API key，交给该 agent 的安全密钥流程，不在本 skill 里生成 inline 教程。

## Codex Imagegen / Image2 Provider

适用：封面图、头图、插画、背景图、视觉隐喻、图标素材、卡片背景、PPT 视觉资产。

不适用：

- 中文密集长图。
- 带大量小字、表格、精确数字、引用、来源说明的信息图。
- 需要严格可编辑文字的 PPT 页面。

规则：

- 先读取 [prompt-codex-image.md](prompt-codex-image.md)。
- 默认生成无字或少字图；标题、作者、来源、数字、表格用 HTML/PPT/图片编辑后期叠加。
- 若 imagegen 输出里出现乱码文字、错误数字或不该有的 logo，要重新生成或裁掉文字区，不要把错误文字交付。
- 回执要区分「imagegen 生成视觉素材」和「本地排版生成最终图片」。

## Publish Provider

适用：公众号 HTML / 草稿箱、X thread、小红书卡片。

按目标平台转交 `publish-*` 家族。微信公众号 AppID / AppSecret 只放私有 config.yml 或 provider 安全存储，不进本仓库、不进 vault。

## Local Markdown Provider

适用：无需外部服务的 quiz、flashcards、Mermaid mindmap、Markdown report。

优点：离线、可审计、能稳定落入 vault。缺点：不是 NotebookLM grounded artifact，复杂内容质量取决于当前 agent。

默认输出：

- `quiz.md`：题目、答案、解析分区。
- `flashcards.md`：正反面或问答表格。
- `mindmap.md`：Mermaid mindmap 或缩进 Markdown outline。
- `report.md`：有来源链接和结构化摘要的 Markdown 报告。
