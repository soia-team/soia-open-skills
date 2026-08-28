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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-ai-cli-upgrade -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
