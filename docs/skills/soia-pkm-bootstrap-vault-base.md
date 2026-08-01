# soia-pkm-bootstrap-vault-base

> 以 plan-first、create-only、可检查的方式初始化平台中立的 AI-native Markdown vault 基座，包含分区下钻规则、工作台生命周期、模板与多 AI 适配层

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-bootstrap-vault-base) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「初始化知识库」「新建 Markdown vault」「搭建 AI-native PKM」

## 能力与用法

### 这个技能可以做什么

- 创建 00/10/20/30/40/50/60/90 分区、下钻 `AGENTS.md`、工作台 Schema v2、长期知识 Schema 与对应模板。
- 建立 `AGENTS.md` 唯一规则源及 Claude/Gemini/opencode/workbuddy 适配层。
- 支持 JSON/YAML 自定义、默认 plan、显式 `--apply`、create-only 幂等和 `--check`。
- 不创建 `.obsidian`、不安装插件、不配置 hook、不删除或覆盖现有文件。

### 客户如何使用

1. 提供目标目录、语言/命名偏好和是否继承默认结构。
2. 先运行 plan，逐项审查 create/skip/conflict/drift。
3. 客户确认后加 `--apply`；已有文件默认跳过。
4. 再运行 `--check`，确认必需目录和种子文件存在。

## 安装

本技能随 `soia-pkm-vault` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-bootstrap-vault-base -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
