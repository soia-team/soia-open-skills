---
name: soia-dev-ai-cli-upgrade
description: Audit and upgrade AI/developer CLIs (codex, claude, gemini, kimi, qwen, opencode, cursor, etc.) with dry-run reports and logs. Triggers：「升级 AI CLI」「更新 codex/claude/gemini」「检查 CLI 版本」
---

# soia-dev-ai-cli-upgrade

Use this skill when the user asks to audit, dry-run, or upgrade local AI and
developer CLIs in a repeatable way.

Do not use it when the user only asks how to install one known CLI and no
version audit or batch workflow is needed.

## 客户可读说明

### 这个技能可以做什么

Audit and upgrade AI/developer CLIs (codex, claude, gemini, kimi, qwen, opencode, cursor, etc.) with dry-run reports and logs

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
- **日志位置与保留**：升级审计日志落 `${XDG_STATE_HOME:-~/.local/state}/soia-dev-ai-cli-upgrade/logs/`（XDG 状态目录——日志属于规范定义的 state 数据，用于事后追溯"哪天升了什么版本"，故不放 /tmp 这类会被系统清掉的临时目录）。脚本每次运行自动只保留最近 `LOG_KEEP`（默认 10）份，不会无限堆积；`LOG_DIR` 可整体改道。
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
