---
name: soia-dev-archify-diagrams
description: Draw, improve, validate, or publish Archify architecture / data-flow / sequence / lifecycle diagrams with JSON IR and PNG previews. Triggers：「画架构图」「画时序图/流程图」「给 README 配图」「用 Archify 画」
version: 1.0.0
created_at: 2026-07-09 07:45:34
updated_at: 2026-07-11 11:06:04
created_by: zp
updated_by: zp / claude opus 4.6
---

# soia-dev-archify-diagrams

Use this skill to turn architecture and process explanations into polished Archify diagrams with maintainable JSON source files and README-friendly PNG previews.

The skill owns the reusable workflow and helper scripts. Archify itself remains an external renderer.

```text
soia-dev-archify-diagrams/
├── SKILL.md
├── scripts/
│   ├── render-archify-diagrams.mjs
│   └── export-archify-previews.mjs
└── assets/examples/
    ├── minimal-architecture.architecture.json
    ├── minimal-dataflow.dataflow.json
    └── minimal-workflow.workflow.json
```

## 客户可读说明

### 这个技能可以做什么

Draw, improve, validate, or publish Archify architecture / data-flow / sequence / lifecycle diagrams with JSON IR and PNG previews

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. Agent 先判断是否命中本技能，再检查依赖、配置、权限和风险动作。
3. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。
4. 执行后验证真实输出，不用“看起来成功”代替证据。
5. 最终回复必须给客户可见总结：做了什么、日志摘要、文件变化、问题和下一步。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-archify-diagrams -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-archify-diagrams/config.yml
SOIA_DEV_ARCHIFY_DIAGRAMS_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- 强依赖、可选依赖和第三方 skill 关系必须以本 `SKILL.md` 后续的“依赖 / 前置 / 资源 / 边界”说明为准；没有写清楚时，先补说明或询问客户，不要猜。
- 第三方 skill 只能声明依赖和安装方式，不直接修改第三方 skill 文件。

### 日志与完成回执

每次执行都要让客户看见过程和结果。最低回执格式：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <检查到的输入/配置/依赖，不打印秘密值>
- processed: <数量或范围>
- created/updated: <数量或路径>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <运行过的检查、命令或人工核对点>

问题与下一步：
- <缺 key / 缺依赖 / 需要客户确认 / 建议下一条命令；没有则写“无”>
```

## Choose Diagram Type

| User intent | Archify type | JSON suffix |
|---|---|---|
| System components, repos, services, local directories, runtime boundaries | `architecture` | `.architecture.json` |
| Installation paths, data movement, lineage, where files flow | `dataflow` | `.dataflow.json` |
| Maintenance process, approval flow, tool-call flow, CI/release steps | `workflow` | `.workflow.json` |
| Who calls whom over time, request/response, fallback behavior | `sequence` | `.sequence.json` |
| State/status transitions, terminal outcomes, retry/cancel paths | `lifecycle` | `.lifecycle.json` |

If a rough Mermaid flowchart mixes components and process, choose one story and split the rest into a second diagram.

## Diagram Rules

1. Keep JSON IR as the source of truth.
2. Generate HTML only as a temporary render/check intermediate.
3. Commit PNG previews for README-visible diagrams.
4. Do not commit generated HTML unless the user explicitly asks for interactive diagrams.
5. Make the main path left-to-right.
6. Put side concerns in cards, not in long crossing arrows.
7. Use few edge labels; label only non-obvious boundaries, policy/security paths, or async/batch paths.
8. Run Archify `validate`, `render`, and `check` before claiming the diagram is done.

## Standard Layout

For repository README/docs diagrams, prefer:

```text
assets/diagrams/
├── <slug>.architecture.json
└── <slug>.png
```

For SOIA proposal diagrams, resolve the workspace root from SOIA config first. If no config value is available, use the default workspace root:

```text
~/.soia/workspaces
```

Then write proposal diagrams under:

```text
<soia-workspaces-root>/<workspace>/proposals/<proposal-id>/design/diagrams/
```

Do not hardcode a maintainer-specific workspace path in SKILL.md, JSON examples, README files, or scripts.

## Setup

Do not copy the Archify upstream source into a skill repository. Use one of these locations at runtime:

1. Explicit binary: `ARCHIFY_BIN=<path-to-archify.mjs>`
2. Command arg: `--archify-root <path-to-archify-root>`
3. Explicit root: `ARCHIFY_ROOT=<path-to-archify-root>`
4. Installed skill locations:
   - `.agents/skills/archify` (current workspace)
   - `~/.gemini/antigravity-cli/skills/archify`
   - `~/.agents/skills/archify`
   - `~/.codex/skills/archify`
   - `~/.claude/skills/archify`

If Archify is not available, clone it outside the skill repo and point `ARCHIFY_ROOT` to that checkout:

```bash
git clone https://github.com/tt-a1i/archify.git <workspace>/archify
cd <workspace>/archify/archify
npm install
```

## Render Workflow

Render all diagrams in a directory and keep only JSON + PNG:

```bash
node skills/soia-dev-archify-diagrams/scripts/render-archify-diagrams.mjs \
  --dir assets/diagrams \
  --png-only \
  --theme light \
  --width 1400 \
  --height 1000 \
  --scale 2
```

Render one diagram:

```bash
node skills/soia-dev-archify-diagrams/scripts/render-archify-diagrams.mjs \
  --file assets/diagrams/system.architecture.json \
  --png-only
```

The helper:

- Finds `*.architecture.json`, `*.workflow.json`, `*.sequence.json`, `*.dataflow.json`, and `*.lifecycle.json`
- Runs `archify validate`
- Runs `archify render`
- Runs `archify check`
- With `--png-only`, exports PNG previews and deletes temporary HTML files

## README Preview Workflow

GitHub README should use committed PNG previews:

1. Render Archify HTML.
2. Export a PNG preview.
3. Delete the temporary HTML.
4. Commit JSON source and PNG preview.
5. Embed the PNG directly.

Use the bundled exporter when HTML already exists:

```bash
node skills/soia-dev-archify-diagrams/scripts/export-archify-previews.mjs \
  --dir assets/diagrams \
  --theme light \
  --width 1400 \
  --height 1000 \
  --scale 2
```

Markdown:

```markdown
![Diagram](assets/diagrams/example.png)
```

Centered HTML:

```html
<p align="center">
  <img src="assets/diagrams/example.png" alt="Example architecture diagram" width="100%">
</p>
```

## Minimal JSON Patterns

Start from `assets/examples/` when creating new diagrams. Use the suffix to select the renderer:

- `*.architecture.json`
- `*.dataflow.json`
- `*.workflow.json`

Keep examples generic. Do not include personal directories, private repo paths, tokens, cookies, or private workspace names.

## Layout Debugging

Archify validation errors are usually actionable. Apply its suggestions directly:

- label collision: set `labelDy`, `labelDx`, `labelAt`, or `labelSegment`
- node collision: move `row` / `col`, change `pos`, or reduce `size` / `width`
- short workflow edge: skip adjacent columns or route through `drop` / `bottom-channel`
- viewBox overflow: increase `meta.viewBox` or reduce node count

Do not ignore overlap errors. Fix JSON and re-render.

## Output Checklist

Before final response:

- JSON IR exists and is ready to commit.
- Temporary HTML rendered and passed `archify check`.
- README PNG exists if the diagram should be visible on GitHub.
- README-visible diagram HTML was deleted unless explicitly requested.
- Markdown links/images resolve locally.
- Report which scripts were used and which checks passed.
