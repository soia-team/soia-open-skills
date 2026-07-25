# Qwen Code 安装指南

Qwen Code 从 `~/.qwen/skills` 加载单技能，也能原生消费 Claude 市场格式。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a qwen-code -s <技能名> -y
```

扩展安装：

```bash
qwen extensions install \
  https://github.com/soia-team/soia-open-skills:<域插件名>
```

## 验证

```bash
readlink ~/.qwen/skills/<技能名>
qwen extensions list
```

## 更新

```bash
npx skills update <技能名> -g
qwen extensions update <域插件名>
```

## 卸载

```bash
npx skills remove -g -a qwen-code -s <技能名> -y
qwen extensions uninstall <域插件名>
```

## 特有说明

扩展可用 `qwen extensions disable --scope User` 和 `qwen extensions enable --scope User` 启用或停用。在 Qwen Code 会话中运行 `/extensions` 可热重载扩展；无需退出当前会话。

[← 返回安装指南](README.md)
