# SOIA Managed Skills

Use this reference for SOIA batch sync from a repository-local preflight source or from the npx-installed shared source.

## Current Managed Set

The batch script discovers current managed skills mechanically:

- Include every directory under the selected source that contains `SKILL.md` and starts with `soia-`.
- Include optional non-SOIA entries only when the user selects optional sync or the script is run with `--optional`.
- Exclude support files and nested helper directories that do not contain their own `SKILL.md`.

This removes two old allowlist problems: adding a new `soia-*` skill requires adding the folder, not editing the sync script, and installing open + private packages into one shared source produces one complete target set.

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

There are currently no optional non-SOIA skills in `soia-private-skills`.

## Retired Cleanup Names

Retired names are removed from target agent directories during SOIA batch sync.

- `soia-dev-project-init` - merged into `soia-dev-project-scaffold`.
- `soia-gov-ui-validation` - merged into `soia-gov-ui-design`.
- `soia-gov-tauri-real-device-test` - merged into `soia-gov-ui-design` Stage 2 (2026-04-24).
- `soia-brand-guidelines` - renamed to `soia-design-brand-guidelines` (2026-04-24).
- `jiuan-docs-v5-project-structure` - v5 legacy; not shipped by `soia-private-skills`.
- `jiuan-docs-v5-references` - v5 legacy; not shipped by `soia-private-skills`.

## Cleanup Boundary

- Managed current set = discovered `soia-*` skills plus optional entries when selected.
- Repository ownership and target-link ownership are separate: `soia-open-skills` publishes `soia-pkm-*`; this script may link those installed shared-source directories without editing their contents.
- Managed retired set = retired cleanup names above.
- Overwrite only current managed skill names selected for this run.
- Delete explicit retired cleanup names and first-level dangling symlinks whose names start with `soia-`.
- Keep dangling symlinks when `--no-prune` is selected.
- Never delete or rewrite unrelated target entries such as user skills or third-party skills not selected here.
- Target entries must be symlinks to the selected source. Do not copy managed skill directories into multiple agent homes.
