# SOIA Skills Installation Guide

[中文](install-guide.md) · [Installation profiles](install-profiles.md)

This concise guide covers the universal installer, domain plugins, on-demand routing, and host-specific notes. Placeholders such as `<repository>`, `<skill-name>`, and `<domain-plugin>` should be replaced before running a command.

## Ecosystem coverage

`~/.agents/skills` is read natively by Zed, Cursor, Copilot, Codex, Gemini, DeepCode, and other hosts, so most need no synchronization. Only Windsurf and Trae need explicit links; both are sync-tool targets. The SOIA marketplace manifest is also reusable by Qwen Code and qodercli.

## Recommended starting points

### Universal npx installation

`npx skills` supports 62+ AI agents and preserves single-skill granularity:

```bash
npx skills add soia-team/<repository> -g -a '*' -s <skill-name> -y
```

Use concrete agent ids instead of `'*'` when needed:

```bash
npx skills add soia-team/<repository> -g \
  -a claude-code codex cursor -s <skill-name> -y
```

Global installs use `~/.agents/skills` as the shared source of truth. Agent directories reuse it through symlinks, while `~/.agents/.skill-lock.json` records source and installation state.

```bash
npx skills list -g
npx skills update <skill-name> -g
npx skills remove -g -a '*' -s <skill-name> -y
```

### Domain plugin marketplaces

One SOIA domain plugin contains all skills from one domain repository and provides a domain-level enable/disable boundary:

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install soia-pkm-clip@soia

codex plugin marketplace add soia-team/soia-open-skills
codex plugin add soia-pkm-clip@soia

qwen extensions install \
  https://github.com/soia-team/soia-open-skills:soia-pkm-clip
```

Prefer either npx or a plugin for the same skills on one host; using both can create duplicate indexes.

### On-demand loading

Install the ecosystem router to keep core skills immediately available while finding and loading long-tail skills only when needed:

```bash
npx skills add soia-team/soia-open-skills -g -a '*' \
  -s soia-meta-find-skill -y
```

For host-specific trimming, use `soia-meta-sync-skills` with `--exclude-skills` and `--save-excludes`.

## By AI agent

### Claude Code

```bash
# User-level symlink under ~/.claude/skills
npx skills add soia-team/<repository> -g \
  -a claude-code -s <skill-name> -y

# Project-level installation under .claude/skills
npx skills add soia-team/<repository> \
  -a claude-code -s <skill-name> -y
```

Plugin lifecycle:

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install <domain-plugin>@soia
claude plugin details <domain-plugin>@soia
claude plugin disable <domain-plugin>@soia
claude plugin enable <domain-plugin>@soia
claude plugin update <domain-plugin>@soia
claude plugin uninstall <domain-plugin>@soia
```

`details` reports the component inventory and projected token cost. Run `claude plugin list` or `readlink ~/.claude/skills/<skill-name>` to verify. Restart after a plugin update.

### Codex

Codex reads `~/.agents/skills` natively, so a global npx install needs no extra synchronization:

```bash
npx skills add soia-team/<repository> -g \
  -a codex -s <skill-name> -y

codex plugin marketplace add soia-team/soia-open-skills
codex plugin add <domain-plugin>@soia
codex plugin list
codex plugin marketplace upgrade soia
codex plugin remove <domain-plugin>@soia
```

This repository's `.agents/plugins/marketplace.json` is the native Codex marketplace manifest. Use `npx skills list -g -a codex` to verify npx installs.

### Qwen Code

```bash
npx skills add soia-team/<repository> -g \
  -a qwen-code -s <skill-name> -y

qwen extensions install \
  https://github.com/soia-team/soia-open-skills:<domain-plugin>
qwen extensions list
qwen extensions update <domain-plugin>
qwen extensions disable --scope User <domain-plugin>
qwen extensions enable --scope User <domain-plugin>
qwen extensions uninstall <domain-plugin>
```

npx creates the `~/.qwen/skills` entry. Qwen consumes the Claude marketplace format natively; run `/extensions` in Qwen Code to hot-reload extensions.

### Gemini CLI

Gemini CLI officially supports `~/.agents/skills` as a user-level alias:

```bash
npx skills add soia-team/<repository> -g \
  -a gemini-cli -s <skill-name> -y
npx skills list -g -a gemini-cli
```

Its extension mechanism remains optional.

### Antigravity CLI (`agy`)

```bash
npx skills add soia-team/<repository> -g \
  -a antigravity-cli -s <skill-name> -y
readlink ~/.gemini/antigravity-cli/skills/<skill-name>

agy plugin import claude
agy plugin list
```

npx and the sync tool cover `~/.gemini/antigravity-cli/skills/`. Recent `agy` versions can import Claude plugins.

### Kimi CLI

Kimi discovers skills automatically:

```bash
npx skills add soia-team/<repository> -g \
  -a kimi-code-cli -s <skill-name> -y
kimi --skills-dir <skill-directory>
```

`--skills-dir` replaces auto-discovery for that run and can be repeated to select a subset. Restart the session to verify the global install.

