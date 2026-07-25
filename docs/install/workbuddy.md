# WorkBuddy 安装指南

同步工具可把共享技能软链接到 `~/.workbuddy/skills`。

## 安装

先按 [npx 通用方案](README.md#1-npx-通用安装按技能安装)完成底座安装，再预览同步：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets workbuddy \
  --skills <技能名> \
  --dry-run
```

确认预览后移除 `--dry-run` 执行。

## 验证

```bash
readlink ~/.workbuddy/skills/<技能名>
```

## 更新

软链接安装的更新由 npx 管理，[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 卸载

可用同步工具排除该技能，或使用对应的 npx remove，[同通用方案](README.md#1-npx-通用安装按技能安装)。

## 特有说明

WorkBuddy 也支持通过 SkillHub 或 zip 导入；zip 的包根目录必须包含 `SKILL.md`。

[← 返回安装指南](README.md)
