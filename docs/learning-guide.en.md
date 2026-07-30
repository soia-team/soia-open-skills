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
Source of truth: 10 Git repos, 100 skills (74 open + 26 private)
        │
        │   routing/routing-manifest.json (machine-readable index, generated)
        ▼
Portal repo generator: scripts/generate_marketplaces.py
        │
        ├─→ .claude-plugin/marketplace.json    ← Claude Code / Qwen / agy
        ├─→ .agents/plugins/marketplace.json   ← Codex native
        └─→ Self-referencing private marketplaces (source: "./", local gh credentials)
        │
        ▼
Host installs: claude plugin install soia-pkm-vault@soia
        │
        ▼
You say "archive this page into my vault" → the agent matches soia-pkm-clip-web by description
```

Three rules run through the whole picture:

1. **One source, many derived faces.** All three marketplace manifests are generated from repo content; CI runs `--check` and turns red on hand edits. This is what keeps the manifests from drifting apart.
2. **Domain repo = domain plugin = unit of on/off.** `plugin disable soia-pkm-vault@soia` removes 26 vault skills from the index at zero context cost; `enable` brings them back on a writing day.
3. **Pin the sha on release channels.** Marketplace entries lock a commit so an upstream ref cannot be moved to different content. This is a supply-chain baseline, not fussiness.

---

## 3. Why many repos and domain plugins, instead of one big repo

Because **always-on cost has to be scoped by domain**.

A skill's body (`SKILL.md` content, `references/`, `scripts/`) only enters context once triggered — but name + description are **always on**. As long as a skill sits in the index, every turn pays for it. Official budgets: Claude reserves roughly 1% of context for the skill list and truncates descriptions at 1536 characters; Codex reserves roughly 2% or 8000 characters.

So the real design constraint is: **how do you pay only for the domains you need today?**

One big repo cannot do that — installing it means installing everything. Split by domain, "writing today" needs only `soia-media-content` plus `soia-pkm-vault`, and the entire coding domain stays out of the index. That is why 12 repos were consolidated to 8 but deliberately not merged into 1: **repo boundaries are the granularity of the on/off switch.**

Corollary: **which repo a new skill belongs in depends on what it gets switched on together with**, not on code similarity.

---

## 4. How delivery evolved (and what is now deprecated)

This section matters more than the rest — older docs and commands are still circulating, and following them causes real problems.

| Era | Delivery | Status |
|---|---|---|
| Early | `npx skills add ... -g` into the shared source `~/.agents/skills`, symlinked into each host | **Deprecated — an anti-pattern** |
| Now | Plugin marketplaces, install and toggle at domain granularity | The one recommended route |

**Why `-g` global install was deprecated**: if the same skill arrives both via npx into `~/.agents/skills` and via a plugin, the host sees **two index entries**, and the two copies update independently and drift. You cannot tell which one fired.

So the rule is **pick one**. The local state confirms the migration is complete: `~/.agents/skills` now holds only third-party skills (`find-skills`, `weread-skills`, and similar) — **no SOIA skills at all**. SOIA delivery is 100% plugin-based.

The `npx` route still works and is a reasonable choice when you want **a single skill**, as long as you know where it lands:

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-clip-web -y
```

If you use it, do not also install that skill's domain plugin.

---

## 5. On-demand loading: four layers

This is the core problem the architecture solves, handled in four layers from coarse to fine:

| Layer | Mechanism | Status |
|---|---|---|
| 1. Resident core | Description slimming; `audit_skills.py --strict` caps new skills at 150 characters | ✅ Live, enforced in CI |
| 2. Domain toggle | `plugin enable/disable` (Claude/Qwen/agy); marketplace level on Codex; expert summoning on WorkBuddy | ✅ Live |
| 3. Machine profiles | [install-profiles.md](install-profiles.md) — four scenarios (writing / coding / education / minimal) | ✅ Published |
| 4. Long-tail routing | `find-skills` for public skills plus `routing-manifest.json` as fallback | ✅ Enabled |

