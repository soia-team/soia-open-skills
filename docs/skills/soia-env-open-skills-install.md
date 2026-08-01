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

### 客户如何使用（自然语言示例）

| 客户说 | 技能的理解 | 执行范围 |
|---|---|---|
| 「帮我装好所有 SOIA 技能」 | 全量安装，全宿主 | 8 域 × 3 宿主 |
| 「帮我装好所有 SOIA 插件」 | 全量安装，全宿主 | 8 域 × 3 宿主 |
| 「帮我在 Codex 下装好所有 SOIA 技能」 | 全量安装，Codex 宿主 | 8 域 × Codex |
| 「帮我在 Codex 下装好所有 SOIA 插件」 | 全量安装，Codex 宿主 | 8 域 × Codex |
| 「帮我在 Claude Code 下装好所有 SOIA 技能」 | 全量安装，Claude Code 宿主 | 8 域 × Claude Code |
| 「帮我更新 Claude Code 下所有 SOIA 插件」 | 全量更新，Claude Code 宿主 | 8 域 × Claude Code |
| 「帮我更新 Claude Code 下 soia-dev 插件」 | 单域更新，Claude Code 宿主 | soia-dev × Claude Code |
| 「帮我更新 Claude Code 下 soia-dev 里的 soia-dev-coding-agent 技能」 | 单技能触发，更新整个插件 | soia-dev × Claude Code |
| 「帮我在 WorkBuddy 里装好所有 SOIA 专家」 | 全量安装，WorkBuddy 宿主 | 8 域 × WorkBuddy |
| 「只查看当前状态，不安装」 | 只读检查 | 3 宿主全查，不改动 |

执行任何安装/更新前都展示计划并等客户确认；没有得到明确同意前不改动机器。

### 8 个开源域插件

| 插件名 | 域仓 | 技能数 | 常驻成本 |
|---|---|---|---|
| `soia-meta` | soia-open-skills | 4 | ~428 tok |
| `soia-dev` | soia-open-dev-skills | 9 | — |
| `soia-dev-design` | soia-open-dev-design-skills | 5 | — |
| `soia-pkm-vault` | soia-open-pkm-vault-skills | 15 | — |
| `soia-media-content` | soia-open-media-content-skills | 6 | ~728 tok |
| `soia-cwork-office` | soia-open-cwork-office-skills | 3 | — |
| `soia-env` | soia-open-env-skills | 15 | — |
| `soia-edu-course` | soia-open-edu-course-skills | — | — |

## 安装

本技能随 `soia-env` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-env@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-env@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-open-skills-install -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
