# Private Data and Intermediate Storage Spec

This repository publishes public, advanced skills across domains (PKM, dev
tooling, collaboration, design). Skills here read and write customer data on
local disk and cloud providers, but must not turn the public repository, a
customer-readable report, or an ordinary config file into a credential store.

## Storage classes

| Class | What belongs here | Default location | Retention |
|---|---|---|---|
| Provider credentials | tokens, cookies, refresh tokens, session material | provider-owned login store or OS keychain | controlled by the provider |
| Non-secret config | preferences, provider name, feature flags, user-selected paths | user config directory | until the user removes it |
| Audit state | redacted receipts for machine-changing work | user state directory | bounded and rotated |
| Cache | downloaded metadata and reproducible derived data | user cache directory | safe to delete |
| Temporary data | per-run downloads, extracts, probes, and conversion files | OS temporary directory | remove on success and failure |
| Deliverables | reports or files the customer asked to keep | customer-selected output directory | controlled by the customer |

Read-only skills should stay stateless by default: print a redacted result and
write nothing unless the customer asks for a saved report.

## Canonical locations

Use portable path APIs instead of string-concatenating a home directory.
`templates/skill-template/scripts/resolve_storage.py` is the reference
implementation.

| Purpose | Linux / Unix default | macOS default | Windows default |
|---|---|---|---|
| Config | `${XDG_CONFIG_HOME:-~/.config}/soia-skills/soia-open-skills/...` | same unless the host integration deliberately uses the native app-support directory | `%APPDATA%\soia-skills\soia-open-skills\...` |
| State | `${XDG_STATE_HOME:-~/.local/state}/soia-skills/soia-open-skills/...` | same | `%LOCALAPPDATA%\soia-skills\soia-open-skills\state\...` |
| Cache | `${XDG_CACHE_HOME:-~/.cache}/soia-skills/soia-open-skills/...` | `~/Library/Caches/soia-skills/soia-open-skills/...` | `%LOCALAPPDATA%\soia-skills\soia-open-skills\Cache\...` |
| Temporary | OS temporary directory under a per-run subdirectory | OS temporary directory under a per-run subdirectory | OS temporary directory under a per-run subdirectory |

The following environment variables may override the SOIA roots:

```text
SOIA_SKILLS_CONFIG_HOME
SOIA_SKILLS_STATE_HOME
SOIA_SKILLS_CACHE_HOME
```

These variables name directories, not secret values.

## Credentials and private information

1. Prefer an official provider login command, browser authorization flow, or OS
   keychain. Store only a provider/profile identifier in SOIA config.
2. If a provider supports only a credential file, leave it in the provider's
   documented location and restrict it to the current user. The skill may check
   whether the file exists, but must not print or copy its contents.
3. Do not put passwords, tokens, cookies, session strings, private keys, or
   authorization headers in `config.yml`, CLI arguments, reports, logs, or
   committed fixtures.
4. Environment variables are a compatibility fallback, not the preferred
   long-lived secret store: process listings, crash dumps, or debug logging can
   expose them.
5. Redact credentials, usernames, account identifiers, query strings, local
   private paths, and response bodies before producing logs or receipts.

## Intermediate data lifecycle

- Audit state is allowed only when a machine-changing action needs traceability.
  Keep the action, result, tool/version, and timestamp; omit command output that
  may contain private data. Rotate or bound retained receipts.
- Cache must be reproducible and safe to remove. Never require a cached token to
  recover access.
- Temporary directories must be unique per run, use user-only permissions where
  supported, and be removed in a `finally`/context-manager path after both
  success and failure.
- Files containing private or audit data should use user-only permissions
  (`0600`) and directories should use (`0700`) where the platform supports
  POSIX modes.
- Never use the repository checkout as a runtime state, cache, temp, or
  credential directory.

## Time fields

Customer-facing status tables include `更新时间`. Structured receipts use
`checked_at`.

- Record the time after the final verification that supports the reported row.
- Use RFC 3339 with an explicit timezone, for example
  `2026-07-21T00:00:00+08:00`.
- Do not substitute the skill package's frontmatter `updated_at`; that field is
  the source-code modification time, not the runtime verification time.

## Implementation references

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir/)
- [platformdirs API](https://platformdirs.readthedocs.io/en/stable/api.html)
- [GitHub CLI authentication storage](https://cli.github.com/manual/gh_auth_login)
- [Docker CLI login and credential stores](https://docs.docker.com/reference/cli/docker/login/)
- [Python temporary files and directories](https://docs.python.org/3/library/tempfile.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
