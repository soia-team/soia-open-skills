# AGENTS.md - soia-open-skills

Rules for all AI agents editing this repository.

## Repository Purpose

`soia-open-skills` is the public SOIA Skills ecosystem portal and specification
source of truth. It retains only the three `soia-meta-*` ecosystem skills, the
shared authoring/storage specifications and template, the canonical audit and
catalog tooling, and the public cross-repository routing manifest. Domain skills
are published from focused spoke repositories. Every committed artifact must be
safe for users who do not share the maintainer's machine, vault layout, accounts,
private data, or SOIA internal workspace.

## Safety Rules

- No real API keys, tokens, cookies, session strings, passwords, account ids,
  private `config.yml`, or `.env` files.
- No maintainer-specific absolute paths such as `/Users/<name>/...`.
- No private family, home, health, finance, or learner profile context.
- Put user-specific behavior behind CLI args, env vars, or skill-specific
  user-owned config files outside this repo:
  `~/.config/soia-skills/<skill-name>/config.yml`. The former
  `<repo>/<skill-type>/<skill-name>/` namespace is only a read-compatible v1
  migration source; all new writes use the v2 skill-name directory.
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

## 维护本仓技能

技能契约、调试安装、新增/改名/拆分/删除的完整流程，以及插件市场发布步骤，统一见
元仓的 [CONTRIBUTING.md](https://github.com/soia-team/soia-open-skills/blob/main/CONTRIBUTING.md)。
本文件只保留本仓特有的用途、边界与验证命令。
