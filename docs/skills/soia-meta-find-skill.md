# soia-meta-find-skill

> 按需求查找合适的 SOIA 技能，未安装时只收集安装选择，不代替技能执行任务

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-find-skill) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

找个技能、有没有技能可以、发现 SOIA 能力

## 能力与用法

### 这个技能可以做什么

- 在项目 `.agents/skills`、用户全局真源或公开生态目录中发现候选技能，识别代码审查、架构评审、调用链、数据流等中文意图。
- 返回“项目/全局、目标 Agent、单技能/整域/全量”的选择意图，交给安装或同步技能执行。

### 客户如何使用

```bash
python3 scripts/find_skill.py --query <关键词> [--domain <领域>] [--project <项目路径>] [--scope auto|project|global|both] [--agent <Agent>]
```

从仓库源码调用时脚本路径为 `skills/soia-meta-find-skill/scripts/find_skill.py`。`--domain` 按领域或 `query-hints.json` 的 `domain_hints` 缩小候选。`--agent` 可重复，只记录客户选的目标 Agent，不猜宿主目录。`--scope auto` 只扫描能确定的当前项目，确定不了就让 Agent 向客户确认范围，不暗自扫全局；`project`、`global`、`both` 是显式范围。

## 安装

客户明确选择安装整个 `soia-meta` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-meta@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-meta@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-skills -a <agent> -s soia-meta-find-skill -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
