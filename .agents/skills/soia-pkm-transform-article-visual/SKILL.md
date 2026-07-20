---
name: soia-pkm-transform-article-visual
description: 把文章转换为长图、信息图、海报、封面、插画等视觉产物。HTML/CSS 截图为本地默认方案，可选 Open Design 或 Codex 图生成。Triggers：「生成长图」「做成信息图」「转成海报」「生成封面」「做成图片」「export visual」「make infographic」
version: 1.1.0
created_at: 2026-07-16 10:58:46
updated_at: 2026-07-20 15:08:21
created_by: claude opus 4.6
updated_by: gpt-5.6-terra
dependencies:
  optional: [soia-dev-open-design-ops]
---

# soia-pkm-transform-article-visual

把已归档或指定文章转换为视觉产物：长图、信息图、海报、封面或插画。

## 客户可读说明

### 这个技能可以做什么

把 Markdown / vault 文章或 URL 渲染为图片产物：

- **长图**：完整文章内容纵向展开为单张 PNG/JPEG
- **信息图**：核心概念可视化，节点 + 连接 + 标注
- **海报 / 封面**：单张设计稿，强排版重视觉
- **插画 / 封面图**：可选 Codex imagegen 生成配图

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 生成长图 | HTML/CSS 渲染截图，prompt 落盘可重跑 | 图片路径、像素尺寸、预览 |
| 指定 provider | 走对应 provider 流程 | provider 日志 |
| 执行完成 | 验收文件存在、尺寸合理、中文可读 | 完成回执 |

### 客户如何使用

1. 说明来源（URL / vault 路径 / 本地 Markdown）和目标视觉类型（长图/信息图/海报/封面，可选）。
2. 可选：指定 provider（`local` / `open-design` / `codex-image`）、风格、尺寸。
3. URL 来源先 clip 归档再转换。

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-transform-article-visual -y
```

- 本地截图方案：`pip install playwright && playwright install chromium`
- Open Design（可选强化依赖）：安装 `soia-dev-open-design-ops` 后才可使用 `provider=open-design`；见 [references/provider-open-design.md](references/provider-open-design.md)
- Codex image / imagegen（可选）：见 [references/prompt-codex-image.md](references/prompt-codex-image.md)

| 路径 | 依赖 | 缺失时行为 |
|---|---|---|
| `local` | 无 | 零依赖可用 |
| `codex-image` | 当前环境的 image generation 能力 | 仅该 provider 停在工具可用性闸门 |
| `open-design` | `soia-dev-open-design-ops`（该路径硬依赖）及其 Open Design 环境 | 停止该 provider，给出安装与环境检查命令；不把它冒充为 Open Design 结果 |

`soia-dev-open-design-ops` 在本技能 frontmatter 中标为 `optional`，因为 `local` 和 `codex-image` 路径不依赖它；一旦用户选择 `provider=open-design`，它就是该次执行的硬依赖。

### 日志与完成回执

```markdown
完成：<一句话>。

日志摘要：
- source: <路径或 URL>
- visual_type: long_image | infographic | poster | cover | illustration
- provider: local | open-design | codex-image
- content_mode: visual_dense
- prompt: <落盘路径>
- output: <图片路径>
- dimensions: <宽x高 px>

验证：
- 文件存在，大小 > 50KB
- 尺寸合理（宽 ≥ 750px，高视类型而定）
- 目视中文可读、无截断、无方块乱码

问题与下一步：
- <无 / provider 降级原因 / 建议>
```

## 边界

- 默认 `visual_dense` 模式：核心概念保留，排版压缩，不逐段重复原文。
- 位图上文字错误（乱码、溢出、重叠）**唯一合法修复是改 prompt 重新生成**，禁止 PIL/Canvas/ImageMagick 描字覆盖。
- prompt 必须落盘到 `outputs/transform/<YYYY>/<stem>/prompts/` 保证可重跑。
- Open Design / Codex-image 是可选 provider。未指定 provider 时可选择本地路径；用户显式选择 `open-design` 而缺少其原子层或环境时，停止该 provider 并说明缺口，不静默降级或声称已使用 Open Design。
- 不做内容总结；但允许信息架构重组（如将段落提炼为节点关系图）。

## 工作流

1. 确认来源 → URL 先 clip。
2. 确定 `visual_type`：`long_image`（默认）/ `infographic` / `poster` / `cover` / `illustration`。
3. 选 provider：用户指定 > 配置 > 本地 HTML/CSS 截图。
4. 读 [references/prompt-infographic.md](references/prompt-infographic.md) 或 [references/prompt-codex-image.md](references/prompt-codex-image.md)（封面/插画时）生成 prompt，落盘。
5. 生成产物到 `outputs/transform/<YYYY>/<stem>/`。
6. 验收：文件存在、尺寸合理、目视中文无乱码、无截断。
7. 回执。

详见 [references/prompt-infographic.md](references/prompt-infographic.md)、[references/design-prompts.md](references/design-prompts.md)、[references/quality-gates.md](references/quality-gates.md)、[references/provider-open-design.md](references/provider-open-design.md)。Open Design 的环境、daemon、目录与导出原子操作以 `soia-dev-open-design-ops/SKILL.md` 为单一真源。
