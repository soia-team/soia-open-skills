# NotebookLM Provider

NotebookLM 适合快速生成 source-grounded 视觉课件。它不是本技能的默认正式母版 provider；在 `hybrid` 中承担视觉对照角色。

## 健康检查

使用 provider 自己的私有登录目录：

```bash
export NOTEBOOKLM_HOME="${NOTEBOOKLM_HOME:-$HOME/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-transform-article-ppt/notebooklm}"
export NOTEBOOKLM_HL="${NOTEBOOKLM_HL:-zh_Hans}"
notebooklm auth check --test --json
```

缺 CLI 时只在用户明确选择 NotebookLM 后安装 `notebooklm-py[browser,cookies]`。缺登录态时运行 `notebooklm login`，由用户完成登录；不要读取或输出邮箱、cookie 和 `storage_state.json`。

## 生成与下载

```bash
notebooklm create "Article PPT - <title>" --json
notebooklm source add "<article.md or URL>" -n <notebook-id> --json
notebooklm generate slide-deck \
  --prompt-file <prompt.txt> \
  -n <notebook-id> \
  --format detailed \
  --length default \
  --language "$NOTEBOOKLM_HL" \
  --json
```

生成可能排队。保存返回的 `task_id`，用 `artifact poll` 或 `artifact wait` 等到 `completed`。同一个 notebook 中存在多个 deck 时，必须按 artifact id 下载，不能只取 latest：

```bash
notebooklm download slide-deck <output.pptx> \
  --format pptx \
  --artifact <artifact-id> \
  -n <notebook-id> \
  --force \
  --json
```

## 验收

1. 用 `file` 或 OOXML 检查确认下载的是 PPTX，不是扩展名伪装的 PDF。
2. 渲染全部页面，核对页数并生成 montage。
3. 查看封面、地图、最密集页面、术语索引和来源页原图。
4. 检查占位符、运行元数据、错误中文、source 外事实和不可读小字。
5. 检查编辑性。若每页只有一张全幅图片，在回执写 `flattened/image-only`。

notebook id、source id 和 artifact id 可写入用户私有运行日志或 manifest 的私有扩展区，但禁止进入幻灯片和公开回执。

## 失败与降级

- 排队不算失败；等待或轮询到终态。
- 生成失败要保留真实错误和 task id，不静默创建假文件。
- `hybrid` 中 NotebookLM 失败不影响本地正式母版；回执列出缺失版本。
- 用户明确只要 NotebookLM 时，不得静默改成本地版并声称完成。

