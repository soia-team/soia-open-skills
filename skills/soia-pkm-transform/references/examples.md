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
