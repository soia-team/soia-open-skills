# AGENTS.md - soia-open-skills

Rules for all AI agents editing this repository.

## Audience

This file is the shared repository rulebook for Codex, Claude Code,
Antigravity CLI, Gemini CLI, OpenCode, Kimi, Cursor, and any other AI agent
that reads project instructions.
Tool-specific commands below are examples or optional validation helpers; they
do not make this a Codex-only file.

## Repository Purpose

`soia-open-skills` publishes public, reusable skills. Every committed skill must
be safe for users who do not share the maintainer's machine, vault layout,
accounts, private data, or SOIA internal workspace.

## Routing Boundary

Maintaining this repository is skill-package work, not SOIA product work. The
repository name and SOIA examples do not authorize or trigger product
`proposal` / `board` / `task-execute` / product-release governance. Follow this
repository's own validation and release rules; use product governance only when
the actual target is an explicitly confirmed SOIA product workspace.

## Read First

- `README.md` for the public catalog, install path, and visible skill list.
- `skills/README.md` for the generated per-skill catalog; regenerate it instead
  of editing by hand.
- `SKILL_SPEC.md` before creating or substantially changing a skill.
- The changed skill's `SKILL.md` and any directly referenced `references/` files.

## Skill Contract

- Real skills live only under `skills/<skill-name>/`.
- The template lives at `templates/skill-template/`.
- Keep the template file named `SKILL.md.template`; do not put a real `SKILL.md`
  under `templates/`, or `npx skills add --full-depth` may discover it as a
  publishable skill.
- Each real skill requires `SKILL.md` with frontmatter `name` and `description`.
- `agents/openai.yaml` is recommended for UI-facing metadata.
- Do not add `metadata.json` in this public repo; it is a legacy private catalog
  format, not part of the public skills.sh/npx skill contract.

### Configuration and structured resources

- Use YAML as the canonical format for editable, human-readable, AI/script-readable
  domain facts and user configuration. Add a small `schema_version` or `version`
  field when the file is a maintained data contract.
- Use Markdown for explanations, workflows, rationale, links, and customer-facing
  reminders. If both Markdown and YAML exist, keep one machine-readable source of
  truth and avoid maintaining duplicated lists by hand.
- Keep JSON when it is an external interchange contract, a tool-specific asset, or
  a deliberate zero-dependency runtime input. Do not convert it only for stylistic
  consistency.
- `agents/openai.yaml` is a platform-facing contract and must retain its required
  YAML shape. It is not a general-purpose skill configuration file.

## Safety Rules

- No real API keys, tokens, cookies, session strings, passwords, account ids,
  private `config.yml`, or `.env` files.
- No maintainer-specific absolute paths such as `/Users/<name>/...`.
- No private family, home, health, finance, or learner profile context.
- Put user-specific behavior behind CLI args, env vars, or skill-specific
  user-owned config files outside this repo:
  `~/.config/soia-skills/soia-open-skills/<skill-type>/<skill-name>/config.yml`.
- Public examples must use placeholders such as `<path>`, `<repo>`, and
  `<YOUR_KEY>`.

## Validation

Before committing skill changes, run:

```bash
python3 -m pip install -r requirements-dev.txt  # once per machine; the audit uses PyYAML
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/generate_skill_catalog.py --check
python3 scripts/audit_skills.py
git diff --check
```

For changed skills, also run a skill validator when one is available. On Codex
machines, this helper is commonly available:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

Final installation acceptance must use the pushed remote repo, not a local
checkout copied into an agent target:

```bash
npx skills add soia-team/soia-open-skills -l --full-depth
npx skills add soia-team/soia-open-skills -g --all
```

## Git Workflow

- Use short-lived branches with `feat/`, `fix/`, or `chore/` prefixes. Open a
  PR, require CI to pass, then merge into the protected `main` branch. Do not
  create long-lived branches or push directly to `main`.
- **No worktrees.** Never run `git worktree add` in this repository. Worktrees
  lock branches and block deletion; they caused real cleanup incidents in this
  repo. If you need to inspect another ref, use `git show <ref>:<path>` or
  `git stash` instead.

## Skill Debug Install Rules

Local checkout installation is only for temporary debugging. It is not a release
or user-facing install path.

Allowed during local testing:

```bash
npx skills add "$PWD" -l --full-depth
```

Rules:

- Use local checkout install only to test an uncommitted or unpublished skill.
- Say "local debug install" in the work log or final response; do not call it
  "installed latest" unless it came from the pushed remote package.
- Do not put a maintainer absolute path in docs, examples, commit messages, or
  user-facing instructions. Use `$PWD`, `<repo-path>`, or the remote package.
