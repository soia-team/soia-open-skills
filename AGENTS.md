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

- **Develop on `main` directly.** Do not create feature branches or long-lived
  topic branches. Commit and push to `main` (or open a short-lived PR if branch
  protection requires it).
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
