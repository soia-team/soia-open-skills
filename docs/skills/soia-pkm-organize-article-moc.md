# soia-pkm-organize-article-moc

> 将 Obsidian 文章库按元数据、主题双链、月份和两级 MOC 规范化整理

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-organize-article-moc) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「整理文章库」「重建 MOC」「收藏归类」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 整理单篇新归档文章（默认闭环） | 补摘要/`topics`/`captured_at`/`author`，按月归位并调 `rebuild_moc.py --article` 增量同步两级 MOC 与地图 | 文章终路径、受影响 MOC 与地图/Base 校验回执 |
| 盘点或全量重建文章库 `_MOC/` | 先 `rebuild_moc.py --full-rebuild --dry-run` 审查未知 topic，确认后同盘原子替换 `_MOC/` | 总篇数、主题分布与未知 topic 报告 |

### 客户如何使用

- 「把刚归档的这篇 X 文章整理归位，并增量同步 MOC。」
- 「先 dry-run 检查一下文章库的 MOC 有没有未知主题或未按月归位的文件。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-organize-article-moc -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