- After merge/push, verify the real install from the remote package:

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s <skill-name> -y
```

Forbidden outside local testing:

```bash
npx skills add /absolute/local/path/to/soia-open-skills -g -a '*' -s <skill-name> -y
```

If validating SOIA AI consumption, sync from `~/.agents/skills` into
`~/.soia/skills` with `soia-dev-sync-skills`; do not copy directories manually.

## New Skill Lifecycle: Branch → Main → Install

When creating new skills, follow this sequence exactly. Do not skip steps or
shortcut with manual symlinks.

### 1. Create on a branch

```bash
cd <your-local-checkout>/soia-open-skills
git checkout -b feat/<topic>
# create skills/<new-skill-name>/SKILL.md, references/, scripts/ etc.
git add skills/<new-skill-name>/
git commit -m "feat(pkm): add <new-skill-name>"
git push -u origin feat/<topic>
```

### 2. (Optional) Local debug install for testing

While the skill is still on a branch and not yet in main:

```bash
npx skills add "$PWD" -l --full-depth
```

This is a **temporary debug install**. Do not treat it as the final install.
Do not manually `ln -s` from the git checkout into `~/.agents/skills/` or
`~/.claude/skills/` — manual symlinks bypass `.skill-lock.json` registration
and will not be tracked by `npx skills check`.

### 3. Merge to main

Open a PR (if branch protection requires it) or merge directly. The skill
becomes available from the remote package only after it lands on main.

### 4. Install from remote (the only correct final install)

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s <new-skill-name> -y
```

This registers the skill in `~/.agents/.skill-lock.json` and creates proper
symlinks in `~/.claude/skills/` and `~/.agents/skills/`. Future updates via
`npx skills check` will track it.

### Why not manual symlinks?

- Manual `ln -s` skips `.skill-lock.json` — the skill becomes invisible to
  `npx skills check` and `npx skills update`.
- Manual symlinks pointing at a feature branch break when the branch is
  deleted after merge.
- Other agents (Codex, Gemini CLI) that read `.skill-lock.json` will not
  discover manually linked skills.

## Skill Rename / Split / Delete

`npx skills add` does not auto-remove old names. When renaming, splitting, or
deleting a skill, manually clean up old installs.

### When to split

A skill should be split when it has **multiple distinct output types or tool
bindings** and a 3-segment name can't tell Claude Code which sub-workflow to
trigger. Symptoms:

- Users have to say "用 X 方式做" to disambiguate within one skill.
- The SKILL.md has grown past 500 lines with unrelated provider sections.
- Different sub-workflows have incompatible dependencies (e.g. Obsidian vs
  NotebookLM).

Don't split prematurely: if the skill has one clear output type and one
primary tool, a 4-segment name is enough.

### How to split (full playbook)

**Phase 1 — Design names before touching code**

1. List the distinct output types or tool bindings in the current skill.
2. For each, pick a name following `SKILL_SPEC.md` naming convention (4–5
   segments). Ask: "Does the name alone tell Claude Code what to trigger?"
3. Verify no name collisions with existing skills:
   `ls skills/ | grep <action>`.
4. Get user confirmation on names before creating directories.

**Phase 2 — Create sub-skills**

5. For each sub-skill:
   - `cp -R skills/<old-name> skills/<new-name>`
   - Edit `SKILL.md`: update `name`, `description`, triggers, workflow to
     cover only this sub-skill's scope.
   - **Copy the full `references/` set** into every sub-skill (see "Reference
     links" below).
   - Add `version`, `created_at`, `updated_at`, `created_by`, `updated_by`
     to frontmatter.

6. Delete the old skill: `git rm -r skills/<old-name>`.
7. Regenerate catalog: `python3 scripts/generate_skill_catalog.py`.
8. Update `README.md` transform/relevant section: replace old row with new
   rows, remove any "deprecated" markers for the old name.
9. Run `python3 scripts/audit_skills.py --strict` — fix until zero findings.

**Phase 3 — Merge and install**

10. Branch → PR → CI passes → squash merge.
11. Clean up old local installs:

```bash
rm -rf ~/.agents/skills/<old-name>
rm -f  ~/.claude/skills/<old-name>
```

12. Install new skills from remote:

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s <new-name-1> -s <new-name-2> -y
```

**Phase 4 — Update downstream docs**

13. Update your maintainer-local architecture notes (kept outside this repo).
14. Grep for old name across both repos and the vault — zero hits before
    declaring done.

### Rename (no split)

Same as split Phase 2–4, but with one new name replacing one old name.

### Delete (no replacement)

Same as split Phase 3 step 11 only (clean up old installs). Skip step 12.

### Reference links during split

When splitting, each sub-skill inherits reference files that cross-link each
other. The audit script checks relative links — a missing target fails CI.

Rule: **copy the full `references/` set into every sub-skill**, even if a
sub-skill doesn't directly use all references. The cost is disk duplication;
the benefit is zero broken links and independent installability. Do not try to
share references across skills via symlinks or relative paths outside the
skill directory — `npx skills add` copies each skill as an isolated unit.

### Lessons from `soia-pkm-transform` split (2026-07-16)

Mistakes made and fixed — read before your next split:

1. **Name accuracy matters more than speed.** We renamed twice
   (`article-notebook` → `article-learning` → `article-notebooklm`) because
   the first two names didn't reflect the actual tool binding. Pick names by
   asking "what is the defining trait: the output type, or the platform?"
2. **Delete the old skill from the repo.** Leaving it as "fallback" creates
   confusion — two skills answering the same trigger.
3. **`git rm -rf` the old directory.** After rename, the old directory may
   linger in the git index even though the files have been moved. Explicitly
   `git rm -rf skills/<old-name>` before committing.
4. **Regenerate `skills/README.md` every time.** The catalog is generated, not
   hand-edited. Forgetting this fails CI.
5. **Check `README.md` (root) too.** The hand-maintained root README has a
   skills table — update it manually and remove deprecated rows.
6. **Grep for the old name across everything.** Old names hide in SKILL.md
   body text, install commands, vault docs, and update logs.
