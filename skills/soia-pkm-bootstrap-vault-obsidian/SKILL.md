---
name: soia-pkm-bootstrap-vault-obsidian
description: 配置 Obsidian 作为本地 Markdown 知识库的消费端：安装 Obsidian、启用 Bases、检查 .obsidian 配置和 CSS snippets，并衔接通用 vault base。Triggers：「配置 Obsidian」「装 Obsidian 插件」「Obsidian 特化配置」「启用 Bases」
dependencies:
  hard: [soia-pkm-bootstrap-vault-base]
version: 1.0.0
created_at: 2026-07-16 16:00:31
updated_at: 2026-07-16 16:00:31
created_by: codex 5
updated_by: codex 5
---

# soia-pkm-bootstrap-vault-obsidian

在 `soia-pkm-bootstrap-vault-base` 创建的本地 Markdown 知识库上配置 Obsidian 消费端。Obsidian 只提供编辑、浏览和数据库视图；Markdown、YAML frontmatter 和 Git（若启用）仍是内容真源。

## 客户可读说明

### 这个技能可以做什么

- 安装或检查 Obsidian 1.9+。
- 启用核心插件 **Bases**，用于书库、文章库等数据库视图。
- 检查 `.obsidian/` 与 `snippets/wide-page.css` 是否已由 base 脚本生成，并说明手动启用步骤。
- 提供 Tars、Terminal、Obsidian Git 等可选配置边界。

本 skill 不创建 PARA 骨架、不替代 base，也不把 Obsidian 数据反向写回其他云端知识库。

### 客户如何使用

1. 先安装并运行 `soia-pkm-bootstrap-vault-base`，通用初始化使用 `--no-obsidian`；如果要让脚本同时生成 CSS snippet，则按下方命令不带该参数运行。
2. 提供已有 vault 路径，确认 Obsidian 是否已安装及版本。
3. 按本 skill 完成核心插件和可选插件配置。
4. 在 Obsidian 中打开目标 vault，确认规则、模板和文章能正常显示。

### 依赖与安装

安装本 skill（hard dependency 会同时要求 base）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-bootstrap-vault-obsidian -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-bootstrap-vault-obsidian/config.yml
SOIA_PKM_BOOTSTRAP_VAULT_OBSIDIAN_CONFIG_FILE=<custom-config-path>
```

外部安装入口：

- Obsidian 下载：https://obsidian.md/download
- 版本建议：1.9+，以当前官方版本和本机系统支持为准。

### 日志与完成回执

回执至少说明：Obsidian 版本检查结果、vault 打开/检查结果、Bases 是否启用、`.obsidian`/CSS 是否存在、可选插件是否跳过，以及仍需用户在客户端手动完成的事项。不要把账号、token 或本机私有路径写入日志。

## 配置流程

### 1. 安装 Obsidian

从 [Obsidian 官方下载页](https://obsidian.md/download) 安装桌面客户端，并登录（若用户需要同步或社区插件等账号能力）。不需要为了打开本地 Markdown vault 而把账号凭据写入 vault 或 skill 配置。

### 2. 运行通用初始化

通用层命令：

```bash
python3 <path-to-base-skill>/scripts/init_vault.py <vault-path> --no-obsidian
```

若希望沿用 base 默认配置里的 CSS snippet：

```bash
python3 <path-to-base-skill>/scripts/init_vault.py <vault-path>
```

`init_vault.py` 的 Obsidian 分离方式是最小过滤：`--no-obsidian` 跳过配置中 `.obsidian/**` 的目录和文件；不带参数时保持原有默认行为。脚本没有独立的 Bases 配置生成逻辑，Bases 需要在 Obsidian 客户端中启用。

### 3. 启用核心功能

在 Obsidian 当前版本的设置中启用核心插件 **Bases**，然后打开一个 Bases 文件或创建视图，确认 YAML frontmatter 能作为字段使用。当前版本的设置名称可能变化；若界面不同，以 Obsidian 实际界面为准并记录校正点。

默认清单：

| 类型 | 项目 | 必需? | 用途 |
|---|---|---|---|
| 本体 | Obsidian 1.9+ | 是 | 打开和编辑本地 Markdown vault |
| 核心插件 | Bases | 推荐/按视图需要 | 书库、文章库等数据库视图 |
| CSS snippet | `wide-page.css` | 推荐 | 撑满编辑器宽度；由默认配置提供 |
| AI CLI | Codex / Claude Code / Gemini CLI / Antigravity CLI / opencode / workbuddy | 推荐 | 直接读写本地 Markdown |
| 社区插件 | Tars | 可选 | 在 Obsidian 内调用 AI |
| 社区插件 | Terminal | 可选 | 在 Obsidian 内运行 AI CLI |
| 社区插件 | Obsidian Git | 可选 | 为 vault 提供 Git 版本控制 |

本体系不用 Dataview，不强依赖 Templater；默认模板和 frontmatter 足以运行通用闭环。安装社区插件前先核对作者、权限和本机安全策略。

### 4. 检查 CSS snippet

如果使用默认配置，确认以下相对路径存在：

```text
.obsidian/snippets/wide-page.css
```

在 Obsidian 外观/主题相关设置中启用该 snippet；具体设置名称以客户端实际界面为准。若用户按通用层的 `--no-obsidian` 初始化，则该文件不会生成，需要重新运行 base 脚本（不带 `--no-obsidian`）或按用户自己的配置补入。

### 5. 验证

在 Obsidian 中打开一篇 Markdown 文章，检查标题、frontmatter、wikilink、模板和中文目录显示；再打开一个 Bases 视图确认字段可读。最后回到 CLI 或文件管理器核对 Markdown 正文仍位于 vault 中，未把平台设置误当成内容真源。

## 完成后回执

执行完输出：

1. 已检查或安装的 Obsidian 版本。
2. Bases、CSS snippet 和可选插件的状态。
3. vault 内仅平台配置发生的文件变化。
4. 实际打开文章与视图的验证结果。
5. 需要用户按当前客户端界面补做的步骤；没有则写“无”。
