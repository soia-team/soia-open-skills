# Providers

Keep provider setup generic. Do not store API keys, cookies, tokens, usernames, or personal paths in this file.

## Selection Order

1. User's explicit provider in the current request.
2. CLI argument or `params.provider`.
3. User config file.
4. Environment variable or repo-level private config policy.
5. Safe auto-detection.
6. Generic fallback.

## Credential Rule

- Document variable names only, such as `<YOUR_PROVIDER_KEY>`.
- Public skills must rely on provider-owned login flows or user-owned config outside the repo.
- Private SOIA skills must follow the repo-level `SKILL_SPEC.md` private config/config policy.
- Never read password files, cookies, browser profiles, or private token stores.

## Provider Template

```yaml
provider_name:
  enabled: auto
  command: <command-name>
  auth_check: <safe-readonly-check>
  install_policy: prompt
  home_env: YOUR_SKILL_PROVIDER_HOME
```

## Bootstrap Rule

If a provider is missing:

1. Run a read-only availability check.
2. If installation is safe and requested, install with user-visible commands.
3. If login is required, hand off to the provider's official login flow.
4. If still unavailable, report the exact missing piece and use a documented fallback only when the result remains honest.
