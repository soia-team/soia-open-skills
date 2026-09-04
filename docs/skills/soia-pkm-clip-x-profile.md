# soia-pkm-clip-x-profile

> 面向公开 X 账号的有限范围检索与研究：采集帖子窗口，按时间、关键词、主题、媒体、模型线索和内容条件筛选，输出账号概览、时间段总结、主题分析与可审计结果，并支持将明确选定的结果交给下游技能继续处理

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-x-profile) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

研究公开 X 账号的有限帖子窗口：先采集，再按范围和条件检索，最后输出摘要、分类清单或下游处理输入。已知账号用脚本；未知账号先做候选发现，再进入账号研究。

### 客户如何使用

先确认四项：账号/候选博主、时间或最新条数、关键词/主题/证据条件、产物类型。默认只做研究摘要，不自动生成图片；自然语言“最近一周/一个月”先换成明确的 CST 日期。

常用脚本入口：

```bash
python3 scripts/profile_x.py https://x.com/<handle> \
  --limit <N> --since <YYYY-MM-DD> --until <YYYY-MM-DD> \
  --query <term> --output-mode summary --output <run-dir>
```

重复 `--query` 默认 OR，需同时命中时加 `--query-mode all`；`--topic` 是别名。完整参数和输出字段见 [研究契约](references/research-contract.md)，可复用命令见 [查询配方](references/query-recipes.md)。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-x-profile -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
