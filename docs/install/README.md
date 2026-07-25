# SOIA 技能生态安装总指南

[English](README.en.md) · [按使用场景选择安装组合](../install-profiles.md)

本指南帮助你按技能粒度、领域粒度或 AI agent 选择 SOIA 技能的安装方式。若不确定从哪里开始，优先使用 `npx skills add`：它覆盖 62+ AI agent，保留单技能粒度，并由统一的锁文件记录安装状态。

## 生态覆盖面

`~/.agents/skills` 已被 Zed、Cursor、Copilot、Codex、Gemini、DeepCode 等宿主原生识别；这些宿主零同步即可覆盖。其他宿主可由 `soia-meta-sync-skills` 从同一共享真源分发软链接。插件市场方面，同一份 SOIA 市场清单可被 Claude Code、Codex、Qwen Code 与 qodercli 复用。

文中的占位符含义如下：

- `<仓库名>`：例如 `soia-open-skills`、`soia-open-dev-skills`。
- `<技能名>`：例如 `soia-meta-prompt-clarity`。
- `<域插件名>`：例如 `soia-pkm-vault`、`soia-dev-coding`。

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

以知识库领域为例：

```bash
# Claude Code
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install soia-pkm-vault@soia

# Codex
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add soia-pkm-vault@soia

# Qwen Code
qwen extensions install \
  https://github.com/soia-team/soia-open-skills:soia-pkm-vault
```

插件适合域级开关，npx 适合单技能选择。不要在同一个宿主里用两种方式安装同一批技能，否则可能出现两份索引。

### 3. 按需加载：核心直达，长尾检索

若不希望预装全部领域技能，可先安装路由技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' \
  -s soia-meta-find-skill -y
```

`soia-meta-find-skill` 让高频核心技能保持直达，同时通过公开路由清单检索并加载低频长尾技能。若某个宿主只需要较小的技能集合，还可使用 `soia-meta-sync-skills` 的 `--exclude-skills` 和 `--save-excludes` 保存该宿主的排除列表；完整命令见[同步工具](#sync-工具多-ai-软链管理)。

## 全量与混合安装（多宿主用户推荐）

**一句话策略：底座全量 + 按宿主能力分层瘦身。** 先用 npx 把全部技能安装到 `~/.agents/skills` 这个单一真源；原生读取该目录的宿主装完即用，其他宿主通过一次软链同步接入；最后只对索引较重或高频使用的宿主启用 RouterV1 核心集或域插件开关。

### 第一步：底座全量安装

先全量安装元仓；对其他开源仓重复同一命令即可覆盖全部 8 个仓：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s '*' -y
```

若要一次安装全部 8 个公开仓，可直接运行：

```bash
repos=(
  soia-open-cwork-office-skills
  soia-open-dev-skills
  soia-open-dev-design-skills
  soia-open-edu-course-skills
  soia-open-env-skills
  soia-open-media-content-skills
  soia-open-pkm-vault-skills
  soia-open-skills
)
for repo in "${repos[@]}"; do
  npx skills add "soia-team/$repo" -g -a '*' -s '*' -y
done
```

全局安装内容进入 `~/.agents/skills`。后续更新、同步和宿主入口都应复用这份内容，不再维护多份技能副本。

### 第二步：按宿主能力覆盖

宿主分为三类：

1. **零同步自动覆盖。** Zed、Cursor、GitHub Copilot CLI、Codex、Gemini CLI 和 DeepCode 原生读取 `~/.agents/skills`；底座安装完成后即可使用，无需额外动作。
2. **一次软链分发。** Windsurf（`~/.codeium/windsurf/skills`）、Trae（`~/.trae/skills`，CN 版为 `~/.trae-cn`）、WorkBuddy、Kimi、OpenCode、qodercli、Antigravity CLI（`agy`）等宿主需要从共享真源建立入口。以下命令一次覆盖常用目标：

   ```bash
   python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
     --source-dir ~/.agents/skills \
     --targets claude,codex,gemini,kimi,opencode,agy,qwen,soia,workbuddy
   ```

   `--targets` 是显式目标列表。使用 Windsurf、Trae 或 qodercli 时，把 `windsurf,trae,qoder` 追加到同一个参数；Trae CN 版可把展开后的绝对路径追加为自定义目标。
3. **插件市场可选叠加。** Claude Code、Codex、Qwen Code 和 qodercli 可在 npx 底座之外按需使用市场安装，获得域级 `enable` / `disable` 开关。例如：

   ```bash
   claude plugin marketplace add soia-team/soia-open-skills
   ```

   同一宿主不要同时索引同一批技能的 npx 入口和插件副本；选择插件管理某个域时，应在该宿主中排除对应的 npx 入口。

### 第三步：按宿主瘦身索引（可选进阶）

全量底座不等于每个宿主都必须常驻索引全部技能。对常用且索引敏感的宿主，可选择以下一种方式：

- **RouterV1 核心集瘦身。** 适合 Claude；实测可减少约 60% 的常驻索引。保留高频核心技能直达，把低频长尾从 Claude 入口持久排除，需要时再由 [`soia-meta-find-skill`](../../skills/soia-meta-find-skill/SKILL.md) 检索并加载。例如：

  ```bash
  python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
    --source-dir ~/.agents/skills \
    --targets claude \
    --exclude-skills soia-pkm-clip-douyin,soia-pkm-clip-rednote \
    --save-excludes
  ```

  这是持久排除的最小示例；按实际核心集继续补充长尾技能名。后续默认全量同步仍会遵守已保存的 Claude 排除列表。

