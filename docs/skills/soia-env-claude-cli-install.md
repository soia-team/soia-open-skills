# soia-env-claude-cli-install

> 为小白安装、登录与授权更新 Anthropic Claude Code CLI

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-claude-cli-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 Claude CLI」「Claude 命令不存在」「Claude 登录」。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 Claude Code | 检查系统和已有来源，使用官方用户级渠道安装 | 当前版本、来源、安装目录和验证结果 |
| 检查或更新 | 比较当前版与官方最新版；明确授权后沿原来源更新 | “无需更新”“可更新，未执行”或“已更新” |
| 登录 Claude | 启动 `claude` 官方登录流程 | 浏览器授权步骤，不显示凭据 |
| 命令不可用 | 检查 PATH、重复安装和 `claude doctor` | 阻塞原因与安全修复方案 |

### 客户如何使用

1. 客户直接说“帮我安装 Claude Code CLI”；不要求客户复制终端命令。
2. Agent 先执行只读检查并展示计划。客户的安装请求只授权安装缺失的 CLI，不授权更新已有版本。
3. 只说“更新 Claude”时先显示两个版本并询问是否更新到最新；只有“更新到最新版本”等明确表述才调用更新器。
4. 需要登录时 Agent 启动流程，客户只在官方页面授权；授权码、API key、密码一律不进聊天。
5. 安装、更新和登录后分别验证独立 CLI 的版本、帮助命令、诊断结果和登录状态。

### 首次登录与真实配置验证

配置状态以 `config_status`/`config_file_status` 实测为准，未创建时引导客户在官方
页面完成首次登录，结果只能写「等待首次登录」；完整细则（API key 方式、复验要求）
见 [operations.md](references/operations.md)。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-claude-cli-install -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
