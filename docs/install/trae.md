# Trae 安装指南

Trae Skills（Beta）采用开放标准，目录为 `.trae/skills` 或 `~/.trae/skills`；需要显式软链。

## 安装

先按 [npx 通用方案](README.md#1-npx-通用安装按技能安装)完成底座安装，再预览同步：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets trae \
  --skills <技能名> \
  --dry-run
```

确认预览后移除 `--dry-run`。

## 验证

```bash
readlink ~/.trae/skills/<技能名>
```

中国版还应探测 `~/.trae-cn`。

## 更新

先运行 `npx skills update <技能名> -g`，再重跑同步。

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

技能按需调用；rules 位于 `.trae/rules/`。Trae 以自定义 Agents 为主，MCP 配置自 v1.3 起位于 `~/.trae/mcp.json`，并可按 Agent 选装工具。

[← 返回安装指南](README.md)
