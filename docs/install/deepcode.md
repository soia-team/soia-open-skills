# DeepCode 安装指南

DeepCode 支持 interoperable skills，并读取 `~/.agents/skills` 互操作层。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

## 验证

```bash
ls ~/.agents/skills/<技能名>/SKILL.md
```

安装后重开会话验证。

## 更新

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 卸载

```bash
npx skills remove -g -a '*' -s <技能名> -y
```

## 特有说明

DeepCode 不需要专用的 npx agent id；它直接消费安装器维护的互操作目录。从共享真源移除技能会同时影响读取该真源的其他宿主，因此卸载前先确认影响范围。

[← 返回安装指南](README.md)
