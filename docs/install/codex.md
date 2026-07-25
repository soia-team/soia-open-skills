# Codex 安装指南

Codex 原生读取 `~/.agents/skills`，因此 npx 全局安装后即可使用，无需额外同步。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a codex -s <技能名> -y
```

本仓的 `.agents/plugins/marketplace.json` 是 Codex 原生市场清单，也可按领域安装：

```bash
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add <域插件名>@soia
```

## 验证

```bash
npx skills list -g -a codex
codex plugin list
```

## 更新

```bash
npx skills update <技能名> -g
codex plugin marketplace upgrade soia
```

## 卸载

```bash
npx skills remove -g -a codex -s <技能名> -y
codex plugin remove <域插件名>@soia
```

## 特有说明

新技能未出现在当前会话时，启动一个新会话。

[← 返回安装指南](README.md)
