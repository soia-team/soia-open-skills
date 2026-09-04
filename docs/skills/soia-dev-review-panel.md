# soia-dev-review-panel

> 从多视角对代码 diff 或技能包进行对抗式复核，只读且不编辑、合并或发布

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-review-panel) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「多角度审改动」「对抗式复核」「审技能包」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 多角度、不漏判地审一次代码改动 | 拆成独立视角逐个过（能并行就并行），每条候选发现再经一轮对抗式复核，只保留经得住反驳的 | 分档发现清单（阻断/应改/提示）+ 每条的证据等级 |
| 审一个技能包（SKILL.md/scripts/references） | 换一套技能包专属视角（宿主无关性、安全门完整性、跨文件描述一致性等） | 同上 |
| 只想知道审了哪些方面、有没有漏检 | 报告里明确列出"检查过、没问题"的部分，不是只报问题 | 覆盖范围说明 |

### 客户如何使用

其他可识别说法包括「用几个视角复查」「审一下这个技能包」；本技能只报告发现，不执行编辑、合并或发布。

1. 说明审查目标：本地未提交的改动、一段已经拿到手的 diff 文本、或一个技能目录路径（如 `skills/<name>/`）。
2. 如果目标类型不明确（代码改动 vs 技能包 vs 两者都有），先问一句再往下走，不要自己猜。
3. 如果对严格程度有要求（比如"再严一点""这次要快"），据此增减视角数量和复核轮数；默认是下面列出的基础视角集。
4. 报告只包含"经复核确认成立"的发现，不自动改代码、不自动提交、不自动合并、不自动发布——这些都是使用者自己的下一步。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-review-panel -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
