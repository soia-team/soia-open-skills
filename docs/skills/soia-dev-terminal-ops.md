# soia-dev-terminal-ops

> 管理 POSIX/macOS/Linux 上的长任务、tmux 后台会话、日志抓取、停滞诊断与安全恢复；杀进程前用日志、CPU、网络多信号交叉判断，并走 TERM→复查→KILL 门

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-terminal-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「进程卡住了」「后台跑这个」「安全杀进程」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 启动或观察长任务 | 用参数化的 session、日志目录和命令启动 tmux/后台任务 | command、workdir、session/PID、日志路径和当前状态 |
| 判断任务是否停滞 | 在用户指定观察窗口内交叉检查日志、CPU、网络/子进程进展 | 每项信号的证据以及“运行中/疑似停滞/无法判断”结论 |
| 恢复或终止任务 | 先确认目标与数据风险，再按 TERM→复查→KILL 顺序处理 | 每个信号、确认点、退出状态和后续恢复建议 |

### 客户如何使用

提供以下输入；缺少会改变终止目标或日志落点的输入时，先询问，不猜：

- 要运行或诊断的命令、工作目录；
- 已有 PID 或 tmux session（如适用）；
- `session_name`、`log_dir`、`stall_window_seconds`、`term_grace_seconds`；
- 可选的 `fallback_command`，以及是否预先授权终止目标进程。

只查看短命令输出或文件内容时无需调用本技能。

## 安装

本技能随 `soia-dev` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-dev-skills -g -a '*' -s soia-dev-terminal-ops -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
