# soia-pkm-manage-vault-lifecycle

> 规划并安全执行整个 Markdown/Obsidian 知识库，或知识库中指定模块的盘点、整理、改名、迁移、归档与清理

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-manage-vault-lifecycle) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「整理知识库」「整理知识库的某个模块」「治理资料库」「整理工作台/资料库/日志/归档」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 盘点并分流工作台/历史证据/稳定知识 | 按 10/20/30/90 层级路由、冲突排查与入链核对生成逐文件 SHA-256 迁移 manifest | 去向建议、冲突阻断、回滚键与验收结果 |
| 规范目录编号与清理明确空壳 | 用 `vault_structure_plan.py` 规范语义编号，并仅删除已列清单的 `.DS_Store`/无入链空正文/最终空目录 | 逐项结构清单、编号验收与前后统计 |
| 闭环收官五段入库 | 修复精确 `incoming_refs`、校验知识库地图统计与目标 `.base` 根范围 | 地图重建统计、`vault_index_verify.py` 通过证明与入库状态表 |

### 客户如何使用

说明「整理整个知识库」或指定模块（如 `20_资料库`、`10_工作台/某项目`、收件箱/归档区）及目标；Agent 先生成 manifest 给客户过目确认再 apply，绝不用裸 `rm` 或 `find -delete`。

## 安装

客户明确选择安装整个 `soia-pkm-vault` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-manage-vault-lifecycle -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