- **域插件开关。** 适合 Claude Code、Codex、Qwen Code 和 qodercli。按工作场景启停整个域，例如写代码时关闭知识库域、写作时再开启：

  ```bash
  claude plugin disable soia-pkm-vault
  claude plugin enable soia-pkm-vault
  ```

### 第四步：验证全量安装

先核对共享真源的技能总数和安装器记录：

```bash
npx skills ls -g
ls ~/.agents/skills | wc -l
```

再对需要软链的宿主抽查任一已安装技能；以下以 Claude Code 为例：

```bash
readlink ~/.claude/skills/<技能名>
```

`readlink` 应解析到 `~/.agents/skills/<技能名>`。其他宿主使用下表中的对应入口目录做同样抽查。

### 混合安装决策表

| 宿主 | 底座覆盖方式 | 是否需软链 | 瘦身手段 | 一句话建议 |
|---|---|---:|---|---|
| Claude Code | 从共享真源分发到 `~/.claude/skills` | 是 | RouterV1 或域插件开关 | 高频使用时只保留核心集，长尾交给路由 |
| Codex | 原生读取 `~/.agents/skills` | 否 | 路由或域插件开关 | 全量安装后直接使用，索引敏感时再按域关闭 |
| Qwen Code | 从共享真源分发到 `~/.qwen/skills` | 是 | 路由或域插件开关 | 需要域级启停时叠加市场能力 |
| Gemini CLI | 原生读取 `~/.agents/skills` | 否 | 路由 | 无需同步；只在需要独立入口时同步到 `~/.gemini/skills` |
| Antigravity CLI (`agy`) | 分发到 `~/.gemini/antigravity-cli/skills` | 是 | 路由 | 全量底座后执行一次 `agy` target 同步 |
| Kimi CLI | 分发到 `~/.kimi/skills` | 是 | 路由 | 同步后重开会话加载技能 |
| OpenCode | 分发到 `~/.config/opencode/skill` | 是 | 路由 | 用 `opencode` target 建立统一入口 |
| DeepCode | 原生读取 `~/.agents/skills` | 否 | 路由 | 不需要专用 target，重开会话即可 |
| WorkBuddy | 分发到 `~/.workbuddy/skills` | 是 | 路由 | 团队机器统一从共享真源同步 |
| qodercli | 分发到 `~/.qoder/skills` | 是 | 路由或域插件开关 | 需要精细场景切换时使用域插件 |
| Cursor | 原生读取 `~/.agents/skills` | 否 | 路由 | 全量底座装完即用 |
| Windsurf | 分发到 `~/.codeium/windsurf/skills` | 是 | 路由 | 使用 `windsurf` target 建立入口 |
| GitHub Copilot CLI | 原生读取 `~/.agents/skills` | 否 | 路由或宿主技能开关 | 用 `/skills` 抽查和控制单项技能 |
| Zed | 原生读取 `~/.agents/skills` | 否 | 路由 | 新会话自动读取共享真源 |
| Trae | 分发到 `~/.trae/skills`；CN 版另查 `~/.trae-cn` | 是 | 路由 | 按实际版本同步对应目录 |
| SOIA AI | 分发到 `~/.soia/skills` | 是 | 路由 | 使用 `soia` target，避免手工复制 |

### 常见组合示例

以下示例均假定已经完成第一步的 8 仓底座全量安装。

**Claude Code + Codex + WorkBuddy 个人开发**

Codex 原生读取共享真源，只需为 Claude Code 和 WorkBuddy 分发入口；随后可单独压缩 Claude 的常驻索引：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,workbuddy

python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude \
  --exclude-skills soia-pkm-clip-douyin,soia-pkm-clip-rednote \
  --save-excludes
```

**团队 WorkBuddy + qodercli**

两种宿主都从同一底座建立软链，团队只需维护 `~/.agents/skills` 的安装状态：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets workbuddy,qoder

readlink ~/.workbuddy/skills/soia-meta-find-skill
readlink ~/.qoder/skills/soia-meta-find-skill
```

**全宿主全量**

一次覆盖同步工具的全部相关目标；DeepCode 和 Zed 继续直接读取共享真源：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets claude,qoder,copilot,cursor,agy,gemini,kimi,codex,opencode,windsurf,trae,qwen,soia,workbuddy

npx skills ls -g
ls ~/.agents/skills | wc -l
```

## 各 AI 安装指南

| AI agent | 安装指南 |
|---|---|
| Claude Code | [查看](claude-code.md) |
| Codex | [查看](codex.md) |
| Qwen Code | [查看](qwen-code.md) |
| Gemini CLI | [查看](gemini-cli.md) |
| Antigravity CLI (`agy`) | [查看](antigravity-agy.md) |
| Kimi CLI | [查看](kimi-cli.md) |
| OpenCode | [查看](opencode.md) |
| DeepCode | [查看](deepcode.md) |
| WorkBuddy | [查看](workbuddy.md) |
| qodercli | [查看](qodercli.md) |
| Cursor | [查看](cursor.md) |
| Windsurf | [查看](windsurf.md) |
| GitHub Copilot CLI / agent | [查看](copilot-cli.md) |
| Zed | [查看](zed.md) |
| Trae | [查看](trae.md) |
| SOIA AI | [查看](soia-ai.md) |

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

若只想按机器用途安装一组常用技能，请继续阅读[分域安装配置](../install-profiles.md)。
