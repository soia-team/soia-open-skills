# soia-dev-agent-cli-dispatch

> 受控调度外部 AI Agent CLI，选择已验证模型、隔离工作目录并回传模型、用量、费用与验证证据

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-agent-cli-dispatch) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「派活给外部 AI」「调用 DeepCode/Pi/agy」「多 CLI 派发」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 派一个任务给指定 AI CLI | 检查 CLI、认证、工作目录和权限，按该执行器规范启动 | 执行器、请求/实际模型、状态与验证结果 |
| 让系统自动选择模型档位 | 只从已有验证证据的候选中选择；无候选时阻断 | 选择理由、推理档、价格区间与证据状态 |
| 批量或断点执行 | 串行运行 case，逐项原子更新脱敏 manifest | 成功、失败、降级、超时、剩余任务与恢复状态 |
| 查看支持哪些 AI Agent | 读取 `references/supported-agents.yml` | 支持状态、使用方式、自动路由范围和对应规范 |

本技能不会把“进程退出码为 0”直接当成模型或任务质量已验证，也不会在没有证据时开放新的自动路由。

### 客户如何使用

客户至少说明：

1. 要完成的任务和验收标准；
2. 目标项目或工作目录；
3. 指定执行器/模型/推理档，或允许自动选择；
4. 是否允许修改文件、联网、创建 worktree、提交或执行其他高影响动作。

示例请求：

```text
把这个小范围修复派给 Pi，允许改当前项目，不允许提交；运行相关测试并回报实际模型和 Token。
```

### 配置文件

本技能目录中有两类 YAML，职责不同：

| 文件 | 性质 | 用途 |
|---|---|---|
| `references/supported-agents.yml` | 随技能发布的公共配置 | 支持哪些 AI Agent、适合什么工作、如何调用、验证到什么程度 |
| `assets/config.example.yml` | 私有配置模板 | 配置 host 标识及 state/temp 根目录；复制后由客户持有 |

可选私有配置位置与覆盖变量：

```text
~/.config/soia-skills/soia-dev-agent-cli-dispatch/config.yml
SOIA_DEV_AGENT_CLI_DISPATCH_CONFIG_FILE=<custom-config-path>
```

配置优先级：本次 CLI 参数 → 进程环境 → 私有 `config.yml` → 跨平台默认值。API key、cookie、token、session 不得写进该配置；它们留在 provider 登录态或系统凭据库。

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
