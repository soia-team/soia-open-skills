# Qwen Code 安装指南

Qwen Code 支持 npx 技能入口，也属于支持 SOIA 插件市场路线的四个宿主之一。

## 路线 A：npx

使用 agent id `qwen`：

```bash
npx skills add soia-team/<仓库名> -g \
  -a qwen -s <技能名> -y
```

技能本体仍先进入 `~/.agents/skills`；`-a qwen` 只建立 Qwen Code 入口。

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g -a qwen
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

## 路线 B：插件市场

插件路线把领域插件放入 Qwen Code 自己的插件缓存，不进入 `~/.agents/skills`，管理粒度为整个领域。插件安装和启停请使用当前 Qwen Code 版本提供的扩展管理命令。

[← 返回安装指南](README.md)
