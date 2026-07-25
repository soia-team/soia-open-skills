# Cursor 安装指南

Cursor 原生直读 `~/.agents/skills`，因此 npx 写入全局技能本体后无需额外同步。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a cursor -s <技能名> -y
```

`-a cursor` 不会把技能隔离到 Cursor；它只决定目标入口。

## 验证与管理

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g -a cursor
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

[← 返回安装指南](README.md)
