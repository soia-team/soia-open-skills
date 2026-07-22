# Source Rules

Use these rules for non-SOIA single-skill sync and for source classification before target confirmation.

## Local Directory

Recognize:

- Absolute paths: `/path/to/skill`
- Home paths: `~/path/to/skill`
- Relative paths: `./skill` or `../skill`

Rules:

- Resolve the path and verify it is a directory.
- Require `SKILL.md` directly inside the directory for single-skill sync.
- Derive the skill name from the directory basename unless the user explicitly supplies another name.
- Do not execute files from the source directory.

## GitHub Repository

Recognize:

- `https://github.com/org/repo`
- `https://github.com/org/repo.git`
- `git@github.com:org/repo.git`

Rules:

- Clone into a temporary directory.
- Strip a trailing `.git` only for display/name derivation; keep the clone URL valid.
- Locate `SKILL.md`.
- If the repo root contains `SKILL.md`, use the repo root as the skill directory.
- If one nested `SKILL.md` exists, use its parent directory.
- If multiple nested `SKILL.md` files exist, ask the user which skill to sync.
- Remove the temporary directory after sync or on failure.

## skillsmp.com Page

Recognize:

- URLs containing `skillsmp.com`.

Rules:

- Fetch or open the page only after confirming the user wants that remote source.
- Extract a skill directory containing `SKILL.md` plus any bundled resources.
- Preserve bundled `scripts/`, `references/`, and `assets/` when present.
- If extraction cannot produce a valid local directory with `SKILL.md`, stop and report the blocker.
- Do not run downloaded scripts during import.

## Generic Copy Boundary

For a single-skill sync, remove only `<target>/<skill-name>` before linking. Do not scan or clean other target entries.

The resolved source directory must remain available after sync. For remote sources, install through `npx skills add` or clone into a durable local source before creating agent symlinks; do not create symlinks to a temporary directory that will be deleted.
