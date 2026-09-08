# SOIA Skills Ecosystem — Learning Guide

[中文](learning-guide.md) · English

This document answers **how the system works**. The [install guide](install/README.en.md) answers **how to install it**. Read this first to build the mental model, then use that one to copy commands.

By the end you should be able to decide for yourself: whether a new need becomes a skill or a script, which repo it belongs in, which plugin to install, and where to look when a skill does not fire.

---

## 1. Five nouns, kept apart

The whole ecosystem has only five concepts. Confusing them is the source of most confusion.

| Noun | What it is | On disk | Consumed by |
|---|---|---|---|
| **Skill** | A directory with `SKILL.md` plus optional `scripts/`, `references/`, `templates/` | `skills/<name>/` in a repo | The agent |
| **Domain plugin** | A repo's outward packaging unit — all of that repo's skills | `.claude-plugin/plugin.json` at repo root | The host's plugin system |
| **Marketplace** | An index of plugins; one URL brings a batch | `.claude-plugin/marketplace.json` in the portal repo | `plugin marketplace add` |
| **Trigger** | Natural language in the `description` frontmatter of `SKILL.md` | frontmatter | The agent's routing decision |
| **Always-on cost** | Context consumed by a skill's name + description | — | Your context budget |

**In one sentence**: skills are atoms, domain plugins are the packaging, the marketplace is the shelf, triggers are the labels — and always-on cost is the shelf fee that drives every other design decision.

---

## 2. The whole ecosystem in one diagram

```text
Source of truth: 7 public domain repos, 85 skills (2026-09-08 snapshot)
        │
        │   routing/routing-manifest.json (machine-readable index, generated)
        ▼
Portal repo generator: scripts/generate_marketplaces.py
        │
        ├─→ .claude-plugin/marketplace.json    ← Claude Code / Qwen / agy
        ├─→ .agents/plugins/marketplace.json   ← Codex native
        │
        ▼
Host installs: one project-scoped skill by default; a domain plugin by explicit choice
        │
        ▼
You say "archive this page into my vault" → the agent matches soia-pkm-clip-web by description
```

Three rules run through the whole picture:

1. **One source, many derived faces.** All three marketplace manifests are generated from repo content; CI runs `--check` and turns red on hand edits. This is what keeps the manifests from drifting apart.
2. **Domain repo = domain plugin = unit of on/off.** `plugin disable soia-pkm-vault@soia` removes 31 vault skills from the index at zero context cost; `enable` brings them back on a writing day.
3. **Pin the sha on release channels.** Cross-repo entries lock a released commit. The portal's self-reference, `source: "./"`, uses its released default `main` branch; it does not have a separate pin.

Use the [generated catalog](skills/README.md) for current counts: 84 routing targets plus the `soia-meta-find-skill` discovery entry point. The dev-design methods and tools now live in dev; the old repo retains history only.

---

## 3. Why many repos and domain plugins, instead of one big repo

Because **always-on cost has to be scoped by domain**.

A skill's body (`SKILL.md` content, `references/`, `scripts/`) only enters context once triggered — but name + description are **always on**. As long as a skill sits in the index, every turn pays for it. Official budgets: Claude reserves roughly 1% of context for the skill list and truncates descriptions at 1536 characters; Codex reserves roughly 2% or 8000 characters.

So the real design constraint is: **how do you pay only for the domains you need today?**

**Source-repo boundaries do not determine single-skill installation boundaries.** Even one repo supports selecting an individual skill with `npx skills add ... -s <skill-name>`. The 7 public domain repos separate maintenance responsibilities and whole-domain plugin distribution. Dev-design is now part of dev, not an eighth active domain. Select the skills a project actually needs first; use domain plugins when you want whole-domain toggling.

Corollary: **which repo a new skill belongs in depends on what it gets switched on together with**, not on code similarity.

---

## 4. Installation granularity and the default choice

