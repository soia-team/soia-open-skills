# NotebookLM Provider

适用：播客、视频、PPT/PPTX、脑图、quiz、flashcards、report、infographic、data table，以及多源资料的 grounded synthesis。

推荐公共实现：`teng-lin/notebooklm-py`。

上游依据：

- README: https://github.com/teng-lin/notebooklm-py
- CLI reference: https://github.com/teng-lin/notebooklm-py/blob/main/docs/cli-reference.md
- Configuration: https://github.com/teng-lin/notebooklm-py/blob/main/docs/configuration.md
- Agent skill: https://github.com/teng-lin/notebooklm-py/blob/main/SKILL.md

## 安全边界

- `notebooklm-py` 是非官方 NotebookLM API/CLI；Google 内部接口可能变化，必须保留降级说明。
- 安装建议用隔离工具：`uv tool install "notebooklm-py[browser,cookies]"` 或 `pipx install "notebooklm-py[browser,cookies]"`。普通 `pip install` 只在 active virtualenv 或用户明确允许时使用。
- 不用 npm 安装 NotebookLM CLI。`npx skills add teng-lin/notebooklm-py` 只安装 agent skill，不安装 Python CLI。
- 初次使用需要 `notebooklm login` 或明确授权的 browser-cookie 导入；skill 不保存 Google 账号、密码、cookie。
- 自动化前用 `NOTEBOOKLM_HOME=... notebooklm auth check --test --json` 验证认证，不能只看本地 cookie 是否存在。
- 每条自动化命令都带上 `NOTEBOOKLM_HOME`；裸跑 `notebooklm ...` 会回落到默认 `~/.notebooklm`，容易让其他 AI 误判“未登录”。
- 并行工作流不要依赖 `notebooklm use` 的全局上下文；优先在 notebook-scoped 命令里传 `-n <notebook-id>`。
- 生成 artifact 后记录 `notebook_id`、`source_id`、`task_id` / `artifact_id`、下载路径。
- 语言代码必须来自 `notebooklm language list`。简体中文是 `zh_Hans`，不是 `zh-Hans`。

## 认证根目录

公共推荐：

```bash
export NOTEBOOKLM_HOME="${NOTEBOOKLM_HOME:-$HOME/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-transform/notebooklm}"
mkdir -p "$NOTEBOOKLM_HOME"
chmod 700 "$NOTEBOOKLM_HOME"
```

如果用户已有自己的 `NOTEBOOKLM_HOME`，尊重现有值。不要把 `~/.notebooklm` 当成唯一约定，也不要把认证文件放到 vault 或开源 skill 仓库。

## Bootstrap

当用户明确要 NotebookLM 产物，或目标默认 provider 是 NotebookLM（podcast / video / quiz / flashcards / grounded report / mindmap）时：

1. 检查 CLI 与认证：

   ```bash
   command -v notebooklm
   notebooklm --version
   NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm language list
   python3 scripts/notebooklm_health.py --ensure-home --json
   NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm auth check --test --json
   ```

2. 缺 CLI 时按顺序安装。只有用户明确要求或配置允许时才执行：

   ```bash
   command -v uv && uv tool install "notebooklm-py[browser,cookies]"
   command -v pipx && pipx install "notebooklm-py[browser,cookies]"
   python -m pip install "notebooklm-py[browser,cookies]"  # only inside active venv or explicit consent
   ```

3. 缺登录态时进入人工登录闸门：

   ```bash
   NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm login
   NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm auth check --test --json
   NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm list --json
   ```

   `notebooklm login` / `notebooklm login --browser chrome` 会打开受控浏览器 profile，不是用户正在使用的 Chrome 窗口。不要把它描述成「使用当前 Chrome」。

4. 若用户明确要复用当前 Chrome 登录态，先说明会读取浏览器 cookie，然后：

   ```bash
   NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm auth inspect --browser chrome --json
   NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm login --browser-cookies 'chrome::<profile>'
   ```

   `<profile>` 由用户提供，或通过 `auth inspect` 的只读结果选择。Agent 不要打印账号邮箱、cookie 值或 `storage_state.json` 内容。

