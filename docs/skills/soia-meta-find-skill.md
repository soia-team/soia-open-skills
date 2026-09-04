# soia-meta-find-skill

> 按需发现 SOIA 技能并收集安全安装选择

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-find-skill) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

技能检索、代码审查、环境安装

## 能力与用法

### 这个技能可以做什么

- 在项目 `.agents/skills`、用户全局真源或公开生态目录中发现候选技能。
- 识别代码审查、架构评审、调用链、数据流、模块边界等中文意图。
- 返回“项目/全局、目标 Agent、单技能/整域/全量”选择意图，交给安装或同步技能执行。

### 客户如何使用

先从当前项目查找；若当前目录不能确定项目，脚本不会暗自扫描全局目录，而会让 Agent 向客户确认范围。

```bash
python3 scripts/find_skill.py --query <关键词> [--project <项目路径>] [--scope auto|project|global|both] [--agent <Agent>]
```

从仓库源码调用：

```bash
python3 skills/soia-meta-find-skill/scripts/find_skill.py --query <关键词> --project <项目路径> --agent claude --agent codex
```

`--agent` 可重复，仅保留客户的目标 Agent 选择，不猜测任何宿主目录。`--scope auto` 仅扫描可确定的当前项目；`project`、`global`、`both` 是显式范围。`--skills-dir` 与 `--directory` 保留给旧离线调用和测试。

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
