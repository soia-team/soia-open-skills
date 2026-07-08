# Providers

按需读取本文件。它定义 `soia-pkm-transform` 可用的 provider、认证边界与降级规则。

## Provider 选择顺序

1. 用户本轮明确指定的 provider。
2. 配置文件 `outputs.<type>.provider`。
3. 本文件默认建议。
4. 当前 agent 实际可用工具。

无法确认 provider 是否可用时，先做只读检查，例如 `command -v notebooklm`、`notebooklm auth check --test --json`、确认 Obsidian 是否能打开目标 vault、确认 Open Design daemon health。不要在未确认时直接承诺产物。

如果 provider 缺失，按本文件的 bootstrap 步骤推进：能安全安装的先安装并验证；需要用户认证的进入人工登录闸门；仍不可用时再降级或停止。不要把「未安装」当作最终答案。

视觉类 provider 的例外：Open Design 是增强项，不是公共默认依赖。若 Open Design 缺失，默认先用 Local visual provider；只有用户明确要求 Open Design、配置指定 `provider: open_design`，或当前环境已检测到可用 Open Design 时，才安装 / 启动 Open Design。

## NotebookLM provider

适用：播客、视频、PPT/PPTX、脑图、quiz、flashcards、report、infographic、data table，以及多源资料的 grounded synthesis。

推荐公共实现：`teng-lin/notebooklm-py`。

关键点：

- 它是非官方 NotebookLM API/CLI，适合个人研究和自动化；Google 内部接口可能变化，必须保留降级说明。
- 安装建议用隔离工具，例如 `uv tool install "notebooklm-py[browser]"` 或 `pipx install "notebooklm-py[browser]"`。普通 `pip install` 只在 active virtualenv 或非 externally-managed Python 中使用。
- 初次使用需要 `notebooklm login`，认证数据由 NotebookLM CLI 管理；skill 不保存 Google 账号、密码、cookie。
- 自动化前用 `notebooklm auth check --test --json` 验证认证，不能只看本地 cookie 是否存在。
- 并行工作流不要依赖 `notebooklm use` 的全局上下文；优先在 notebook-scoped 命令里传 `-n <notebook-id>`。
- 生成 artifact 后记录 `notebook_id`、`source_id`、`task_id` / `artifact_id`、下载路径。
- 如果 `command -v notebooklm` 失败，先进入安装步骤，不能只报告缺 CLI。
- 如果 CLI 已安装但 auth check 失败，进入登录闸门：提示用户运行或同意执行 `notebooklm login`，由用户在浏览器里登录 Google；agent 不读取密码、cookie 或 `storage_state.json` 内容。
- 如果登录后 `auth check --test --json` 仍失败，本轮不能写「已调用 NotebookLM」；只能写「NotebookLM provider 不可用，缺少登录态 / 网络 / 账号权限」，并给出可重跑命令。

### NotebookLM bootstrap

当用户明确要 NotebookLM 产物，或目标默认 provider 是 NotebookLM（podcast / video / quiz / flashcards / grounded report / mindmap）时：

1. **检查 CLI**：

   ```bash
   command -v notebooklm
   notebooklm --version
   ```

2. **缺 CLI 时安装**，按顺序选择可用工具：

   ```bash
   command -v uv && uv tool install "notebooklm-py[browser]"
   # 或
   command -v pipx && pipx install "notebooklm-py[browser]"
   # 仅在 active venv / 用户明确允许时：
   python -m pip install "notebooklm-py[browser]"
   ```

   安装后重跑 `command -v notebooklm && notebooklm --version`。

3. **验证认证**：

   ```bash
   notebooklm auth check --test --json
   ```

4. **缺登录态时进入人工登录闸门**：

   ```bash
   notebooklm login
   notebooklm auth check --test --json
   notebooklm list --json
   ```

   只要登录未完成，就不要生成 NotebookLM artifact。可先生成本地降级草稿，但回执必须标注「未调用 NotebookLM」。

5. **可选安装 NotebookLM skill**：

   ```bash
   notebooklm skill install
   ```

   这只注册 agent skill，不替代 CLI 安装和 auth check。

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

定位：Open Design 是**增强 provider**，不是 `soia-pkm-transform` 的硬依赖。公共默认实现必须在没有 Open Design 的机器上可用。

Open Design 有两种使用模式，回执必须说清楚是哪一种：

1. **Open Design handoff**：把 brief / prompt / 素材交给 Open Design app / agent / template runtime 生成或继续编辑设计产物。
2. **Template-guided local render**：读取 Open Design 的 design template / html-ppt 规则，由当前 agent 生成 HTML/CSS/PPTX，再用 Playwright managed Chromium 渲染验证。这是模板指导的本地生成，不要声称「Open Design agent 已生成」。

推荐用途：

