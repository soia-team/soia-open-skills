# Examples

这些是公共、匿名、可复用的 transform 使用样例。每个例子先解析路由，再执行对应 recipe。

## 1. Markdown 文章转本地 PPT

用户说：

```text
把 <path-to-article.md> 转成 PPT，10 页，给小白，课程风。
```

路由检查：

```bash
python3 scripts/resolve_route.py --target ppt --provider local --json
```

预期读取：

- [design-prompts.md](design-prompts.md)
- [output-recipes.md](output-recipes.md) 的 PPT 小节
- [prompt-ppt.md](prompt-ppt.md)

## 2. Markdown 文章转 NotebookLM PPT

用户说：

```text
用 NotebookLM 把 <path-to-article.md> 生成 slide deck。
```

路由检查：

```bash
python3 scripts/resolve_route.py --target ppt --provider notebooklm --json
```

预期读取：

- [providers.md](providers.md) 的 NotebookLM bootstrap/auth check
- [prompt-notebooklm-ppt.md](prompt-notebooklm-ppt.md)

## 3. 文章转高密度长图

用户说：

```text
把 <path-to-article.md> 转成 1080x1920 高密度长图。
```

路由检查：

```bash
python3 scripts/resolve_route.py --target image --image-subtype long_image --json
```

预期读取：

- [design-prompts.md](design-prompts.md)
- [prompt-infographic.md](prompt-infographic.md)

注意：中文密集信息图默认走 local_visual HTML/CSS 截图，不让 Codex image 直接生成大量中文小字。

## 4. 文章生成封面图素材

用户说：

```text
给 <path-to-article.md> 生成一张 16:9 封面图，不要文字。
```

路由检查：

```bash
python3 scripts/resolve_route.py --target image --provider codex_image --image-subtype cover_image --json
```

预期读取：

- [prompt-codex-image.md](prompt-codex-image.md)

注意：这只生成视觉素材；标题、作者、来源应后期用 HTML/PPT/图片编辑叠加。

## 5. 文章生成 NotebookLM Quiz

用户说：

```text
用 NotebookLM 给 <path-to-article.md> 出一套测验。
```

路由检查：

```bash
python3 scripts/resolve_route.py --target quiz --provider notebooklm --json
```

预期读取：

- [providers.md](providers.md) 的 NotebookLM bootstrap/auth check
- [prompt-notebooklm-quiz.md](prompt-notebooklm-quiz.md)

## 6. 文章全文导出 PDF

用户说：

```text
把 <path-to-article.md> 导出 PDF。
```

路由检查：

```bash
python3 scripts/resolve_route.py --target pdf --provider obsidian --json
```

预期读取：

- [output-recipes.md](output-recipes.md) 的 PDF 小节

注意：PDF 默认是 `preserve` 全文转换，不是 report 或 summary。

## 7. 本地全量转换并验收

用户说：

```text
把 <path-to-article.md> 支持的格式都跑一遍，我要看成品。
```

执行：

```bash
python3 scripts/local_artifact_smoke.py \
  --article <path-to-article.md> \
  --out-dir <out-dir> \
  --strict \
  --json
```

二次验收：

```bash
python3 scripts/validate_artifact_quality.py \
  --article <path-to-article.md> \
  --out-dir <out-dir> \
  --strict \
  --json
```

预期产物至少包含：

- `report.md/html/pdf`
- `deck.html/pptx/pdf`
- `infographic.html/png`
- `quiz.md`
- `flashcards.md/csv`
- `data-table.csv`
- `mindmap.mmd`
- `podcast-script.md`
- `video-script.md`
- `cinematic-video-shotlist.md`

## 好坏样例

### 不合格：PPT 变成摘要

- 只有 5-6 页。
- 每页只有 3 个泛泛 bullet。
- 没有 source 地图、概念覆盖矩阵、案例/流程、易混点、风险边界、自测、来源页。
- 原文有 12 个以上概念，但 PPT 只讲了 3-5 个。

### 合格：PPT 是可讲课件

- 中长文默认 14-18 页，至少 4 种版式。
- 先展示文章地图，再展示概念矩阵和案例链。
- 每个主要模块至少有一页，术语速查或覆盖索引能回指 source。
- 最后有行动清单、自测和来源页。

### 不合格：Report 只是 brief

- 只有执行摘要或几段总结。
- 没有逐模块解释、概念矩阵、source 引用、风险边界。
- 用户要求 PDF preserve 时，却交付了 report summary。

### 合格：Report 可支撑再加工

- 明确标注它是 grounded report、study guide 还是全文 PDF。
- 包含 source 地图、概念覆盖矩阵、逐模块解释、案例/流程、易混表、风险边界、行动清单和继续追问。
- 机械质量门通过后，再做人工可读性检查。

### 不合格：长图只是海报

- 一个大标题加几张卡片，大面积留白。
- 中文小字不可读，信息没有层级。
- 没有流程、矩阵、支持/风险或行动清单。

### 合格：长图是信息密度高的视觉摘要

- 1080x1920 或用户指定尺寸内至少 12 个信息块。
- 同时呈现主判断、流程、概念矩阵、风险边界和行动清单。
- 中文文字可读，不让 imagegen 直接生成大量中文小字。
