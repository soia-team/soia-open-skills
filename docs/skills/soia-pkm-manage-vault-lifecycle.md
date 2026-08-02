# soia-pkm-manage-vault-lifecycle

> 规划并安全执行整个 Markdown/Obsidian 知识库，或知识库中指定模块的盘点、整理、改名、迁移、归档与清理

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-manage-vault-lifecycle) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「整理知识库」「整理知识库的某个模块」「治理资料库」「整理工作台/资料库/日志/归档」

## 能力与用法

### 这个技能可以做什么

- 盘点整个知识库或指定模块，识别当前源、被取代材料、冻结证据、稳定知识与可归档内容。
- 生成含 source/target/SHA-256/入链/冲突/阻断/回滚信息的迁移 manifest。
- 用户确认后执行无覆盖移动，并验证数量与哈希；结构整理另有独立的目录编号/空对象 manifest，支持在目标未漂移时 rollback。

### 客户如何使用

用户只需说明“整理整个知识库”或指定模块（例如 `20_资料库`、`10_工作台/某项目`、某个 Inbox/归档区）以及目标；Agent 先读根与目标区规则，再查已有控制面、内容层级和引用关系，生成精确清单。客户确认 manifest 后才 apply；删除只能来自结构 manifest 中明确列出的 `.DS_Store`、无正文 Markdown 或最终空目录，不能用裸 `rm`/`find -delete`。

## 安装

本技能随 `soia-pkm-vault` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-manage-vault-lifecycle -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
