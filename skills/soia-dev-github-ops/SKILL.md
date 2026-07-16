---
name: soia-dev-github-ops
description: Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates. Triggers：「看下这个 PR」「查 CI 为什么挂了」「列 issue」「合并/评审 PR」「发个 release」「check GitHub PR/checks」
version: 1.0.0
created_at: 2026-07-09 07:45:34
updated_at: 2026-07-09 19:32:52
created_by: zp
updated_by: zp / claude opus 4.6
---

# soia-dev-github-ops

Use this skill when the user asks to inspect or operate GitHub state: issues,
pull requests, checks, reviews, workflow run logs, labels, releases, or PR
lifecycle actions.

Do not use it for local-only git work such as commits, rebases, branch cleanup,
or worktree management unless a GitHub operation is also required.

## 客户可读说明

### 这个技能可以做什么

Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
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
  dispatch against production, or any action that closes public work.
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
