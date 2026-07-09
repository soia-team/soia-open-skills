---
name: soia-dev-archify-diagrams
description: Draw, improve, validate, or publish Archify architecture / data-flow / sequence / lifecycle diagrams with JSON IR and PNG previews. Triggers：「画架构图」「画时序图/流程图」「给 README 配图」「用 Archify 画」
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
