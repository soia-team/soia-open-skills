# Claude Code 安装指南

Claude Code 通过用户级 `~/.claude/skills` 或项目级 `.claude/skills` 加载技能，也支持 SOIA 域插件市场。

## 安装

```bash
# 用户级单技能；入口位于 ~/.claude/skills
npx skills add soia-team/<仓库名> -g \
  -a claude-code -s <技能名> -y

# 项目级技能；在目标项目目录执行，不加 -g
npx skills add soia-team/<仓库名> \
  -a claude-code -s <技能名> -y
```

插件市场安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install <域插件名>@soia
```

## 验证

运行 `claude plugin list`，或检查用户级软链接：

```bash
readlink ~/.claude/skills/<技能名>
```

## 更新

```bash
npx skills update <技能名> -g
claude plugin update <域插件名>@soia
```

插件更新后需重启 Claude Code 才会应用。

## 卸载

```bash
npx skills remove -g -a claude-code -s <技能名> -y
claude plugin uninstall <域插件名>@soia
```

## 特有说明

项目专用技能也可以直接放在项目的 `.claude/skills/<技能名>/` 中。`claude plugin details <域插件名>@soia` 可查看组件清单和预计 token 成本；插件还可用 `claude plugin disable` 和 `claude plugin enable` 启用或停用。

[← 返回安装指南](README.md)
