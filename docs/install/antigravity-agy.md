# Antigravity CLI（`agy`）安装指南

Antigravity 使用 npx 的 agent id `agy`。技能本体先进入 `~/.agents/skills`，`-a agy` 再建立宿主入口。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a agy -s <技能名> -y
```

## 验证与管理

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g -a agy
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

`-a agy` 不是隔离安装；全局本体始终存在于 `~/.agents/skills`。

[← 返回安装指南](README.md)
