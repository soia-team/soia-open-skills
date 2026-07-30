# soia-dev-fix-loop

> 用五步闭环处理代码审查或测试发现：复现、决策、修复、回归复核与回执，防止遗漏、假修复和无证据收口

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-fix-loop) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 执行闭环 | 客户能看到 |
|---|---|---|
| 按审查意见逐条修复 | 汇总、决策、修复和逐项验证 | 每条 finding 的状态与证据 |
| 确认是否可以收口 | 独立复核修复和回归结果 | 通过、需修改或受阻的结论 |
| 暂缓部分问题 | 给出可追踪的后续位置与原因 | 明确的延后边界 |

### 客户如何使用

提供 findings、目标工作区、相关测试或复现信息，以及允许的修改范围。若某项可能涉及删除、覆盖、远端状态、发布或扩大范围，先明确授权；信息不足时先整理输入清单，不开始修改。

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
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-fix-loop -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
