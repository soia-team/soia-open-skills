# soia-dev-doc-sync

> 审计并修复任意代码仓的 docs、README、CHANGELOG、VERSION 与明确真源之间的事实漂移；先建立真源优先级与证据，再按依赖顺序同步派生文档

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-doc-sync) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「文档和代码对不上」「更新 README」「同步 CHANGELOG」

## 能力与用法

### 这个技能可以做什么

把代码、版本元数据、发布记录等明确真源与 `docs/`、README、CHANGELOG、VERSION 等派生文档逐项对账，报告事实漂移并在授权范围内修复。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 检查文档是否过时 | 建立真源清单，比较每个声明和对应证据 | finding、证据、严重度和建议修复顺序 |
| 发布或重大改动后同步文档 | 先更新真源，再回填派生层 | 改动范围、验证结果与残余风险 |

### 客户如何使用

提供目标仓库、待检查的文档范围，以及已知的真源（例如 manifest、版本文件、release note、API schema、测试或生成输出）。若真源优先级不明确，先确认，不用旧文档互相佐证。

涉及覆盖、删除、发布或远端状态时，先展示目标、影响和补丁预览并取得确认。普通单篇创作、纯翻译或不需要事实对账的文案不触发本技能。

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
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-doc-sync -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
