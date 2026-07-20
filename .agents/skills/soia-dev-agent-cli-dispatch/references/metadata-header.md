# 代码文件元数据规范 / Code file metadata (MUST)

所有新建或修改的源代码文件（`.rs`、`.ts`、`.tsx`、`.js` 等）顶部必须携带元数据头。

## Rust 文件格式

```rust
//! @created_by  anthropic/claude-opus-4-6
//! @created_at  2026-04-10 16:30:22
//! @modified_by openai/gpt-5.3-codex
//! @modified_at 2026-04-10 17:15:08
//! @version     0.1.0
//! @description User model registry: load/save/merge user-defined models
//! @changelog   Fix builtin key collision guard
```

## TypeScript / TSX 文件格式

```typescript
/**
 * @created_by  anthropic/claude-sonnet-4-6
 * @created_at  2026-04-10 16:30:22
 * @modified_by anthropic/claude-sonnet-4-6
 * @modified_at 2026-04-10 17:15:08
 * @version     0.1.0
 * @description CLI model subcommands: list, show, add, remove
 * @changelog   Add builtin/user source badge to model selector
 */
```

## 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `@created_by` | ✅ | 创建者。人工写名字；AI 写 `<provider>/<model-id>`（如 `openai/gpt-5.3-codex`、`anthropic/claude-opus-4-6`、`google/gemini-2.0-flash`） |
| `@created_at` | ✅ | 创建时间，格式 `YYYY-MM-DD HH:MM:SS`（到秒） |
| `@modified_by` | ✅ | 最后修改者，格式同 `@created_by` |
| `@modified_at` | ✅ | 最后修改时间，格式同 `@created_at` |
| `@version` | ✅ | 文件版本（语义化或提案编号，如 `0.1.0` 或 `0048`） |
| `@description` | ✅ | 文件用途一句话描述 |
| `@changelog` | ✅ | 本次修改的简短说明（新建时写 `Initial creation`） |

## 规则

- **新建文件**：`@created_by` = `@modified_by`，`@created_at` = `@modified_at`
- **修改已有文件**：只更新 `@modified_by`、`@modified_at`、`@changelog`，不动 `@created_*`
- **多人 / 多 Agent 修改**：`@modified_by` 写最后一个修改者
- **时间**：使用执行时的本地时间（不需要时区后缀，默认跟随 workspace 时区）
- **已有文件无元数据头**：修改时补上（`@created_by` / `@created_at` 写 `unknown` / `unknown`）
