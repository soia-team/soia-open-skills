# soia-env-open-skills-install

> 在 Claude Code、Codex、WorkBuddy 上安装或更新 SOIA 开源技能，支持全部/单插件/单技能粒度与指定宿主

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-open-skills-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「装好所有 SOIA 插件」「在 Codex 下装 SOIA」「更新 soia-dev 插件」。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 全量装好所有 SOIA 技能 / 插件 | 接入市场 → 安装全部 8 个域插件 → 三宿主 | 每宿主安装计划与域级回执 |
| 在指定宿主装全部 SOIA 技能 | 只操作目标宿主，跳过其余 | 单宿主域级回执 |
| 装或更新某个域插件（如 soia-dev） | `plugin install / plugin update` 该域 | 该域在各宿主的前后版本对比 |
| 更新某个域插件下的单个技能 | 更新整个插件（技能以插件为交付单元）+ 说明哪个技能已更新 | 插件级更新 + 技能变更说明 |
| 检查当前安装状态，不改动机器 | 列出各宿主市场状态与已安装插件版本 | 三宿主三列状态表 |

> **粒度说明**：SOIA 以「域插件」为最小交付单元（如 `soia-dev@soia` 含 9 个技能）。「更新单个技能」在插件模式下等价于更新整个域插件，但技能会说明是哪个技能触发了更新。若需要真正按技能粒度安装（不安装同域其他技能），必须改用 `npx skills add` 路线——技能会提示该路线与插件路线互斥，让客户选择。

### 客户如何使用

完整自然语言示例表（10 条：全量/单域/单技能 × 三宿主，含「只查看当前状态」）见 [user-phrases.md](references/user-phrases.md)。执行任何安装/更新前都展示计划并等客户确认；没有得到明确同意前不改动机器。

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
