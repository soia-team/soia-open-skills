---
name: soia-dev-ai-cli-upgrade
description: Audit and upgrade AI/developer CLIs (codex, claude, gemini, kimi, qwen, opencode, cursor, etc.) with dry-run reports and logs. Triggers：「升级 AI CLI」「更新 codex/claude/gemini」「检查 CLI 版本」
---

# soia-dev-ai-cli-upgrade

Use this skill when the user asks to audit, dry-run, or upgrade local AI and
developer CLIs in a repeatable way.

Do not use it when the user only asks how to install one known CLI and no
version audit or batch workflow is needed.

## Tools Covered

| Tool | Command | Default upgrade method |
|---|---|---|
| Codex | `codex` | `npm install -g --prefix <npm-prefix> @openai/codex` |
| Claude Code | `claude` | `npm install -g --prefix <npm-prefix> @anthropic-ai/claude-code` |
| Gemini CLI | `gemini` | `npm install -g --prefix <npm-prefix> @google/gemini-cli` |
| Qwen Code | `qwen` | `npm install -g --prefix <npm-prefix> @qwen-code/qwen-code` |
| MiniMax CLI | `mmx` | `npm install -g --prefix <npm-prefix> mmx-cli` |
| Kimi Code | `kimi` | `brew upgrade kimi-code`, install if missing |
| OpenCode | `opencode` | `npm install -g --prefix <npm-prefix> opencode-ai` |
| Qoder CLI | `qodercli` | `qodercli update` |
| Cursor | `cursor` | version audit only unless `CURSOR_UPGRADE_CMD` is set |

## Safety Model

- Start with `DRY_RUN=1` unless the user explicitly asked to upgrade.
- Never edit shell profiles or PATH files automatically.
- Never write API keys, tokens, cookies, or login material to logs.
- Treat `CURSOR_UPGRADE_CMD` as user-supplied code. Only run it when the user
  has explicitly provided or approved that command.
- If an updater requires interactive login or privileged access, stop and report
  the blocker instead of guessing.

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
  NPM_PACKAGES: "codex,claude,gemini"
  NPM_PREFIX: "$HOME/.npm-global"
```

Supported variables:

| Variable | Purpose | Default |
|---|---|---|
| `DRY_RUN=1` | Print current versions without upgrading | `0` |
| `NPM_PACKAGES="codex,claude"` | Limit the tool list | all supported tools |
| `NPM_PREFIX=<path>` | npm global prefix for npm-based CLIs | `$HOME/.npm-global` |
| `LOG_DIR=<path>` | Upgrade log directory | `${XDG_STATE_HOME:-$HOME/.local/state}/soia-dev-ai-cli-upgrade/logs` |
| `CURSOR_UPGRADE_CMD=<command>` | Optional Cursor updater command | unset |

## Standard Workflow

From this repository:

```bash
# Version audit only
DRY_RUN=1 bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh

# Upgrade all supported tools
bash skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh

# Upgrade a subset
NPM_PACKAGES="codex,claude,gemini" \
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
| `STATUS` | `UPDATED`, `ALREADY_LATEST`, `NOT_INSTALLED`, `SKIP_DRY_RUN`, `MANUAL`, `FAILED` |
| `NOTE` | short reason or next action |

## Validation

Before claiming the skill or script changed safely:

```bash
bash -n skills/soia-dev-ai-cli-upgrade/scripts/upgrade-ai-clis.sh
DRY_RUN=1 NPM_PACKAGES="codex" \
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
- If live upgrades were run, report old and new versions where available.
