---
name: soia-dev-github-ops
description: Use gh CLI for GitHub issue/PR/checks/review/run/release/collaborator ops, pre-merge rule review, and author-side fix-the-review. Triggers：「看下这个 PR」「查 CI 挂了」「合并/评审 PR」「发 release」「加协作者权限」「审核 PR 该不该合」「帮我修复这个 PR」
version: 2.1.0
created_at: 2026-07-09 07:45:34
updated_at: 2026-07-22 11:53:19
created_by: claude opus 4.6
updated_by: claude fable 5
dependencies:
  hard: [soia-dev-review-panel, soia-dev-fix-loop]
---

# soia-dev-github-ops

Use this skill when the user asks to inspect or operate GitHub state: issues,
pull requests, checks, reviews, workflow run logs, labels, releases, or PR
lifecycle actions.

Do not use it for local-only git work such as commits, rebases, branch cleanup,
or worktree management unless a GitHub operation is also required.

## 客户可读说明

### 这个技能可以做什么

Use gh CLI for GitHub issue, PR, checks, review, workflow run, release, and collaborator-permission operations, plus a pre-merge rule-review procedure and an author-side "address a review and fix it" procedure, with structured JSON output and safety gates

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
| 给某个人加/查/撤仓库协作者权限 | 先确认目标仓库、用户名、权限级别，再执行 `gh api` 写操作并核实生效 | 权限级别说明、确认清单、生效核实结果 |
| 合并前想知道这个 PR 符不符合规则 | 拉 diff + 这个仓库自己的规则文件，交叉核对后给分档建议；不自动合并 | 一句话结论、按阻断/应改/无异议分档的发现清单、CI 与 mergeable 状态 |
| 收到评审意见（贴 PR/评审 URL 说"帮我修复"）| 拉取评审（含行内 + 会话评论）→ checkout 分支 → 委托 fix-loop 逐条修 → push 回原分支并请求重审；不自动合并 | 每条意见的处理状态、验证证据、push 结果、请求重审回执 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. Agent 先判断是否命中本技能，再检查依赖、配置、权限和风险动作。
3. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。
4. 执行后验证真实输出，不用“看起来成功”代替证据。
5. 最终回复必须给客户可见总结：做了什么、日志摘要、文件变化、问题和下一步。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-github-ops -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-github-ops/config.yml
SOIA_DEV_GITHUB_OPS_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- 强依赖、可选依赖和第三方 skill 关系必须以本 `SKILL.md` 后续的“依赖 / 前置 / 资源 / 边界”说明为准；没有写清楚时，先补说明或询问客户，不要猜。
- 第三方 skill 只能声明依赖和安装方式，不直接修改第三方 skill 文件。

### 日志与完成回执

每次执行都要让客户看见过程和结果。最低回执格式：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <检查到的输入/配置/依赖，不打印秘密值>
- processed: <数量或范围>
- created/updated: <数量或路径>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <运行过的检查、命令或人工核对点>

问题与下一步：
- <缺 key / 缺依赖 / 需要客户确认 / 建议下一条命令；没有则写“无”>
```

## Safety Model

- Read-only `gh` queries may run once the target repo is known.
- Mutating operations require clear user intent in the current request.
- High-impact operations require an explicit final confirmation before running:
  `gh pr merge`, `gh release create`, branch deletion, label deletion, workflow
  dispatch against production, granting/revoking a collaborator's permission,
  or any action that closes public work or changes who can write to a repo.
- Collaborator permission changes are the single most sensitive operation this
  skill performs — more sensitive than `gh pr merge`. A bad merge affects one
  change; a wrong permission grant is a standing capability the person keeps
  using until someone notices and revokes it. Never infer the target repo,
  username, or permission level from prior conversation turns alone — restate
  all three and get explicit confirmation in the current exchange before the
  write call. See "Collaborator Access Management" below for the full gate.
- Use `gh auth status` before operations. If auth is missing or expired, stop
  and tell the user what needs to be configured.
- Never put GitHub tokens in `SKILL.md`, shell history, scripts, issue bodies,
  PR bodies, or comments. Use `gh auth login` for credentials; keep only non-token
  defaults in the skill-specific private config.

## Repo Resolution

Resolve the target repository in this order:

1. Explicit command argument: `--repo <owner>/<repo>`.
2. Current git remote if the command runs inside a GitHub checkout.
3. Environment variable: `GITHUB_REPOSITORY=<owner>/<repo>`.
4. Optional private config: `~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-github-ops/config.yml`.
5. Ask the user if the repo is still ambiguous.

The optional config file is a user-owned YAML file with an `env:` mapping, for example:

```yaml
env:
  GITHUB_REPOSITORY: "<owner>/<repo>"
