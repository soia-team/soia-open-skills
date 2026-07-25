# Antigravity CLI（agy）安装指南

Antigravity CLI 的技能目录为 `~/.gemini/antigravity-cli/skills/`；npx 和同步工具都可以建立软链接。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a antigravity-cli -s <技能名> -y
```

较新版本的 `agy` 也可导入 Claude 插件：

```bash
agy plugin import claude
```

## 验证

```bash
readlink ~/.gemini/antigravity-cli/skills/<技能名>
agy plugin list
```

## 更新

npx 安装[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 卸载

```bash
npx skills remove -g -a antigravity-cli -s <技能名> -y
agy plugin uninstall
```

## 特有说明

插件可用 `agy plugin enable` 和 `agy plugin disable` 管理。npx 安装仍使用 npx 更新和卸载。

[← 返回安装指南](README.md)
