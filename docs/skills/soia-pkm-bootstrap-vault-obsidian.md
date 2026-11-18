# soia-pkm-bootstrap-vault-obsidian

> 以 dry-run 和保留未知配置的结构化合并方式，把已有 Markdown vault 配置为 Obsidian 消费端，启用 Bases 与可选宽页 CSS

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-bootstrap-vault-obsidian) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「配置 Obsidian vault」「启用 Obsidian Bases」「接入 Obsidian 消费端」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 为已有 Markdown vault 启用 Obsidian Bases 与宽页样式 | dry-run 预览并结构化合并 `core-plugins.json`/`appearance.json`/`app.json`，保留已有主题/插件/未知键，建缺失 `.base` | JSON 合并、CSS create/drift 清单、备份路径与 `--check` 结果 |

### 客户如何使用

先确认已完成 `soia-pkm-bootstrap-vault-base` 初始化（base 不写 `.obsidian`），提供 vault 路径跑默认 dry-run，核对清单后再 `--apply` 与 `--check`，最后在 Obsidian（建议 1.9+，可按需装社区插件如 Tars/Terminal/Obsidian Git）中验证打开视图。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-bootstrap-vault-obsidian -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
