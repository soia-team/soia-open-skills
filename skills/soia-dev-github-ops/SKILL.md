---
name: soia-dev-github-ops
description: Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates. Triggers：「看下这个 PR」「查 CI 为什么挂了」「列 issue」「合并/评审 PR」「发个 release」「check GitHub PR/checks」
---

# soia-dev-github-ops

Use this skill when the user asks to inspect or operate GitHub state: issues,
pull requests, checks, reviews, workflow run logs, labels, releases, or PR
lifecycle actions.

Do not use it for local-only git work such as commits, rebases, branch cleanup,
or worktree management unless a GitHub operation is also required.

## Safety Model

- Read-only `gh` queries may run once the target repo is known.
- Mutating operations require clear user intent in the current request.
- High-impact operations require an explicit final confirmation before running:
  `gh pr merge`, `gh release create`, branch deletion, label deletion, workflow
  dispatch against production, or any action that closes public work.
- Use `gh auth status` before operations. If auth is missing or expired, stop
  and tell the user what needs to be configured.
- Never put GitHub tokens in `SKILL.md`, shell history, scripts, issue bodies,
  PR bodies, or comments. Use `gh auth login` or the user's private environment.

## Repo Resolution

Resolve the target repository in this order:

1. Explicit command argument: `--repo <owner>/<repo>`.
2. Current git remote if the command runs inside a GitHub checkout.
3. Environment variable: `GITHUB_REPOSITORY=<owner>/<repo>`.
4. Optional private config: `~/.config/soia-dev-github-ops/env`.
5. Ask the user if the repo is still ambiguous.

The optional config file is a user-owned shell env file, for example:

```bash
GITHUB_REPOSITORY=<owner>/<repo>
```

Load it only when needed:

```bash
set -a
source ~/.config/soia-dev-github-ops/env
set +a
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
  --json name,state,conclusion,startedAt,completedAt,link

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

## Output Checklist

Before final response:

- State the resolved repo and how it was resolved.
- Separate facts from inference when summarizing failures.
- Include exact PR/issue/run/release identifiers.
- For mutating operations, say what changed and include the resulting URL or id.
- For blocked auth or permission, say which `gh` command failed and what the user
  must configure.
