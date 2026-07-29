# SOIA Skills

[中文](README.md) · English

AI workflow skills packaged by domain — 74 skills across development, knowledge vaults, social content, collaborative office, design docs, courses, and environment setup. Install as plugins, enable what you need.

## What this is

A "skill" is a written procedure that tells an AI **how to do one specific thing** — steps, boundaries, acceptance criteria, and the traps already discovered. It is not a prompt template; it is a versioned, testable, composable engineering artifact.

This repository is the ecosystem **portal**: specifications, cross-repo navigation, the marketplace manifest, and four meta skills that manage the ecosystem itself. **Domain skills live in their own repositories** and are distributed through the plugin marketplace.

```text
soia-open-skills (you are here)
    ├── Specs      SKILL_SPEC.md · DATA_STORAGE_SPEC.md · CONTRIBUTING.md
    ├── Market     register once, install any of 8 domain plugins
    └── Meta       search, sync, release, prompt drafting
                    ↓
        7 domain repos (dev · pkm-vault · media · cwork · design · edu · env)
```

### When to use it

- "I want AI to fix this code, but it keeps saying 'should be fine' and calling it done."
- "My clipped articles are scattered everywhere; I want one searchable local vault."
- "After writing a piece I have to reformat it for WeChat, X, and Rednote separately."
- "Team material is locked inside Feishu and ProcessOn; I want local files."
- "Setting up a new machine with a dozen AI CLIs goes wrong every time."

### What it does not do

- Not an AI client. It extends the Claude Code / Codex you already use rather than replacing them.
- Does not host your data. Everything stays on your machine; the skills only supply the method.
- Does not store credentials. Platform sessions stay in their official flows — never in the repo or logs.
- No internal company process. Industry-specific requirement, test, and release standards live in private repos.

## Where to start

**First time — two commands:**

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

```bash
claude plugin install soia-meta@soia
```

Then just say "**find me a skill**". `soia-meta-find-skill` searches all 74 skills against your need and tells you which plugin to install — no need to read the table below first.

**Already know what you want — install that domain directly:**

| What you want to do | Install | Skills | Always-on cost |
|---|---|---|---|
| Write code, review code, manage PRs | `soia-dev` | 12 | ~971 tok |
| Build a vault: clip, organize, transform | `soia-pkm-vault` | 26 | ~2.8k tok |
| Set up a machine, install AI CLIs, diagnose the network | `soia-env` | 15 | ~1.5k tok |
| Write articles, generate imagery, publish everywhere | `soia-media-content` | 6 | ~691 tok |
| PRDs, prototypes, architecture diagrams, Office files | `soia-dev-design` | 6 | ~548 tok |
| Export material from Feishu and ProcessOn | `soia-cwork-office` | 3 | ~309 tok |
| Course outlines and lesson plans | `soia-edu-course` | 2 | ~140 tok |
| Manage the skill ecosystem itself | `soia-meta` | 4 | ~396 tok |

> **Always-on cost** is the context that plugin's skill index consumes in every session; skill bodies load only when a skill is actually triggered.
> Turn off a domain you are not using with `claude plugin disable <plugin>` — the cost drops to zero and comes back instantly.

Codex users: swap `claude` for `codex` and `install` for `add`; everything else is identical.
For the other 60+ hosts (Cursor, Zed, Windsurf, …) see the [install guide](docs/install/README.md);
for setups organized by machine purpose see [install-profiles.md](docs/install-profiles.md).

## Ecosystem

| Repository | Responsibility | Plugin |
|---|---|---|
| [soia-open-skills](https://github.com/soia-team/soia-open-skills) | Portal, specifications, marketplace manifest, meta skills | `soia-meta` |
| [soia-open-dev-skills](https://github.com/soia-team/soia-open-dev-skills) | Engineering contracts: task execution, fix loops, review, GitHub ops | `soia-dev` |
| [soia-open-dev-design-skills](https://github.com/soia-team/soia-open-dev-design-skills) | Design and document pipeline: PRDs, prototypes, diagrams, Office | `soia-dev-design` |
| [soia-open-pkm-vault-skills](https://github.com/soia-team/soia-open-pkm-vault-skills) | Full vault lifecycle: capture, organize, distill, transform | `soia-pkm-vault` |
| [soia-open-media-content-skills](https://github.com/soia-team/soia-open-media-content-skills) | Last mile of content: drafting, imagery, per-platform publishing | `soia-media-content` |
| [soia-open-cwork-office-skills](https://github.com/soia-team/soia-open-cwork-office-skills) | Export SaaS-locked material into local files | `soia-cwork-office` |
| [soia-open-edu-course-skills](https://github.com/soia-team/soia-open-edu-course-skills) | Course outline and lesson plan design | `soia-edu-course` |
| [soia-open-env-skills](https://github.com/soia-team/soia-open-env-skills) | Environment readiness: network diagnosis, runtimes, AI CLI installs | `soia-env` |

The machine-readable catalog of every skill is in [routing-manifest.json](routing/routing-manifest.json).

## Skills in this repository

| Skill | Responsibility |
|---|---|
| [`soia-meta-find-skill`](skills/soia-meta-find-skill/) | Search the whole ecosystem by need and load the right skill — no need to know its name. |
| [`soia-meta-skill-release`](skills/soia-meta-skill-release/) | After a skill change merges, publish to the marketplace, update clients, reclaim caches. |
| [`soia-meta-sync-skills`](skills/soia-meta-sync-skills/) | Symlink a shared skill source into the AI tool directories you explicitly choose. |
| [`soia-meta-prompt-clarity`](skills/soia-meta-prompt-clarity/) | Draft, diagnose, and specify prompts in Chinese or English, preserving intent and safety boundaries. |

## Specifications

| Document | Covers |
|---|---|
| [SKILL_SPEC.md](SKILL_SPEC.md) | Skill structure, naming, frontmatter, and validation requirements |
| [DATA_STORAGE_SPEC.md](DATA_STORAGE_SPEC.md) | Boundaries for config, credentials, state, cache, and output |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributor guide plus the maintainer handbook |
| [docs/install/](docs/install/README.md) | Install guides for 60+ AI hosts |
| [docs/plugin-dev.md](docs/plugin-dev.md) | Local plugin iteration and the portal refresh after a domain release |

## License

[MIT](LICENSE)
