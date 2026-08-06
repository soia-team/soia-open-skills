# soia-dev-test-draft-doc

> 从需求、PRD 或变更说明生成测试计划、测试用例与验收对照；适用于测试设计、回归清单和质量评审

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-test-draft-doc) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「写测试用例」「出测试计划」「验收标准怎么定」

## 能力与用法

### 这个技能可以做什么

提供需求材料、目标平台和已知约束；材料可以是粘贴文本、用户明确提供的文件或公开链接。技能先识别可验证行为与未决问题，再产出可执行、可追溯的测试设计。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 为新功能制定测试计划 | 划定范围、风险、环境、数据和进入/退出准则 | 测试计划与风险优先级 |
| 从 PRD 设计测试用例 | 按正常、边界、异常和数据流覆盖可观察行为 | 编号用例表与待确认项 |
| 上线前回归和验收 | 提炼受影响路径，并把需求逐项映射到验收证据 | 回归清单与验收对照表 |

### 客户如何使用

说明需求来源、功能目标、角色、平台、变更范围、已有规则和期望交付格式。例如：`基于以下订单取消需求，设计 Web 与 API 的测试计划、用例、回归清单和验收对照表：<需求文本>`。

只读取客户在当前对话明确提供或授权的材料；缺少需求、可观察结果、权限规则或数据约束时，先列为待确认项，不把猜测写成验收结论。

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
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-test-draft-doc -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
