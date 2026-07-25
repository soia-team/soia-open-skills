# OpenCode 安装指南

OpenCode 需要在自己的技能目录中获得同步软链接。npx 的 agent id `opencode` 负责建立该入口；技能本体仍先进入 `~/.agents/skills`。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a opencode -s <技能名> -y
```

## 验证与管理

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g -a opencode
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

如果当前会话没有发现新入口，请重启 OpenCode 会话。

[← 返回安装指南](README.md)