```

Do not hardcode maintainer-specific repositories in reusable commands.

## Query Patterns

Prefer `--json` and `--jq` for agent-readable output.

```bash
# Auth and repo sanity checks
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef,isPrivate

# Open PRs
gh pr list --repo <owner>/<repo> --state open \
  --json number,title,state,author,headRefName,baseRefName,updatedAt

# Single PR status
gh pr view <number> --repo <owner>/<repo> \
  --json number,title,state,mergeable,mergeStateStatus,reviewDecision,headRefName,baseRefName

# PR checks
gh pr checks <number> --repo <owner>/<repo> \
  --json name,state,bucket,startedAt,completedAt,link

# Issues
gh issue list --repo <owner>/<repo> --state open \
  --json number,title,state,labels,assignees,updatedAt

# Workflow runs
gh run list --repo <owner>/<repo> --limit 20 \
  --json databaseId,status,conclusion,workflowName,headBranch,createdAt,url
```

When reporting results, include:

- repo: `<owner>/<repo>`
- object: PR / issue / run / release
- identifier: number, run id, or tag
- status: open / closed / merged / passing / failing / cancelled
- next action or blocker

## PR Lifecycle

Create PRs with a concise body containing summary and verification evidence.

```bash
gh pr create --repo <owner>/<repo> \
  --base <base-branch> \
  --head <feature-branch> \
  --title "<type>: <short change>" \
  --body "$(cat <<'EOF'
## Summary
- <what changed>

## Verification
- <command>: <result>
EOF
)"
```

Review operations:

```bash
gh pr review <number> --repo <owner>/<repo> --approve --body "<review note>"
gh pr review <number> --repo <owner>/<repo> --request-changes --body "<required changes>"
gh pr comment <number> --repo <owner>/<repo> --body "<comment>"
```

Before merge:

```bash
gh pr view <number> --repo <owner>/<repo> \
  --json mergeable,mergeStateStatus,reviewDecision,statusCheckRollup \
  --jq '{mergeable, mergeStateStatus, reviewDecision, checks: .statusCheckRollup}'
```

Only merge after explicit confirmation:

```bash
gh pr merge <number> --repo <owner>/<repo> --squash --delete-branch
```

## Pre-Merge Rule Review

Use for: "审核下这个 PR 该不该合" / "这个 PR 符不符合规则，帮我看看" / a bare PR
list URL the user wants reviewed / "review 一下 `<repo>` 的 pull/`<n>`".

The output of this procedure is advice, not a merge trigger. The user
reviews the findings and decides. A request to review is not a request to
merge — this holds even if the same message also pre-authorizes merging
("review PR 42, merge it if it's fine"). Pre-authorization is conditional on
findings the user has not seen yet, so it cannot substitute for the
confirmation Safety Model requires before `gh pr merge`. Always post the
graded findings from Step 4 first, then treat the next message as the actual
merge confirmation — never merge in the same turn the report is produced.

### Step 0 — Resolve which PR

If the user gave a PR list URL or repo without a specific number, list the
open PRs first and ask which one to review — do not guess:

```bash
gh pr list --repo <owner>/<repo> --state open \
  --json number,title,author,updatedAt
```

### Step 1 — Pull the facts (read-only, no confirmation needed)

```bash
gh pr view <number> --repo <owner>/<repo> \
  --json title,body,author,baseRefName,headRefName,state,additions,deletions,changedFiles,labels,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup

gh pr diff <number> --repo <owner>/<repo>

