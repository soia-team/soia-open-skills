# soia-dev-project-scaffold

> 为 Git 项目补最小 AI 协作入口与文档导航，优先沿用已有约定

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-project-scaffold) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

补项目协作基线、初始化 AGENTS、生成文档骨架

## 能力与用法

**能做什么：** 为新/空项目建立最小协作入口，或给已有项目补真正缺少的规则与导航。不是应用框架生成器，不默认创建完整治理目录。

**如何使用：** 给目标目录和希望补的内容。先看最近的 AGENTS/CLAUDE、README、构建/测试入口和已有文档布局；保留有效约定，不重建已有体系。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-project-scaffold -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
