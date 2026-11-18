# soia-pkm-clip-github-repo

> 将 GitHub 开源仓库归档为 Obsidian vault 的项目卡和调研笔记

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-github-repo) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这个项目 URL」「clip 这个 repo」「刷新项目卡」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档单个 GitHub 仓库 | 克隆/复用本地 upstream 仓库，调用 `gen_repo_catalog.py --add` 建更新项目卡并起研读笔记骨架 | 项目卡、带双链的 `YYYY-MM-DD-调研-<仓名>.md` 骨架与同步索引 |
| 批量刷新已克隆仓库字段 | 扫描 `--upstream` 子目录幂等更新项目卡自动字段（不覆盖人工笔记） | 新增/刷新仓库数、失效/未核实提交提醒 |

### 客户如何使用

- 「归档这个项目 URL：`https://github.com/<owner>/<repo>`」
- 「扫描 upstream 目录，批量刷新所有开源项目卡的自动字段。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-github-repo -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
