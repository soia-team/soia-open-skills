# soia-media-compose-article-draft

> 把 distill 提炼出的观点写成成文草稿。以用户观点为骨、vault 摘抄为料，生成可继续交给 publish 的文章。可指定公众号/知乎/随笔风格

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-media-compose-article-draft) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「把这些观点写成一篇」「把 X 主题写成文章」「compose 这篇」「写成草稿」「起草这篇」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把观点或主题写成成文草稿 | 读取个人说明书与指定笔记/观点综述，按公众号、知乎或随笔（极简意象体）风格组织结构 | 带规范 frontmatter（`tags`/`title`/`series_intro`/`preface`/`digest`/`sources`）的草稿 |
| 区分合集引语与单篇摘要 | 把 `series_intro`、`preface` 与单篇 `digest`（20–40 字）分离写入 frontmatter，不混入正文首段 | 干净起笔的正文与可直接复用的多平台头部元数据 |
| 发表前勘误与防撞库打散重写 | 检查重字、错别字与标点缺漏列对照表；基于他人文章重创作时打散结构并校 `6-gram`/`8-gram` 重叠 | 勘误对照清单、`0.00%` 重叠率核验与高原创度定稿 |

### 客户如何使用

- 「把我在 `[[xxx]]` 里的观点写成一篇公众号文章，走极简随笔风。」
- 「参考这篇底稿的核心立意打散重写一篇，彻底换掉句式与段落骨架，确保通过微信原创声明检测。」
- 「帮我检查这篇草稿有没有错别字或重字，并补齐单篇 `digest` 摘要，先列勘误对照再改。」

## 安装

客户明确选择安装整个 `soia-cwork-office` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-cwork-office@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-cwork-office@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-media-compose-article-draft -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
