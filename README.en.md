<div align="center">

# soia-open-skills

[中文](README.md) | English

> *Turn "saved" into "made" — a personal knowledge management skill system for the AI era.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

<br>

**A `soia-pkm-*` personal knowledge-management skill set for Obsidian + `soia-cwork-*` enterprise collaboration connectors + publicly reusable `soia-dev-*` dev helpers**

```bash
npx skills add soia-team/soia-open-skills
```

Agent-agnostic — works with Claude Code, Cursor, Codex, Antigravity, Gemini, Kimi, and any [skills.sh](https://skills.sh)-compatible agent.

[The loop](#pkm-loop-the-life-of-a-piece-of-content) · [Skills catalog](#skills-catalog) · [CWork · enterprise collaboration](#-cwork--enterprise-collaboration) · [Frequently used skills](#frequently-used-skills) · [Installation](#installation) · [Telegram sync](#telegram-saved-messages-sync-clip-x) · [Design philosophy](#design-philosophy)

</div>

---

## PKM loop: the life of a piece of content

```
                     soia-pkm personal knowledge management loop

  Collect ──────→ Organize ─────→ Distill ─────→ Compose ─────→ Publish
 ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
 │ clip-x  │  │         │  │         │  │         │  │         │
 │ clip-   │  │organize │  │ distill │  │ compose │  │ publish │
 │  wechat │─→│ classify│─→│saved →  │─→│ opinion │─→│ WeChat  │
 │ clip-web│  │ /MOC/   │  │ opinion │  │ → draft │  │/X/RedNote│
 │ clip-   │  │ file/   │  │ (your   │  │         │  │         │
 │  drive  │  │ backlink│  │ take)   │  │         │  │         │
 └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
   multi-source input                                        │
      ↑                                                       ▼
      └──── flywheel: publish → feedback into vault → better input ────┘

  Support: soia-pkm-bootstrap (one command to bootstrap a vault + wire up multiple AIs)
           soia-pkm-transform (transform line: article → PDF/PPT/image/quiz/mindmap/podcast/flashcards)
           soia-pkm-reading-plan (reading line: turn a book list into an executable reading schedule)
           soia-pkm-library (library line: WeChat Reading sync + record backfill + overview generation)
           soia-pkm-alipan (cloud drive line · atomic layer: reliable atomic operations via the aliyunpan CLI)
           soia-pkm-alipan-curator (cloud drive line · advisor layer: inventory/organize/catalog/study plans)
           soia-dev-archify-diagrams (doc diagram line: Archify JSON IR → README/docs PNG diagrams)
           soia-dev-github-ops / soia-dev-ai-cli-upgrade (shared dev-tooling line)
           soia-cwork-feishu-cli (enterprise collaboration line: read-only Feishu CLI research across drives, docs, and wikis)
```

**Core idea**: saving ≠ absorbing. Most people's knowledge bases are "information graveyards" — piled high, never revisited. `soia-pkm` breaks the chain from "save → opinion → draft → publish" — the path **from consumption to creation** — into single-purpose, composable skills, so AI helps you turn hoarded information into work that is genuinely **yours**.

---

## Skills catalog

> **Shared capabilities (common to every skill)**
> - 🤖 **Supported AI**: agent-agnostic — Claude Code, Codex, Cursor, Antigravity, Gemini, Kimi, amp, Warp, Zed, and any AI compatible with the [skills.sh](https://skills.sh) standard. Write `SKILL.md` once, run it anywhere.
> - 📚 **Target knowledge base**: an Obsidian vault (PARA structure recommended; don't have one yet? use `bootstrap` to set one up in one shot). The underlying storage is plain Markdown + YAML frontmatter — no platform lock-in.
> - 🔗 **Dependency chain**: `clip-*` is the entry point (usable standalone) → `organize` / `distill` need content already in the vault → `compose` needs an opinion produced by `distill` → `publish` needs a draft produced by `compose`.
> - 🧩 **Third-party skill policy**: this repo's own skills only *declare* dependencies / optional enhancements / methodology references on third-party skills — it never modifies third-party skill files. The actual source of truth is `~/.agents/.skill-lock.json`.
> - **Status legend**: ✅ ready to use · 🟡 usable but needs a script filled in / credentials configured

### 📥 Collect · the clip family

Core value: bring content scattered across platforms into the vault with one command — this is the entry point of the whole loop. Without a reliable "collect" step, organizing, distilling, and composing have nothing to work with.

| Skill | What it does | Ready now? | Dependencies |
|-------|------|----------|------|
| [`soia-pkm-clip-x`](./skills/soia-pkm-clip-x/) | X tweets/threads/long-form → vault | ✅ Fully usable (scripts complete, field-tested repeatedly) | None (Telegram sync optional) |
| [`soia-pkm-clip-wechat`](./skills/soia-pkm-clip-wechat/) | WeChat Official Account articles → vault | ✅ Ready (stdlib fetch, quality gate, URL dedupe, dry-run, atomic write) | None |
| [`soia-pkm-clip-web`](./skills/soia-pkm-clip-web/) | Generic web pages/blogs → vault | 🟡 SKILL.md ready, fetch script pending | Python `trafilatura` |
| [`soia-pkm-clip-drive`](./skills/soia-pkm-clip-drive/) | Cloud-drive PDF/Word → vault | 🟡 SKILL.md ready, import script pending | Python `pypdf`/`python-docx` |
| [`soia-pkm-clip-repo`](./skills/soia-pkm-clip-repo/) | GitHub open-source repos → vault "open-source project library" index | ✅ Usable (scripts complete: single-repo archiving + bulk refresh) | None (needs one local upstream clone directory) |
| [`soia-pkm-clip-gzh`](./skills/soia-pkm-clip-gzh/) | Bulk-archive your own WeChat Official Account's published articles → vault | ✅ Usable (official API / logged-in cookie, two paths) | WeChat Official Account dev credentials or a logged-in cookie |

### 🗂️ Organize

Core value: turn a messy pile of saved content into structured, searchable, aggregatable knowledge — saving is not the same as absorbing, and organizing is the first step toward actually activating what you collected.

| Skill | What it does | Ready now? | Dependencies |
|-------|------|----------|------|
| [`soia-pkm-organize`](./skills/soia-pkm-organize/) | Classify / backfill frontmatter / build two-tier MOCs / file by month / add backlinks | ✅ Usable (underlying `rebuild_moc`/`backfill` scripts already in production) | Vault must already have archived content |

### ✍️ Distill → compose → publish

Core value: the real value-conversion stage of the loop — turning someone else's information into your own judgment, then turning that judgment into a publishable piece of writing. This is the line between "consuming" and "creating."

| Skill | What it does | Ready now? | Dependencies |
|-------|------|----------|------|
| [`soia-pkm-translate`](./skills/soia-pkm-translate/) | **Foreign-language article → Chinese version**: quick (literal) / normal (analyze style, terminology, and audience first, default) / refined (adds proofreading + polish); long articles are mechanically chunked to keep terminology consistent; output is an independent `-中文版.md`, never overwrites the original | ✅ Usable (all three modes + chunking script complete) | Python 3 (hard dependency, runs the chunking script); PyYAML optional enhancement |
| [`soia-pkm-interpret`](./skills/soia-pkm-interpret/) | **Saved content → AI reading**: a five-part structure (overview / key points / insights / critique / further reading) that helps you decide whether an article is worth distilling before you invest in `distill`; produces an independent `-AI解读.md`, never touches the original's "My Take" | ✅ Usable (pure LLM reading, no scripts needed) | No hard dependency (the `clip-*` family is a common upstream source) |
| [`soia-pkm-distill`](./skills/soia-pkm-distill/) | **Saved content → opinion**: read the source → ask one question at a time → you answer → "my take" (the content is yours, AI only writes it down) | ✅ Fully usable (battle-tested) | Articles already in the vault (produced by `clip-*`) |
| [`soia-pkm-compose`](./skills/soia-pkm-compose/) | **Opinion → article draft** (your opinion as the skeleton, excerpts as supporting material) | ✅ Usable (pure LLM, no scripts needed) | An opinion produced by `distill` |
| [`soia-pkm-cover-image`](./skills/soia-pkm-cover-image/) | Generates a cover image for WeChat/X/RedNote articles (five parameters: type/palette/rendering/text/mood); output feeds directly into `publish --cover` | ✅ Usable (backend is codex CLI's built-in image generation; stops and prompts if not installed/logged in — never degrades silently) | codex CLI (`codex exec`, must be logged in) |
| [`soia-pkm-publish`](./skills/soia-pkm-publish/) | **One draft → multiple platforms**: WeChat formatting + push to drafts / X thread / RedNote (Xiaohongshu) | 🟡 The `render.py` renderer is usable; WeChat push needs a private `config.yml` with credentials | A draft from `compose` + WeChat Official Account API |

### 🔁 Transform · article → artifacts

Core value: let the same piece of content fit different consumption contexts — feed in one source once, and route it on demand to PDF, PPT, long-form images, podcasts, and other media formats.

| Skill | What it does | Ready now? | Dependencies |
|-------|------|----------|------|
| [`soia-pkm-transform`](./skills/soia-pkm-transform/) | **Article → many artifacts**: PDF / PPT / long-form image / quiz / mindmap / podcast / flashcards / report; a shared routing layer that can optionally call Obsidian, NotebookLM, Codex's built-in document/image/PPT capabilities, and `publish` | ✅ Usable (routing skill + config templates; the actual artifact depends on the local provider) | A vault article or URL; NotebookLM / Obsidian / Codex built-in capabilities are optional, as needed |

### 🧰 Support

Core value: the infrastructure that keeps the loop running — bootstrapping the vault, maintaining the library, managing cloud storage, routine upkeep, and the dev tooling chain. None of these sit on the loop's main path, but the whole system depends on them.

| Skill | What it does | Ready now? | Dependencies |
|-------|------|----------|------|
| [`soia-pkm-bootstrap`](./skills/soia-pkm-bootstrap/) | Bootstrap an AI-native vault from scratch (PARA + AGENTS + templates + Bases + CSS + multi-AI wiring) | ✅ Usable (`init_vault.py` verified end to end) | None (this is the starting point) |
| [`soia-pkm-reading-plan`](./skills/soia-pkm-reading-plan/) | Scenario-based reading plans (book list/topic → scheduled by real word count) | ✅ Usable | `weread-skills` optionally enhances real word counts/ratings; `huashu-weread-advisor` optionally reuses its recommendation methodology; no hard third-party dependency |
| [`soia-pkm-library`](./skills/soia-pkm-library/) | Maintain the book library: WeChat Reading sync (catalog/highlights) + enrich book details + backfill reading records + generate three overview views (library/reading records/genre) | ✅ Usable (7 mechanical scripts, idempotent and safe to re-run) | Sync scripts hard-depend on the official `weread-skills` + `WEREAD_API_KEY`; local overview scripts only depend on the vault |
| [`soia-pkm-maintain`](./skills/soia-pkm-maintain/) | Weekly vault maintenance, full-vault map regeneration, AI session-log ingestion | ✅ Usable (Python stdlib / bash scripts) | An Obsidian vault, via `--vault <path>` or `OBSIDIAN_VAULT` |
| [`soia-pkm-alipan`](./skills/soia-pkm-alipan/) | Alibaba Cloud Drive atomic operations layer: login/switch between drives/browse/move/rename/upload/download/quota check, with output parsing and safety rules | ✅ Usable (no scripts needed, drives the `aliyunpan` CLI directly) | `aliyunpan` CLI (installed via brew + QR-code login) |
| [`soia-pkm-baidupan`](./skills/soia-pkm-baidupan/) | Baidu Netdisk atomic operations layer: official `baidu-drive` / `bdpan` by default, with an explicit community `baidupan-cli` mode and read-only JSONL scanning | ✅ Usable (private config selects the provider) | Official `baidu-drive` Skill or `mqhe2007/baidupan-cli` + Open Platform app |
| [`soia-pkm-alipan-curator`](./skills/soia-pkm-alipan-curator/) | Cloud-drive resource advisor: inventory checks / standardized organizing / cataloging into Obsidian / study plans for kids | ✅ Usable (pure methodology layer, all commands routed through alipan) | `soia-pkm-alipan` (atomic layer) |
| [`soia-dev-archify-diagrams`](./skills/soia-dev-archify-diagrams/) | Archify diagram workflow: architecture / data-flow / workflow / sequence / lifecycle diagrams, maintaining a JSON IR and exporting README/docs PNGs | ✅ Usable (scripts complete; requires a local Archify install) | `ARCHIFY_BIN` or `ARCHIFY_ROOT`, with optional Playwright/Chrome for PNG export |
| [`soia-dev-github-ops`](./skills/soia-dev-github-ops/) | GitHub operations workflow: issues / PRs / checks / reviews / run logs / releases, defaulting to structured `gh` queries with safety confirmation gates | ✅ Usable (no scripts; command templates already shared) | `gh` CLI logged in; target repo from `--repo` / the current git remote / `$GITHUB_REPOSITORY` |
| [`soia-dev-ai-cli-upgrade`](./skills/soia-dev-ai-cli-upgrade/) | Bulk inventory and upgrade of AI/dev CLIs: Codex / Claude / Antigravity (`agy`, consumer Google-login successor) / Gemini (enterprise, API Key, and Vertex only) / Kimi / Qwen / OpenCode / Cursor / qodercli / mmx | ✅ Usable (scripts complete; supports dry-run and logging) | Node/npm; some tools use an official installer, Homebrew, or their own updater |
| [`soia-dev-prompt-clarity`](./skills/soia-dev-prompt-clarity/) | General-purpose prompt-writing skill: draft from scratch with seven elements / diagnose & optimize on six dimensions / rewrite to avoid false-positive safety refusals / compile vague requirements into verifiable specs — four modes; asks clarifying questions first when information is insufficient | ✅ Usable (pure methodology output, no scripts, no hard third-party dependency) | None |
| [`soia-dev-agent-md-advisor`](./skills/soia-dev-agent-md-advisor/) | Design advisor for AGENTS.md / CLAUDE.md / `.claude` configuration: review & diagnose / draft for a new project / best-practice Q&A — three modes, with a six-dimension health check (length budget / actionability / section routing / duplication & contradiction / entry-point consistency / staleness) | ✅ Usable (pure methodology diagnosis, no scripts, no hard dependency) | None |
| [`soia-dev-agent-cli-dispatch`](./skills/soia-dev-agent-cli-dispatch/) | Controlled dispatch of tasks to external coding CLIs (codex/agy/gemini/kimi/opencode/qwen, etc.): task-boundary splitting, injection-resistant prompt patterns, a model-tiering matrix, and three-step Anti-Fake-Fix verification | ✅ Usable (command templates + tiering matrix complete) | The target coding CLI (codex/agy/gemini/kimi/opencode/qwen, etc., as needed), installed and logged in |

### 🏢 CWork · enterprise collaboration

`soia-cwork-*` targets enterprise work systems rather than an Obsidian vault. These skills connect to Feishu and other collaboration platforms to read and analyze work documents, cloud drives, knowledge bases, permissions, and metadata, and can mirror authorized work content into Git/Obsidian/VitePress. They default to read-only behavior; credentials, tenant scope, and resource authorization stay with the user.

| Skill | What it does | Ready now? | Dependencies |
|-------|------|----------|------|
| [`soia-cwork-feishu-cli`](./skills/soia-cwork-feishu-cli/) | Uses the official `lark-cli` with app credentials (bot identity) to inventory Feishu drives, cloud documents, wikis, comments, permissions, and metadata in read-only mode | ✅ Usable (configure Feishu app credentials and grant access to target resources) | Official Feishu `lark-cli`; app credentials; target docs/wikis must be visible to the app |
| [`soia-cwork-feishu-doc-git-sync`](./skills/soia-cwork-feishu-doc-git-sync/) | Mirrors a Feishu wiki by stable `node_token` while preserving hierarchy, using incremental Markdown sync for Git, Obsidian, and VitePress; event targets are optional and write-back is not enabled by default | ✅ Usable (run a dry-run and establish a baseline first; grant the target space document read scopes) | `soia-cwork-feishu-cli`; `lark-cli`; Python 3.10+; PyYAML; Git/VitePress/Obsidian optional |

#### Minimal Feishu setup

```bash
npx @larksuite/cli@latest install
npx skills add larksuite/cli -g -y
```

Then copy [`assets/config.example.yml`](./skills/soia-cwork-feishu-cli/assets/config.example.yml) to a private config path and fill in `LARK_APP_ID` / `LARK_APP_SECRET`. The app must enable bot capability, request the minimum tenant read-only scopes, configure app data permissions, and publish an app version before remote reads are considered ready.

- Permission source of truth: [`references/permissions.yml`](./skills/soia-cwork-feishu-cli/references/permissions.yml)
- Human-facing permission guide: [`references/permissions.md`](./skills/soia-cwork-feishu-cli/references/permissions.md)
- Permission page: `https://open.feishu.cn/app/<APP_ID>/auth`
- Default identity: app credentials with `tenant_access_token` / bot; no silent fallback to user OAuth
- Default boundary: read-only; no create, edit, delete, move, upload, or public sharing actions

### soia-cwork-feishu-doc-git-sync

Syncs a Feishu knowledge base into local Markdown so the same content can be backed up in Git and viewed in Obsidian or VitePress. The default direction is read-only “Feishu → local”; `10_knowledge-base/` is generated, while `20_本地补录/` is preserved for local additions.

```text
Mirror my Feishu wiki to Git/Obsidian/VitePress
Run a dry-run first, then sync after checking node counts, permissions, and output paths
```

See [`soia-cwork-feishu-doc-git-sync`](./skills/soia-cwork-feishu-doc-git-sync/) for the config template, permission layers, ID-based incremental flow, and event boundary. Bidirectional sync requires an explicit ownership model, conflict policy, and Feishu write scopes.

---

## Frequently used skills

A closer look at the 8 skills most often invoked directly in the loop, each with a minimal working example. Path placeholders in the commands are written as `<vault-path>`; substitute your own vault location.

### soia-pkm-clip-x

Archives X/Twitter tweets, threads, and X Articles into an Obsidian vault in one shot; built on the public fxtwitter API, so a single item needs zero configuration, with optional bulk sync from your Telegram "Saved Messages."

```bash
python3 archive_x.py <tweet-URL>
python3 archive_x.py <tweet-URL> --force                    # overwrite an existing archive
python3 archive_x.py <tweet-URL> --vault <vault-path>        # override the environment variable
python3 sync_telegram_export.py <telegram-export-json-path> --dry-run   # preview a bulk sync
```

**Typical output**: a new Markdown file appears under the vault's articles directory, with frontmatter filled in (author, publish date, topic backlinks, language tag) and `## My Take` left blank for you to fill in later.

### soia-pkm-organize

Organizes the messy backlog of saved content in a vault — backfilling frontmatter, classifying by topic with backlinks, rebuilding two-tier MOCs, and filing files by month.

```bash
python3 scripts/rebuild_moc.py --vault <vault-path>
python3 scripts/backfill_reading_records.py --vault <vault-path>
```

**Typical output**: the terminal reports how many articles were processed, which topics were backfilled, the MOC update status, and how many files were refiled.

### soia-pkm-distill

Distills a saved article into your own opinion: AI asks one question at a time, you answer out loud, and AI only organizes your answers into fluent first-person prose — it never makes the judgment call for you.

```text
Add my take to this article
Distill my overall view on the "Agent development" topic
```

**Typical output**: the article's `## My Take` section gets filled with a first-person opinion assembled from what you said out loud; in topic-aggregation mode, a synthesis draft is created in the drafts folder instead.

### soia-pkm-compose

Turns the opinion distilled by `distill` into a publishable draft, using your opinion as the skeleton and vault excerpts as supporting evidence.

```text
Turn these opinions into an article
Write an article on the "X" topic
```

**Typical output**: a new Markdown draft appears in the drafts folder with `tags:[draft]` frontmatter, along with an outline, a word count, and suggested edits.

### soia-pkm-publish

Adapts a finished draft and publishes it across platforms — WeChat Official Account (formatting + push to drafts), X threads, RedNote (Xiaohongshu) cards. WeChat is the primary flow: it renders inline-styled HTML that respects WeChat's platform restrictions, runs it through mechanical validation, and only then creates a draft — it never broadcasts automatically.

```bash
python3 scripts/render_wechat.py --file <article.md> --output <out.html>
python3 scripts/validate_wechat_html.py --file <out.html>
python3 scripts/publish.py --article <article.md> --cover <cover.png> --dry-run
python3 scripts/archive.py --article <article.md> --url <published-article-link>
```

**Typical output**: a draft appears in the WeChat Official Account backend (not yet broadcast), and the terminal reminds you to "confirm and broadcast manually, then come back to run archive afterward."

### soia-pkm-transform

A shared routing layer that converts an article into PDF, PPT, long-form images, quizzes, mindmaps, podcasts, flashcards, reports, and other artifacts, automatically routing to different providers (Obsidian native export, NotebookLM, Open Design, etc.) depending on the target format.

```bash
python3 scripts/resolve_route.py --target ppt --provider notebooklm --json
python3 scripts/notebooklm_artifact_matrix.py --article <article.md> --out-dir <output-dir> --targets all --run --json
python3 scripts/validate_artifact_quality.py --article <article.md> --out-dir <output-dir> --strict --json
```

**Typical output**: an artifact file in the requested format lands in the specified output directory, along with a validation report (page count, coverage, whether it opens/parses correctly).

### soia-pkm-library

Maintains an Obsidian book library: syncs your WeChat Reading shelf and highlights, enriches details for individual books, backfills reading records, and regenerates three overview views (library / reading records / genre). All 7 mechanical scripts are idempotent and safe to re-run.

```bash
python3 sync_weread_to_library.py --vault <vault-path>
python3 sync_weread_highlights.py --all
python3 backfill_reading_records.py
python3 gen_library_md.py
python3 gen_records_md.py
```

**Typical output**: the terminal reports the number of new book cards, new reading records, and failures, plus a suggested next step (e.g., regenerate the overviews).

### soia-cwork-feishu-cli

Uses app credentials and bot identity to read Feishu wikis, drives, and work documents. On first use, it maps the request to the minimum permission set and checks whether the published app and bot can see the target resources.

```text
Research my Feishu drive and wiki, and tell me which permissions I need first
Read this Feishu Wiki: <wiki-url>
Inventory my visible Feishu spaces and node hierarchy without changing remote content
```

**Important boundary**: an approved app scope does not automatically expose every resource to the bot. Document owners or wiki administrators may still need to authorize the app. When a command returns `missing_scopes` and `console_url`, apply only the reported minimum scopes; do not expand into write permissions.

---

## Installation

```bash
npx skills add soia-team/soia-open-skills
```

This installs every skill under `skills/` into your agent's skill directory — **agent-agnostic** (Claude Code / Codex / Cursor / Antigravity / Gemini / Kimi …). Once installed, just say:

| You say | Triggers |
|------|------|
| `Archive this X post: <URL>` | clip-x |
| `Archive this project <github url>` | clip-repo |
| `Organize the article library` / `Rebuild the MOC` | organize |
| `Add my take to this article` | distill |
| `Turn these opinions into an article` | compose |
| `Convert this article to PPT` / `Turn this into a mindmap` | transform |
| `Publish this as a WeChat article` | publish |
| `Bootstrap a knowledge base from scratch` | bootstrap |
| `Draw an architecture diagram for the README` / `Redraw this flow with Archify` | soia-dev-archify-diagrams |
| `Check this PR's checks` / `Find out why the recent GitHub Actions run failed` | soia-dev-github-ops |
| `Upgrade my local AI CLIs` / `Dry-run to check codex/claude versions` | soia-dev-ai-cli-upgrade |
| `Research my Feishu drive/wiki` / `Read a Feishu work document` | soia-cwork-feishu-cli |
| `Mirror my Feishu wiki to Git/Obsidian/VitePress` | soia-cwork-feishu-doc-git-sync |

Antigravity CLI uses the `agy` command. Its global skill directory is
`~/.gemini/antigravity-cli/skills/`, and workspace skills live under
`.agents/skills/`. Consumer Google OAuth migrates from Gemini CLI to
Antigravity; Gemini enterprise, API-key, and Vertex AI lanes remain separate,
so never silently alias `gemini` to `agy`.

### Configuring the vault path

```yaml
# ~/.config/soia-skills/soia-open-skills/<skill-type>/<skill-name>/config.yml
env:
  OBSIDIAN_VAULT: "<vault-path>"
  OBSIDIAN_ARTICLES: "<vault-relative-articles-dir>"
```

### Configuring Feishu app credentials

Keep Feishu credentials in the skill-specific private config. Do not commit them, put them in the vault, pass them as command-line arguments, or send them in chat:

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-feishu-cli/config.yml
```

See [`soia-cwork-feishu-cli`](./skills/soia-cwork-feishu-cli/) for the template and permission workflow.

The wiki mirror uses a separate skill-specific config:

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-feishu-doc-git-sync/config.yml
```

Do not commit enterprise wiki URLs, node tokens, or app secrets to the public skill repository.

Or override it per invocation with `--vault`. Each skill only reads its own skill-specific config directory, so no two skills share one large config file.

---

## Telegram Saved Messages sync (clip-x)

`clip-x`'s killer feature: batch-archive X links you casually forwarded to Telegram's "Saved Messages" from your phone, with a single command.

**Recommended path: JSON export** (compliant, zero risk of rate-limiting/bans, no API credentials needed)

1. Telegram Desktop → Settings → Advanced → Export Telegram data → check "Personal chats" + choose **Machine-readable JSON** → export.
2. You get a `result.json`.
3. Run the sync (URLs are deduplicated automatically; already-archived items are skipped):

```bash
python3 ~/.claude/skills/soia-pkm-clip-x/scripts/sync_telegram_export.py \
  "$HOME/Downloads/Telegram Desktop/ChatExport_XXXX/result.json" --dry-run   # preview
python3 ~/.claude/skills/soia-pkm-clip-x/scripts/sync_telegram_export.py \
  "<path>"                                                                     # actually run it
```

The more advanced MTProto API path (not recommended if you're in mainland China — carries account-risk exposure) is documented in [clip-x's SKILL.md](./skills/soia-pkm-clip-x/SKILL.md).

---

## Design philosophy

1. **Saving ≠ absorbing**: the lifeblood of the loop is `distill` — turning someone else's article into **your own** judgment. Absorbing one idea beats hoarding ten thousand.
2. **The opinion is yours, AI only writes it down**: `distill` / `compose` never invent an opinion for you and always ask when material is missing. What comes out is your work, not an AI summary.
3. **The vault has no subject subfolders — it relies on multi-dimensional indexing**: articles are stored flat by year; topic aggregation happens through frontmatter `topics:[[]]` + `_MOC/` + [Bases](https://help.obsidian.md/bases), never through folder structure.
4. **A dual track of machine layer + AI layer**: scripts handle fetching / deduping / normalizing (the mechanical section), the LLM handles summarizing / topic judgment / distillation (the user section); the two communicate through an agreed-upon set of section headings and never overwrite each other.
5. **Single responsibility, composable**: every skill does exactly one thing, chained together into the loop; extending the system means adding a new skill plus a dependency declaration — **never modifying a third-party skill** (since `npx skills check` may overwrite local changes to it).
6. **Agent-agnostic**: write `SKILL.md` once, and any AI that supports the skills standard can run it.

---

## Naming convention

Use lowercase kebab-case with a domain prefix:

- `soia-pkm-*`: personal knowledge management around an Obsidian vault — collect, organize, distill, compose, and publish.
- `soia-cwork-*`: enterprise collaboration — connect to Feishu and other work systems for documents, drives, wikis, and collaboration metadata.
- `soia-dev-*`: publicly reusable development and engineering tools.
- `soia-design-*` / `soia-gov-*` / `soia-meta-*`: design, governance, and meta-skill domains.

## Repository structure

```
soia-open-skills/
├── AGENTS.md
├── README.md
├── LICENSE · CONTRIBUTING.md
├── SKILL_SPEC.md              ← public skill spec
├── scripts/audit_skills.py    ← audits skills in this repo
├── scripts/generate_skill_catalog.py ← generates skills/README.md and an optional registry JSON
├── templates/skill-template/  ← starter template for new skills
└── skills/                    ← npx skills scans this directory
    ├── README.md              ← skill catalog generated from SKILL.md / agents/openai.yaml
    ├── soia-pkm-clip-x/       ├── soia-pkm-clip-wechat/
    ├── soia-pkm-clip-gzh/     ├── soia-pkm-clip-web/
    ├── soia-pkm-clip-drive/   ├── soia-pkm-clip-repo/
    ├── soia-pkm-organize/     ├── soia-pkm-distill/
    ├── soia-pkm-compose/      ├── soia-pkm-publish/
    ├── soia-pkm-transform/    ├── soia-pkm-bootstrap/
    ├── soia-pkm-reading-plan/ ├── soia-pkm-library/
    ├── soia-pkm-maintain/     ├── soia-pkm-alipan/
    ├── soia-pkm-alipan-curator/
    ├── soia-pkm-translate/    ├── soia-pkm-interpret/
    ├── soia-pkm-cover-image/
    ├── soia-dev-archify-diagrams/
    ├── soia-dev-github-ops/
    ├── soia-dev-ai-cli-upgrade/
    ├── soia-dev-prompt-clarity/
    ├── soia-dev-agent-md-advisor/
    ├── soia-dev-agent-cli-dispatch/
    └── soia-cwork-feishu-cli/
```

Every skill lives in its own folder with an independent `SKILL.md` (frontmatter holding just `name` + `description`) and its own `scripts/`.
This public repo doesn't use `metadata.json`; any extra info meant for agent/UI display goes in `agents/openai.yaml`.

### Who uses `agents/openai.yaml`?

`SKILL.md` is the authoritative entry point for every AI: capability description, dependencies, configuration, install steps, workflow, logging requirements, and completion summary must all live here.
`agents/openai.yaml` is only optional display/discovery metadata — it must never carry a required flow that's visible to only one particular AI.

| Consumer | How it's used |
|---|---|
| Claude Code | Reads `SKILL.md` from the installed skill directory. It doesn't depend on `agents/openai.yaml` directly, so hard dependencies, install steps, and missing-key prompts must all be written into `SKILL.md`. |
| Codex / OpenAI-style interfaces | Reads and executes `SKILL.md`; may use `agents/openai.yaml`'s `display_name`, `short_description`, and `default_prompt` for friendlier search, listing, and default prompts. |
| SOIA | Treats `SKILL.md` as authoritative; when the v7 registry is needed, run `python3 scripts/generate_skill_catalog.py --registry-out <soia-repo>/runtime/registry/skills`, and the generator merges `SKILL.md` with the optional `agents/openai.yaml`. |
| Other skills.sh-compatible AIs | Assumed by default to only read `SKILL.md`. If a given AI genuinely needs dedicated metadata, add a new `agents/<agent>.yaml` and document the consumer here. |

Maintenance rule: required instructions must never live only in `agents/openai.yaml`; after editing `SKILL.md` or `agents/openai.yaml`, re-run `python3 scripts/generate_skill_catalog.py`.

To add a new skill, start by copying the template:

```bash
cp -R templates/skill-template skills/your-skill-name
mv skills/your-skill-name/SKILL.md.template skills/your-skill-name/SKILL.md
python3 scripts/generate_skill_catalog.py
python3 scripts/audit_skills.py
```

---

## Credits and related projects

Third-party skills this repo works alongside (this repo only declares the relationship and never modifies their files; `npx skills check` may overwrite any local changes to them):

| Third-party skill | Upstream | Relationship to this repo |
|---|---|---|
| `weread-skills` | [Tencent/WeChatReading](https://github.com/Tencent/WeChatReading) | **Hard dependency** for `soia-pkm-library`'s WeChat Reading sync scripts; an optional data enhancement for `soia-pkm-reading-plan` |
| `huashu-weread-advisor` | [alchaincyf/huashu-weread](https://github.com/alchaincyf/huashu-weread) | `soia-pkm-reading-plan` optionally reuses its book-selection/recommendation methodology; `soia-pkm-distill` only references its "alchemy" method, with no runtime dependency |
| `book-to-skill` | [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | Not a runtime dependency; a standalone tool for turning books/documents into skills |
| `find-skills` | [vercel-labs/skills](https://github.com/vercel-labs/skills) | Not a runtime dependency; a helper tool for discovering/installing skills |

## Contributing

PRs and issues are welcome. To add a skill: ① read [SKILL_SPEC.md](./SKILL_SPEC.md) first ② copy from [templates/skill-template](./templates/skill-template/) ③ place it in `skills/<name>/` ④ include a `SKILL.md` (only `name` + `description`, description ideally ≤200 characters) ⑤ pass all paths/keys/personal data via CLI arguments, environment variables, or a skill-specific `config.yml` — never hardcode them ⑥ run `python3 scripts/generate_skill_catalog.py && python3 scripts/audit_skills.py` ⑦ include at least one end-to-end example. See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## License

[MIT](./LICENSE) — fork it, adapt it, use it commercially, just keep the attribution.

## Maintainers

**soia-team** · [GitHub](https://github.com/soia-team)
