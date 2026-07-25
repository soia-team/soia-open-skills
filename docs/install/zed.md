# Zed 安装指南

Zed v1.4 起原生读取 `~/.agents/skills` 和工作树内的 `.agents/skills`，因此全局 npx 安装无需额外同步。

## 安装

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

## 验证

新开 Zed 会话并确认技能可被调用。

## 更新

```bash
npx skills update <技能名> -g
```

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

`AGENTS.md` / `.rules` 是 Instructions；技能可使用 `disable-model-invocation`。Zed 支持可包含 MCP 的 WASM 扩展，也可作为 ACP 客户端外挂 Claude Code 或 Gemini；每个 profile 的 `context_servers` 与三态工具权限可分别配置。

[← 返回安装指南](README.md)
