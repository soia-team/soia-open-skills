# soia-dev-github-ops

> 查询和操作 GitHub PR、CI、Release 与协作者权限

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-github-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

查 GitHub CI、处理 PR 生命周期、管理仓库协作者

## 能力与用法

**这个技能可以做什么：** 用 gh CLI 查询或操作 GitHub issue、PR、checks、workflow、release 和协作者权限。纯本地 commit、rebase、worktree 管理不触发。

**客户如何使用：** 给仓库或对象 URL 和需要的动作。查询不授权修复或远端写入；已批准、范围未变的完整工作流连续推进，不逐命令重复确认。

## 安装

客户明确选择安装整个 `soia-dev` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-github-ops -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
