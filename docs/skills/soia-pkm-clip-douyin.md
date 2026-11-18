# soia-pkm-clip-douyin

> 归档单条抖音视频到 Obsidian vault，并保留本地媒体索引

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-douyin) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这条抖音」「clip 这个抖音视频」「只要抖音文案」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档一条抖音视频 | 用 Playwright 拦截签名响应、校验 `video_id` 去重、下载 MP4 至本机目录并写入 Markdown | vault 笔记路径、MP4 本地路径、作者/时长/互动数 |
| 只要文案与元数据（暂不下载视频） | `--metadata-only` 跳过下载并写笔记 | `media_local_path` 置空、`media_fetched: false` |
| 强制更新已归档视频 | `--force` 重抓并在覆盖时保留人工 `topics`/`people`/`## 摘要` | 更新后的笔记与核验回执 |

### 客户如何使用

- 「归档这条抖音：`https://www.douyin.com/video/<id>`」（支持 `modal_id=`/`resource_id=` 与 `v.douyin.com` 短链）
- 「先只抓这条抖音文案和元数据，不要下视频（`--metadata-only`）」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-douyin -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
