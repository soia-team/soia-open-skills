# Claude Code 安装指南

Claude Code 有两条独立的技能通道：

- npx：技能本体在 `~/.agents/skills`，Claude 入口在 `~/.claude/skills`。
- 插件：插件在 `~/.claude/plugins/cache/<市场>/<插件>/<sha>/`，启用状态写入对应设置文件的 `enabledPlugins`。

## 路线 A：npx

```bash
npx skills add soia-team/<仓库名> -g \
  -a claude-code -s <技能名> -y
```

这不是“只装到 Claude”。技能本体仍会先进入 `~/.agents/skills`，`-a claude-code` 只负责建立 Claude 入口。

需要让 Claude 目录保存实体副本时可以加 `--copy`：

```bash
npx skills add soia-team/<仓库名> -g \
  -a claude-code -s <技能名> --copy -y
```

`--copy` 不改变全局本体先进入 `~/.agents/skills` 的机制。

验证、更新和卸载：

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
ls -ld ~/.claude/skills/<技能名>
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

## 路线 B：Claude 插件

先注册 SOIA 市场，再选择领域插件：

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install <域插件名>@soia --scope user
```

市场定义来自仓库根目录 `.claude-plugin/marketplace.json`。插件安装到 `~/.claude/plugins/cache/soia/<域插件名>/<sha>/`，不进入 `~/.agents/skills`。

### 三种作用域

| 作用域 | 命令参数 | `enabledPlugins` 所在文件 | 用途 |
|---|---|---|---|
| `user` | `--scope user` | `~/.claude/settings.json` | 当前用户的所有项目 |
| `project` | `--scope project` | `.claude/settings.json` | 当前项目的团队共享配置，应提交版本库 |
| `local` | `--scope local` | `.claude/settings.local.json` | 当前项目的本机配置，不用于团队共享 |

项目配置优先于用户配置。团队希望项目成员使用同一组领域插件时，在项目根目录执行：

```bash
claude plugin install <域插件名>@soia --scope project
git add .claude/settings.json
```

这里只把项目级插件选择写入版本库；插件内容仍由每位用户的 Claude 插件缓存管理。个人在同一项目中的临时选择使用 `local`：

```bash
claude plugin install <域插件名>@soia --scope local
```

### 启用、停用、详情与更新

用户作用域：

```bash
claude plugin disable <域插件名>@soia --scope user
claude plugin enable <域插件名>@soia --scope user
claude plugin update <域插件名>@soia --scope user
```

项目作用域：

```bash
claude plugin disable <域插件名>@soia --scope project
claude plugin enable <域插件名>@soia --scope project
claude plugin update <域插件名>@soia --scope project
```

本地项目作用域：

```bash
claude plugin disable <域插件名>@soia --scope local
claude plugin enable <域插件名>@soia --scope local
claude plugin update <域插件名>@soia --scope local
```

查看组件清单和 always-on token 成本：

```bash
claude plugin details <域插件名>@soia
```

停用插件后，该插件不产生上下文成本。插件更新后需要重启 Claude Code 才会应用。

更新市场清单或卸载指定作用域：

```bash
claude plugin marketplace update soia
claude plugin uninstall <域插件名>@soia --scope user
claude plugin uninstall <域插件名>@soia --scope project
claude plugin uninstall <域插件名>@soia --scope local
```

[← 返回安装指南](README.md)