5. 可选安装 NotebookLM agent skill：

   ```bash
   notebooklm skill install
   npx -g skills add teng-lin/notebooklm-py
   ```

   这只注册 agent skill，不替代 CLI 安装和 auth check。使用 `npx` 时需要 `-g`，不要在项目/vault 里生成本地 `node_modules`。

## 常见命令形态

```bash
export NOTEBOOKLM_HOME="${NOTEBOOKLM_HOME:-$HOME/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-transform/notebooklm}"
export NOTEBOOKLM_HL="${NOTEBOOKLM_HL:-zh_Hans}"
notebooklm auth check --test --json
notebooklm create "Article Transform - <title>" --json
notebooklm source add "<article.md or URL>" -n <notebook-id> --json
notebooklm generate slide-deck --prompt-file prompt.txt -n <notebook-id> --format detailed --length default --language "$NOTEBOOKLM_HL" --wait --json
notebooklm download slide-deck "<out.pptx>" --format pptx -n <notebook-id> --force --json
```

音频/视频下载的兼容写法：

```bash
NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm generate audio "..." -n <notebook-id> --format deep-dive --length long --language "$NOTEBOOKLM_HL" --wait --json
NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME" notebooklm download audio --all "<out-dir>/podcast" -n <notebook-id> --force --json
```

实测 `download audio <single-file> --latest` 在部分版本会返回空 `UNEXPECTED_ERROR`，但 `download audio --all <dir>` 能列出并下载已生成 artifact。video / cinematic-video smoke 也优先用 `--all <dir>`，再按扩展名验证。

`generate quiz` 和 `generate flashcards` 当前 CLI 不支持 `--language`；用 `NOTEBOOKLM_HL=zh_Hans` 或在描述文字中要求简体中文，不要给这两个子命令追加 `--language`。

`generate report` 支持 `--format briefing-doc|study-guide|blog-post|custom`。transform 的普通 report 默认使用 `custom / Create Your Own`；只有用户明确要 quick brief / study guide / blog post 时才使用对应内置格式。

`generate video` 支持 `--format explainer|brief|cinematic`。transform 的 cinematic-video 目标应走 `notebooklm generate video --format cinematic`，不是 `generate cinematic-video`。

## 目标映射

| Transform 目标 | 先读 prompt | NotebookLM 命令 |
|----------------|-------------|-----------------|
| podcast | [prompt-notebooklm-podcast.md](prompt-notebooklm-podcast.md) | `generate audio` -> `download audio` |
| video | [prompt-notebooklm-podcast.md](prompt-notebooklm-podcast.md) | `generate video` -> `download video` |
| cinematic-video | [prompt-notebooklm-podcast.md](prompt-notebooklm-podcast.md) | `generate video --format cinematic` -> `download video` |
| ppt | [prompt-notebooklm-ppt.md](prompt-notebooklm-ppt.md) | `generate slide-deck` -> `download slide-deck --format pptx` 或 PDF |
| mindmap | [prompt-notebooklm-mindmap.md](prompt-notebooklm-mindmap.md) | `generate mind-map` -> `download mind-map` |
| quiz | [prompt-notebooklm-quiz.md](prompt-notebooklm-quiz.md) | `generate quiz` -> `download quiz --format markdown/json/html` |
| flashcards | [prompt-notebooklm-flashcards.md](prompt-notebooklm-flashcards.md) | `generate flashcards` -> `download flashcards --format markdown/json/html` |
| report | [prompt-notebooklm-report.md](prompt-notebooklm-report.md) | `generate report --format custom` -> `download report` |
| infographic | [prompt-notebooklm-image.md](prompt-notebooklm-image.md) | `generate infographic` -> `download infographic` |
| data-table | [prompt-notebooklm-report.md](prompt-notebooklm-report.md) | `generate data-table` -> `download data-table` |

全量 smoke / dry-run 见 [notebooklm-test-matrix.md](notebooklm-test-matrix.md)。

脚本：

```bash
python3 scripts/notebooklm_artifact_matrix.py --article <article.md> --out-dir <out> --targets all --run --json
```

该脚本会逐目标记录 `status`；某个 artifact 生成或下载失败时继续后续目标，并在 `summary.failed` 中列出真实失败点。