Layer 4's cost must be stated plainly: **routing gives up direct trigger matching**. A routed skill is not in the index, so the agent will not match it automatically — you look it up and install it first. That makes it suitable only for low-frequency long tail; high-frequency capability must stay in layer 1.

---

## 6. How each host loads skills

Hosts fall into two classes, and the class determines which layer of switch you get.

**With a plugin layer** (domain-level toggling available):

| Host | Loading mechanism | Toggle |
|---|---|---|
| Claude Code | name+description index; body loaded on demand | `plugin enable/disable`, zero context cost |
| Codex | Five-level discovery chain including `$HOME/.agents/skills` | Marketplace-level enable; no per-skill switch |
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

Per-host commands live in the [install guide's host pages](install/README.en.md).

---

## 7. Frontmatter: seven fields and the Codex fold

SOIA skills use seven frontmatter fields (`name`, `description`, `version`, `created_at`, `updated_at`, `created_by`, `updated_by`), but Codex's official `quick_validate.py` only accepts a five-key allowlist (`name`, `description`, `license`, `allowed-tools`, `metadata`).

**This is solved in a layer, not by changing the source of truth**:

- The ecosystem source keeps all seven fields (zero churn; 88+ skills do not get rewritten).
- The release pipeline folds the extra fields into `metadata:` when producing a Codex package — `metadata` is an allowlisted key whose interior shape is not checked, and OpenAI itself uses `metadata.short-description`.

Measured behavior at three layers: **the runtime tolerates all seven fields** (it even loads a Chinese `name`), **plugin packaging ingestion tolerates unknown keys**, and only skill-creator's validator rejects them. The conflict surface is much smaller than it appears.

---

## 8. Supply-chain security baseline

Skills are plain text, and plain text can still be poisoned — social-engineer the agent into running an install command. Real incidents: the postmark-mcp backdoor, mcp-remote CVE-2025-6514 (RCE), the Shai-Hulud npm worm, and 11.9% of ClawHub's 2857 skills found malicious.

Eight baseline rules:

1. Release-channel marketplace entries always pin a `sha`; only dev channels follow a branch.
2. No `@latest` in MCP registration — pin exact versions.
3. Full review before publishing a skill (`soia-dev-review-panel`), and diff the descriptions of approved MCP servers across versions to catch rug-pulls.
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
It is the machine-readable source of truth mapping skill → repo → path, serving five purposes: (1) `find-skills` routing queries, (2) ecosystem-wide duplicate-name CI checks, (3) cross-repo hard-dependency closure, (4) the data source for the marketplace generator, (5) install-doc generation. CI regenerates it after any repo publishes.

**Q: Why can't a `skills` array in `plugin.json` expose only a subset?**
Neither host allows it, for different reasons. **Codex**: the official validator requires `skills` to be a string that normalizes to exactly `"skills"`; an array is rejected outright. **Claude**: the official field table states `skills` **adds to** the default `skills/` scan — while `commands`, `agents`, and `workflows` in the same table all say "replaces". Testing confirms the array is a no-op. **Only directory separation actually splits plugin content**, which is how `soia-private-skills` serves three plugins from one repo (`skills/`, `workspace/skills/`, `harness/skills/`).

**Q: A skill did not fire — how do I diagnose it?**
In order: (1) is the plugin installed (`claude plugin list`), (2) is it enabled, (3) do the triggers in its description match what you actually said, (4) does the same skill exist twice (npx and plugin side by side). Item 4 is the sneakiest — check `~/.agents/skills` for a directory of the same name.

**Q: `plugin update` says "already at the latest version" but I changed the code.**
Claude Code compares the `version` field in `plugin.json`, **not the sha**. Change content without bumping the version and the client sees nothing. Release flow in [plugin-dev.md](plugin-dev.md).

**Q: How are private repos distributed?**
The two private repos host **self-referencing marketplaces** (`source: "./"`) that use your local `gh` credentials, so only repo-authorized users can install them. No private entry appears in any public manifest.

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
