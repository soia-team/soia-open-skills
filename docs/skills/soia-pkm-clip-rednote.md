# soia-pkm-clip-rednote

> 将单篇小红书图文或视频笔记归档到 Obsidian vault

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-rednote) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这条小红书」「clip 小红书笔记」「存这篇 rednote」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档小红书单篇图文/视频笔记 | 解析完整分享链（须含 `xsec_token`），提取正文、作者、话题标签与互动数写 vault，媒体落本地 Downloads | vault Markdown 笔记与本地媒体路径 |
| 只抓元数据与文案 | `--metadata-only` 跳过下载并在正文 `## 媒体候选（未下载）` 保留直链 | 轻量笔记与可重下候选直链 |
| 重抓或去重 | 按 `note_id` 去重默认 `SKIP`；`--force` 覆盖更新同时保留 `topics`/`people`/`## 摘要` | 更新状态与核验回执 |

### 客户如何使用

- 「归档这条小红书：`<App 复制的完整分享链接>`」（须保留完整 `xsec_token`）
- 「先用 `--metadata-only` 抓这篇小红书文案和直链，不用下载视频」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-rednote -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
