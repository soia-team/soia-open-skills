# WorkBuddy 安装指南

WorkBuddy 需要把 `~/.agents/skills` 中的全局技能同步为宿主目录软链接。

## 安装全局本体

```bash
npx skills add soia-team/<仓库名> -g \
  -a '*' -s <技能名> -y
```

## 同步 WorkBuddy 入口

先安装同步工具：

```bash
npx skills add soia-team/soia-open-skills -g \
  -a '*' -s soia-meta-sync-skills -y
```

再预览同步：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir ~/.agents/skills \
  --targets workbuddy \
  --skills <技能名> \
  --dry-run
```

确认预览后，移除 `--dry-run` 再执行同一命令。

## 验证与管理

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

同步只建立宿主入口，不会把 WorkBuddy 目录变成技能本体来源。

[← 返回安装指南](README.md)
