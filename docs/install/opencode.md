# OpenCode 安装指南

OpenCode 需要从共享真源分发到 `~/.config/opencode/skill`。

## 安装

先按 [npx 通用方案](README.md#1-npx-通用安装按技能安装)完成底座安装，再同步技能：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets opencode \
  --skills <技能名>
```

## 验证

```bash
readlink ~/.config/opencode/skill/<技能名>
```

## 更新

共享真源的更新[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 卸载

共享真源的卸载[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

当前会话未刷新时重启 OpenCode。

[← 返回安装指南](README.md)