gh pr checks <number> --repo <owner>/<repo> --json name,state,bucket
```

### Step 2 — Find this repo's own rules (do not borrow another repo's)

These four are the common ones, but they aren't the full list for every repo —
list the actual root directory and check for any `*_SPEC.md`/`*.md` rule file
by name, not just these:

- `CLAUDE.md` / `AGENTS.md` — agent behavior conventions
- `CONTRIBUTING.md`
- `.github/PULL_REQUEST_TEMPLATE.md` — if it has a checklist, the PR body
  should address each item
- If the changed files live under a subdirectory that has its own
  `AGENTS.md`/`README.md` (common in this org's repos: "read the zone's own
  rules before touching it"), read that too

This org's skill repos in particular also carry `SKILL_SPEC.md` (skill
authoring rules — version bump discipline, frontmatter requirements),
`DATA_STORAGE_SPEC.md` (where credentials/config/cache may and may not live),
and `THIRD_PARTY_NOTICES.md` (any new adapted code or dependency must be
registered there) — check for these by name specifically when the PR's repo
is one of the `soia-*-skills` repos, since a diff that skips registering a
new third-party adaptation is a real, previously-seen failure mode here, not
a hypothetical one.

If no rule file exists, say so plainly in the final report instead of
inventing rules from memory of other repositories.

### Step 3 — Hand off to soia-dev-review-panel for the actual cross-check

Do not re-derive a review checklist here. Use `soia-dev-review-panel`'s code
lens group (correctness/self-verification, security, test coverage & anti-fake-fix,
scope & consistency) against the diff from Step 1, with the rule files from
Step 2 as its "rules" input for the scope/consistency lens. That skill also
owns the "open the real file, don't trust the diff snippet" discipline and
the graded-confidence (seen/inferred/unconfirmed) finding format — this
procedure doesn't maintain a second copy of either.

If `soia-dev-review-panel` isn't installed, stop and tell the user to install
it (`npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-review-panel -y`)
rather than falling back to an ad-hoc checklist.

### Step 4 — Report

Use `soia-dev-review-panel`'s Step 5 output as the body of the reply (verdict
first, findings by tier, coverage notes), plus these two additions that are
specific to this GitHub procedure and not part of the generic methodology:

- CI/mergeable status from Step 1 — report what was actually observed, don't
  re-guess it.
- Explicit handoff: "the merge decision is yours" — never follow this report
  with `gh pr merge` in the same turn, even if the original request
  pre-authorized merging; wait for the user's next message after they have
  seen the findings.

## Address Review Feedback (author side)

Use when the user is the PR *author* and hands you a review to act on: "帮我修复
这个 PR" / "把这个评审意见改了" / a PR or review URL with "按评审改一下" /
"reviewer 要我改的都改了". This is the mirror image of Pre-Merge Rule Review:
that one produces advice for a reviewer; this one consumes a reviewer's advice
and turns it into pushed fixes. It never merges — see Step 5.

### Step 0 — Resolve the PR and pull the review as findings

From a PR URL, a review URL (`.../pull/<n>#pullrequestreview-<id>`), or a bare
number, resolve `<owner>/<repo>` and `<n>`, then fetch the review text. The
review body, inline diff comments, AND plain conversation-tab comments are all
findings input — they live on three separate endpoints, so fetch all three
(a reviewer's ask typed in the conversation box is an *issue* comment, not a
PR review comment, and is easy to miss):

```bash
gh pr view <n> --repo <owner>/<repo> \
  --json number,title,headRefName,baseRefName,state,reviewDecision,url,isCrossRepository,headRepositoryOwner,maintainerCanModify
# review summaries (CHANGES_REQUESTED / COMMENTED / APPROVED), newest last:
gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews \
  --jq '.[] | {id, user: .user.login, state, body}'
# inline diff comments (file + line + body), often where the real detail is:
gh api --paginate repos/<owner>/<repo>/pulls/<n>/comments \
  --jq '.[] | {path, line, user: .user.login, body}'
# conversation-tab comments (no file/line) — a third, disjoint channel:
gh api --paginate repos/<owner>/<repo>/issues/<n>/comments \
  --jq '.[] | {user: .user.login, body}'
```

