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

## Git Workflow（本仓特有：默认分支是 main）

- 本仓同样以 `dev` 为集成分支，但**默认分支保持 `main`**——本仓既是插件市场
  又是插件（`soia-meta` 的 marketplace `source` 为 `"./"`，无 sha pin），
  客户端克隆市场时取的是**默认分支**。把默认分支指向 `dev` 会让 `-SNAPSHOT`
  直达所有客户端，且发布门禁拦不住（没有 pin 提交可检查）。
- 因此：提 PR 必须**显式 `--base dev`**，不要依赖默认分支。
- **新分支从 `main` 开**（最新正式版），PR 目标仍是 `dev`：`main` 始终是
  `dev` 的祖先，这样开出来的分支必定能干净并入。确实要基于 dev 上尚未发布的
  工作时才从 `dev` 开，并在 PR 正文说明。
- `main` 不接收任何 PR：它只在正式发版时由 `dev` 快进推进。
- `dev` 上 plugin.json 版本带 `-SNAPSHOT` 声明下个目标，feature PR 不改版本号。

## 正式发版需用户逐次授权（硬门禁）

**正式发版是对外动作，必须用户当次点头才能执行，不得顺手做、不得推断授权。**

- 需授权：`formal_release.py`（或等效的手工步骤）、`gh release create`、打 tag、
  发版 PR（dev→main）合并、市场 pin 刷新——这些都会改变外部用户收到的内容。
- 不需授权：feature/fix PR 进 `dev`、本地验证、`--dry-run` 预演、体检脚本。
- 「用户让我修某个 bug」**不等于**「用户让我发版」。改动合进 `dev` 即算交付完成；
  要不要发、什么时候发、发什么版本号，由用户决定。做完改动后报告「已进 dev，
  待你决定是否发版」，然后停下。
- 多 AI 并行时尤其重要：另一个 agent 可能正在改同一批仓，未经协调的发版会把
  它未完成的工作一起送出去。2026-08-03 实际发生过一次未授权发版。

## Open Items (current state)

- **Formal release plan P3/P4** (see the 2026-08-01 release plan, owned at the v7 workspace level): SkillHub onboarding (env / media-content / pkm-vault first), WorkBuddy sharecode trial, Red Skill uploads, first Xiaohongshu notes — blocked on the user's market report; decisions D5-D8 still open.
- **Unattended marketplace refresh** is undecided (needs a PAT secret or a ruleset change that weakens classic branch protection) — awaiting user decision. Until then, refresh pins via the skill-release flow.
- Version discipline is live: `dev` is the integration branch, `main` is always the latest formal release, plugin.json uses `-SNAPSHOT` during development, and the marketplace generator rejects manifests containing `-SNAPSHOT`. Do not revert this.

## 维护本仓技能

技能契约、调试安装、新增/改名/拆分/删除的完整流程，以及插件市场发布步骤，统一见
元仓的 [CONTRIBUTING.md](https://github.com/soia-team/soia-open-skills/blob/main/CONTRIBUTING.md)。
本文件只保留本仓特有的用途、边界与验证命令。
