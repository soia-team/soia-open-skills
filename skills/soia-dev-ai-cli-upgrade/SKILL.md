---
name: soia-dev-ai-cli-upgrade
description: Audit and upgrade AI CLIs with dry-run logs; use agy for consumer Google login and keep gemini opt-in for enterprise/API Key/Vertex. Triggers：「升级 AI CLI」「更新 agy/gemini」「检查 CLI 版本」
version: 1.0.0
created_at: 2026-07-09 07:45:34
updated_at: 2026-07-15 14:21:31
created_by: claude opus 4.6
updated_by: claude opus 4.6
---

# soia-dev-ai-cli-upgrade

Use this skill when the user asks to audit, dry-run, or upgrade local AI and
developer CLIs in a repeatable way.

Do not use it when the user only asks how to install one known CLI and no
version audit or batch workflow is needed.

## 客户可读说明

### 这个技能可以做什么

Audit and upgrade AI/developer CLIs (codex, claude, Antigravity/agy,
Gemini's supported non-consumer lanes, kimi, qwen, opencode, cursor, etc.)
with dry-run reports and logs.

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-ai-cli-upgrade -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-ai-cli-upgrade/config.yml
SOIA_DEV_AI_CLI_UPGRADE_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- **日志位置与保留**：升级日志定位为**用完即弃**——当次报告看完即无价值，默认落系统临时区 `${TMPDIR:-/tmp}/soia-dev-ai-cli-upgrade/logs/`（macOS 的 $TMPDIR 约 3 天自动清、/tmp 重启清），同日多次运行由 `LOG_KEEP`（默认 10）轮转防堆积。若确需留审计追溯（例如排查"哪天升了什么版本导致行为变化"），设 `LOG_DIR` 改道到持久位置（如 `~/.local/state/...`）。
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

## Tools Covered

| Tool | Command | Default upgrade method |
|---|---|---|
| Codex | `codex` | `codex update` (auto-detects native/brew-cask/npm internally); installs via `curl https://chatgpt.com/codex/install.sh`, `brew install --cask codex`, or `npm install -g @openai/codex`; **⚑ npm path**: NOTE column shows curl recommendation |
| Claude Code | `claude` | auto-detected: native → `claude update`; brew cask → `brew upgrade --cask claude-code[@@latest]`; npm (legacy) → `npm install -g @anthropic-ai/claude-code`; Desktop-managed → skip (MANUAL); **⚑ npm path**: NOTE column shows native-installer recommendation |
| Antigravity CLI (consumer Google accounts) | `agy` | Official successor to Gemini CLI consumer Google login; native `agy update`; missing-command install is gated by `AGY_INSTALL=1` |
| Gemini CLI (non-consumer lanes) | `gemini` | auto-detected: brew formula (`brew install gemini-cli`) → `brew upgrade <formula>`; npm → `npm install -g @google/gemini-cli`; native → `gemini update`; explicit opt-in with `TOOLS=gemini` |
| Qwen Code | `qwen` | auto-detected: brew formula (`brew install qwen-code`) → `brew upgrade <formula>`; npm → `npm install -g @qwen-code/qwen-code`; native (curl) → `qwen update`; **⚑ npm path**: NOTE column shows curl recommendation |
| MiniMax CLI | `mmx` | `mmx update` (wraps npm internally); npm-only: `npm install -g mmx-cli` |
| Kimi Code | `kimi` | auto-detected: brew formula (`brew install kimi-code`) → `brew upgrade <formula>`; npm → `npm install -g @moonshot-ai/kimi-code`; native (curl) → `kimi upgrade`; **⚑ npm path**: NOTE column shows `brew install kimi-code` recommendation |
| OpenCode | `opencode` | auto-detected: brew formula (`brew install opencode`) → `brew upgrade <formula>`; npm → `npm install -g opencode-ai`; native (curl) → MANUAL (re-run `curl -fsSL https://opencode.ai/install \| bash`); **⚑ npm path**: NOTE column shows curl recommendation |
| Qoder CLI | `qodercli` | `qodercli update` |
| Cursor | `cursor` | version audit only unless `CURSOR_UPGRADE_CMD` is set |

Why both rows remain: `agy` is the replacement for Gemini CLI's consumer
Google-login path. `gemini` stays only so this skill can audit explicitly
supported Standard/Enterprise, API Key, and Vertex AI installations; it is no
longer part of the default batch.

## Safety Model

- Start with `DRY_RUN=1` unless the user explicitly asked to upgrade.
- Never edit shell profiles or PATH files automatically.
- Missing `agy` is installed only when `AGY_INSTALL=1`. The helper downloads
  Google's HTTPS installer to a temporary directory, syntax-checks it, and runs
  it with an isolated temporary `HOME`; `--dir` places the native binary in
  `AGY_INSTALL_DIR` without letting vendor setup edit the user's real profiles.
- Never write API keys, tokens, cookies, or login material to logs.
- Treat `CURSOR_UPGRADE_CMD` as user-supplied code. Only run it when the user
  has explicitly provided or approved that command.
- If an updater requires interactive login or privileged access, stop and report
  the blocker instead of guessing.

## Gemini consumer migration and Antigravity authentication

These are two separate executables and authentication products. `agy` replaces
Gemini CLI only for the consumer **Login with Google** path; it is not a 1:1
command alias. Keep `gemini` coverage for supported non-consumer lanes, but do
not reinstall or upgrade it in the default batch. Never alias `gemini` to
`agy`, delete Gemini CLI without explicit authorization, or silently move an
account or billing channel.

- Since June 18, 2026, Gemini Code Assist consumer accounts can no longer use
  **Sign in with Google** in Gemini CLI. Google directs consumer users to
  Antigravity. Re-check the current [Google deprecation notice](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals)
  and [migration guide](https://antigravity.google/docs/gcli-migration) before
  acting.
- Gemini Code Assist Standard and Enterprise remain supported in Gemini CLI.
  Gemini API-key and Vertex AI authentication are also separate supported lanes;
  preserve them and follow the current [Gemini CLI authentication guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/authentication.mdx).
- Antigravity CLI uses the system keyring when a session is available and falls
  back to Google Sign-In. The batch upgrade script does not inspect the keyring,
  open a browser, read auth files, or send a model prompt.

After installation, launch `agy` in a PTY only when the user explicitly asked to
log in. If a browser, account chooser, consent screen, paid-credit choice, or
first-launch migration checklist appears, return `blocked_user_action` and wait
for the user. Do not log OAuth URLs, state values, cookies, tokens, account ids,
or credential-file contents. A successful `agy --version` proves only that the
binary runs; it does not prove authentication.

`agy plugin import gemini` writes migrated plugin configuration. Run it only
after the user reviews and approves that separate migration action.

## Configuration

The script uses environment variables. If persistent local configuration is
needed, keep it in the skill-specific private `config.yml`:

```text
~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-ai-cli-upgrade/config.yml
```

Example:

```yaml
env:
  LOG_DIR: "$HOME/.local/state/soia-dev-ai-cli-upgrade/logs"
  TOOLS: "codex,claude,agy"
  NPM_PREFIX: "$HOME/.npm-global"
  AGY_INSTALL: "0"
  AGY_INSTALL_DIR: "$HOME/.local/bin"
```

Supported variables:

| Variable | Purpose | Default |
|---|---|---|
| `DRY_RUN=1` | Print current versions without upgrading | `0` |
| `TOOLS="codex,claude,agy"` | Limit the tool list | consumer-safe default set; `gemini` is opt-in |
| `NPM_PACKAGES="codex,claude"` | Backward-compatible alias for `TOOLS`; ignored when `TOOLS` is set | unset |
| `NPM_PREFIX=<path>` | npm global prefix for npm-based CLIs | `$HOME/.npm-global` |
| `AGY_INSTALL=1` | Allow a missing `agy` to be installed from Google's fixed official HTTPS endpoint | `0` |
| `AGY_INSTALL_DIR=<path>` | Native `agy` installation and fallback detection directory | `$HOME/.local/bin` |
| `LOG_DIR=<path>` | Upgrade log directory | `${TMPDIR:-/tmp}/soia-dev-ai-cli-upgrade/logs` |
| `CURSOR_UPGRADE_CMD=<command>` | Optional Cursor updater command | unset |

## Standard Workflow

From this repository:

```bash
# Version audit only
DRY_RUN=1 bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh

# Upgrade all supported tools
bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh

# Upgrade a consumer-safe subset
TOOLS="codex,claude,agy" \
  bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh

# Upgrade Gemini CLI only after confirming a supported non-consumer lane
TOOLS="gemini" \
  bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh

# Explicitly install agy if it is missing; this does not perform login
AGY_INSTALL=1 TOOLS="agy" \
  bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh
```

From an installed skill:

```bash
DRY_RUN=1 bash ~/.agents/skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh
```

The script writes one timestamped log file and prints a table:

| Column | Meaning |
|---|---|
| `TOOL` | logical tool name |
| `COMMAND` | executable checked |
| `OLD` | version before upgrade or current version in dry-run |
| `NEW` | version after upgrade, or `N/A` in dry-run |
| `STATUS` | `INSTALLED`, `UPDATED`, `ALREADY_LATEST`, `NOT_INSTALLED`, `SKIP_DRY_RUN`, `MANUAL`, `FAILED` |
| `NOTE` | short reason or next action |

`MANUAL` for `agy` can mean installation or update succeeded but the resolved
binary directory is absent from PATH, or PATH resolves to a different binary.
The script reports the absolute resolved path and never edits PATH itself.

## Antigravity diagnosis

Use non-sensitive checks first:

```bash
type -a agy || true
agy --version
agy models
DRY_RUN=1 TOOLS="agy" \
  bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh
```

`agy models` is a model-list discovery request, not a model prompt. Its output
is scoped to the authenticated account, plan, and current service state; do not
hardcode its count, order, display names, aliases, or a default model. If it
requires browser interaction, return `blocked_user_action`. Do not use
`agy -p` as an auth or model-list check because that is a real model call and
may consume quota or credits.

On macOS, source verification can also inspect the installed executable without
reading authentication state:

```bash
agy_bin="$(command -v agy)"
file "$agy_bin"
codesign -dv --verbose=4 "$agy_bin" 2>&1
spctl -a -vv -t execute "$agy_bin"
```

Compare the signing identity, executable architecture, and current release with
Google's [official repository](https://github.com/google-antigravity/antigravity-cli)
and [CLI documentation](https://antigravity.google/docs/cli-overview). Do not
hardcode a release version or checksum in this public skill.

## Validation

Before claiming the skill or script changed safely:

```bash
bash -n skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh
bash skills/soia-dev-ai-cli-upgrade/tests/test_upgrade_ai_clis.sh
DRY_RUN=1 TOOLS="codex,agy" \
  bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh
python3 scripts/audit_skills.py
```

For final install validation after release, install through the remote npx path.
Do not copy a local checkout into an agent skill directory and call that tested:

```bash
npx skills add soia-team/soia-open-skills -g --all
DRY_RUN=1 bash ~/.agents/skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh
```

## Output Checklist

Before final response:

- Say whether the run was dry-run or live.
- Include the log file path.
- Summarize each tool status.
- Call out any `FAILED`, `MANUAL`, or interactive-login blockers.
- Treat a non-zero script exit as at least one true `FAILED` row; the script
  still processes the remaining selected tools before returning failure.
- State that authentication was not checked unless an explicit PTY login flow
  was completed by the user. Use `blocked_user_action` while waiting.
- When model discovery was requested, report `model_source=runtime_account_scoped`
  and the display names returned by `agy models`; do not invent stable model ids,
  aliases, a default, or plan eligibility from that output.
- If live upgrades were run, report old and new versions where available.
