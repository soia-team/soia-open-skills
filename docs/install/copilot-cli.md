# Copilot CLI / agent 安装指南

Copilot 原生发现 `~/.copilot/skills`、`~/.agents/skills` 与 `.github/skills` 等目录；全局 npx 安装后共享目录即覆盖。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

## 验证

在 Copilot 中用 `/skills` 查看并逐项启用或停用技能。

## 更新

```bash
npx skills update <技能名> -g
```

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

团队技能适合放在 `.github/skills`；Copilot 也支持 Markdown custom agents、带 provenance 的 `gh` skill 分发和 ACP server。可通过 `allowed-tools` 或 `--allow-tool` / `--deny-tool` 限制工具。

[← 返回安装指南](README.md)
