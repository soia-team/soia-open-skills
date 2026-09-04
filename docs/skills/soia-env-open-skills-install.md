# soia-env-open-skills-install

> 在 Claude Code、Codex、WorkBuddy 上按确认范围安装或更新 SOIA 开源技能；默认项目级单技能，支持全局、整域和全量

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-open-skills-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 SOIA 技能」「在 Codex 下装」「更新 soia-dev」

## 能力与用法

### 这个技能可以做什么

- 只读检查 Claude Code、Codex、WorkBuddy 的可用性、市场状态和当前安装。
- 生成机器可读的选择计划与 Agent × 范围 × 粒度矩阵。
- 在确认后按当前 CLI/官方脚本安装或更新单技能、整域或全量，并验证实际结果。

### 客户如何使用

请明确说明安装范围、宿主和粒度，例如“在这个项目给 Codex 装单个技能”“全局给 Claude Code 更新 `soia-dev`”。范围、宿主或粒度任一缺失时只检查并返回 `selection_required`，先询问，不检测全部后默认全域执行。要扩大到全局、整域、多宿主或 `*` 全量，必须明确选择；先展示 dry-run/安装矩阵，再等待确认。

## 安装

客户明确选择安装整个 `soia-env` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-env@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-env@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-open-skills-install -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
