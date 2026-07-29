# Contributing to SOIA Skills

本文件覆盖两类读者：**外部贡献者**（想加一个新 skill）看前半部分，
**维护者 / AI Agent**（在仓内做改动）看后半部分的维护手册。

各仓的 `AGENTS.md` 只保留本仓特有的用途、边界与验证命令；技能契约、调试安装、
新增/改名/拆分/删除流程与插件市场发布步骤统一在这里，按需查阅，不必每次进仓通读。

> 后半部分抽取自各仓 AGENTS.md 中跨仓完全相同的 8 节。原先 6 份副本各 318 行，
> 其中「New Skill Lifecycle」66 行 +「Skill Rename / Split / Delete」111 行合计
> 1062 行纯重复——按 Anthropic《The new rules of context engineering for
> Claude 5》的建议，这类操作手册应当按需加载而非常驻。

---

# 一、外部贡献者：加一个新 skill

## 加新 skill 的步骤

1. **Fork** 这个仓库

2. **先读技能规范**：[SKILL_SPEC.md](./SKILL_SPEC.md)。所有 public skill 必须遵守其中的路径、配置、secret、个人信息和验证口径约束。

3. **从模板复制一个新目录**，命名用小写连字符（如 `soia-pkm-clip-notion`）：

   ```bash
   cp -R templates/skill-template skills/your-skill-name
   mv skills/your-skill-name/SKILL.md.template skills/your-skill-name/SKILL.md
   ```

4. **写 SKILL.md**，frontmatter 必须有：

   ```yaml
   ---
   name: your-skill-name
   description: 一句话说明 skill 干什么 + 触发词清单（控制在 200 字符内）
   version: 0.1.0
   created_at: <YYYY-MM-DD HH:mm:ss>
   updated_at: <YYYY-MM-DD HH:mm:ss>
   created_by: <concrete-model-name>
   updated_by: <concrete-model-name>
   ---
   ```

   frontmatter 必须包含 `name`、`description`、`version`（SemVer）、
   `created_at`、`updated_at`、`created_by`、`updated_by`，并遵循
   [SKILL_SPEC.md](./SKILL_SPEC.md) 的字段规范；`created_by` / `updated_by`
   填写具体模型名。
   不要新增 `metadata.json`；公开仓使用 `SKILL.md` + 可选 `agents/openai.yaml`。

5. **路径参数化**：
   - 严禁硬编码 `/Users/xxx`、`/home/xxx` 等本地路径
   - 严禁把维护者自己的 vault 子目录当作公共默认值（如某个中文 PARA 目录）
   - 用环境变量（如 `OBSIDIAN_VAULT`）+ 命令行 `--vault` 参数
   - 提供清晰的错误提示（"please set OBSIDIAN_VAULT or use --vault"）

6. **不要 commit 任何 secret**：
   - 不 commit `.env`
   - 不 commit `*.session`
   - 不在代码里写真实 API key / token / 密码
   - 文档里举例用 `<YOUR_KEY>` 占位符

7. **同步公共说明**：
   - 新增 skill 或新增 domain 时，更新根目录 `README.md` 和 `README.en.md` 的简介、目录、安装/配置入口和触发示例。
   - `skills/README.md` 是生成文件，不要手工编辑；运行 `python3 scripts/generate_skill_catalog.py` 更新它。
   - 如果 skill 有机器可读配置和人类说明，保持 YAML/JSON 事实源与 Markdown 说明的链接一致，避免维护两份权限或字段清单。

8. **测试**：
   - 至少给出 1 个端到端用例
   - 文档里说明如何手动验证
   - 区分「静态检查通过」「已安装」「端到端测试通过」「已提交」，不要混用
   - 提交前运行：

     ```bash
     python3 scripts/audit_skills.py
     git diff --check
     ```

9. **提 PR**，说明：
   - 这个 skill 解决什么问题
   - 触发词是什么
   - 与其他 skill 的关系

## 跨库迁移的域归属复核

