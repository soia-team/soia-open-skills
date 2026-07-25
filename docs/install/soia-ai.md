# SOIA AI 安装指南

SOIA AI 从共享真源分发到 `~/.soia/skills`，使用 `soia` target，避免手工复制。

## 安装

先按 [npx 通用方案](README.md#1-npx-通用安装按技能安装)完成底座安装，再同步技能：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets soia \
  --skills <技能名> \
  --dry-run
```

确认来源、目标和待创建或摘除的链接后，再移除 `--dry-run` 执行。

## 验证

[同通用方案](README.md#第四步验证全量安装)。

## 更新

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 卸载

[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

使用 `soia` target，避免手工复制。

[← 返回安装指南](README.md)
