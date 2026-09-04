# soia-env-qoder-cli-install

> 面向小白检查、安装、登录和按明确授权更新 Qoder CLI；识别官方独立安装、Homebrew 与 npm 来源，默认只报告版本和自动更新设置

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-qoder-cli-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 Qoder CLI」「qodercli 不存在」「Qoder 登录」「检查 Qoder 更新」「更新 Qoder 到最新」。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 Qoder CLI | 检查系统和现有来源，安装官方稳定版 | 版本、安装来源、目录和验证结果 |
| 检查或更新 | 只读比较版本；明确要求最新版后沿原来源更新 | 是否可更新及真实处理结果 |
| 登录 Qoder | 启动 `qodercli login` 或官方交互登录 | 官方浏览器授权步骤 |
| 命令不可用 | 检查 PATH、重复安装和配置状态 | 阻塞原因与安全修复方案 |

### 客户如何使用

1. 客户直接说“安装 Qoder CLI”；不要求客户输入终端命令。
2. Agent 先只读检查并展示安装计划。安装缺失工具不等于更新已有工具。
3. “更新 Qoder”先汇报当前和最新版本；只有明确说“更新到最新版本”才执行更新。
4. 登录时 Agent 启动官方流程，客户只在官方浏览器点击授权；不在聊天或终端粘贴密钥。
5. 完成后验证版本、帮助命令和一次无副作用启动，再输出固定十列列表。

### 首次登录与真实配置验证

- `配置文件目录`只显示候选目录；技能必须同时检查 `config_status` 和 `config_file_status`，目录或 `~/.qoder/settings.json` 不存在时明确报告“未初始化”。
- 首次使用时由 Agent 启动 `qodercli`，在交互界面执行 `/login`；客户选择浏览器登录并在 Qoder 官方页面完成授权，不需要客户操作终端。
- 如果客户明确选择 Personal Access Token，申请入口是 [Qoder Integrations](https://qoder.com/account/integrations)；客户只在官方登录流程中输入，Agent 不接收或打印 token。
- 登录后重新检查 `~/.qoder/settings.json`、运行 `qodercli --version` 和无副作用启动；没有完成登录时处理结果写“等待首次登录”，不能只写“已安装”。

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
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-qoder-cli-install -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
