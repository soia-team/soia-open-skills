# soia-pkm-library-book-catalog

> 纯本地、幂等、可重复运行地维护 Obsidian 书库：补建待读记录并重新生成图书馆、阅读记录和按类型总览，不依赖微信读书

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-library-book-catalog) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「重新生成图书馆总览」「更新阅读记录总览」「补建待读记录」「书库整理」

## 能力与用法

### 这个技能可以做什么

这个技能适合在已有书卡或阅读记录的基础上整理本地书库。它会按书卡的分类字段生成图书馆总览和阅读记录总览，也可以把“有书卡但没有阅读记录”的书幂等地补成“待读”记录，并生成按类型分组的视图。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 补建待读记录 | 扫描书卡与阅读记录，创建缺失记录，已有目标则跳过 | 新建、跳过和失败数量 |
| 重新生成图书馆总览 | 读取本地书卡并生成分类嵌套视图 | 输出文件与书目统计 |
| 更新阅读记录总览 | 以书卡分类为准汇总 7 态阅读生命周期 | 状态、分类和处理统计 |
| 书库整理 | 依次执行补建与三份视图生成 | 每阶段回执和可重复执行结果 |

### 客户如何使用

1. 用自然语言说明要补建待读记录、更新某份总览，或整理整个书库。
2. 提供 `--vault <path>`，或在私有配置中设置 `OBSIDIAN_VAULT`；不需要 `WEREAD_API_KEY` 或微信读书登录态。
3. 生成脚本支持 `--output <path>` 预览，确认内容后再省略该参数写回 vault。
4. 执行后核对真实输出与统计；所有脚本均可安全重复运行。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-library-book-catalog -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