The [root README installation section](../README.en.md#install) is the canonical scope policy. Public distribution and a user's local installation granularity are separate choices; a maintainer's local directories do not prove every user's installation state.

| Choice | Delivery | Boundary |
|---|---|---|
| Default | One project-scoped skill for a selected host | Install only capability needed for the task |
| Explicit choice | User-global, multiple hosts, domain plugins, or a full install | Confirm the affected scope before installation or synchronization |

**Avoid duplicate indexes; global scope itself is still supported.** A directory install and a plugin can expose the same skill twice on one host, with independently updated copies that drift. Inspect existing sources before installing.

Choose one effective source per skill per host. Project skill content normally lives under `<project>/.agents/skills`; `~/.agents/skills` is for global scope. Verify host links and plugin caches through the actual loader rather than equating directory presence with a successful trigger.

For example, from the target project, install one web-archiving skill for Codex:

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -a codex -s soia-pkm-clip-web
```

Replace `-a` for another host; add `-g` only after choosing global scope. Record publication, installation, and real-task verification separately. Publishing does not automatically update local skills.

---

## 5. On-demand loading: four layers

This is the core problem the architecture solves, handled in four layers from coarse to fine:

| Layer | Mechanism | Status |
|---|---|---|
| 1. Resident core | Description slimming; `audit_skills.py --strict` caps new skills at 150 characters | ✅ Live, enforced in CI |
| 2. Domain toggle | `plugin enable/disable` (Claude/Qwen/agy); marketplace level on Codex; expert summoning on WorkBuddy | ✅ Live |
| 3. Machine profiles | [install-profiles.md](install-profiles.md) — four scenarios (writing / coding / education / minimal) | ✅ Published |
| 4. Long-tail routing | `soia-meta-find-skill` searches SOIA first; use `find-skills` for the public ecosystem only when no candidate exists | ✅ Enabled |

Layer 4's cost must be stated plainly: **routing gives up direct trigger matching**. A routed skill is not in the index, so the agent will not match it automatically — you look it up and install it first. That makes it suitable only for low-frequency long tail; high-frequency capability must stay in layer 1.

---

## 6. How each host loads skills

Hosts fall into two classes, and the class determines which layer of switch you get.

**With a plugin layer** (domain-level toggling available):

| Host | Loading mechanism | Toggle |
|---|---|---|
| Claude Code | name+description index; body loaded on demand | `plugin enable/disable`, zero context cost |
| Codex | Scans `.agents/skills` from the working directory to the Git root, plus user/admin/system sources; follows skill symlinks | Local skills can be disabled with `skills.config`; plugins use the host's controls |
| Qwen | Consumes the Claude marketplace format natively (auto-converted) | Extension-level toggle plus scope |
| agy | `plugin import claude` channel | plugin enable/disable |
| WorkBuddy | Expert plugins carry their own skill sets | Summon / switch expert |

**Without a plugin layer** (only directory contents can be changed): Kimi (`--skills-dir` explicit subset — the most thorough), OpenCode, DeepCode, Gemini CLI. For these, use `soia-meta-sync-skills` with the `--skills` allowlist and `--exclude-skills` to add and remove at the directory level.

WorkBuddy is a special case worth calling out: its unit of on/off is not a plugin but an
**expert** — a role-based agent preset that carries its own persona and skill set, and is not
in context until summoned. This is the ecosystem's third distribution face, alongside the two
marketplace manifests, derived from each domain repo's `.codebuddy-plugin/plugin.json`. The
granularity rule is unchanged: one repo, one expert.

Two differences from Claude and Codex matter before you install: there is **no sha-pinned
remote-repo layer** (a marketplace entry's `source` must be a path string), and custom experts
are only detected in a **hardcoded `my-experts` directory**. So installation means placing a
checkout of the domain repo in that directory — the equivalent of the clone Claude and Codex
each keep in their own plugin cache. See the [WorkBuddy install guide](install/workbuddy.md).

Per-host commands live in the [install guide's host pages](install/README.en.md). See [official Codex skills documentation](https://developers.openai.com/codex/skills#where-to-save-skills) for discovery boundaries and controls; a shared directory outside the Git root is not automatically visible merely because it is a parent directory.

---

## 7. Frontmatter: seven fields and the Codex fold

SOIA skills use seven frontmatter fields (`name`, `description`, `version`, `created_at`, `updated_at`, `created_by`, `updated_by`), but Codex's official `quick_validate.py` only accepts a five-key allowlist (`name`, `description`, `license`, `allowed-tools`, `metadata`).

**This is solved in a layer, not by changing the source of truth**:

- The ecosystem source keeps all seven fields; do not rewrite every skill to satisfy one helper validator.
- The release pipeline folds the extra fields into `metadata:` when producing a Codex package — `metadata` is an allowlisted key whose interior shape is not checked, and OpenAI itself uses `metadata.short-description`.

Measured behavior at three layers: **the runtime tolerates all seven fields** (it even loads a Chinese `name`), **plugin packaging ingestion tolerates unknown keys**, and only skill-creator's validator rejects them. The conflict surface is much smaller than it appears.

---

## 8. Supply-chain security baseline

Skills are plain text, and plain text can still be poisoned — social-engineer the agent into running an install command. Real incidents: the postmark-mcp backdoor, mcp-remote CVE-2025-6514 (RCE), the Shai-Hulud npm worm, and 11.9% of ClawHub's 2857 skills found malicious.

Eight baseline rules:

1. Release-channel marketplace entries always pin a `sha`; only dev channels follow a branch.
2. No `@latest` in MCP registration — pin exact versions.
3. Run one read-only review before publishing a skill (`soia-dev-review-code`), and diff the descriptions of approved MCP servers across versions to catch rug-pulls.
4. Least privilege: narrow `allowed-tools` in frontmatter.
5. Leave third-party marketplace auto-update off (the default).
6. Sandbox untrusted stdio servers; remote servers over HTTPS + OAuth only.
7. Plaintext key hygiene: AI config files (`models.json`, `opencode.json`, and friends) commonly hold API keys in cleartext — move them to Keychain or environment variables.
8. Two-layer redaction gates cover private → open-source content extraction.

Full policy in [SECURITY.md](../SECURITY.md).

---

## 9. Frequently asked

**Q: When a plugin is enabled, do all its skills enter the index, or are they loaded on demand?**
All of the plugin's skills enter the index — that is where always-on cost comes from. But **triggering is still per skill**: either an automatic description match, or `/plugin-name:skill-name` manually. `disable` removes the whole domain at zero context cost.

**Q: What is `routing-manifest.json` for?**
It is the machine-readable skill → repo → path index used by `soia-meta-find-skill`, duplicate-name CI checks, cross-repo dependencies, and marketplace/document derivation. Check it against `SKILL.md` and released content; an index match is not proof of installation or verified capability.

**Q: Why can't a `skills` array in `plugin.json` expose only a subset?**
Neither host allows it, for different reasons. **Codex**: the official validator requires `skills` to be a string that normalizes to exactly `"skills"`; an array is rejected outright. **Claude**: the official field table states `skills` **adds to** the default `skills/` scan — while `commands`, `agents`, and `workflows` in the same table all say "replaces". Testing confirms the array is a no-op. **Only directory separation actually splits plugin content** — to ship several plugins from one repo, each plugin root needs its own directory (with its own `skills/` and `.claude-plugin/plugin.json`), not a subset listed in the manifest.

**Q: A skill did not fire — how do I diagnose it?**
In order: (1) is it visible in the actual skill catalog for this project and host, checking directory and plugin installs separately; (2) are its source, version, enabled state, and link target correct; (3) does the description match the natural request; (4) do project/user directories or plugins duplicate it? Then run a real input in a fresh project session, recording visibility, selection, full-instruction loading, and execution separately. A manual file read or one success does not establish natural trigger reliability.

**Q: `plugin update` says "already at the latest version" but I changed the code.**
Claude Code compares the `version` field in `plugin.json`, **not the sha**. Change content without bumping the version and the client sees nothing. Release flow in [plugin-dev.md](plugin-dev.md).

**Q: How do I publish skills that are not public?**
Make the repo a **self-referencing marketplace** (`source: "./"`) backed by your local `gh` credentials — only repo collaborators can install it, and it never appears in a public manifest. The generators derive manifests from public repos only, so non-public content never reaches a public artifact.

---

## 10. What to read next

| What you want to do | Where |
|---|---|
| Install skills into an AI tool | [Install guide](install/README.en.md) |
| Pick domains by scenario | [install-profiles.md](install-profiles.md) |
| Write a new skill | [SKILL_SPEC.md](../SKILL_SPEC.md) |
| Publish after changing a skill | [plugin-dev.md](plugin-dev.md) · [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Where skills store data | [DATA_STORAGE_SPEC.md](../DATA_STORAGE_SPEC.md) |
| Security boundaries and redaction | [SECURITY.md](../SECURITY.md) |
