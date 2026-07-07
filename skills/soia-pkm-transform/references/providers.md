# Providers

按需读取本文件。它定义 `soia-pkm-transform` 可用的 provider、认证边界与降级规则。

## Provider 选择顺序

1. 用户本轮明确指定的 provider。
2. 配置文件 `outputs.<type>.provider`。
3. 本文件默认建议。
4. 当前 agent 实际可用工具。

无法确认 provider 是否可用时，先做只读检查，例如 `command -v notebooklm`、`notebooklm auth check --test --json`、确认 Obsidian 是否能打开目标 vault、确认 Open Design daemon health。不要在未确认时直接承诺产物。

## NotebookLM provider

适用：播客、视频、PPT/PPTX、脑图、quiz、flashcards、report、infographic、data table，以及多源资料的 grounded synthesis。

推荐公共实现：`teng-lin/notebooklm-py`。

关键点：

- 它是非官方 NotebookLM API/CLI，适合个人研究和自动化；Google 内部接口可能变化，必须保留降级说明。
- 安装建议用隔离工具，例如 `uv tool install "notebooklm-py[browser]"` 或 `pipx install "notebooklm-py[browser]"`。
- 初次使用需要 `notebooklm login`，认证数据由 NotebookLM CLI 管理；skill 不保存 Google 账号、密码、cookie。
- 自动化前用 `notebooklm auth check --test --json` 验证认证，不能只看本地 cookie 是否存在。
- 并行工作流不要依赖 `notebooklm use` 的全局上下文；优先在 notebook-scoped 命令里传 `-n <notebook-id>`。
- 生成 artifact 后记录 `notebook_id`、`source_id`、`task_id` / `artifact_id`、下载路径。
- 如果 `command -v notebooklm` 或 auth check 失败，本轮不能写「已调用 NotebookLM」；只能写「NotebookLM provider 不可用，缺少 CLI / 登录态 / 网络 / 账号权限」，并给出可重跑命令。

常见命令形态：

```bash
notebooklm auth check --test --json
notebooklm create "Article Transform - <title>" --json
notebooklm source add "<article.md or URL>" -n <notebook-id> --json
notebooklm source wait <source-id> -n <notebook-id>
notebooklm generate slide-deck "Create a concise Chinese deck" -n <notebook-id> --json
notebooklm artifact wait <task-id> -n <notebook-id>
notebooklm download slide-deck "<out.pptx>" --format pptx -n <notebook-id> -a <artifact-id>
```

目标映射：

| transform 目标 | NotebookLM 命令 |
|----------------|-----------------|
| podcast | `generate audio` -> `download audio` |
| video | `generate video` -> `download video` |
| ppt | `generate slide-deck` -> `download slide-deck --format pptx` 或 PDF |
| mindmap | `generate mind-map` -> `download mind-map` |
| quiz | `generate quiz` -> `download quiz --format markdown/json/html` |
| flashcards | `generate flashcards` -> `download flashcards --format markdown/json/html` |
| report | `generate report` -> `download report` |
| infographic | `generate infographic` -> `download infographic` |

使用 NotebookLM 的好处是 source-grounded、低消耗本地上下文、支持多种 artifact 下载；不足是依赖账号、网络、非官方接口和生成队列。

## Open Design / html-ppt provider

适用：高质量 PPT/HTML deck、高密度信息图、长图、课程模块、技术分享、视觉探索。

推荐用途：

- `visual_dense`：用 HTML/CSS 做高密度信息海报，再用 managed Chromium 截图成 PNG。
- `ppt`：用 `html-ppt` full-deck 模板生成 HTML deck，再按需要导出 PNG / PDF / PPTX。
- `learning`：用 `course-module` / `presenter-mode-reveal`，保留学习目标、讲稿、自测题。
- `workflow / architecture`：用 `knowledge-arch-blueprint`。
- `AI-native / graph / tool`：用 `graphify-dark-graph`。

可用性检查：

```bash
node -v
pnpm -v
pnpm tools-dev run web
curl -s http://127.0.0.1:<daemon-port>/api/health
```

注意：

- Open Design 要求 Node `~24`；如果当前 Node 不匹配，使用用户环境里的 Node 24，不要把路径写死进 skill。
- 如果跳过 postinstall，需要先构建缺失的 workspace dist，再启动。按报错补依赖，不要静默失败。
- `html-ppt/scripts/render.sh` 使用 Playwright managed Chromium；不要默认 fallback 到系统 Google Chrome，macOS 上容易被 profile / Crashpad 卡住。
- 生成 deck 时必须从 template 出发，不要手写低质白底 bullet PPT。
- 生成高密度图时，先写内容结构和视觉信息架构，再写 HTML；不要只做低信息量摘要卡。

## Obsidian provider

适用：vault 内 Markdown -> PDF。

规则：

- 只要源 Markdown 已在 Obsidian vault 内，PDF 默认走 Obsidian 自带导出。
- 这样能最大程度保留 Obsidian 渲染、主题、wikilink 展示和中文排版。
- 外部 PDF 引擎只作为明确降级方案。
- 导出后检查 PDF 文件存在、页数合理，必要时用 `pdfinfo` / `pdftoppm` 抽查视觉。

不要把 Obsidian 插件配置、主题路径或个人 vault 路径写进 skill。需要路径时走用户输入、`OBSIDIAN_VAULT` 或配置文件。

## Codex / agent native providers

适用：本地可编辑产物和强视觉校验。

- PPTX：使用当前 agent 的 presentation / PowerPoint 能力；生成后必须渲染预览，检查文字溢出和重叠。
- PDF：使用当前 agent 的 PDF 能力；适合非 Obsidian 源或需要程序化版式的试卷/报告。
- 图片：使用 image generation 或 HTML screenshot；生成后检查尺寸和可读性。
- 文档：Word / DOCX 类产物使用当前 agent 的 documents 能力。

这些 provider 不需要在 skill 里写模型 key。若某个 agent 需要 API key，交给该 agent 的安全密钥流程，不在本 skill 里生成 inline 教程。

## Publish provider

适用：公众号 HTML / 草稿箱、X thread、小红书卡片。

直接转交 `soia-pkm-publish`。微信公众号 AppID / AppSecret 只放私有 env 文件或 provider 安全存储，不进本仓库、不进 vault。

## Local markdown provider

适用：无需外部服务的 quiz、flashcards、Mermaid mindmap、Markdown report。

优点：离线、可审计、能稳定落入 vault。缺点：不是 NotebookLM grounded artifact，复杂内容质量取决于当前 agent。

默认输出：

- `quiz.md`：题目、答案、解析分区。
- `flashcards.md`：正反面或问答表格。
- `mindmap.md`：Mermaid mindmap 或缩进 Markdown outline。
- `report.md`：有来源链接和结构化摘要的 Markdown 报告。
