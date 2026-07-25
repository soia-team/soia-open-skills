# Gemini CLI 安装指南

Gemini CLI 原生直读 `~/.agents/skills`，因此 npx 写入全局技能本体后无需额外同步。它在 npx 中的 agent id 是 `gemini`。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a gemini -s <技能名> -y
```

不要使用 `gemini-cli` 作为 `-a` 的值。`-a gemini` 只控制宿主入口，技能本体仍在全局目录。

## 验证与管理

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g -a gemini
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

[← 返回安装指南](README.md)
