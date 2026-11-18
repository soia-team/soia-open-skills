# soia-dev-agent-cli-dispatch

> 派任务给外部 AI CLI 进程并核验模型、额度与产物；支持同一 CLI 多账号（账号槽位）、登录检测与各账号套餐/剩余额度查看，宿主内置 subagent 不用本技能

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-agent-cli-dispatch) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

派给 Codex/Pi/agy 等外部 CLI、多账号/切换账号、看额度/agy 账号

## 能力与用法

### 这个技能可以做什么

- **派给指定 CLI、自动选模：** 检查 CLI、认证、工作目录与权限后按该执行器规范启动，回报请求/实际模型、Token 与验证结果；自动选模只在本次预检里 `available` 且有验证证据的桶中选。说「把这个派给 Codex」即可；支持哪些 CLI 见 `references/supported-agents.yml`，路由判据见 `references/executor-routing.md`。
- **同一 CLI 多账号（账号槽位）：** 每个账号是一个槽位（一组隔离登录态的环境变量，如 agy 用独立 `HOME`），派单 `--slot <名>` 指定或 `--rotate` 轮流，额度与用量按槽位分开记，不按剩余额度自动调度。登记与建槽位：`scripts/account_slots.py init`；详见 `references/account-slots.md`。
- **查看各账号套餐与剩余额度（agy）：** `python3 scripts/agy_quota.py` 并行列出每个槽位的 5 小时 / 7 天剩余百分比与重置时间、AI credits 和可用模型，只读、不耗额度；套餐名 agy 不提供时标「CLI 不提供」。字段见 `references/account-slots.md`「查看各槽位额度（agy）」。
- **登录检测与选账号：** `python3 scripts/agy_quota.py --pick --model <id> --rotate` 先检测不先问：未建槽位给 init 命令，未登录给确切的 `HOME=~/.agy-profiles/<槽位> agy` 命令（须本人在浏览器授权），已登录只汇报一行并自动跳过额度用尽、不含该模型的账号。
- **agy / Gemini 4 显式派单：** 代码单默认 `gemini-4-argon-high`、日常小单 `gemini-4-hydrogen-<level>`，显式写 `--mode`；不同账号可见模型不同（如部分账号有 `gemini-4-carbon-*`）。见 `references/antigravity-cli.md`「派单默认」与「派单选择」。
- **批量或断点执行：** `scripts/run_matrix.py` 串行跑 case（可带 `slot`），逐项原子更新脱敏 manifest，中断后按 manifest 续跑。

进程退出码 0 不等于模型或任务质量已验证；没有证据不开放新的自动路由。

### 客户如何使用

说明任务与验收标准、目标工作目录、执行器/模型/推理档（或允许自动选择），以及是否允许改文件、联网、建 worktree、提交或其他高影响动作。例：「把这个小修复派给 Pi，允许改当前项目、不许提交；跑相关测试并回报实际模型和 Token。」

## 安装

客户明确选择安装整个 `soia-dev` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-agent-cli-dispatch -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
