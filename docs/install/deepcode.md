# DeepCode 安装指南

DeepCode 原生直读 `~/.agents/skills`。安装器不需要为它维护一个独立技能本体。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

`-a '*'` 会为所有受支持宿主建立入口；DeepCode 直接使用其中的全局本体。

## 验证与管理

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

[← 返回安装指南](README.md)
