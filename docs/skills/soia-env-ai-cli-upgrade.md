# soia-env-ai-cli-upgrade

> 审计并按授权升级多款 AI CLI，先预演并核验结果

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-ai-cli-upgrade) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「升级 AI CLI」「更新 Claude/Kimi」「检查 CLI 版本」。

## 能力与用法

### 这个技能可以做什么

进阶维护工具：面向已装多套 AI CLI 的用户，与本仓面向小白的单工具安装技能定位不同。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 盘点本机 AI CLI 版本 | `DRY_RUN=1` 只读审计，不动任何东西 | 七列状态表 + 日志路径 |
| 升级全部或指定工具 | 明确授权后按检测到的安装通道升级 | 每款工具旧/新版本与结果 |
| 安装通道不合官方推荐 | 不代迁移，`NOTE` 列给出建议 | 「下载 → 审阅 → 本地执行」三段式迁移指引 |

覆盖 codex、claude、agy、gemini（非消费者通道，显式 opt-in）、qwen、kimi、mmx、
opencode、qodercli、deepcode、pi、cursor（仅审计）。各工具安装通道与默认升级方式
见 [tools-covered.md](references/tools-covered.md)。

### 客户如何使用

1. 说人话即可：「升级 AI CLI」「检查 CLI 版本」「我的 codex 该更新吗」。默认先
   dry-run 只读盘点，客户圈定后才真升级。
2. 涉及换安装通道、安装缺失工具等动作，先展示计划并单独征求确认。

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
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-ai-cli-upgrade -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