### OpenCode and DeepCode

Both use the `~/.agents/skills` interoperability layer; DeepCode documents this as interoperable skills:

```bash
npx skills add soia-team/<repository> -g \
  -a opencode -s <skill-name> -y
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y
```

DeepCode has no dedicated npx agent id; it consumes the installer's shared interoperability directory directly. Verify OpenCode with `npx skills list -g -a opencode`, verify DeepCode with `ls ~/.agents/skills/<skill-name>/SKILL.md`, update with `npx skills update`, and restart the host if the current session does not refresh.

### WorkBuddy

Link skills into `~/.workbuddy/skills` with the sync tool:

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets workbuddy \
  --skills <skill-name> \
  --dry-run
```

Remove `--dry-run` after reviewing the plan, then verify with `readlink ~/.workbuddy/skills/<skill-name>`. WorkBuddy also accepts SkillHub or zip imports when `SKILL.md` is at the package root.

### qodercli

```bash
qodercli --plugin-dir <plugin-directory>
npx skills add soia-team/<repository> -g \
  -a qoder -s <skill-name> -y
```

qodercli discovers `~/.qoder/skills` and `.qoder/skills` (user-level wins); run `/skills reload` to verify. Update npx installs with `npx skills update <skill-name> -g`. Its Claude-compatible plugin format can reuse the SOIA marketplace with near-zero changes; plugins/MCP can be enabled or disabled, and `--permission-mode` plus `--tools` constrain a run.

### Cursor

```bash
npx skills add soia-team/<repository> -g \
  -a cursor -s <skill-name> -y
```

Cursor natively supports `.cursor/skills` and `~/.agents/skills`; verify with `npx skills list -g -a cursor` or a new session, then update with `npx skills update <skill-name> -g`. Skills are description-triggered; rules support `paths` globs and `disable-model-invocation`. Cursor also has extensions, a marketplace, hooks, and per-item MCP sidebar toggles. Retire a duplicate `~/.cursor/skills` link if present.

### Windsurf

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets windsurf \
  --skills <skill-name> \
  --dry-run
```

Windsurf requires an explicit link to `~/.codeium/windsurf/skills` (or project `.windsurf/skills`); remove `--dry-run` after review and verify with `readlink`. Update the shared source with npx, then sync again. It progressively discloses skills; rules have three activation modes and MCP supports per-tool toggles with a 100-tool cap.

### Copilot CLI / agent

```bash
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y
```

Copilot natively reads `~/.copilot/skills`, `~/.agents/skills`, and `.github/skills`; use `/skills` to verify and toggle individual skills, and update with npx. Team skills belong in `.github/skills`; custom Markdown agents, provenance-aware `gh` distribution, ACP servers, and `allowed-tools` / `--allow-tool` / `--deny-tool` are also available.

### Zed

```bash
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y
```

Since v1.4 Zed reads `~/.agents/skills` and worktree `.agents/skills`; start a new session to verify and update with npx. `AGENTS.md` / `.rules` provide instructions, skills support `disable-model-invocation`, and profiles can set `context_servers` plus three-state tool permissions. Zed also supports WASM extensions (including MCP) and acts as an ACP client.

### Trae

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets trae \
  --skills <skill-name> \
  --dry-run
```

Trae Skills (Beta) use `.trae/skills` or `~/.trae/skills`; remove `--dry-run` after review, verify with `readlink`, and also probe `~/.trae-cn` for the CN edition. Update with npx, then sync again. Skills invoke on demand; rules live in `.trae/rules/`, and custom Agents plus MCP (`~/.trae/mcp.json`, v1.3+) can choose tools per agent.

## Multi-agent symlink synchronization

Install the helper first:

```bash
npx skills add soia-team/soia-open-skills -g -a '*' \
  -s soia-meta-sync-skills -y
```

Always preview with `--dry-run`, then remove that flag after checking the source, targets, and link changes:

```bash
# All skills to selected hosts
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets codex,claude,qwen \
  --dry-run

# One skill and its hard dependencies
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,codex \
  --skills <skill-name> \
  --dry-run

# Persist host-specific exclusions
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,codex \
  --exclude-skills <skill-a>,<skill-b> \
  --save-excludes
```

Use `--list-targets` to see built-in target ids.

## Troubleshooting

- **Not detected:** start a new host session, then check `~/.agents/skills/<skill-name>/SKILL.md`, `~/.agents/.skill-lock.json`, and `readlink <host-skill-directory>/<skill-name>`.
- **Plugin plus npx:** choose one method per host for the same skills to avoid duplicate indexing.
- **Private repositories:** authenticate with `gh auth status`, then run the normal `npx skills add soia-team/<private-repository> ...` command. Never place a token in the command or repository.

| Installation method | Update |
|---|---|
| npx | `npx skills update -g` |
| Claude plugin | `claude plugin update <domain-plugin>@soia` |
| Codex marketplace | `codex plugin marketplace upgrade soia` |
| Qwen extension | `qwen extensions update <domain-plugin>` |

See [installation profiles](install-profiles.md) for curated sets by machine role.
