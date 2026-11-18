# soia-pkm-clip-x

> 将单条 X/Twitter 推文、thread 或 Article 归档到 Obsidian vault

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-x) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这条 X」「clip 这条推文」「整理这条 thread」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档单条推文、thread 或 X Article | 调用 `archive_x.py` 走免密 FxTwitter API（兜底 syndication），回溯 thread、展开 `t.co`、提取 `content.blocks[]` 与首图 | `<articles>/<YYYY>/<MM>/` Markdown 笔记、摘要、双链与 MOC 更新 |
| 归档外文推文或导出 PDF | 自动补充自然中文意译段（`## 中文译文`）；请求导出 PDF 时走 Obsidian 原生导出参考 | 双语对照归档笔记或原生 PDF |
| 批量导入 Telegram「我的收藏」X 链接 | 解析 JSON 导出（或按授权走 MTProto），先 `--dry-run` 预览再去重归档 | 新增/跳过篇数与异常链接清单 |

### 客户如何使用

- 「归档这条 X：`https://x.com/<handle>/status/<id>`」
- 「整理这条 X thread 并导出 PDF」
- 「用 `--dry-run` 同步我的 Telegram 收藏导出 JSON 里的 X 链接」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-x -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
