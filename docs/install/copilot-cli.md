# GitHub Copilot 安装指南

Copilot 原生直读 `~/.agents/skills`，因此 npx 写入全局技能本体后无需额外同步。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a copilot -s <技能名> -y
```

`-a copilot` 只控制安装器为 Copilot 建立的入口；Copilot 实际可直接读取全局本体。

## 验证与管理

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g -a copilot
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

[← 返回安装指南](README.md)