`--paginate` matters: without it `gh api` returns only the first 30 items, so a
heavily-reviewed PR would silently drop later comments. Normalize every
distinct point the reviewer raised into one finding with a stable id, severity
(take the reviewer's tier if given), file:line, and the quoted ask. If a review
URL was given, prioritize that specific review's body; still scan the other two
channels, since detail and follow-up asks land there too.

### Step 1 — Get onto the PR branch (do not fix on the wrong branch)

Precondition: you must be inside a local clone of `<owner>/<repo>` — `gh pr
checkout` checks out into the current repo, it does not clone. If cwd is not a
clone of that repo, `cd` into one or clone it first; running `gh pr checkout`
from an unrelated repo silently checks the PR out against the wrong remote.

```bash
gh pr checkout <n> --repo <owner>/<repo>
git status -sb   # confirm you are on <headRefName>, clean tree
```

If the PR head is on a fork you cannot push to (`isCrossRepository: true` and
`maintainerCanModify: false` when you are not the fork owner), stop and say so
— the fix would have nowhere to go. If the local tree is dirty, stop and
surface it rather than fixing on top of unrelated uncommitted work.

### Step 2 — Hand the findings to soia-dev-fix-loop

Do not invent a fix procedure here. Pass the normalized findings from Step 0 to
`soia-dev-fix-loop`, which runs the reproduce → decide (fix/reject/defer) →
minimal-fix → regression + independent recheck → receipt loop, applying
`soia-dev-coding-protocol`'s anti-fake-fix discipline during the edits. This
skill owns none of that — it only supplies the findings and the checked-out
branch.

If `soia-dev-fix-loop` isn't installed, stop and tell the user to install it
(`npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-fix-loop -y`)
rather than hand-rolling a fix loop.

A reviewer finding is a claim, not a verdict: fix-loop may legitimately
`reject` one with evidence or `defer` it with a tracked follow-up. Do not
silently skip any — every point the reviewer raised must end with a fix,
reject, or defer that you can show.

### Step 3 — Optional self-review before pushing

If the fixes are non-trivial, run `soia-dev-review-panel` over your own diff
(`git diff origin/<baseRefName>...HEAD` — use the remote-tracking base ref,
which is present after checkout, rather than a bare `<baseRefName>` that may not
exist locally) with its code lens group + adversarial verification, so you
catch your own regressions before the reviewer does. Higher first-pass
acceptance, fewer round-trips.

### Step 4 — Push back to the PR branch

Commit with a message that references which review points it addresses, then
push — this updates the existing PR, never opens a new one:

```bash
git push
```

Use a bare `git push`, not `git push origin <headRefName>`: after `gh pr
checkout` the branch is already configured to track the correct remote
(the fork for a cross-repo PR, `origin` for a same-repo PR), and `git push
origin ...` would push to the wrong repo for a fork PR — silently creating a
stray branch on the base repo without updating the PR. Pushing to an open PR's
branch is an externally visible update to shared work, so confirm the diff with
the user before pushing if they haven't already told you to push in this
exchange.

### Step 5 — Request re-review, do NOT merge

The author does not merge their own PR that a reviewer marked
`CHANGES_REQUESTED` — that bypasses the exact gate the reviewer just raised.
After pushing, re-request review and hand back:

```bash
gh pr edit <n> --repo <owner>/<repo> --add-reviewer <reviewer-login>
# or leave a comment summarizing what was addressed:
gh pr comment <n> --repo <owner>/<repo> --body "<per-finding: fixed / rejected+why / deferred+where>"
```

Report: fix-loop's receipt (each finding → fixed/rejected/deferred with
evidence), the push result, and that re-review has been requested. State
explicitly that merging is the reviewer's call, not this procedure's — even if
the author has write/admin permission and could merge. Only merge if the user,
in a later message after seeing this report, explicitly says to.

## CI Failure Triage

Use this order:

1. Identify the failing run and job.
2. Read the first actionable error in the failed log.
3. Classify the failure.
4. Reproduce locally only if the repo has enough context and the command is safe.
5. Report the exact failing command, file, or external blocker.

```bash
gh run view <run-id> --repo <owner>/<repo> --json status,conclusion,workflowName,jobs,url
gh run view <run-id> --repo <owner>/<repo> --log-failed
```

Common classes:

| Class | Signal | Next step |
|---|---|---|
| Compile | compiler, typecheck, or lint error | Read the first error and map to file/line |
| Test | assertion failure or failing test name | Reproduce that test locally if possible |
| Environment | missing tool, package, or cache | Check setup steps and runner image |
| Permission | `Resource not accessible` or denied secret | Check workflow permissions and fork context |
| Quota/timeout | quota message or cancelled after timeout | Report external limit or split work |

## Release Operations

Release creation is a publish action. Prepare the command, show the tag/name/body
summary, and ask for explicit confirmation before running:

```bash
gh release create <tag> --repo <owner>/<repo> \
  --title "<release title>" \
  --notes-file <notes-file>
```

After release, verify:

```bash
gh release view <tag> --repo <owner>/<repo> \
  --json tagName,name,isDraft,isPrerelease,publishedAt,url
```

## Collaborator Access Management

Use for: "给 `<user>` 在 `<repo>` 加个能提交 PR 的权限" / "把 xxx 加到这个仓库" /
"看看这个仓库现在有哪些协作者" / "把 xxx 从这个仓库移除".

### Permission levels

