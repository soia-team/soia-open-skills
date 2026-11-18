# soia-pkm-distill-article-opinion

> 通过苏格拉底式逐问，把用户对 vault 文章的回答整理成其本人观点，并写入「我的看法」或主题综述

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-distill-article-opinion) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「补我的看法」「炼成观点」「主题观点综述」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 给单篇文章补「我的看法」 | 读原文后按三角度**一次只抛一个问题**（带回答示例），根据用户回答整理成第一人称视图 | 仅填入原文 `## 我的看法` 段，其余段落保持不变 |
| 跨同主题多篇文章聚合观点 | 读取 `_MOC/<分类>/<主题>.md` 下各篇「我的看法」，不足先提示逐篇提炼，素材够后综合综述 | `<vault-drafts-dir>/YYYY-MM-DD-<主题>-观点综述.md`，供 `compose` 成文 |

### 客户如何使用

- 「帮我给《xxx》补『我的看法』，一次问一个问题引导我。」
- 「把 MOC 里『某主题』下这几篇我的观点汇成一份主题综述。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-distill-article-opinion -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
