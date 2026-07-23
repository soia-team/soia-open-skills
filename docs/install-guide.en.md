# SOIA Skills Installation Guide

[中文](install-guide.md) · [Installation profiles](install-profiles.md)

This concise guide covers the universal installer, domain plugins, on-demand routing, and host-specific notes. Placeholders such as `<repository>`, `<skill-name>`, and `<domain-plugin>` should be replaced before running a command.

## Ecosystem coverage

`~/.agents/skills` is read natively by Zed, Cursor, Copilot, Codex, Gemini, and DeepCode, so those hosts need no synchronization. Other hosts can receive symlinks from the same shared source through `soia-meta-sync-skills`. The SOIA marketplace manifest is reusable by Claude Code, Codex, Qwen Code, and qodercli.

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

## Full and mixed installation for multi-host users

**Strategy: install a complete base, then trim by host capability.** Install every skill once into the single source of truth at `~/.agents/skills`; let native hosts consume it directly, distribute symlinks once to the remaining hosts, and trim only index-sensitive or frequently used hosts with RouterV1 or domain plugin switches.

### Step 1: install the complete base

Install the meta repository first. Repeat the command for each public repository, or use the 12-repository loop below:

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s '*' -y
```

```bash
repos=(
  soia-open-cwork-office-skills
  soia-open-dev-coding-skills
  soia-open-dev-design-skills
  soia-open-dev-product-skills
  soia-open-dev-release-skills
  soia-open-dev-testing-skills
  soia-open-edu-course-skills
  soia-open-env-skills
  soia-open-media-content-skills
  soia-open-pkm-clip-skills
  soia-open-pkm-vault-skills
  soia-open-skills
)
for repo in "${repos[@]}"; do
  npx skills add "soia-team/$repo" -g -a '*' -s '*' -y
