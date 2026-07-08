# NotebookLM Test Matrix

用于测试 `teng-lin/notebooklm-py` 的 NotebookLM provider。默认先 dry-run；只有用户明确要求全量跑、且 auth check 通过时，才生成真实 artifacts。

## 前置检查

```bash
export NOTEBOOKLM_HOME="${NOTEBOOKLM_HOME:-$HOME/.config/soia-pkm/notebooklm}"
export NOTEBOOKLM_HL="${NOTEBOOKLM_HL:-zh_Hans}"
python3 scripts/notebooklm_health.py --ensure-home --json
NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm auth check --test --json
notebooklm --version
notebooklm language list
```

若 `auth check` 不通过，停止在登录闸门，不跑 artifact 测试。

## 快速 dry-run

```bash
python3 scripts/notebooklm_artifact_matrix.py \
  --article "<article.md>" \
  --out-dir "<output-dir>" \
  --json
```

输出会列出每个 artifact 的 generate / download 命令，不创建 notebook，不上传资料。

## 全量生成测试

这是重型测试，会创建临时 notebook、上传文章、生成并下载多种 artifacts。只有用户确认后执行：

```bash
python3 scripts/notebooklm_artifact_matrix.py \
  --article "<article.md>" \
  --out-dir "<output-dir>" \
  --run \
  --targets all \
  --timeout 600 \
  --json
```

如果要保留 notebook 方便人工检查，加 `--keep-notebook`。默认脚本只在成功创建了本轮临时 notebook 时才会尝试清理它。

脚本会逐目标记录 `status`；某个目标失败时继续后续目标。要保持旧行为可加 `--stop-on-error`。

## Artifact 覆盖表

| 目标 | Generate | Download | 主要验证 |
|------|----------|----------|----------|
| podcast | `generate audio --wait` | `download audio --all podcast/` | MP3 存在且大小合理 |
| video | `generate video --wait` | `download video --all video/` | MP4 存在且大小合理 |
| cinematic-video | `generate cinematic-video --wait` | `download cinematic-video --all cinematic-video/` | MP4 存在 |
| ppt | `generate slide-deck --format detailed --wait` | `download slide-deck deck.pptx --format pptx` | PPTX 能打开 / 可渲染 |
| infographic | `generate infographic --orientation portrait --detail detailed --wait` | `download infographic infographic.png` | PNG 尺寸与文字可读 |
| mindmap | `generate mind-map --kind interactive` | `download mind-map mindmap.json` | JSON 可解析 |
| report | `generate report --format study-guide --wait` | `download report report.md` | Markdown 非空、有结构 |
| data-table | `generate data-table "..." --wait` | `download data-table data.csv` | CSV 可读 |
| quiz | `generate quiz --difficulty medium --quantity standard --wait` | `download quiz quiz.md --format markdown` | 题目/答案数量一致 |
| flashcards | `generate flashcards --difficulty medium --quantity standard --wait` | `download flashcards flashcards.md --format markdown` | 卡片数量与格式合理 |

## 回执标准

执行后必须报告：

- `NOTEBOOKLM_HOME` 是否为公共推荐目录或用户自定义目录。
- CLI version 与 auth check 结果。
- notebook_id、source_id。
- 每个 artifact 的 task/artifact 状态、下载路径和验证结果。
- 失败项的真实错误与可重跑命令。
