<div align="center">

# SOIA Skills Ecosystem Portal

[中文](README.md) | English

The specification source of truth, cross-repository catalog, public routing manifest, and three ecosystem-level meta skills.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

</div>

## What this repository is now

`soia-open-skills` is the portal for the SOIA Skills ecosystem, not the monorepo for every domain skill. Domain skills are published from focused repositories. This repository retains only:

- `soia-meta-sync-skills`, `soia-meta-skill-release`, and `soia-meta-prompt-clarity`;
- the shared skill/storage specifications, template, and audit tools;
- the topology of 14 public repositories;
- the machine-readable manifest generated from 12 public routing sources.

To find a skill, start with [`routing/routing-manifest.json`](routing/routing-manifest.json), then use its `repo` and `skillPath` fields to install or inspect the package.

## 14-repository topology

| Repository | Responsibility | Install / inspect example |
|---|---|---|
| [`soia-open-skills`](https://github.com/soia-team/soia-open-skills) | Ecosystem portal, specification source, public routing, and meta skills | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-sync-skills -y` |
| [`soia-open-env-skills`](https://github.com/soia-team/soia-open-env-skills) | Beginner-friendly environment diagnosis, installation, and upgrade support | `npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-environment-setup -y` |
| [`soia-open-pkm-clip-skills`](https://github.com/soia-team/soia-open-pkm-clip-skills) | Web/social clipping plus cloud-drive ingestion and atomic operations | `npx skills add soia-team/soia-open-pkm-clip-skills -g -a '*' -s soia-pkm-clip-web -y` |
| [`soia-open-pkm-vault-skills`](https://github.com/soia-team/soia-open-pkm-vault-skills) | Markdown vault bootstrap, organization, distillation, transformation, and library maintenance | `npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-bootstrap-vault-base -y` |
| [`soia-open-media-content-skills`](https://github.com/soia-team/soia-open-media-content-skills) | Article writing, cover creation, and WeChat/X/Rednote publishing | `npx skills add soia-team/soia-open-media-content-skills -g -a '*' -s soia-media-compose-article-draft -y` |
| [`soia-open-cwork-office-skills`](https://github.com/soia-team/soia-open-cwork-office-skills) | Feishu, ProcessOn, and office collaboration integrations | `npx skills add soia-team/soia-open-cwork-office-skills -g -a '*' -s soia-cwork-feishu-cli -y` |
| [`soia-open-dev-coding-skills`](https://github.com/soia-team/soia-open-dev-coding-skills) | Coding protocols, task execution, reviews, fixes, and GitHub operations | `npx skills add soia-team/soia-open-dev-coding-skills -g -a '*' -s soia-dev-task-execute -y` |
| [`soia-open-dev-design-skills`](https://github.com/soia-team/soia-open-dev-design-skills) | Open Design, Archify, draw.io/Visio, and Office design workflows | `npx skills add soia-team/soia-open-dev-design-skills -g -a '*' -s soia-dev-open-design-ops -y` |
| [`soia-open-dev-ts-skills`](https://github.com/soia-team/soia-open-dev-ts-skills) | Technical support, long-running terminal diagnostics, and general operations | `npx skills add soia-team/soia-open-dev-ts-skills -g -a '*' -s soia-dev-terminal-ops -y` |
| [`soia-open-safe-skills`](https://github.com/soia-team/soia-open-safe-skills) | Code security audits and public vulnerability-intelligence tracking | `npx skills add soia-team/soia-open-safe-skills -g -a '*' -s soia-safe-audit-fix-codebase -y` |
| [`soia-open-edu-course-skills`](https://github.com/soia-team/soia-open-edu-course-skills) | Incubator for course outlines, teaching materials, and assessments | `npx skills add soia-team/soia-open-edu-course-skills -l --full-depth` |
| [`soia-open-dev-ba-skills`](https://github.com/soia-team/soia-open-dev-ba-skills) | Incubator for general requirements research, specifications, and review presentations | `npx skills add soia-team/soia-open-dev-ba-skills -l --full-depth` |
| [`soia-open-dev-testing-skills`](https://github.com/soia-team/soia-open-dev-testing-skills) | Incubator for general test documentation and test-case generation | `npx skills add soia-team/soia-open-dev-testing-skills -l --full-depth` |
| [`soia-open-dev-release-skills`](https://github.com/soia-team/soia-open-dev-release-skills) | Incubator for software release checklists, requests, and post-release verification | `npx skills add soia-team/soia-open-dev-release-skills -l --full-depth` |

The first 12 repositories are the current public inputs to the routing generator; `dev-testing` and `dev-release` join after publishing their first public skill. Private repositories are excluded. Corp-specific increments are maintained in the corp repository's own routing data.

Generic commands:

```bash
npx skills add soia-team/<repo> -l --full-depth
npx skills add soia-team/<repo> -g -a '*' -s <skill-name> -y
```

## The three retained meta skills

| Skill | Purpose | Install |
|---|---|---|
| [`soia-meta-sync-skills`](skills/soia-meta-sync-skills/) | Safely sync an installed shared skill source into explicitly selected AI tool directories, with dry-run, hard-dependency closure, and bounded cleanup | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-sync-skills -y` |
| [`soia-meta-skill-release`](skills/soia-meta-skill-release/) | Finish post-merge installation, old-name cleanup, symlink setup, and lock/version reconciliation | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-skill-release -y` |
| [`soia-meta-prompt-clarity`](skills/soia-meta-prompt-clarity/) | Draft, diagnose, and compile Chinese or English prompts while preserving the user's language and boundaries | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-prompt-clarity -y` |

The generated local catalog is [`skills/README.md`](skills/README.md).

## Specification source of truth

All public skill repositories use this repository as the canonical source for:

- [`SKILL_SPEC.md`](SKILL_SPEC.md): structure, naming, frontmatter, customer-readable contract, and validation;
- [`DATA_STORAGE_SPEC.md`](DATA_STORAGE_SPEC.md): storage boundaries for config, credentials, state, cache, temporary data, and outputs;
- [`templates/skill-template/`](templates/skill-template/): the new-skill template;
- [`scripts/audit_skills.py`](scripts/audit_skills.py): the canonical public skill audit;
- [`scripts/generate_skill_catalog.py`](scripts/generate_skill_catalog.py): per-repository catalog generation;
- [`scripts/scaffold_repo_baseline.py`](scripts/scaffold_repo_baseline.py): repository baseline scaffolding.

Domain repositories may carry synchronized copies, but this repository wins if those copies conflict.

## Public routing manifest

Every entry in [`routing/routing-manifest.json`](routing/routing-manifest.json) has this shape:

```json
{
  "skill_name": "soia-meta-sync-skills",
  "repo": "soia-open-skills",
  "skillPath": "skills/soia-meta-sync-skills",
  "visibility": "public"
}
```

Regenerate it with:

```bash
python3 scripts/generate_routing_manifest.py
```

While the portal-slimming PR is unmerged, preview the local three-skill portal while still reading every spoke repository through `gh api`:

```bash
python3 scripts/generate_routing_manifest.py --local-portal-root .
```

The generator includes public repositories only. Private and company-specific skills publish incremental routing from their owning private repository.

## Maintenance and validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/generate_skill_catalog.py --check
python3 scripts/check_readme_coverage.py
python3 scripts/audit_skills.py --strict
git diff --check
```

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for third-party boundaries. Contributions use a short-lived branch, PR, passing CI, and merge; protected `main` is never pushed directly.

---

**soia-team** · [GitHub](https://github.com/soia-team)
