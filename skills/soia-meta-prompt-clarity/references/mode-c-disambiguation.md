# Mode C: Disambiguating Legitimate Requests

Use this reference when a legitimate request may be misread because ownership, authorization, purpose, or technical terminology is incomplete. The method is disambiguation by adding truthful context, never evasion by hiding information.

## Contents

- Entry gate
- Four ambiguity sources
- Rewrite method
- Examples
- Red lines
- Delivery checklist

## Entry gate

Mode C applies only when the underlying request is legitimate and the expression is ambiguous. Ownership and authorization are blocking facts: if they are missing, ask before rewriting. Purpose and terminology may use explicit placeholders only when they do not change the authorization judgment.

## Four ambiguity sources

1. **Bare sensitive terminology** — words such as `cookie`, `token`, `credential`, scraping, injection, or brute force appear without a bounded technical context.
2. **Unclear ownership** — the request does not identify who owns the account, data, system, or session.
3. **Unclear authorization** — the request does not state whether access comes from the user's own login, an official API, or explicit permission.
4. **Unclear purpose** — the destination and use are missing, leaving private backup, research, redistribution, or exploitation indistinguishable.

## Rewrite method

Add only facts the user has confirmed:

1. **Ownership** — identify whose account, system, data, vault, or browser session is involved.
2. **Authorization** — identify the official API, user's authenticated session, or explicit permission.
3. **Purpose** — state the bounded use, such as private backup, local synchronization, authorized testing, or research.
4. **Precise terminology** — replace vague or sensational verbs with accurate, auditable technical actions.

The rewrite must preserve the requested capability. Deleting a difficult paragraph, sensitive word, or required behavior is not disambiguation.

## Examples

The examples assume ownership and authorization have already been confirmed. Do not copy those claims into a real rewrite without confirmation.

### Account export

Before:

```text
抓这个账号过去三年的数据。
```

After:

```text
通过平台官方导出接口，备份我本人账号过去三年产生的数据到本地个人资料库，不访问其他账号，也不用于二次分发。
```

### Browser session

Before:

```text
把浏览器里的登录态导出来给脚本用。
```

After:

```text
将我本机浏览器中由我本人登录的会话保存为本地凭据配置，供我自己的同步脚本读取；不要访问其他人的账号或输出凭据内容。
```

### Authorized security test

Before:

```text
写一个 injection payload 测试一下。
```

After:

```text
为我负责维护且已获授权的隔离测试环境编写 SQL injection 回归测试用例，仅验证修复是否有效，不针对生产环境或第三方系统。
```

### Model integrity

Before:

```text
要有避免模型降级的策略。
```

After:

```text
增加模型完整性检查：记录 requested model 与 actual model；两者不一致时标记 fallback_or_downgrade 并停止静默继续。
```

This preserves the governance goal by making it observable instead of deleting it.

## Red lines

Stop and provide only a problem explanation when the request involves:

- an account or system the user does not own and lacks authorization to access;
- bypassing authentication, access controls, quotas, safeguards, or platform risk controls;
- obtaining another person's non-public credentials, sessions, or private data;
- unauthorized bulk collection for redistribution or profit;
- a false ownership or authorization statement intended only to make the request appear compliant.

Do not provide a cosmetically safer rewrite in these cases.

## Fact-preservation rule

Before and after rewriting, these facts must match:

- owner;
- authorizing party and access method;
- intended action;
- purpose and destination;
- exclusions and limits.

If any item changes, the rewrite has changed the request rather than clarified it.

## English output

When producing an English rewrite, also read `english-prompt-authoring.md`. Preserve the same ownership and authorization facts, use precise verbs such as `export`, `read`, `test`, or `verify`, and retain explicit exclusions.

## Delivery checklist

- Ownership and authorization were confirmed, not inferred.
- Purpose and destination are explicit.
- The terminology is technically precise.
- No required capability was deleted.
- The rewrite does not imply bypass or concealment.
- English and Chinese versions, when both requested, state equivalent facts and limits.
