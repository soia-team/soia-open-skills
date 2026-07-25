# qodercli 安装指南

qodercli 原生发现 `~/.qoder/skills` 和项目的 `.qoder/skills`，且用户级优先于项目级。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a qoder -s <技能名> -y
```

qodercli 的插件格式与 Claude Code 同构，可近乎零改动复用 SOIA 插件市场。

## 验证

```bash
npx skills list -g -a qoder
```

在 qodercli 中运行 `/skills reload`，并确认技能出现在可用列表。

## 更新

npx 安装使用 `npx skills update <技能名> -g`；插件市场安装则按 qodercli 的插件管理命令更新或启用/停用。

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

可通过 `--plugin-dir <插件目录>` 为一次运行指定插件目录。插件与 MCP 均支持启用/停用；可用 `--permission-mode` 和 `--tools` 限制本次运行的权限及工具。

[← 返回安装指南](README.md)
