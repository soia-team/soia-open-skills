# SOIA 技能安装指南

[English](README.en.md) · [按使用场景选择安装组合](../install-profiles.md)

截至 2026-07-25，SOIA 的 8 个开源仓库共提供 73 个技能。安装有两条彼此独立的路线：通用的 `npx skills`，以及部分宿主支持的插件市场。

## 两条安装路线

| | 路线 A：`npx skills` | 路线 B：插件市场 |
|---|---|---|
| 适用宿主 | 所有受支持宿主 | Claude Code、Codex、Qwen Code、qodercli |
| 安装粒度 | 单技能或整仓技能 | 整个领域插件 |
| 技能本体位置 | 永远先进入 `~/.agents/skills` | 各宿主自己的插件缓存，不进入 `~/.agents/skills` |
| 宿主入口 | `-a` 决定链接到哪些 AI 目录 | 由宿主的插件配置管理 |
| 适合场景 | 跨宿主使用、按技能选择 | 按领域安装和启停 |

### 路线 A 的真实机制

下面的命令即使只写 `-a claude-code`，技能本体也会先进入全局目录 `~/.agents/skills`：

```bash
npx skills add soia-team/<仓库名> -g \
  -a claude-code -s <技能名> -y
```

`-a` 只决定为哪些宿主建立入口，不能实现“只安装到某个 AI、但不进入全局目录”。`-a '*'` 表示为所有受支持宿主建立入口。

`--copy` 只把目标 AI 目录中的软链接改成实体副本，仍不会绕过 `~/.agents/skills`。Claude Code 的目标目录可使用实体副本；Codex 直接读取全局目录，因此 `--copy` 对 Codex 的读取路径没有作用。

### 路线 B 的真实机制

插件市场把领域插件安装到宿主自己的缓存，不写入 `~/.agents/skills`：

- Claude Code：`~/.claude/plugins/cache/<市场>/<插件>/<sha>/`
- Codex：`~/.codex/plugins/cache/<市场>/<插件>/`

Claude Code 的 npx 技能目录与插件缓存是两条独立通道。Codex 插件则是对 `~/.agents/skills` 的**叠加**：安装、移除或切换 Codex 插件都不会减少 Codex 已从全局目录读到的技能。

## 我用哪条路线

| 你的需求 | 建议 |
|---|---|
| 同一批技能要给多个 AI 使用 | 路线 A |
| 只安装一个或少量技能 | 路线 A，用 `-s <技能名>` |
| 安装某仓全部技能并覆盖所有宿主 | 路线 A，用 `--all --full-depth` |
| 在 Claude Code 中按领域启停，停用后不产生该插件的上下文成本 | 路线 B |
| 团队要把 Claude 项目插件配置提交到版本库 | 路线 B，使用 `project` 作用域 |
| 想用 Codex 插件减少全局技能索引 | 不可行；Codex 插件只会叠加 |
| 使用 Cursor、Windsurf、Copilot、Zed、Gemini、Kimi 等其他宿主 | 路线 A |

## 路线 A：npx 安装

安装一个技能并为所有宿主建立入口：

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

只为指定宿主建立入口：

```bash
npx skills add soia-team/<仓库名> -g \
  -a claude-code codex cursor -s <技能名> -y
```

可用的 agent id 包括 `claude-code`、`codex`、`cursor`、`windsurf`、`qwen`、`kimi`、`opencode`、`copilot`、`qoder`、`trae`、`agy`、`gemini`、`zed` 等。无论选择哪个 id，技能本体都在 `~/.agents/skills`。

安装仓库中的全部技能并覆盖全部 agent：

```bash
npx skills add soia-team/<仓库名> -g --all --full-depth
```

常用管理命令：

```bash
npx skills ls -g
npx skills ls -g -a claude-code --json
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
npx skills find <关键词>
npx skills use soia-team/<仓库名>@<技能名>
```

`skills use` 只生成使用该技能的提示词，不执行安装。

## 路线 B：插件市场

SOIA 市场提供 8 个领域插件：

```text
soia-dev
soia-dev-design
soia-cwork-office
soia-pkm-vault
soia-media-content
soia-edu-course
soia-env
soia-meta
```

Claude Code：

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install soia-pkm-vault@soia --scope user
```

Codex：

```bash
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add soia-pkm-vault@soia
```

Claude Code 的完整作用域和管理命令见 [Claude Code 指南](claude-code.md)。Codex 的叠加机制和生命周期命令见 [Codex 指南](codex.md)。

## 宿主读取机制

| 宿主 | npx 后的读取方式 | 是否需要宿主入口 |
|---|---|---:|
| Codex、Zed、Cursor、Copilot、Gemini、DeepCode | 原生直读 `~/.agents/skills` | 否 |
| Claude Code | 读取 `~/.claude/skills` | 是，由 `-a claude-code` 建立 |
| Windsurf、Trae、WorkBuddy、Kimi、OpenCode、qodercli | 读取各自目录 | 是，需要同步软链接 |
| Qwen Code、Antigravity (`agy`) | 使用对应 npx agent id 建立入口 | 是 |

原生直读 `~/.agents/skills` 的宿主不需要额外同步。对需要独立目录的宿主，`-a` 或同步工具只建立入口；全局技能本体仍保留在 `~/.agents/skills`。

## 各 AI 安装指南

| AI | npx agent id / 入口 | 插件路线 | 指南 |
|---|---|---:|---|
| Claude Code | `claude-code` | 支持 | [查看](claude-code.md) |
| Codex | `codex`；直读全局 | 支持，且只做叠加 | [查看](codex.md) |
| Qwen Code | `qwen` | 支持 | [查看](qwen-code.md) |
| qodercli | `qoder` | 支持 | [查看](qodercli.md) |
| Cursor | `cursor`；直读全局 | — | [查看](cursor.md) |
| Windsurf | `windsurf` | — | [查看](windsurf.md) |
| GitHub Copilot | `copilot`；直读全局 | — | [查看](copilot-cli.md) |
| Zed | `zed`；直读全局 | — | [查看](zed.md) |
| Gemini CLI | `gemini`；直读全局 | — | [查看](gemini-cli.md) |
| Antigravity (`agy`) | `agy` | — | [查看](antigravity-agy.md) |
| Kimi CLI | `kimi` | — | [查看](kimi-cli.md) |
| OpenCode | `opencode` | — | [查看](opencode.md) |
| DeepCode | 直读全局 | — | [查看](deepcode.md) |
| WorkBuddy | 同步软链接 | — | [查看](workbuddy.md) |
| Trae | `trae` | — | [查看](trae.md) |
| SOIA AI | 宿主配置 | — | [查看](soia-ai.md) |

## 验证与排错

先确认全局本体：

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g
```

再检查需要独立入口的宿主，例如 Claude Code：

```bash
ls -ld ~/.claude/skills/<技能名>
```

若当前会话未发现新技能，重新启动宿主会话。不要把目标 AI 目录中的链接误认为技能本体；更新和全局卸载应使用 `npx skills update -g` 与 `npx skills remove -g ...`。
