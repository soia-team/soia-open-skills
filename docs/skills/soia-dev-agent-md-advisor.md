# soia-dev-agent-md-advisor

> AI 项目指令与配置设计顾问，提供诊断、起草和改写建议

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-agent-md-advisor) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「审查我的 AGENTS.md」「CLAUDE.md 怎么写」「多个 AI 入口怎么管」

## 能力与用法

### 这个技能可以做什么

覆盖 AGENTS.md/CLAUDE.md/GEMINI.md 与 `.claude/` 配置的三种工作模式：诊断已有配置的设计质量、为新项目起草配置骨架、回答最佳实践问题。本技能不调用外部 API、不读取账号或凭据、审查模式默认不写文件——纯文本诊断与产出。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 审查现有配置（模式①） | 按六维度逐项诊断，定位到具体文件:行，只诊断不动手改 | 问题清单（文件:行/维度/症状/建议改法/优先级）+ 改写建议 + 结论等级 |
| 为新项目起草配置（模式②） | 先问项目类型/目录结构/协作 AI 数量，按"根文件精简+子目录就近"原则出骨架 | 一版可直接使用的骨架文件草稿（占位项显式标注）+ 每个字段为什么这样设计的说明 |
| 最佳实践问答（模式③） | 直接给结论、推荐结构、注意事项 | 简洁的问答式回复 |
| 输入信息不足 | 不猜、不硬编，先问最小必要问题 | 一份具体的澄清问题清单 |
| 要求"帮我改/优化/执行"（仅模式①） | 诊断完成、客户明确确认后，只改被诊断出问题的部分 | 改动前后对比 + 逐条改动说明 |

### 客户如何使用

1. 说明诉求，并提供必要输入：审查模式给目标文件路径或全文；起草模式给项目类型、目录结构、协作 AI 数量；问答模式直接提问。
2. Agent 判定命中哪种模式；判定不了先问，不硬猜。
3. **审查模式默认只诊断，不动手改文件**——这是诊断请求还是改动请求必须分清楚，客户没有明确说"帮我改/优化/执行"之前，只交付诊断报告。
4. 起草模式在项目类型/目录结构/协作 AI 数量任一项不明确时，先给一次问全的澄清清单，不脑补产出。
5. 最终回复必须包含：模式判定、诊断或产出全文、逐条说明；模式①还需给出结论等级，以及"是否已落地修改"的明确状态。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-agent-md-advisor -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
