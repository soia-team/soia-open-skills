# SOIA Skills Installation Guide

[中文](README.md) · [Installation profiles](../install-profiles.md)

As of 2026-07-25, the eight public SOIA repositories contain 73 skills. There are two independent installation routes.

## Two installation routes

| | Route A: `npx skills` | Route B: plugin marketplace |
|---|---|---|
| Hosts | All supported hosts | Claude Code, Codex, Qwen Code, and qodercli |
| Granularity | One skill or all skills in a repository | One domain plugin |
| Skill location | Always starts in `~/.agents/skills` | Host-specific plugin cache; never `~/.agents/skills` |
| Host selection | `-a` only selects which host entries are linked | Managed by the host plugin system |
| Best for | Cross-host use and skill-level selection | Domain-level installation and switching |

### What `-a` actually does

This command does not install only into Claude Code:

```bash
npx skills add soia-team/<repository> -g \
  -a claude-code -s <skill-name> -y
```

The skill body always lands in `~/.agents/skills` first. `-a claude-code` only controls the host entry. `-a '*'` creates entries for all supported agents.

`--copy` changes a selected host entry from a symlink to a physical copy, but the global body still exists. It is effective for the Claude Code entry. Codex reads the global directory directly, so `--copy` does not change the Codex read path.

### What plugins do

Plugins are installed into host-specific caches:

- Claude Code: `~/.claude/plugins/cache/<marketplace>/<plugin>/<sha>/`
- Codex: `~/.codex/plugins/cache/<marketplace>/<plugin>/`

Claude Code's npx and plugin paths are independent. Codex plugins are an **overlay** on top of `~/.agents/skills`, not a replacement. Installing or removing a Codex plugin never reduces the global skill index.

## Which route should I use?

| Need | Route |
|---|---|
| Use skills in several AI hosts | A |
| Install a small skill set | A with `-s <skill-name>` |
| Install every skill for every supported agent | A with `--all --full-depth` |
| Switch complete domains in Claude Code | B |
| Commit a shared Claude plugin selection to a project | B with `--scope project` |
| Reduce Codex's global index with plugins | Not possible; Codex plugins only add an overlay |
| Use a host outside Claude/Codex/Qwen/qoder | A |

## Route A: npx

```bash
npx skills add soia-team/<repository> -g \
  -a '*' -s <skill-name> -y
```

Selected host entries:

```bash
npx skills add soia-team/<repository> -g \
  -a claude-code codex cursor -s <skill-name> -y
```

Common agent ids include `claude-code`, `codex`, `cursor`, `windsurf`, `qwen`, `kimi`, `opencode`, `copilot`, `qoder`, `trae`, `agy`, `gemini`, and `zed`.

Install all skills for all agents:

```bash
npx skills add soia-team/<repository> -g --all --full-depth
```

Manage installations:

```bash
npx skills ls -g
npx skills ls -g -a claude-code --json
npx skills update -g
npx skills remove -g -a '*' -s <skill-name> -y
npx skills find <keyword>
npx skills use soia-team/<repository>@<skill-name>
```

`skills use` generates a prompt without installing the skill.

## Route B: plugin marketplaces

The eight domain plugins are:

```text
soia-dev
soia-dev-design
soia-cwork-office
soia-pkm-vault
soia-media-content
soia-edu-course
soia-env
soia-meta
```

Claude Code:

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install soia-pkm-vault@soia --scope user
```

Codex:

```bash
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add soia-pkm-vault@soia
```

Claude has `user`, `project`, and `local` plugin scopes. A project-scoped selection is stored in `.claude/settings.json` for version-controlled team sharing; local project selection uses `.claude/settings.local.json`. See the [Claude Code host guide](hosts.en.md#claude-code).

Codex records marketplaces and plugins in `~/.codex/config.toml` and stores plugin content in its own cache. The global `~/.agents/skills` index remains active. See the [Codex host guide](hosts.en.md#codex).

## Host read mechanisms

| Mechanism | Hosts |
|---|---|
| Read `~/.agents/skills` directly | Codex, Zed, Cursor, Copilot, Gemini, DeepCode |
| Read an independent skill directory | Claude Code |
| Require a synchronized host entry | Windsurf, Trae, WorkBuddy, Kimi, OpenCode, qodercli |
| Use the matching npx agent entry | Qwen Code, Antigravity (`agy`) |

## Host guides

| Host | Agent id / route | Guide |
|---|---|---|
| Claude Code | `claude-code`; plugins supported | [Guide](hosts.en.md#claude-code) |
| Codex | `codex`; global read plus plugin overlay | [Guide](hosts.en.md#codex) |
| Qwen Code | `qwen`; plugins supported | [Guide](hosts.en.md#qwen-code) |
| qodercli | `qoder`; plugins supported | [Guide](hosts.en.md#qodercli) |
| Cursor | `cursor`; direct global read | [Guide](hosts.en.md#cursor) |
| Windsurf | `windsurf` | [Guide](hosts.en.md#windsurf) |
| GitHub Copilot | `copilot`; direct global read | [Guide](hosts.en.md#github-copilot) |
| Zed | `zed`; direct global read | [Guide](hosts.en.md#zed) |
| Gemini CLI | `gemini`; direct global read | [Guide](hosts.en.md#gemini-cli) |
| Antigravity | `agy` | [Guide](hosts.en.md#antigravity-agy) |
| Kimi CLI | `kimi` | [Guide](hosts.en.md#kimi-cli) |
| OpenCode | `opencode` | [Guide](hosts.en.md#opencode) |
| DeepCode | direct global read | [Guide](hosts.en.md#deepcode) |
| WorkBuddy | sync entry | [Guide](hosts.en.md#workbuddy) |
| Trae | `trae` | [Guide](hosts.en.md#trae) |
| SOIA AI | host configuration | [Guide](hosts.en.md#soia-ai) |

## Verification

Check the global body first:

```bash
test -f ~/.agents/skills/<skill-name>/SKILL.md
npx skills ls -g
```

Then inspect the host entry when the host does not read the global directory directly. Start a new host session if an existing session has not refreshed.
