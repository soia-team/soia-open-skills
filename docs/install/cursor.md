# Cursor 安装指南

Cursor 原生支持 `.cursor/skills` 与 `~/.agents/skills` 等 AgentSkills 目录；全局 npx 安装后即可由共享目录覆盖。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a cursor -s <技能名> -y
```

## 验证

执行 `npx skills list -g -a cursor`，或新开 Cursor 会话确认技能可用。

## 更新

```bash
npx skills update <技能名> -g
```

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

技能由 `description` 按需触发；`.cursor/rules/*.mdc` 可按 `paths` glob 等四种模式生效，也可使用 `disable-model-invocation`。Cursor 还支持扩展、Marketplace、`hooks.json` 与 `.cursor/mcp.json`；MCP 可在侧栏逐项开关。已有的 `~/.cursor/skills` 软链可退役以避免重复。

[← 返回安装指南](README.md)
