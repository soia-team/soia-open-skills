# soia-pkm-manage-vault-lifecycle

> 规划并安全执行 Markdown/Obsidian vault 的 Inbox、工作台、冻结证据、长期知识与历史归档分流

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-manage-vault-lifecycle) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「整理工作台」「清理 Inbox」「归档已完成项目」「做 vault 生命周期迁移」

## 能力与用法

### 这个技能可以做什么

- 盘点 Inbox 和工作台，识别当前源、被取代材料、冻结证据与可提炼知识。
- 生成含 source/target/SHA-256/入链/冲突/阻断/回滚信息的迁移 manifest。
- 用户确认后执行无覆盖移动，并验证数量与哈希；支持在目标未漂移时 rollback。

### 客户如何使用

提供 vault 路径和整理范围。Agent 先读根与目标区规则，再查已有控制面和引用关系，给逐文件建议。客户确认 manifest 后才 apply；删除请求不属于本技能。

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
