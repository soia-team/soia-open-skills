# SOIA 技能生态安装总指南

[English](install-guide.en.md) · [按使用场景选择安装组合](install-profiles.md)

本指南帮助你按技能粒度、领域粒度或 AI agent 选择 SOIA 技能的安装方式。若不确定从哪里开始，优先使用 `npx skills add`：它覆盖 62+ AI agent，保留单技能粒度，并由统一的锁文件记录安装状态。

## 生态覆盖面

`~/.agents/skills` 已被 Zed、Cursor、Copilot、Codex、Gemini、DeepCode 等宿主原生识别；多数宿主因此零同步即可覆盖。只有 Windsurf 和 Trae 需要显式软链，`soia-meta-sync-skills` 的 targets 已包含对应目标。插件市场方面，同一份 SOIA 市场清单可被 Qwen Code 与 qodercli 复用。

文中的占位符含义如下：

- `<仓库名>`：例如 `soia-open-skills`、`soia-open-dev-coding-skills`。
- `<技能名>`：例如 `soia-meta-prompt-clarity`。
- `<域插件名>`：例如 `soia-pkm-clip`、`soia-dev-coding`。

## 通用方案（推荐起点）

### 1. npx 通用安装：按技能安装

安装一个技能到所有受支持的 agent：

```bash
npx skills add soia-team/<仓库名> -g -a '*' -s <技能名> -y
```

例如：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' \
  -s soia-meta-prompt-clarity -y
```

`-g` 表示用户级安装，`-s` 选择技能，`-y` 跳过交互确认。`-a '*'` 会为所有受支持的 agent 建立入口；也可以只选择具体宿主：

```bash
npx skills add soia-team/<仓库名> -g \
  -a claude-code codex cursor -s <技能名> -y
```

全局安装以 `~/.agents/skills` 为共享真源，各 AI agent 目录通过软链接复用同一份技能，避免复制多份内容。`~/.agents/.skill-lock.json` 记录来源和安装状态，供后续检查与更新使用。

常用管理命令：

```bash
# 查看全局技能
npx skills list -g

# 更新全部全局技能，或只更新一个技能
npx skills update -g
npx skills update <技能名> -g

# 从所有 agent 卸载指定技能
npx skills remove -g -a '*' -s <技能名> -y
```

### 2. 域插件市场：按领域安装

Claude Code、Codex 和 Qwen Code 等支持插件或扩展。一个 SOIA 域插件对应一个领域仓库及其中的全部技能，适合需要整组能力、并希望按领域启用或停用的用户。

以知识剪藏领域为例：

```bash
# Claude Code
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install soia-pkm-clip@soia

# Codex
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add soia-pkm-clip@soia

# Qwen Code
qwen extensions install \
  https://github.com/soia-team/soia-open-skills:soia-pkm-clip
```

插件适合域级开关，npx 适合单技能选择。不要在同一个宿主里用两种方式安装同一批技能，否则可能出现两份索引。

### 3. 按需加载：核心直达，长尾检索

若不希望预装全部领域技能，可先安装路由技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' \
  -s soia-meta-find-skill -y
```

