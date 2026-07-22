# Targets and Confirmation

## Target Directory Matrix

| Target id | Tool | Directory | Notes |
|---|---|---|---|
| `soia` | SOIA AI | `~/.soia/skills` | Optional named target; select it explicitly when the customer uses it. |
| `workbuddy` | WorkBuddy | `~/.workbuddy/skills` | Optional named target; select it explicitly when the customer uses it. |
| `claude` | Claude Code | `~/.claude/skills` | User-level skill directory. |
| `codex` | OpenAI Codex | `~/.codex/skills` | Codex user skill directory. |
| `agy` | Antigravity CLI | `~/.gemini/antigravity-cli/skills` | Consumer Google-account successor target; independent from Gemini CLI. |
| `gemini` | Gemini CLI | `~/.gemini/skills` | Retained for Standard/Enterprise, API Key, and Vertex AI lanes. |
| `kimi` | Kimi CLI | `~/.kimi/skills` | User-level skill directory. |
| `opencode` | OpenCode | `~/.config/opencode/skill` | Directory name is singular `skill`. |
| `qwen` | Qwen Code | `~/.qwen/skills` | Actual command name is `qwen`, not `qwencode`. |
| `cursor` | Cursor | `~/.cursor/skills` | User-level skill directory. |
| `qoder` | QoderCLI | `~/.qoder/skills` | Keep synced even when subscription is inactive. |
| `copilot` | GitHub Copilot | `~/.copilot/skills` | Optional target when directory exists or user selects it. |
| `windsurf` | Windsurf | `~/.codeium/windsurf/skills` | Optional target when directory exists or user selects it. |
| `openclaw` | OpenClaw | `~/.openclaw/skills` | Optional target when directory exists or user selects it. |

Command-name truth:

- `agy` is the Antigravity CLI command. It replaces only Gemini CLI consumer
  Google login and must not be aliased to `gemini`.
- `qwen` is the command name, not `qwencode`.
- `opencode` is the command name and supports `run`, `serve`, and `web`.

## Target Selection

- Do not assume any product-specific target. Require `--targets`, or use only known target directories that already exist on disk.
- A target selected by id is linked from the source directory supplied for this run; the tool never infers a repository checkout.
- Add known target dirs that already exist on disk. Also propose `agy` when the
  `agy` command exists, even if its global skill directory has not been created
  yet.
- Allow explicit known target ids, comma-separated ids, and custom paths.
- Create selected target dirs during execution if they do not exist.
- Reject a target path that resolves to the same path as the source skills root.
- Target entries are symlinks. If a target already has a same-name copied directory, remove that directory and replace it with a symlink after confirmation.

## Confirmation Compatibility

AskUserQuestion-capable clients:

- Present target choices as a multi-select question.
- Recommend only targets explicitly named by the customer or present in their user-owned configuration.
- Add a final continue/cancel confirmation after showing the sync plan.
- Use the client-provided "Other" option for custom target paths when available.

Codex Default or plain-text clients:

- Ask the user to reply with target ids or paths in text.
- Show the final plan and command.
- Wait for explicit confirmation before running a writing command.
- Treat `confirm`, `yes`, `y`, `执行`, `继续`, `可以`, or `go` as confirmation only when it clearly refers to the displayed plan.
- If the current user request explicitly asks to install/sync now, treat that request as authorization for the displayed write operation and still report the exact targets afterward.

Never execute writes from an implied or stale confirmation.
