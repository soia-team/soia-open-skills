# Kimi CLI 安装指南

Kimi CLI 需要从共享真源分发到 `~/.kimi/skills`，同步后重开会话加载技能。

## 安装

先按 [npx 通用方案](README.md#1-npx-通用安装按技能安装)完成底座安装，再执行一次同步：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets kimi \
  --skills <技能名>
```

## 验证

```bash
readlink ~/.kimi/skills/<技能名>
```

## 更新

共享真源的更新[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 卸载

共享真源的卸载[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

需要为一次任务限定技能子集时，可重复指定 `kimi --skills-dir <技能目录>`。`--skills-dir` 会替换本次启动的自动发现目录；需要多个目录时重复传入。

[← 返回安装指南](README.md)
