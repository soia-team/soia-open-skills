# soia-edu-compose-lesson-plan

> 按课程大纲编写可执行教案与讲义结构；适用于“教案”“讲义”“课堂活动”等请求

所属：[`soia-edu-course`](https://github.com/soia-team/soia-open-edu-course-skills) · [技能源码](https://github.com/soia-team/soia-open-edu-course-skills/tree/main/skills/soia-edu-compose-lesson-plan) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把大纲变成可授课的教案 | 提取单课目标、内容与评估证据，编排课堂环节 | 逐课时流程、教师动作、学习者任务和时间分配 |
| 准备讲义框架 | 把核心概念、示例、练习和小结组织成讲义层级 | 可直接扩写的讲义目录与内容提示 |
| 增加互动和课后学习 | 设计与目标对齐的提问、协作、作业和延伸 | 互动规则、作业要求、评价标准与延伸资源方向 |

### 客户如何使用

1. 提供已确认的课程大纲，至少包含本课教学目标、受众起点、课时长度和评估方式。
2. 可选说明班级规模、授课方式、可用设备、材料限制和无障碍需求；只使用聚合描述。
3. 指定要生成一个课时还是整套课程，并说明需要详案、简案或讲义结构。
4. 审阅时间预算、互动可行性与作业负担，再提出调整。

## 安装

本技能随 `soia-edu-course` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-edu-course@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-edu-course@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-edu-course-skills -g -a '*' -s soia-edu-compose-lesson-plan -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
