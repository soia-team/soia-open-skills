# SOIA Skills Ecosystem Portal

[中文](README.md)

The public SOIA Skills portal for shared specifications, ecosystem navigation, the public routing manifest, and ecosystem-level meta skills.

## Skill catalog

| Skill | Summary |
|---|---|
| [`soia-meta-prompt-clarity`](skills/soia-meta-prompt-clarity/) | Draft, diagnose, and normalize Chinese and English prompts while preserving their language and boundaries. |
| [`soia-meta-skill-release`](skills/soia-meta-skill-release/) | Support post-release skill installation, old-name cleanup, and version-state checks. |
| [`soia-meta-sync-skills`](skills/soia-meta-sync-skills/) | Safely synchronize shared skills to AI tool directories explicitly selected by the user. |

## Ecosystem topology

| Repository | Responsibility |
|---|---|
| [`soia-open-skills`](https://github.com/soia-team/soia-open-skills) | Ecosystem portal, shared specifications, public routing, and meta skills. |
| [`soia-open-env-skills`](https://github.com/soia-team/soia-open-env-skills) | Development-environment diagnosis, installation, and upgrade support. |
| [`soia-open-pkm-clip-skills`](https://github.com/soia-team/soia-open-pkm-clip-skills) | Clipping and importing web, social, and cloud-drive material. |
| [`soia-open-pkm-vault-skills`](https://github.com/soia-team/soia-open-pkm-vault-skills) | Markdown knowledge-base bootstrap, organization, distillation, transformation, and library maintenance. |
| [`soia-open-media-content-skills`](https://github.com/soia-team/soia-open-media-content-skills) | Article creation, cover production, and multi-platform content publishing. |
| [`soia-open-cwork-office-skills`](https://github.com/soia-team/soia-open-cwork-office-skills) | Integrations for collaborative office tools and document services. |
| [`soia-open-dev-coding-skills`](https://github.com/soia-team/soia-open-dev-coding-skills) | Coding, task execution, code review, fixes, and GitHub operations. |
| [`soia-open-dev-design-skills`](https://github.com/soia-team/soia-open-dev-design-skills) | Open Design, architecture diagrams, charting, and Office design workflows. |
| [`soia-open-dev-infra-skills`](https://github.com/soia-team/soia-open-dev-infra-skills) | Infrastructure, terminal operations, and operational-maintenance capabilities. |
| [`soia-open-safe-skills`](https://github.com/soia-team/soia-open-safe-skills) | Code security audits and public vulnerability-intelligence tracking. |
| [`soia-open-edu-course-skills`](https://github.com/soia-team/soia-open-edu-course-skills) | Course outlines, teaching materials, and assessment design. |
| [`soia-open-dev-product-skills`](https://github.com/soia-team/soia-open-dev-product-skills) | Product requirements, user stories, and requirements-review workflows. |
| [`soia-open-dev-testing-skills`](https://github.com/soia-team/soia-open-dev-testing-skills) | Test cases, test documentation, and quality-assurance workflows. |
| [`soia-open-dev-release-skills`](https://github.com/soia-team/soia-open-dev-release-skills) | Software release checklists, preflight checks, and release verification. |

The complete machine-readable skill catalog is [`routing/routing-manifest.json`](routing/routing-manifest.json).

## Installation

### Plugin method (recommended)

Plugins install and toggle a domain-sized group of skills. For example, install the knowledge-clipping plugin:

```bash
claude plugin marketplace add soia-team/soia-open-skills
/plugin install soia-pkm-clip@soia

codex plugin marketplace add soia-team/soia-open-skills
codex plugin add soia-pkm-clip@soia

qwen extensions install https://github.com/soia-team/soia-open-skills:soia-pkm-clip
```

Use `claude plugin enable`, `claude plugin disable`, and `claude plugin update` to manage installed Claude plugins.

### npx method

The npx method retains single-skill granularity when you only need one specific skill.

Install an individual skill as needed:

```bash
npx skills add soia-team/<repository> -g -a '*' -s <skill-name> -y
```

For example, install the prompt-clarity skill:

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-prompt-clarity -y
```

For installation sets organized by machine role, see [`docs/install-profiles.md`](docs/install-profiles.md).

## Specifications

- [`SKILL_SPEC.md`](SKILL_SPEC.md): skill structure, naming, frontmatter, and validation requirements.
- [`DATA_STORAGE_SPEC.md`](DATA_STORAGE_SPEC.md): storage boundaries for configuration, credentials, state, caches, and outputs.
- [`docs/install-profiles.md`](docs/install-profiles.md): installation profiles by use case.

## Ecosystem navigation

The canonical specifications and complete ecosystem catalog are available in [`soia-team/soia-open-skills`](https://github.com/soia-team/soia-open-skills).

## License

[MIT](LICENSE)
