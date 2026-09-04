# soia-meta-sync-skills

> 按明确项目或全局范围同步 SOIA 技能，并先输出可审计划

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-sync-skills) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

项目安装、技能同步、同步预览

## 能力与用法

### 这个技能可以做什么

将一个已安装或本地的共享技能目录同步到用户选择的 AI 工具目录。它只创建或替换同名的软链接；先用 `--dry-run` 展示影响，再在已有明确授权时写入。

### 客户如何使用

提供源目录、`--scope`、目标粒度和技能范围。没有 `--scope`、`--target-kind` 或项目 Agent 选择时，脚本只返回 `selection_required`，不写入。

```bash
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir <shared-skill-dir> \
  --scope project --project-dir <project> --agents codex \
  --target-kind skill --skills <skill-name> \
  --dry-run
```

`skill`、`domain`、`all` 都支持；默认不全量。`--skills '*'` 和 `--targets '*'` 必须显式选择 `all`，先 dry-run；全宿主写入还需 `--confirm-all-targets`。使用 `--exclude-skills a,b` 可在本次运行中对每个选中 target 跳过并摘除这些技能的既有软链。

## 安装

客户明确选择安装整个 `soia-meta` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-meta@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-meta@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-skills -a <agent> -s soia-meta-sync-skills -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
