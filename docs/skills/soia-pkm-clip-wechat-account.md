# soia-pkm-clip-wechat-account

> 批量归档用户自己管理的微信公众号已发文章到 Obsidian vault。支持官方 API、公众号后台接口、登录态 Cookie 三条路线，并按 url 去重

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-wechat-account) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「同步我的公众号」「批量拉取我公众号历史文章」「批量归档我的公众号」「导入公众号已发文章」「clip 我的公众号」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 盘点多账号及路线就绪度 | 运行 `--list-accounts` 脱敏显示各 alias、显示名与 API / 后台 / Cookie 就绪态 | 多账号脱敏清单 |
| 预览待归档历史文章 | 执行 `--dry-run --limit N` 只拉列表并按 vault 已有 `url` 比对去重 | 待新增标题、日期与 URL 预览 |
| 批量归档自己公众号的历史文章 | 按 `--account <alias>` 走指定路线抓取并写 `<出版日期>-公众号-<显示名>-<标题>.md` | 新增/跳过篇数、文件路径与缺口标记 |

### 客户如何使用

- 「先 `--list-accounts` 看看我配置了哪些公众号账号，哪个路线通着。」
- 「用 `--dry-run` 看下 `<alias>` 最近还有几篇没归档进知识库。」
- 「批量同步我 `<alias>` 公众号的历史文章到收件箱目录。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-wechat-account -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
