# soia-pkm-translate-article-zh

> 将外文文章按 quick、normal 或 refined 模式翻译成独立中文稿，保持术语一致且不覆盖原文

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-translate-article-zh) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「翻译这篇」「精翻」「继续润色」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 快速看懂大意（`quick`） | 整篇直译，速度优先 | `<原文件名>-<语言>版.md` 直译全文 |
| 自然流畅的默认译文（`normal`，默认） | 先定文体/受众/术语表再整篇翻译（长文分块保持术语一致） | 通顺可归档的完整译文 |
| 出版级精翻（`refined`） | 分析 → 翻译 → 审校诊断 → 应用润色 | 诊断说明 + 最终润色全文 |

### 客户如何使用

给出文件路径（如 clip 归档笔记）或直接贴正文，说明目标语言/模式/受众（缺省用 CLI 参数 > 环境变量 > 私有 `config.yml` > 内置 `zh-CN / normal / general`；输入明确且无覆盖冲突时直接运行并回显默认值，回复「继续润色」可从 `normal` 升级进入 `refined` 审校）。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-translate-article-zh -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
