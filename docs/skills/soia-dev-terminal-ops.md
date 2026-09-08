# soia-dev-terminal-ops

> 管理长任务与后台日志，诊断停滞并安全停止或恢复明确进程

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-terminal-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

后台跑这个、进程疑似卡住、安全停止进程

## 能力与用法

**能做什么：** 在 POSIX/macOS/Linux 中管理长任务、日志与恢复。普通短命令不用本技能；Windows 原生不在兼容范围，可使用已具备的 WSL/POSIX 环境。

**如何使用：** 指定命令/工作目录或已有 PID/session 及目标。先用宿主现有会话与等待能力；确需脱离会话运行时才用 tmux，不因超过固定秒数自动后台化。

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
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-terminal-ops -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