- `visual_dense`：用 HTML/CSS 做高密度信息海报，再用 managed Chromium 截图成 PNG。
- `ppt`：用 `html-ppt` full-deck 模板生成 HTML deck，再按需要导出 PNG / PDF / PPTX。
- `learning`：用 `course-module` / `presenter-mode-reveal`，保留学习目标、讲稿、自测题。
- `workflow / architecture`：用 `knowledge-arch-blueprint`。
- `AI-native / graph / tool`：用 `graphify-dark-graph`。

可用性检查：

```bash
test -n "$OPEN_DESIGN_HOME" && test -d "$OPEN_DESIGN_HOME"
command -v od
node -v
pnpm -v
pnpm tools-dev run web
curl -s http://127.0.0.1:<daemon-port>/api/health
```

### Open Design bootstrap

仅在用户明确要求 / 配置指定 / 已检测到 Open Design 时执行。不要为了普通「转换文章为长图/PPT」强制安装 Open Design。

推荐来源：`https://github.com/nexu-io/open-design.git`。

1. **定位已有安装**：

   ```bash
   command -v od
   test -n "$OPEN_DESIGN_HOME" && test -d "$OPEN_DESIGN_HOME"
   ```

2. **没有源码时询问或使用用户指定目录 clone**：

   ```bash
   git clone https://github.com/nexu-io/open-design.git "$OPEN_DESIGN_HOME"
   cd "$OPEN_DESIGN_HOME"
   ```

   `OPEN_DESIGN_HOME` 必须来自用户配置或当前环境，不要在公共 skill 里写死个人路径。

3. **准备运行环境**：

   ```bash
   node -v      # 需要 Node 24.x
   corepack enable
   corepack pnpm --version
   pnpm install
   ```

4. **启动本地开发服务**：

   ```bash
   pnpm tools-dev run web
   ```

   如果只是要 daemon / web 背景运行，可按 Open Design Quickstart 使用 `pnpm tools-dev`。启动后用打印出的 URL 和 daemon port 验证健康。

5. **可选 MCP 接入**：

   ```bash
   od mcp install codex --print
   od mcp install claude --print
   ```

   是否真正写入 agent 配置应由用户确认；公共 skill 不自动改用户的多 agent 配置。

注意：

- Open Design 要求 Node `~24`；如果当前 Node 不匹配，使用用户环境里的 Node 24，不要把路径写死进 skill。
- 如果跳过 postinstall，需要先构建缺失的 workspace dist，再启动。按报错补依赖，不要静默失败。
- `html-ppt/scripts/render.sh` 使用 Playwright managed Chromium；不要默认 fallback 到系统 Google Chrome，macOS 上容易被 profile / Crashpad 卡住。
- 生成 deck 时必须从 template 出发，不要手写低质白底 bullet PPT。
- 如果没有可用的 Open Design agent/session API，就采用 template-guided local render，并在回执里写明。
- 生成高密度图时，先写内容结构和视觉信息架构，再写 HTML；不要只做低信息量摘要卡。

## Local visual provider

适用：没有 Open Design 的普通用户环境。它是视觉类转换的公共默认路径。

能力：

- PPT / PPTX：使用当前 agent 的 presentations / PowerPoint 能力，或生成自包含 HTML deck 后导出。
- 长图 / 信息图：使用本地 HTML/CSS 生成页面，再用 Playwright / browser screenshot / 当前 agent 截图能力导出 PNG。
- 视觉报告：生成 Markdown/HTML，再按 PDF 或截图导出。

流程：

1. 读取 [design-prompts.md](design-prompts.md)，先写 visual brief 和信息架构。
2. 生成自包含 HTML/CSS 或 PPTX；不要依赖外部模板路径。
3. 渲染检查：尺寸、文字可读性、截断、重叠、乱码。
4. 若渲染失败，先修布局；不要把未验收产物交付。

降级边界：

- 若环境没有 Playwright，也可以用当前 agent 的浏览器截图能力、系统浏览器打印、或 PDF/PNG 工具。
- 若没有可编辑 PPT 能力，先交 HTML deck / PDF deck，并在回执说明不是 PPTX。

## Codex imagegen / image2 provider

适用：封面图、头图、插画、背景图、视觉隐喻、图标素材、卡片背景、PPT 视觉资产。

不适用：

- 中文密集长图。
- 带大量小字、表格、精确数字、引用、来源说明的信息图。
- 需要严格可编辑文字的 PPT 页面。

规则：

- 先读取 [design-prompts.md](design-prompts.md) 的「Imagegen / 封面图 Prompt」。
- 默认生成无字或少字图；标题、作者、来源、数字、表格用 HTML/PPT/图片编辑后期叠加。
- 若 imagegen 输出里出现乱码文字、错误数字或不该有的 logo，要重新生成或裁掉文字区，不要把错误文字交付。
- 回执要区分「imagegen 生成视觉素材」和「本地排版生成最终图片」。

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
