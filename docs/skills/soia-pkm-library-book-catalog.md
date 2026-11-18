# soia-pkm-library-book-catalog

> 纯本地、幂等、可重复运行地维护 Obsidian 书库：补建待读记录并重新生成图书馆、阅读记录和按类型总览，不依赖微信读书

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-library-book-catalog) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「重新生成图书馆总览」「更新阅读记录总览」「补建待读记录」「书库整理」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 为有书卡但无记录的书补待读条目 | `backfill_reading_records.py` 幂等新建缺失记录（已有跳过） | 新建/跳过/失败数 |
| 更新图书馆 / 7 态阅读记录 / 类型总览 | `gen_library_md.py`、`gen_records_md.py`、`gen_genre_library_md.py` 生成分类视图 | 输出路径与书目统计（支持 `--output` 预览） |

### 客户如何使用

给出 `--vault <path>`（或配置 `OBSIDIAN_VAULT`）与可选 `--base <relpath>`，先可用 `--output <preview-path>` 预览总览，确认后省略 `--output` 写回书库（重复运行幂等安全）。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-library-book-catalog -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
