# soia-env-pi-cli-install

> 为小白安装、配置与授权更新 Pi（pi-coding-agent）CLI

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-pi-cli-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 Pi」「pi 不存在」「更新 Pi CLI」「pi-coding-agent」。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 Pi | 核对项目身份、Node.js 和 npm，再安装上游包 | 版本、来源、安装和配置目录 |
| 检查或更新 | 从 npm 官方元数据比较版本；明确授权后沿 `pi update --self` 更新 | 可更新状态或“已更新” |
| 配置模型/Provider | 检查 `~/.pi/agent/settings.json` 的 provider/model 设置，保护凭据 | 配置位置与本地安全配置下一步 |
| 命令不可用 | 检查 PATH、npm 全局目录和同名命令 | 阻塞原因与修复方案 |

### 客户如何使用

1. 客户说“安装 Pi”；Agent 先确认目标是 `@earendil-works/pi-coding-agent`，客户不需要操作终端。
2. Agent 只读检查 `pi`、Node.js、npm、实际包来源和版本，再展示计划。
3. 安装请求只授权安装缺失 CLI；已有版本默认不更新。模糊“更新”只显示版本，明确“更新到最新”才执行。
4. 运行需要模型凭据时，客户在对应 Provider 平台（如 DeepSeek）自行创建或管理 key；不得把 key 发到聊天中。Agent 只指导本机受保护输入或使用客户已有的安全凭据注入。
5. 完成后验证版本和帮助命令；未配置凭据时如实写“已安装，等待本地配置”，不伪报运行正常。

### 首次配置与真实验证

- `~/.pi/agent` 只是默认数据目录（sessions、skills、extensions、git、npm 包）；必须同时检查目录和 `~/.pi/agent/settings.json`。目录存在不代表 provider 已配置。
- 首次启动 `pi` 会初始化部分本地运行状态，但不会替客户生成包含凭据的 `settings.json`。
- Pi 的模型/Provider 配置在 `~/.pi/agent/settings.json`（如 `defaultProvider`、`defaultModel`、`theme`），**不包含密钥**；Provider 凭据走环境变量（如 `DEEPSEEK_API_KEY`）或 `pi auth`。
- 客户在 Provider 平台创建 API key 后，在 shell 环境（如 `~/.zshrc`）或 `pi auth` 中配置，不把 key 发给 Agent。
- Agent 重新检查 `config_status`、`config_file_status`，再做无副作用验证；只有实际请求成功，运行状态才写“正常”。

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
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-pi-cli-install -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
