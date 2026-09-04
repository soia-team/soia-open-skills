# soia-pkm-library-weread-sync

> 同步微信读书已读书目与划线到 Obsidian 书库，并调用微信读书 API 补单本书详情

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-library-weread-sync) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「同步微信读书」「同步划线」「同步已读书目」「补一下这本书的详情」「补书详情」

## 能力与用法

### 这个技能可以做什么

这个技能负责所有需要访问微信读书的动作：同步已读书目、同步划线/想法，以及为指定书卡补充简介、章节、相似书和阅读进度。它会读取用户提供的 vault 路径和私有配置，把结果幂等地落到书卡与阅读记录中。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 同步微信读书书架 | 拉取已读书目，创建或更新书卡和阅读记录 | 处理数量、新增/更新/跳过/失败统计 |
| 同步划线 | 拉取划线和想法，覆盖机器维护段并保留用户笔记 | 每本书的处理进度和写入结果 |
| 补一下这本书的详情 | 调用微信读书 API，补充书籍信息、章节、相似书和阅读进度 | API 阶段、写入类别和失败原因 |

### 客户如何使用

1. 用自然语言说明要同步书架、同步划线，或提供要补详情的书名。
2. 提供 `--vault <path>`，或在私有配置中设置 `OBSIDIAN_VAULT`；同步前确认 `weread-skills` 和 `WEREAD_API_KEY` 可用。
3. 先用划线脚本的默认预览或单本模式确认范围，再运行 `--all` 全量同步。
4. 执行后核对终端回执；如需刷新本地视图，再运行 `soia-pkm-library-book-catalog` 的生成脚本。

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