GitHub collaborator permissions, narrowest to broadest:

| Level | Grants | Typical fit |
|---|---|---|
| `pull` | Read-only; can fork and open cross-fork PRs | External contributor on a private repo — on a public repo, anyone can already fork and PR without being added at all |
| `triage` | `pull` + manage issue/PR labels and assignees, no code writes | Triage-only, no code access |
| `push` | `triage` + push branches, open PRs from branches in the repo itself | What "能提交 PR 的权限" usually means |
| `maintain` | `push` + manage some repo settings (not sensitive ones, not collaborators) | Needs to manage issue templates/wiki, not full admin |
| `admin` | Full control: delete repo, manage collaborators, manage secrets | Rare; treat as a distinct, higher-bar request |

Default rule: when the user says "加个能提交 PR 的权限" without naming a
level, confirm whether the person is an internal collaborator (→ `push`)
or an external contributor (→ usually no grant needed on a public repo;
on a private repo, `pull` or `triage` is enough to see the repo and open
PRs against it — `push` is more than they need). Do not default to `push`
without asking when it's ambiguous which case this is. Never grant
`maintain`/`admin` unless the user names that level explicitly.

### Commands

```bash
# List current collaborators and their permission (read-only, always safe)
gh api repos/<owner>/<repo>/collaborators \
  --jq '.[] | {login: .login, permission: .role_name}'

# Look up one person's current permission (read-only)
gh api repos/<owner>/<repo>/collaborators/<username>/permission \
  --jq '{permission: .permission, role_name: .role_name}'

# Grant or change a collaborator's permission (write — see Safety Gate below)
gh api repos/<owner>/<repo>/collaborators/<username> \
  -X PUT -f permission=<pull|triage|push|maintain|admin>

# Remove a collaborator (write — same Safety Gate)
gh api repos/<owner>/<repo>/collaborators/<username> -X DELETE
```

### Safety Gate

This is the one operation in this skill that never runs on inferred intent —
restate and get explicit confirmation on all of the following in the current
exchange before the write call:

- Target repo: `<owner>/<repo>`
- Target user: the actual GitHub username, not a display name or email —
  if you only have an email or display name, resolve the username first
  (`gh api "search/users?q=<query>"` — note the query goes in the URL so `gh
  api` stays a GET; passing it via `-f` would switch the call to a POST and
  fail — or ask the user) rather than guessing the spelling
- Permission level: `pull` / `triage` / `push` / `maintain` / `admin`
- If revoking: confirm this removes their direct collaborator access —
  it does not close their open PRs/branches (this skill does not cascade
  that cleanup), and it does not touch access granted through org Team
  membership, which is a separate permission path this call cannot revoke

Inviting someone to a private repo sends them a GitHub notification/email —
an externally visible action — so the confirmation gate applies even when it
feels like "just adding one person."

### Verify after granting

```bash
gh api repos/<owner>/<repo>/collaborators/<username>/permission \
  --jq '.permission'
```

Confirm the returned value matches what was requested before reporting
success. Do not treat a 2xx response alone as proof the grant took effect:
GitHub's collaborator-add endpoint returns `201` when it creates a pending
invitation (not in effect until the person accepts) versus `204` when it
updates an existing collaborator (in effect immediately) — for a `201`, say
explicitly in the report that access is pending acceptance, not yet active.

### Verify after revoking

```bash
gh api repos/<owner>/<repo>/collaborators/<username> --silent && echo "still a direct collaborator" || echo "removed as direct collaborator"
```

A successful `DELETE` (2xx) only means direct-collaborator access is gone —
it is not proof the person has no access at all. If `<owner>` is an org (not
a personal account), check whether a Team grants them access independently
before reporting "access revoked" as a complete statement:

```bash
gh api orgs/<owner>/teams --jq '.[].slug' \
  | xargs -I{} gh api orgs/<owner>/teams/{}/repos/<owner>/<repo> --silent 2>/dev/null \
    && echo "a team still grants access to this repo — check its membership"
```

If any Team still has access to the repo, report both facts separately:
direct-collaborator access removed, Team-based access (if applicable)
unchanged — do not collapse them into one "access revoked" claim.

## Output Checklist

Before final response:

- State the resolved repo and how it was resolved.
- Separate facts from inference when summarizing failures.
- Include exact PR/issue/run/release identifiers.
- For mutating operations, say what changed and include the resulting URL or id.
- For blocked auth or permission, say which `gh` command failed and what the user
  must configure.
