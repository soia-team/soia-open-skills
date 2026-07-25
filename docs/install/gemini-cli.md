# Gemini CLI 安装指南

Gemini CLI 官方支持 `~/.agents/skills` 作为用户层技能目录别名，npx 全局安装后即可使用。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a gemini-cli -s <技能名> -y
```

## 验证

```bash
npx skills list -g -a gemini-cli
```

## 更新

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

Gemini CLI 的 extensions 机制也可用于需要扩展级打包的场景，但安装 SOIA 单技能时 npx 路径更直接。

[← 返回安装指南](README.md)
