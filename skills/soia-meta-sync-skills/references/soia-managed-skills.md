# SOIA Managed Skills

Use this reference for SOIA batch sync from a repository-local preflight source or from the npx-installed shared source.

## Current Managed Set

The batch script discovers current managed skills mechanically:

- Include every directory under the selected source that contains `SKILL.md` and starts with `soia-`.
- Include optional non-SOIA entries only when the user selects optional sync or the script is run with `--optional`.
- Exclude support files and nested helper directories that do not contain their own `SKILL.md`.

Adding a new `soia-*` skill needs only its folder; several packages installed into one shared source produce one complete target set.

## Included SOIA Domains

Governance:

- `soia-gov-*`

Development:

- `soia-dev-*`

Design:

- `soia-design-*`

Meta:

- `soia-meta-*`

Public PKM:

- `soia-pkm-*` (published by `soia-open-skills`, linked by this script after npx installs it into the shared source)

## Optional Set

Optional skills are linked only when the user selects optional sync or the script is run with `--optional`.

No optional entries are currently bundled.

## Retired Cleanup Names

Retired names are removed from target agent directories during SOIA batch sync. The authoritative list is `RETIRED_SKILLS` in `scripts/sync_soia_skills.py`; add a name there when a skill is renamed or merged.

## Cleanup Boundary

- Managed current set = discovered `soia-*` skills plus optional entries when selected.
- Repository ownership and target-link ownership are separate: `soia-open-skills` publishes `soia-pkm-*`; this script may link those installed shared-source directories without editing their contents.
- Managed retired set = `RETIRED_SKILLS` in the sync script.
- Overwrite only current managed skill names selected for this run.
- Delete explicit retired cleanup names and first-level dangling symlinks whose names start with `soia-`.
- Keep dangling symlinks when `--no-prune` is selected.
- Never delete or rewrite unrelated target entries such as user skills or third-party skills not selected here.
- Target entries must be symlinks to the selected source. Do not copy managed skill directories into multiple agent homes.
