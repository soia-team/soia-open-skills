# soia-meta-prompt-clarity

> 起草、诊断并规格化中英文提示词，保留用户意图、语言与安全边界

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-prompt-clarity) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「写提示词 / write a prompt」「优化 prompt / improve this prompt」「扩展成可验证规格」

## 能力与用法

### 这个技能可以做什么

| 客户需要 | 技能行为 | 客户看到 |
|---|---|---|
| 从零写提示词 | 模式 A，按复杂度选取必要要素 | 完整提示词 + 构成说明 |
| 优化已有提示词 | 模式 B，六维诊断后只改问题部分 | 诊断 + 改写版 + 改动说明 |
| 写英文或双语提示词 | 分离提示词语言与说明语言，英文原生编写 | 英文或两个完整语言版本 |
| 选择提示框架 | 仅在有实际收益时匹配精选框架 | 框架、选择理由与完整提示词 |
| 正当请求被误判 | 模式 C，补真实的所有权、授权和用途 | 诊断与合规改写，或红线说明 |
| 复杂需求变成规格 | 模式 D，建立需求账本和验收结构 | 可直接执行的完整规格提示词 |
| 适配不同能力模型 | 按前沿/中坚/基础三级选择约束策略 | 按模型能力层级的提示词策略 |

### 客户如何使用

1. 提供需求、现有提示词或被误报的原句。
2. 可选说明目标 AI、提示词语言、说明语言、输出形态和哪里不满意。
3. 待处理文本与给技能的指示混杂时，用代码块定界。
4. 默认只产出；需要执行时必须在当前消息明确说明。

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-prompt-clarity -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
