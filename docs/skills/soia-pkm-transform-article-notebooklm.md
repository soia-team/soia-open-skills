# soia-pkm-transform-article-notebooklm

> 用 NotebookLM 将文章转换为学习材料

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-transform-article-notebooklm) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「NotebookLM 生成试卷」「NotebookLM 做闪卡」「NotebookLM 生成播客」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 生成试卷 / 闪卡 / 脑图 / 播客 / 学习笔记 | 按 `learning` 模式提炼全部核心知识点，选 `notebooklm` 或本地 Markdown 生成 | `outputs/transform/<YYYY>/<stem>/` 产物、`prompts/`、题数或节点数 |

### 客户如何使用

说明来源（vault 路径/URL 先 clip）及类型（`quiz` 默认 / `flashcards` / `mindmap` / `podcast` / `notes`），可选指定题数、难度与 `provider`（`local` / `notebooklm`；不用于做封面/PPT）。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-transform-article-notebooklm -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