done
```

All global content lands in `~/.agents/skills`. Updates, synchronization, and host entries should reuse that source instead of maintaining copied skill directories.

### Step 2: cover hosts by capability

1. **Native, zero-sync coverage:** Zed, Cursor, GitHub Copilot CLI, Codex, Gemini CLI, and DeepCode read `~/.agents/skills` directly and work immediately after the base install.
2. **One-time symlink distribution:** Windsurf (`~/.codeium/windsurf/skills`), Trae (`~/.trae/skills`; `~/.trae-cn` for the CN edition), WorkBuddy, Kimi, OpenCode, qodercli, Antigravity CLI (`agy`), and similar hosts need entries from the shared source. This command covers the common target set:

   ```bash
   python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
     --source-dir ~/.agents/skills \
     --targets claude,codex,gemini,kimi,opencode,agy,qwen,soia,workbuddy
   ```

   `--targets` is explicit. Append `windsurf,trae,qoder` when those hosts are in use; for the Trae CN edition, append its expanded absolute path as a custom target.
3. **Optional plugin overlay:** Claude Code, Codex, Qwen Code, and qodercli can add marketplace installation for domain-level `enable` / `disable` switches:

   ```bash
   claude plugin marketplace add soia-team/soia-open-skills
   ```

   Do not index both an npx entry and a plugin copy of the same skills in one host. Exclude the npx entries for any domain managed as a plugin.

### Step 3: trim host indexes (optional)

- **RouterV1 core set:** Recommended for Claude; measured index reduction is about 60%. Keep high-frequency core skills directly available, persistently exclude long-tail skills from Claude, and load them when needed through [`soia-meta-find-skill`](../skills/soia-meta-find-skill/SKILL.md):

  ```bash
  python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
    --source-dir ~/.agents/skills \
    --targets claude \
    --exclude-skills soia-pkm-clip-douyin,soia-pkm-clip-rednote \
    --save-excludes
  ```

  Extend the exclusion list to match the selected core set. Later full syncs continue to honor the saved Claude exclusions.

- **Domain plugin switches:** Recommended for Claude Code, Codex, Qwen Code, and qodercli. Disable a clipping domain while coding and re-enable it for writing:

  ```bash
  claude plugin disable soia-pkm-clip
  claude plugin enable soia-pkm-clip
  ```

### Step 4: verify the full installation

```bash
npx skills ls -g
ls ~/.agents/skills | wc -l
readlink ~/.claude/skills/<skill-name>
```

The link should resolve to `~/.agents/skills/<skill-name>`. Use the corresponding host directory in the table for other symlink-based hosts.

### Mixed-install decision table

| Host | Base coverage | Symlink required | Trimming | Recommendation |
|---|---|---:|---|---|
| Claude Code | Distribute to `~/.claude/skills` | Yes | RouterV1 or domain plugins | Keep the core set direct and route the long tail |
| Codex | Native `~/.agents/skills` | No | Router or domain plugins | Use the full base directly; trim only when needed |
| Qwen Code | Distribute to `~/.qwen/skills` | Yes | Router or domain plugins | Add marketplace control when domain switches matter |
| Gemini CLI | Native `~/.agents/skills` | No | Router | Sync to `~/.gemini/skills` only if a separate entry is needed |
| Antigravity CLI (`agy`) | Distribute to `~/.gemini/antigravity-cli/skills` | Yes | Router | Run the `agy` target once |
| Kimi CLI | Distribute to `~/.kimi/skills` | Yes | Router | Restart the session after synchronization |
| OpenCode | Distribute to `~/.config/opencode/skill` | Yes | Router | Use the `opencode` target |
| DeepCode | Native `~/.agents/skills` | No | Router | No dedicated target is needed |
| WorkBuddy | Distribute to `~/.workbuddy/skills` | Yes | Router | Keep team machines on the shared source |
| qodercli | Distribute to `~/.qoder/skills` | Yes | Router or domain plugins | Use domain plugins for scenario-level switching |
| Cursor | Native `~/.agents/skills` | No | Router | The full base works immediately |
| Windsurf | Distribute to `~/.codeium/windsurf/skills` | Yes | Router | Use the `windsurf` target |
| GitHub Copilot CLI | Native `~/.agents/skills` | No | Router or host skill switches | Inspect and control individual skills with `/skills` |
| Zed | Native `~/.agents/skills` | No | Router | Start a new session after installation |
| Trae | Distribute to `~/.trae/skills`; also inspect `~/.trae-cn` | Yes | Router | Sync the directory for the installed edition |
| SOIA AI | Distribute to `~/.soia/skills` | Yes | Router | Use the `soia` target instead of copying |

### Common mixed-install profiles

The following profiles assume the 12-repository base installation from step 1 is complete.

**Claude Code + Codex + WorkBuddy for personal development**

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,workbuddy

python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude \
  --exclude-skills soia-pkm-clip-douyin,soia-pkm-clip-rednote \
  --save-excludes
```

Codex reads the shared source directly; only Claude Code and WorkBuddy need entries.

**Team WorkBuddy + qodercli**

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets workbuddy,qoder

readlink ~/.workbuddy/skills/soia-meta-find-skill
readlink ~/.qoder/skills/soia-meta-find-skill
```

**Complete coverage for all hosts**

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,qoder,copilot,cursor,agy,gemini,kimi,codex,opencode,windsurf,trae,qwen,soia,workbuddy

npx skills ls -g
ls ~/.agents/skills | wc -l
```

DeepCode and Zed continue to read the shared source directly.

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

Distribute the shared source into `~/.kimi/skills`, then restart the session:

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets kimi \
  --skills <skill-name>

kimi --skills-dir <skill-directory>
```

`--skills-dir` replaces auto-discovery for that run and can be repeated to select a subset. Verify the shared entry with `readlink ~/.kimi/skills/<skill-name>`.

### OpenCode

Distribute the shared source into `~/.config/opencode/skill`:

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets opencode \
  --skills <skill-name>
readlink ~/.config/opencode/skill/<skill-name>
```

Update or remove the shared source with npx, and restart OpenCode if the current session does not refresh.

### DeepCode

DeepCode reads the `~/.agents/skills` interoperability layer directly:

```bash
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y
```

DeepCode has no dedicated npx agent id. Verify with `ls ~/.agents/skills/<skill-name>/SKILL.md`, update with `npx skills update`, and restart the host if the current session does not refresh.

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
