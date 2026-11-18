# soia-pkm-alipan-curator

> 规划并整理阿里云盘资源，产出可复核的馆藏索引与学习规划

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-alipan-curator) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「整理阿里云盘资源」「更新阿里云盘索引」「用网盘资源做学习计划」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 盘点与规划整理阿里云盘资源 | 基于只读扫描生成分类、可配编号与结构合同计划（plan-first，确认后单写入执行） | 内容审计表、逐项迁移 manifest、结构与发布审计报告 |
| 更新 Obsidian 馆藏总览与检索索引 | 调用 `gen_catalog.py` 生成折叠树总览与分区全文检索清单 | 云盘馆藏总览 Markdown、分区全文检索清单与导出位置 |
| 生成增量 Excel 总索引与家长导航 | 调用 `gen_catalog_xlsx.py` / `gen_family_nav_xlsx.mjs` 按 SHA-256 增量构建工作簿 | 交付目录下的 Excel 总索引与校验回执 |
| 基于学情制定云盘学习计划 | 匹配已有书/视频资源（按字数或集数×时长排期），输出待确认计划 | 带映射表与周排期的学习计划 Markdown |

### 客户如何使用

- 「根据最新扫描 JSONL 更新 Obsidian 云盘馆藏总览和全文检索索引。」
- 「增量刷新阿里云盘 Excel 总索引到默认交付目录。」
- 「为阿里云盘某分区生成目录重组 dry-run 计划，先给我裁定模糊项后再执行。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-alipan-curator -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
