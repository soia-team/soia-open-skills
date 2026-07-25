# Windsurf 安装指南

Windsurf 的原生技能目录为 `.windsurf/skills` 或 `~/.codeium/windsurf/skills`，需要从共享真源显式软链。

## 安装

先按 [npx 通用方案](README.md#1-npx-通用安装按技能安装)完成底座安装，再预览同步：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets windsurf \
  --skills <技能名> \
  --dry-run
```

确认预览后移除 `--dry-run`。

## 验证

```bash
readlink ~/.codeium/windsurf/skills/<技能名>
```

然后新开会话。

## 更新

先用 `npx skills update <技能名> -g` 更新共享真源，再运行上述同步命令。

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

Windsurf 对技能采用渐进披露；rules 有三种 activation 模式，MCP 可以逐工具开关，且有 100 个工具上限。它还支持 MCP Marketplace（Plugins）、`hooks.json` 的五类事件和 VS Code 扩展。

[← 返回安装指南](README.md)
