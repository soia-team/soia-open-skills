# AI Host Installation Guides

Every npx example below installs the skill body into `~/.agents/skills` first. An `-a` value selects a host entry; it never creates a host-only installation.

## Claude Code

### npx

```bash
npx skills add soia-team/<repository> -g \
  -a claude-code -s <skill-name> -y
```

Claude reads `~/.claude/skills`. Add `--copy` when that entry must be a physical copy instead of a symlink; the global body remains in place.

### Plugin scopes and lifecycle

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install <domain-plugin>@soia --scope user
claude plugin install <domain-plugin>@soia --scope project
claude plugin install <domain-plugin>@soia --scope local
```

Scopes:

- `user`: `enabledPlugins` in `~/.claude/settings.json`, available across the user's projects.
- `project`: `enabledPlugins` in `.claude/settings.json`, shared by the team and committed to the repository.
- `local`: `enabledPlugins` in `.claude/settings.local.json`, local to one user in one project.

Project settings take precedence over user settings. Plugin content is cached under `~/.claude/plugins/cache/soia/<domain-plugin>/<sha>/`.

```bash
claude plugin disable <domain-plugin>@soia --scope user
claude plugin enable <domain-plugin>@soia --scope user
claude plugin disable <domain-plugin>@soia --scope project
claude plugin enable <domain-plugin>@soia --scope project
claude plugin disable <domain-plugin>@soia --scope local
claude plugin enable <domain-plugin>@soia --scope local
claude plugin details <domain-plugin>@soia
claude plugin update <domain-plugin>@soia --scope user
claude plugin update <domain-plugin>@soia --scope project
claude plugin update <domain-plugin>@soia --scope local
```

`details` reports the component inventory and always-on token cost. A disabled plugin has no context cost. Restart Claude Code after an update.

## Codex

Codex reads `~/.agents/skills` directly:

```bash
npx skills add soia-team/<repository> -g \
  -a codex -s <skill-name> -y
```

The Codex plugin route is separate:

```bash
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add <domain-plugin>@soia
codex plugin list
codex plugin marketplace upgrade soia
codex plugin remove <domain-plugin>@soia
```

Plugins are cached under `~/.codex/plugins/cache/soia/<domain-plugin>/` and recorded in `~/.codex/config.toml`. They are added on top of the global skill index. They do not replace or reduce anything already visible in `~/.agents/skills`.

## Qwen Code

```bash
npx skills add soia-team/<repository> -g \
  -a qwen -s <skill-name> -y
npx skills ls -g -a qwen
```

Qwen Code also supports the SOIA plugin-marketplace route. Its plugin content remains outside `~/.agents/skills`.

## qodercli

qodercli requires a synchronized host entry:

```bash
npx skills add soia-team/<repository> -g \
  -a qoder -s <skill-name> -y
npx skills ls -g -a qoder
```

qodercli also supports the SOIA plugin-marketplace route. Its plugin content remains outside `~/.agents/skills`.

## Cursor

Cursor reads `~/.agents/skills` directly:

```bash
npx skills add soia-team/<repository> -g \
  -a cursor -s <skill-name> -y
```

## Windsurf

Windsurf requires a synchronized host entry:

```bash
npx skills add soia-team/<repository> -g \
  -a windsurf -s <skill-name> -y
```

## GitHub Copilot

Copilot reads `~/.agents/skills` directly:

```bash
npx skills add soia-team/<repository> -g \
  -a copilot -s <skill-name> -y
```

## Zed

Zed reads `~/.agents/skills` directly:

```bash
npx skills add soia-team/<repository> -g \
  -a zed -s <skill-name> -y
```

## Gemini CLI

Gemini reads `~/.agents/skills` directly. Its npx agent id is `gemini`, not `gemini-cli`:

```bash
npx skills add soia-team/<repository> -g \
  -a gemini -s <skill-name> -y
```

## Antigravity (`agy`)

```bash
npx skills add soia-team/<repository> -g \
  -a agy -s <skill-name> -y
```

## Kimi CLI

Kimi requires a synchronized host entry:

```bash
npx skills add soia-team/<repository> -g \
  -a kimi -s <skill-name> -y
```

## OpenCode

OpenCode requires a synchronized host entry:

```bash
npx skills add soia-team/<repository> -g \
  -a opencode -s <skill-name> -y
```

## DeepCode

DeepCode reads `~/.agents/skills` directly:

```bash
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y
```

## WorkBuddy

Install the global body, then create the required synchronized entry:

```bash
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y

npx skills add soia-team/soia-open-skills -g \
  -a '*' -s soia-meta-sync-skills -y

python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets workbuddy \
  --skills <skill-name> \
  --dry-run
```

Review the preview, then rerun without `--dry-run`.

## Trae

Trae requires a synchronized host entry:

```bash
npx skills add soia-team/<repository> -g \
  -a trae -s <skill-name> -y
```

## SOIA AI

The verified host matrix does not define a SOIA AI auto-discovery directory. Install the global body, then configure the specific SOIA AI version to read `~/.agents/skills` or use an explicitly supported synchronization entry:

```bash
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y
```

## Common management commands

```bash
npx skills ls -g
npx skills update -g
npx skills remove -g -a '*' -s <skill-name> -y
```

[← Back to the installation guide](README.en.md)
