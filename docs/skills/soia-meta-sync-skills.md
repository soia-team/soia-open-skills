# soia-meta-sync-skills

> 将一个共享技能源以软链接同步到用户明确选择的 AI 工具目录；支持预览、单项同步、硬依赖闭包和受限清理

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-sync-skills) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

将一个已安装或本地的共享技能目录同步到用户选择的 AI 工具目录。它只创建或替换同名的软链接；先用 `--dry-run` 展示影响，再在已有明确授权时写入。

### 客户如何使用

提供源目录、目标 id 或路径，以及可选的单项技能名。目标由 `--targets` 显式提供；没有适合的内置 id 时使用绝对路径。

```bash
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir <shared-skill-dir> \
  --targets codex,claude \
  --dry-run
```

确认计划后移除 `--dry-run`。使用 `--skills <name>` 只同步指定技能，默认会把其 frontmatter 中的 `dependencies.hard` 一并纳入；`--no-deps` 可关闭该行为。使用 `--exclude-skills a,b` 可在本次运行中对每个选中 target 跳过并摘除这些技能的既有软链。

## 安装

本技能随 `soia-meta` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-meta@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-meta@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-sync-skills -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