跨库迁移 skill 时，除内容和安全边界外，必须复核 skill 的域前缀是否与目标仓的域语义一致。迁入通用仓的工具不能因历史归属继续使用产品专用域前缀；必要时在迁移中改名并更新所有 catalog、README 和交叉引用。此检查源于 PR #37：`design-explorer` 曾以产品域前缀迁入通用仓而未被发现。

## 改 bug / 改进体验

直接提 PR，关联 issue 编号。无需事先沟通。

## 行为准则

- 中文 / 英文都欢迎
- 不接受打广告、写垃圾内容
- 尊重原作者（如果借鉴了别人的 skill，明确标注）

## 联系

请在本仓 [GitHub Issues](https://github.com/soia-team/soia-open-skills/issues) 提 issue。

---

# 二、维护者手册

以下内容中的 `soia-open-pkm-vault-skills`、`soia-pkm-vault` 等仅为示例，
实际使用时替换为你所在仓库与对应插件名（对照表见文末）。

## Audience

This file is the shared repository rulebook for Codex, Claude Code,
Antigravity CLI, Gemini CLI, OpenCode, Kimi, Cursor, and any other AI agent
that reads project instructions.
Tool-specific commands below are examples or optional validation helpers; they
do not make this a Codex-only file.

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
- Do not add `metadata.json` in this repository; it is a legacy private catalog
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

## Git Workflow

- Use short-lived branches with `feat/`, `fix/`, or `chore/` prefixes. Open a
  PR, require CI to pass, then merge into the protected `main` branch. Do not
  create long-lived branches or push directly to `main`.
- **No worktrees.** Never run `git worktree add` in this repository. Worktrees
  lock branches and block deletion; they caused real cleanup incidents in this
  repo. If you need to inspect another ref, use `git show <ref>:<path>` or
  `git stash` instead.

## 清理分支：不要相信 `git cherry` 和 `--merged`

本仓群全部走 **squash 合并**。squash 把分支的 N 个提交压成一个**全新提交**，
与原分支没有任何祖先关系，于是：

| 命令 | 在 squash 流程下的表现 |
|---|---|
| `git branch --merged main` | 认不出，已合并的分支不会列出 |
| `git branch -d <分支>` | 拒绝删除，报「未完全合并」 |
| `git cherry origin/main <分支>` | **误报**，把已落地的提交标成 `+`（未落地） |

2026-07-27 单日踩到 **3 次**：`codex/processon-virtual-scroll`、
`fix/processon-collision-archive`、`feat/article-ppt-quality-contracts` 都被
`git cherry` 报有 3–4 个未落地提交，实测文件内容 **100% 已在 main**。

### 可靠判据：比文件内容，不比提交

```bash
BRANCH=<要检查的分支>
git diff --name-only origin/main...$BRANCH | while read -r f; do
  git diff --quiet "$BRANCH" origin/main -- "$f" || echo "真有差异: $f"
done
```

无输出即表示分支内容已全部落地，可安全 `git branch -D` 删除。

再补两个交叉验证：

```bash
# 1. 有没有只存在于分支、main 上没有的文件
git diff --name-only "$BRANCH" origin/main | while read -r f; do
  git show "origin/main:$f" >/dev/null 2>&1 || echo "main 缺少: $f"
done

# 2. main 上有没有对应的 squash 提交（按关键词搜）
git log --oneline origin/main --since=<分支最后提交日期> | grep -i <关键词>
```

### 注意方向

`git diff --stat $BRANCH origin/main` 常显示大量删除行——那通常是**分支落后于
main**（缺了 main 后来的改动），不是分支有独家内容。判断「能否删除」只看上面
第一个循环的输出。

### 确有未落地内容时

不要直接删。先判断它是否与 main 现行设计冲突（可能是已被推翻的旧方案），
需要保留就开 PR 合并；确认放弃再删，并留存可还原的存档：

```bash
git bundle create <名>.bundle "$BRANCH"      # git clone <file> 可完整还原
git diff origin/main..."$BRANCH" > <名>.patch # git apply 可直接打回
```

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
claude plugin update soia-pkm-vault@soia   # 交付走插件市场，勿装全局
```

Forbidden outside local testing:

```bash
npx skills add /absolute/local/path/to/soia-open-pkm-vault-skills -g -a '*' -s <skill-name> -y
```

If validating SOIA AI consumption, sync from `~/.agents/skills` into
`~/.soia/skills` with `soia-dev-sync-skills`; do not copy directories manually.

## New Skill Lifecycle: Branch → Main → Install

When creating new skills, follow this sequence exactly. Do not skip steps or
shortcut with manual symlinks.

### 1. Create on a branch

```bash
cd <your-local-checkout>/soia-open-pkm-vault-skills
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

### 4. Publish through the plugin marketplace

Skills reach users through the SOIA plugin marketplace, not through a global
`npx skills add -g`. Once the change is on main:

1. **Bump `version`** in `.claude-plugin/plugin.json` and
   `.codex-plugin/plugin.json`. This is mandatory. Claude Code compares the
   plugin `version` field, not the marketplace sha pin — without a bump,
   `claude plugin update` answers "already at the latest version" and users
   never receive the change even though the pin moved.
2. **Refresh the marketplace sha pin** in the meta repo `soia-open-skills`.
   Its `main` is protected, so the refresh has to go through a PR; CI cannot
   push it. The `soia-meta-skill-release` skill drives the whole sequence —
   say 「发布技能」 or 「更新插件」 rather than running the steps by hand.
3. **Users update** with `claude plugin update soia-pkm-vault@soia` or
   `codex plugin add soia-pkm-vault@soia`.

Do not install SOIA skills into your own `~/.agents/skills` with
`npx skills add -g`. That directory is reserved for a small set of third-party
skills; a SOIA skill placed there becomes a second copy that drifts from the
plugin version and appears twice in every agent's index. (End users who prefer
per-skill installs may still use the npx route — see `docs/install/` in the
meta repo. That is a consumer choice, not the maintainer's delivery path.)

### 5. Refresh WorkBuddy experts if the domain has one

Three domains (`soia-pkm-vault`, `soia-media-content`, `soia-cwork-office`) are
also packaged as WorkBuddy experts. Their skill sets are **copies made at
generation time**, not live references — a skill added, renamed, or deleted in
one of those repos does not reach WorkBuddy until the generator reruns:

```bash
python3 scripts/generate_workbuddy_experts.py
```

The expert package is rebuilt as a whole directory, so a deleted skill really
disappears rather than lingering. `experts/` in the meta repo holds only the
definitions (persona, display metadata, avatar); definitions are validated by
`tests/test_workbuddy_experts.py` in CI, while the final verdict comes from
WorkBuddy's own `expert-manager` toolkit, which the generator invokes. Details
in [`experts/README.md`](experts/README.md).

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

12. Publish the rename through the plugin marketplace:

```bash
# bump version in .claude-plugin/plugin.json and .codex-plugin/plugin.json first,
# then let soia-meta-skill-release refresh the pin and guide client updates
claude plugin update soia-pkm-vault@soia
```

Renames only reach users after the pin refresh lands on the meta repo's main.
Do not `npx skills add -g` the new names — that puts a drifting second copy in
`~/.agents/skills`.
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

## 域仓与插件对照

| 域仓 | 插件名 | 技能前缀 |
|---|---|---|
| soia-open-dev-skills | soia-dev | `soia-dev-*` |
| soia-open-dev-design-skills | soia-dev-design | `soia-dev-*` |
| soia-open-pkm-vault-skills | soia-pkm-vault | `soia-pkm-*` |
| soia-open-media-content-skills | soia-media-content | `soia-media-*` |
| soia-open-cwork-office-skills | soia-cwork-office | `soia-cwork-*` |
| soia-open-edu-course-skills | soia-edu-course | `soia-edu-*` |
| soia-open-env-skills | soia-env | `soia-env-*` |
| soia-open-skills | soia-meta | `soia-meta-*` |
