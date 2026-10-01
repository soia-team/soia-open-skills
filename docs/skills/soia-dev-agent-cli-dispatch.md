# soia-dev-agent-cli-dispatch

> 派任务给外部 AI CLI 进程并核验模型、额度与产物；宿主内置 subagent 不用本技能

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-agent-cli-dispatch) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

派给 Codex/Pi 等外部 CLI、多 CLI 分工、外部自动选模

## 能力与用法

### 这个技能可以做什么

- **派给指定 CLI：** 检查 CLI、认证、工作目录与权限，按该执行器规范启动；回报请求/实际模型、状态与验证结果。
- **自动选模：** 只在本次预检报告里 `available` 且有验证证据的候选桶中选；报告缺失、错绑或畸形时阻断。
- **批量或断点执行：** 串行跑 case，逐项原子更新脱敏 manifest。
- **查支持哪些 CLI：** 读 `references/supported-agents.yml`。

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
