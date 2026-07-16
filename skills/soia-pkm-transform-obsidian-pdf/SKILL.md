---
name: soia-pkm-transform-obsidian-pdf
description: 用 Obsidian 原生导出把 vault 内 Markdown 笔记导出为 PDF。vault 外文章降级 pandoc/weasyprint。Triggers：「转成PDF」「导出PDF」「归档并转PDF」「生成PDF」「export PDF」
version: 1.0.0
created_at: 2026-07-16
updated_at: 2026-07-16
created_by: zp + claude opus 4.6
updated_by: zp + claude opus 4.6
---

# soia-pkm-transform-obsidian-pdf

把已归档或指定的 Markdown/vault 文章导出为 PDF，输出到与源文件同目录（或用户指定目录）。

它是 `soia-pkm-transform` PDF 分支的独立 skill，与 `clip-*` 衔接。

## 客户可读说明

### 这个技能可以做什么

把 Markdown 文章或已归档 vault 笔记导出为 PDF，使用 Obsidian 原生导出（`Creator: Chromium / Producer: Skia/PDF`）保证中文正确渲染。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取文章、调用 Obsidian 导出或降级本地渲染 | PDF 路径、页数、文件大小 |
| 缺少 Obsidian / vault | 提示降级方案（pandoc / weasyprint） | 降级说明与命令 |
| 执行完成 | 验证 PDF 可打开、页数合理 | 完成回执 + 验证结果 |

### 客户如何使用

1. 说明来源：vault 内已归档笔记路径 / X URL / 网页 URL / 本地 Markdown。
2. 可选：指定输出目录（默认与源文件同目录）。
3. URL 来源先走 `soia-pkm-clip-*` 归档，再执行 PDF 导出。

### 依赖与安装

安装本技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-transform-obsidian-pdf -y
```

- 强依赖：Obsidian（vault 内文章）或 pandoc/weasyprint（vault 外降级）
- 可选：`pdfinfo`、`pdftoppm`（验收用）

### 日志与完成回执

```markdown
完成：<一句话说明>。

日志摘要：
- source: <路径或 URL>
- provider: obsidian-native | pandoc | weasyprint
- output: <PDF 完整路径>
- pages: <页数>
- size: <文件大小>

验证：
- pdfinfo 确认页数、Creator、Producer
- 必要时渲染首页确认中文正常

问题与下一步：
- <无 / 降级原因 / 建议>
```

## 边界

- 来源是 URL → 先调用 `soia-pkm-clip-*` 归档为 vault Markdown，再导出 PDF。
- 来源是本地 Markdown 且不在 vault 内 → 降级：pandoc → weasyprint → 报告失败。
- 不做内容改写，只做格式转换（preserve 模式）。
- 输出目录默认与源文件同目录；vault 外文章输出到 `outputs/transform/<YYYY>/<stem>/`。

## 工作流

1. 确认来源（vault 内 / URL / 本地文件）。
2. URL → `soia-pkm-clip-*` → 得到 vault Markdown 路径。
3. vault 内文章 → Obsidian URI 打开 → `File > 导出 PDF`（osascript 自动化，参照 `references/provider-soia-local.md`）。
4. 确认保存路径，移到目标目录。
5. 验收：`pdfinfo` 确认页数 > 0、Creator/Producer、文件非空；必要时渲染首页目视中文。
6. 回执。

## 验收门（摘自 quality-gates.md）

- 文件存在且非空（> 10KB）
- `pdfinfo` 可读，Pages ≥ 1
- Creator: Chromium 或 Producer: Skia/PDF（Obsidian 导出标志）
- 首页目视：中文正常、无乱码、无全黑页

详见 [references/quality-gates.md](references/quality-gates.md)。
[references/provider-soia-local.md](references/provider-soia-local.md)。
