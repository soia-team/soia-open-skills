# soia-pkm-library-weread-sync

> 同步微信读书已读书目与划线到 Obsidian 书库，并调用微信读书 API 补单本书详情

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-library-weread-sync) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「同步微信读书」「同步划线」「同步已读书目」「补一下这本书的详情」「补书详情」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 同步微信读书书架与状态 | 运行 `sync_weread_to_library.py` 幂等新建/更新书卡与阅读记录 | 新增/更新/跳过/失败统计 |
| 同步划线与想法 | 运行 `sync_weread_highlights.py` 覆盖机器段同时保留 `### 用户笔记` | 每本书同步进度与写入结果 |
| 补充单本书详情与章节 | 运行 `enrich_book_details.py` 拉简介/目录/进度/相似书回填 | API 阶段、更新数量与失败原因 |

### 客户如何使用

说明要同步书架、划线或补详情书名，并提供 `--vault <path>`（或私有配置 `OBSIDIAN_VAULT`）；划线同步先默认预览或指定单本再 `--all` 全量。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-library-weread-sync -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
