# SOIA AI 安装指南

通用 npx 路线保证技能本体安装到 `~/.agents/skills`：

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

本指南的已验证宿主读取清单没有定义 SOIA AI 的自动读取目录，因此不要把某个专用目录写成默认机制。请在所用 SOIA AI 版本中把技能来源配置为 `~/.agents/skills`，或使用该版本明确支持的同步入口。

验证全局本体与管理安装：

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

[← 返回安装指南](README.md)
