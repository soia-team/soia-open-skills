# soia-edu-design-course-outline

> 从主题、受众和课时约束设计课程大纲；适用于“课程大纲”“教学目标”“课时规划”等请求

所属：[`soia-edu-course`](https://github.com/soia-team/soia-open-edu-course-skills) · [技能源码](https://github.com/soia-team/soia-open-edu-course-skills/tree/main/skills/soia-edu-design-course-outline) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 从一个主题规划完整课程 | 澄清受众、总课时、单课时长度和教学情境 | 课程定位、约束摘要和待确认假设 |
| 把学习期待变成可验收目标 | 用可观察动作、完成条件和达标标准改写目标 | 可测量教学目标与目标—评估对齐表 |
| 安排模块和每课时内容 | 按先修关系和认知难度排序，控制课时负荷 | 模块划分、每课时要点、前置知识与评估方式 |

### 客户如何使用

1. 说明课程主题、目标受众、总课时、每课时长度和教学场景。
2. 可选提供已有材料、必须覆盖或排除的内容、评估限制和无障碍需求。
3. 若关键信息缺失，先回答最少量澄清问题；无法等待时，明确列出假设再生成草案。
4. 审阅目标、课时负荷和评估方式；指出要调整的优先级或约束即可迭代。

## 安装

客户明确选择安装整个 `soia-edu-course` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-edu-course@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-edu-course@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-edu-course-skills -a <agent> -s soia-edu-design-course-outline -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
