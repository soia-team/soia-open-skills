# soia-pkm-interpret-article-analysis

> 为 vault 长文或论文生成独立 AI 解读，帮助判断是否值得深挖，且不改原文或代写用户观点

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-interpret-article-analysis) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「解读这篇」「精读这篇」「值得细读吗」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 快速判断长文/论文是否值得精读 | 快读：生成五段式（每段 2–3 句）结构化解读 | 同目录 `<原文件名>-AI解读.md`，双链回原文 |
| 精读并逐节核查论证链 | 精读：逐节展开论点与证据对应检查，标出跃迁与未明前提 | 深度五段式解读，含明确「原文未明确/需核对」标记 |
| 批量解读（>3 篇） | 先列出待解读清单及主题确认范围，再逐篇落盘并汇总回执 | 清单确认 + 逐篇解读文件与合并回执 |

### 客户如何使用

- 「解读这篇《xxx》，帮我先快速判断值不值得深挖。」
- 「精读这篇论文并逐节核查论证链与边界前提。」
- 「把这个 MOC 下的 5 篇文章列出清单，等我挑出几篇后再解读。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-interpret-article-analysis -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