`soia-meta-find-skill` 让高频核心技能保持直达，同时通过公开路由清单检索并加载低频长尾技能。若某个宿主只需要较小的技能集合，还可使用 `soia-meta-sync-skills` 的 `--exclude-skills` 和 `--save-excludes` 保存该宿主的排除列表；完整命令见[同步工具](#sync-工具多-ai-软链管理)。

## 按 AI agent 分类

除插件或扩展命令另有说明外，本节的 npx 更新和卸载均可使用：

```bash
npx skills update <技能名> -g
npx skills remove -g -a <agent-id> -s <技能名> -y
```

### Claude Code

安装：

```bash
# 用户级单技能；入口位于 ~/.claude/skills
npx skills add soia-team/<仓库名> -g \
  -a claude-code -s <技能名> -y

# 项目级技能；在目标项目目录执行，不加 -g
npx skills add soia-team/<仓库名> \
  -a claude-code -s <技能名> -y
```

项目专用技能也可以直接放在项目的 `.claude/skills/<技能名>/` 中。

插件市场完整管理命令：

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install <域插件名>@soia
claude plugin details <域插件名>@soia
claude plugin disable <域插件名>@soia
claude plugin enable <域插件名>@soia
claude plugin update <域插件名>@soia
claude plugin uninstall <域插件名>@soia
```

`claude plugin details` 可查看组件清单和预计 token 成本。插件更新后需重启 Claude Code 才会应用。验证时运行 `claude plugin list`，或检查用户级软链接：

```bash
readlink ~/.claude/skills/<技能名>
```

### Codex

Codex 原生读取 `~/.agents/skills`，因此 npx 全局安装后即可使用，无需额外同步：

```bash
npx skills add soia-team/<仓库名> -g \
  -a codex -s <技能名> -y
```

本仓的 `.agents/plugins/marketplace.json` 是 Codex 原生市场清单，也可按领域安装：

```bash
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add <域插件名>@soia

# 验证、更新市场快照、卸载
codex plugin list
codex plugin marketplace upgrade soia
codex plugin remove <域插件名>@soia
```

npx 安装可用 `npx skills list -g -a codex` 验证。新技能未出现在当前会话时，启动一个新会话。

### Qwen Code

单技能安装到 `~/.qwen/skills`：

```bash
npx skills add soia-team/<仓库名> -g \
  -a qwen-code -s <技能名> -y
readlink ~/.qwen/skills/<技能名>
```

Qwen Code 也能原生消费 Claude 市场格式：

```bash
qwen extensions install \
  https://github.com/soia-team/soia-open-skills:<域插件名>
qwen extensions list
qwen extensions update <域插件名>
qwen extensions disable --scope User <域插件名>
qwen extensions enable --scope User <域插件名>
qwen extensions uninstall <域插件名>
```

在 Qwen Code 会话中运行 `/extensions` 可热重载扩展；无需退出当前会话。

### Gemini CLI

Gemini CLI 官方支持 `~/.agents/skills` 作为用户层技能目录别名，npx 全局安装后即可使用：

```bash
npx skills add soia-team/<仓库名> -g \
  -a gemini-cli -s <技能名> -y
npx skills list -g -a gemini-cli
```

Gemini CLI 的 extensions 机制也可用于需要扩展级打包的场景，但安装 SOIA 单技能时 npx 路径更直接。更新和卸载使用本节开头的 npx 命令。

### Antigravity CLI（agy）

Antigravity CLI 的技能目录为 `~/.gemini/antigravity-cli/skills/`；npx 和同步工具都可以建立软链接：

```bash
npx skills add soia-team/<仓库名> -g \
  -a antigravity-cli -s <技能名> -y
readlink ~/.gemini/antigravity-cli/skills/<技能名>
```

较新版本的 `agy` 也可导入 Claude 插件：

```bash
agy plugin import claude
agy plugin list
```

插件可用 `agy plugin enable`、`agy plugin disable` 和 `agy plugin uninstall` 管理。npx 安装仍使用 npx 更新和卸载。

### Kimi CLI

Kimi CLI 默认自动发现技能。全局安装后，重开会话即可使用：

```bash
npx skills add soia-team/<仓库名> -g \
  -a kimi-code-cli -s <技能名> -y
```

需要为一次任务限定技能子集时，可重复指定目录：

```bash
kimi --skills-dir <技能目录>
```

`--skills-dir` 会替换本次启动的自动发现目录；需要多个目录时重复传入。默认发现模式下可用 `ls ~/.agents/skills/<技能名>/SKILL.md` 验证。更新和卸载使用 npx。

### OpenCode

OpenCode 读取 `~/.agents/skills` 互操作层，npx 全局安装后即可使用：

```bash
npx skills add soia-team/<仓库名> -g \
  -a opencode -s <技能名> -y
npx skills list -g -a opencode
```

更新和卸载使用 npx；当前会话未刷新时重启 OpenCode。

### DeepCode

DeepCode 官方文档明确支持 interoperable skills，并读取 `~/.agents/skills` 互操作层：

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
ls ~/.agents/skills/<技能名>/SKILL.md
```

DeepCode 不需要专用的 npx agent id；它直接消费安装器维护的互操作目录。安装后重开会话验证；更新使用 npx。卸载时从共享真源移除该技能会同时影响读取该真源的其他宿主，因此先确认影响范围：

```bash
npx skills remove -g -a '*' -s <技能名> -y
```

### WorkBuddy

同步工具可把共享技能软链接到 `~/.workbuddy/skills`：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets workbuddy \
  --skills <技能名> \
  --dry-run
```

确认预览后移除 `--dry-run` 执行，再验证：

```bash
readlink ~/.workbuddy/skills/<技能名>
```

WorkBuddy 也支持通过 SkillHub 或 zip 导入；zip 的包根目录必须包含 `SKILL.md`。软链接安装的更新由 npx 管理，卸载时可用同步工具排除该技能，或使用对应的 npx remove。

### qodercli

安装：qodercli 原生发现 `~/.qoder/skills` 和项目的 `.qoder/skills`，且用户级优先于项目级。SOIA 的现有软链已可用；也可用 npx 管理共享技能入口：

```bash
npx skills add soia-team/<仓库名> -g \
  -a qoder -s <技能名> -y
npx skills list -g -a qoder
```

验证：在 qodercli 中运行 `/skills reload`，并确认技能出现在可用列表。更新：npx 安装使用 `npx skills update <技能名> -g`；插件市场安装则按 qodercli 的插件管理命令更新或启用/停用。

特有说明：qodercli 的插件格式与 Claude Code 同构，可近乎零改动复用 SOIA 插件市场；也可通过 `--plugin-dir <插件目录>` 为一次运行指定插件目录。插件与 MCP 均支持启用/停用；可用 `--permission-mode` 和 `--tools` 限制本次运行的权限及工具。

### Cursor

安装：Cursor 原生支持 `.cursor/skills` 与 `~/.agents/skills` 等 AgentSkills 目录；全局 npx 安装后即可由共享目录覆盖：

```bash
npx skills add soia-team/<仓库名> -g \
  -a cursor -s <技能名> -y
```

验证：执行 `npx skills list -g -a cursor`，或新开 Cursor 会话确认技能可用。更新：`npx skills update <技能名> -g`。

特有说明：技能由 `description` 按需触发；`.cursor/rules/*.mdc` 可按 `paths` glob 等四种模式生效，也可使用 `disable-model-invocation`。Cursor 还支持扩展、Marketplace、`hooks.json` 与 `.cursor/mcp.json`；MCP 可在侧栏逐项开关。已有的 `~/.cursor/skills` 软链可退役以避免重复。

### Windsurf

安装：Windsurf 的原生技能目录为 `.windsurf/skills` 或 `~/.codeium/windsurf/skills`，需要从共享真源显式软链：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets windsurf \
  --skills <技能名> \
  --dry-run
```

确认预览后移除 `--dry-run`。验证：`readlink ~/.codeium/windsurf/skills/<技能名>`，然后新开会话。更新：先用 `npx skills update <技能名> -g` 更新共享真源，再运行上述同步命令。

特有说明：Windsurf 对技能采用渐进披露；rules 有三种 activation 模式，MCP 可以逐工具开关，且有 100 个工具上限。它还支持 MCP Marketplace（Plugins）、`hooks.json` 的五类事件和 VS Code 扩展。

### Copilot CLI / agent

安装：Copilot 原生发现 `~/.copilot/skills`、`~/.agents/skills` 与 `.github/skills` 等目录；全局 npx 安装后共享目录即覆盖：

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

验证：在 Copilot 中用 `/skills` 查看并逐项启用或停用技能。更新：`npx skills update <技能名> -g`。

特有说明：团队技能适合放在 `.github/skills`；Copilot 也支持 Markdown custom agents、带 provenance 的 `gh` skill 分发和 ACP server。可通过 `allowed-tools` 或 `--allow-tool` / `--deny-tool` 限制工具。

### Zed

安装：Zed v1.4 起原生读取 `~/.agents/skills` 和工作树内的 `.agents/skills`，因此全局 npx 安装无需额外同步：

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

验证：新开 Zed 会话并确认技能可被调用。更新：`npx skills update <技能名> -g`。

特有说明：`AGENTS.md` / `.rules` 是 Instructions；技能可使用 `disable-model-invocation`。Zed 支持可包含 MCP 的 WASM 扩展，也可作为 ACP 客户端外挂 Claude Code 或 Gemini；每个 profile 的 `context_servers` 与三态工具权限可分别配置。

### Trae

安装：Trae Skills（Beta）采用开放标准，目录为 `.trae/skills` 或 `~/.trae/skills`；需要显式软链：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets trae \
  --skills <技能名> \
  --dry-run
```

确认预览后移除 `--dry-run`。验证：`readlink ~/.trae/skills/<技能名>`；中国版还应探测 `~/.trae-cn`。更新：先运行 `npx skills update <技能名> -g`，再重跑同步。

特有说明：技能按需调用；rules 位于 `.trae/rules/`。Trae 以自定义 Agents 为主，MCP 配置自 v1.3 起位于 `~/.trae/mcp.json`，并可按 Agent 选装工具。

## sync 工具（多 AI 软链管理）

先安装同步技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' \
  -s soia-meta-sync-skills -y
```

以下命令均先使用 `--dry-run` 查看计划。确认来源、目标和待创建或摘除的链接后，再移除 `--dry-run` 执行。

全量同步到指定宿主：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets codex,claude,qwen \
  --dry-run
```

只同步一个技能及其硬依赖：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,codex \
  --skills <技能名> \
  --dry-run
```

只选择需要的宿主：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets agy,workbuddy,cursor \
  --dry-run
```

本次排除技能，不保存配置：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,codex \
  --exclude-skills <技能一>,<技能二> \
  --dry-run
```

确认后持久保存各宿主的排除列表：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,codex \
  --exclude-skills <技能一>,<技能二> \
  --save-excludes
```

持久排除按 target 分开保存；后续全量同步仍会尊重这些设置。可用以下命令查看内置目标：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --list-targets
```

## 常见问题

### 安装后没有生效

先重开 AI agent 会话。若仍未发现，检查共享真源、锁文件和宿主入口：

```bash
ls ~/.agents/skills/<技能名>/SKILL.md
ls ~/.agents/.skill-lock.json
readlink <宿主技能目录>/<技能名>
```

若 `readlink` 没有输出，使用 sync 工具的 `--dry-run` 检查目标映射，不要手工复制技能目录。

### 插件和 npx 可以同时安装吗

可以，但同一宿主同时索引同一批技能时可能出现重复。建议同一宿主二选一：需要单技能粒度时用 npx，需要整领域开关时用插件。

### 如何安装私有仓库中的技能

先让 GitHub CLI 完成有权访问该仓库的认证，再用 npx 安装：

```bash
gh auth status
npx skills add soia-team/<私有仓库名> -g -a '*' \
  -s <技能名> -y
```

不要把 token 写入命令、文档或仓库文件。

### 各安装方式如何更新

| 安装方式 | 更新命令 | 说明 |
|---|---|---|
| npx 单技能或仓库 | `npx skills update -g` | 可追加 `<技能名>` 只更新一个技能 |
| Claude 插件 | `claude plugin update <域插件名>@soia` | 更新后重启 Claude Code |
| Codex 插件市场 | `codex plugin marketplace upgrade soia` | 刷新市场快照后按需重新安装插件 |
| Qwen 扩展 | `qwen extensions update <域插件名>` | 也可用 `--all` 更新全部扩展 |

若只想按机器用途安装一组常用技能，请继续阅读[分域安装配置](install-profiles.md)。
