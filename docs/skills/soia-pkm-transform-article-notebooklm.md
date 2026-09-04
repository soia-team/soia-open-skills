# soia-pkm-transform-article-notebooklm

> 用 NotebookLM 将文章转换为学习材料

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-transform-article-notebooklm) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「NotebookLM 生成试卷」「NotebookLM 做闪卡」「NotebookLM 生成播客」

## 能力与用法

### 这个技能可以做什么

把 Markdown / vault 文章或 URL 转换为学习产物：

- **试卷（quiz）**：选择题 + 简答题 + 答案解析
- **闪卡（flashcards）**：Anki 兼容双面卡片
- **脑图（mindmap）**：Mermaid / Markdown 层级结构
- **播客脚本（podcast）**：对话式音频脚本
- **学习笔记**：NotebookLM 综合摘要

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 生成试卷 | 本地 Markdown 或 NotebookLM quiz artifact | 题数、题型分布、文件路径 |
| 做闪卡 | Anki 兼容 Markdown 或 NotebookLM flashcards | 卡片数、文件路径 |
| 脑图 / 播客 | Mermaid 脑图 / 对话脚本 Markdown | 文件路径、节点数 / 字数 |
| 上传 NotebookLM | 上传源文件、记录 notebook id | notebook id / artifact 路径 |
| 执行完成 | 验收产物结构完整、题目答案数量一致 | 完成回执 |

### 客户如何使用

其他可识别说法包括「生成脑图」「做播客」「NotebookLM」「generate quiz」「make flashcards」「mindmap」「podcast」；泛称「生成封面」或「做 PPT」时不使用本技能。

1. 说明来源（URL / vault 路径 / 本地 Markdown）和目标类型（试卷/闪卡/脑图/播客，可选）。
2. 可选：指定 provider（`local` / `notebooklm`）、题数、卡片数、难度。
3. URL 来源先 clip 归档再转换。

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
