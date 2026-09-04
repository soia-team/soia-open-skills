# soia-dev-coding-protocol

> 为普通工程代码改动建立最小范围、验证前置、anti-fake-fix 与写后复核契约；适用于修复、重构、实现和评审

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-coding-protocol) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「改这个 bug」「重构这段」「加个功能」

## 能力与用法

### 这个技能可以做什么

为代码实现、bug fix、重构和评审建立可验证的工作契约：改什么、为何改、如何证明改变正确，以及哪些风险尚未覆盖。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 修复缺陷或实现功能 | 先定义最小范围和验收证据，再做最小可靠改动 | 变更映射、测试证据和残余风险 |
| 评审或重构 | 检查行为保持、类型边界与同类模式 | 发现、复核路径和未处理项 |

### 客户如何使用

说明目标、目标仓库、相关文件、可观察的预期行为，以及可用的测试或复现路径。涉及认证、删除、不可逆数据变更、公开 API 或远端发布时，缺少关键约束必须先询问。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-coding-protocol -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
