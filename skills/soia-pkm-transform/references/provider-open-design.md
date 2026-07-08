# Open Design Provider

适用：高质量 PPT/HTML deck、高密度信息图、长图、课程模块、技术分享、视觉探索。

定位：Open Design 是**增强 provider**，不是 `soia-pkm-transform` 的硬依赖。公共默认实现必须在没有 Open Design 的机器上可用。

## 使用模式

回执必须说清楚是哪一种：

1. **Open Design handoff**：把 brief / prompt / 素材交给 Open Design app / agent / template runtime 生成或继续编辑设计产物。
2. **Template-guided local render**：读取 Open Design 的 design template / html-ppt 规则，由当前 agent 生成 HTML/CSS/PPTX，再用 Playwright managed Chromium 渲染验证。这是模板指导的本地生成，不要声称「Open Design agent 已生成」。

## Integrations 页面确认的主路径

Open Design 的 `/integrations` / README 指向三条主路径：

- Agent MCP：`od mcp install <agent>`，支持 `claude | codex | cursor | copilot | openclaw | antigravity | gemini | pi | vibe | hermes | cline | kimi | trae | opencode`。
- Headless CLI：`od plugin`、`od export`、`od media generate`、`od automation`、`od tools ...`。
- BYOK / no CLI：通过 `POST /api/proxy/{anthropic,openai,azure,google,ollama,senseaudio}/stream` 使用 OpenAI-compatible endpoint。

MCP 安装写入用户 agent 配置，必须先 dry-run：

```bash
od mcp install codex --print
od mcp install claude --print
od mcp install gemini --print
od mcp install opencode --print
```

只有用户确认后才去掉 `--print`。公共 skill 不自动改用户多 agent 配置。

## 可用性检查

```bash
test -n "$OPEN_DESIGN_HOME" && test -d "$OPEN_DESIGN_HOME"
command -v od
node -v      # Open Design source dev expects Node ~24
pnpm -v
pnpm tools-dev status --json
curl -sS http://127.0.0.1:<daemon-port>/api/health
```

若只通过源码运行，先读取 Open Design 根目录 `AGENTS.md`，并遵守它的启动规则：使用 `pnpm tools-dev` / `pnpm tools-dev run web`，不要随手 `pnpm dev`。

## Bootstrap

仅在用户明确要求、配置指定，或已检测到 Open Design 时执行。不要为了普通「转换文章为长图/PPT」强制安装 Open Design。

推荐来源：`https://github.com/nexu-io/open-design.git`。

1. 定位已有安装：

   ```bash
   command -v od
   test -n "$OPEN_DESIGN_HOME" && test -d "$OPEN_DESIGN_HOME"
   ```

2. 没有源码时询问或使用用户指定目录 clone：

   ```bash
   git clone https://github.com/nexu-io/open-design.git "$OPEN_DESIGN_HOME"
   cd "$OPEN_DESIGN_HOME"
   ```

   `OPEN_DESIGN_HOME` 必须来自用户配置或当前环境，不要在公共 skill 里写死个人路径。

3. 准备运行环境：

   ```bash
   node -v      # 需要 Node 24.x
   corepack enable
   corepack pnpm --version
   pnpm install
   ```

4. 启动本地开发服务：

   ```bash
   pnpm tools-dev run web
   ```

   启动后用打印出的 web URL 和 daemon port 验证健康。

## 模板选择

| 文章/任务类型 | Open Design template hint |
|---------------|---------------------------|
| 概念入门 / 教学 | `html-ppt-course-module`, `html-ppt-presenter-mode-reveal` |
| 技术分享 / 工具链 | `html-ppt-tech-sharing` |
| 系统结构 / 知识库 / 流程 | `html-ppt-knowledge-arch-blueprint` |
| AI 工具 / 图谱 / 关系网络 | `html-ppt-graphify-dark-graph` |
| 观点文章 / 媒体风 | `guizang-ppt`, `html-ppt-taste-editorial` |
| 高密度研究海报 | `magazine-poster`, `finance-report`, `trading-analysis-dashboard-template` |
| 小红书卡片 | `html-ppt-xhs-white-editorial`, `html-ppt-xhs-pastel-card`, `social-carousel` |
| 动效 / 视频 | `hyperframes`, `motion-frames` |

## 注意

- Open Design 要求 Node `~24`；如果当前 Node 不匹配，使用用户环境里的 Node 24，不要把路径写死进 skill。
- 如果跳过 postinstall，需要先构建缺失的 workspace dist，再启动。按报错补依赖，不要静默失败。
- `od export <file> --project <id> --format <pdf|image|pptx>` 是程序化导出路径；没有 project id 时不要假装已走 Open Design 导出。
- `od tools connectors` / `od tools live-artifacts` 需要 Open Design 在 agent run 内注入 `OD_TOOL_TOKEN`；普通终端没有 token 时返回缺 token 是正常安全门。
- 生成 deck 时必须从 template / style preset 出发，不要手写低质白底 bullet PPT。
- 生成高密度图时，先写内容结构和视觉信息架构，再写 HTML；不要只做低信息量摘要卡。
- 具体 prompt 读取 [prompt-open-design.md](prompt-open-design.md)。
