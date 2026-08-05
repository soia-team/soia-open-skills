# soia-dev-project-scaffold

> 为任意新 Git 项目生成最小 AI 协作基线：可编辑的 AGENTS.md 和 docs 导航目录；在写入前确认目标路径

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-project-scaffold) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

为一个新建或空白的 Git 项目创建一套最小、可编辑的 AI 协作基线：`AGENTS.md`、文档导航、项目概览、变更记录和 AI 工作记录目录。它不生成应用框架、云服务模块或组织内部治理结构。

### 客户如何使用

提供目标项目的绝对路径，并明确允许创建文件。先运行帮助或检查目录；目标已有同名文件时，先展示差异并取得覆盖确认。

```bash
bash skills/soia-dev-project-scaffold/shells/init-project-baseline.sh <project-path>
```

## 安装

本技能随 `soia-dev` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-project-scaffold -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
