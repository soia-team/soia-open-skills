# soia-env-kimi-cli-install

> 面向小白检查、安装、登录和按明确授权更新 Moonshot AI Kimi Code CLI；识别官方独立安装与 npm 来源，默认只报告版本和产品自动更新状态

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-kimi-cli-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 Kimi CLI」「安装 Kimi Code」「kimi 不存在」「Kimi 登录」「更新 Kimi 到最新」。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 Kimi Code | 检查已有来源并使用官方稳定渠道安装 | 版本、安装方式、安装和配置目录 |
| 检查或更新 | 从官方 npm 发布元数据比较版本；明确授权后沿原来源更新 | 是否可更新及处理结果 |
| 登录 Kimi | 启动 `kimi login` 或交互界面的 `/login` | 官方浏览器授权步骤 |
| 命令不可用 | 检查 PATH、重复安装和配置目录 | 阻塞原因与安全修复方案 |

### 客户如何使用

1. 客户说“安装 Kimi Code CLI”；不要求客户复制终端命令。
2. Agent 先只读检查并展示计划；安装缺失 CLI 不授权更新已有 CLI。
3. 只说“更新 Kimi”时先显示当前版和最新版；明确“更新到最新版本”才执行更新。
4. 登录由 Agent 启动，客户只在 Moonshot/Kimi 官方页面点击授权；不发送 token、密码或授权码。
5. 完成后验证版本、帮助命令和登录状态，再输出固定十列列表。

### 首次登录与真实配置验证

- `~/.kimi-code` 是候选数据目录；用户配置文件是 `~/.kimi-code/config.toml`，技能必须分别检查目录和文件是否真实存在。
- Kimi Code 首次运行可以自动创建 `config.toml`；如果目录或文件不存在，Agent 启动 `kimi login`（设备码流程）或 TUI 的 `/login`，客户在 Kimi 官方页面完成授权。
- 使用 Kimi Code 托管服务不需要客户手动填写 API key；如果客户选择 Kimi Platform 或其他供应商，才按官方配置文件写入对应 provider，申请入口以官方页面为准。密钥不得发到聊天中。
- 登录或配置后运行 `kimi doctor`、`kimi --version` 和无副作用启动；没有完成授权时处理结果写“等待首次登录/配置”，不能只显示默认目录。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-kimi-cli-install -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
