# Claude Code 安装指南

Claude Code 从 `~/.claude/skills`（用户级）或 `.claude/skills`（项目级）加载技能，同时支持插件市场。两条通道相互独立。

## 路线 A：npx 安装技能

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a claude-code -s soia-pkm-clip-web -y
```

技能本体写入 `~/.agents/skills`，并在 `~/.claude/skills` 建立入口。加 `--copy` 会在 `~/.claude/skills` 放实体副本而非软链接。

项目级安装（在目标项目目录执行，不加 `-g`）：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -a claude-code -s soia-pkm-clip-web -y
```

## 路线 B：插件市场（推荐）

### 注册市场

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

### 安装领域插件

```bash
claude plugin install soia-pkm-vault@soia
```

可用插件：`soia-dev`、`soia-dev-design`、`soia-pkm-vault`、`soia-media-content`、`soia-cwork-office`、`soia-edu-course`、`soia-env`、`soia-meta`。

### 插件工作原理

```
仓库根 .claude-plugin/marketplace.json     市场清单，声明有哪些插件
        ↓ claude plugin marketplace add
本机注册（~/.claude/plugins/known_marketplaces.json）
        ↓ claude plugin install <插件>@soia
插件缓存 ~/.claude/plugins/cache/soia/<插件>/<sha>/
        ↓ 状态记入 settings.json 的 enabledPlugins
新会话启动时，该插件全部技能的描述进入索引
```

插件缓存独立于 `~/.agents/skills`，因此插件安装不会影响 npx 通道，也不会增加共享真源的内容。

### 三种作用域

| 作用域 | 配置文件 | 用途 |
|---|---|---|
| `user`（默认） | `~/.claude/settings.json` | 个人全局，所有项目生效 |
| `project` | `<项目>/.claude/settings.json` | 团队共享，随仓库提交 |
| `local` | `<项目>/.claude/settings.local.json` | 本机本项目，通常 gitignore |

优先级：project > user。团队共享插件的做法是在项目 `.claude/settings.json` 中声明市场与启用项，成员信任该目录后会收到安装提示：

```json
{
  "extraKnownMarketplaces": {
    "soia": { "source": { "source": "github", "repo": "soia-team/soia-open-skills" } }
  },
  "enabledPlugins": { "soia-dev@soia": true }
}
```

指定作用域安装：

```bash
claude plugin install soia-dev@soia --scope project
```

## 验证

```bash
claude plugin list
```

```bash
claude plugin details soia-pkm-vault
```

`details` 会显示该插件包含的技能清单，以及它们进入每个会话的常驻 token 成本（Always-on）。

## 领域开关

```bash
claude plugin disable soia-pkm-vault
```

```bash
claude plugin enable soia-pkm-vault
```

禁用后该插件的全部技能退出索引，常驻上下文成本归零；重新启用即刻恢复，无需重新下载。

## 更新

```bash
claude plugin marketplace update soia
```

```bash
claude plugin update soia-pkm-vault
```

第三方市场默认不自动更新，需要手动执行以上命令。

## 卸载

```bash
claude plugin uninstall soia-pkm-vault
```

npx 安装的技能用 `npx skills remove -g -a claude-code -s <技能名> -y` 移除。

## 特有说明

- 技能索引占用上下文预算的 1%，描述超过 1536 字符会被截断；技能正文在被调用时才载入。
- 同一技能若同时经 npx 和插件安装，会出现两份索引条目，建议二选一。
- 插件内的技能调用名为 `插件名:技能名`，npx 安装的技能使用原始技能名。


## 保持更新

SOIA 的市场清单在每次技能发布时刷新（sha pin 指向各域仓当时的最新提交），因此你只需要让本地拉取这份清单。

### 手动更新

界面：`Manage plugins` → 目标插件齿轮 → 更新；或 `Browse plugins` → Sync 刷新市场清单。

命令：

```bash
claude plugin marketplace update soia
```

```bash
claude plugin update <域插件名>@soia
```

### 开启自动更新（推荐）

第三方市场默认不自动更新。在 `~/.claude/settings.json` 中为 soia 市场开启：

```json
{
  "extraKnownMarketplaces": {
    "soia": {
      "source": { "source": "github", "repo": "soia-team/soia-open-skills" },
      "autoUpdate": true
    }
  }
}
```

开启后 Claude Code 启动时会自动拉取最新市场清单并更新已安装插件。

### 团队统一配置

在项目根目录的 `.claude/settings.json` 中声明市场与启用的插件，提交到版本库；成员信任该目录后会收到安装提示，无需各自配置：

```json
{
  "extraKnownMarketplaces": {
    "soia": {
      "source": { "source": "github", "repo": "soia-team/soia-open-skills" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "soia-dev@soia": true,
    "soia-pkm-vault@soia": true
  }
}
```

项目级配置优先于用户级配置。

[← 返回安装指南](README.md)
