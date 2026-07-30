# soia-env-opencode-cli-install

> 为新手安装、登录、配置或按授权更新 OpenCode CLI

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-opencode-cli-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 OpenCode」「配置 OpenCode CLI」「OpenCode 登录」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 OpenCode | 检查已有来源并用官方稳定渠道安装 | 版本、来源、安装和配置目录 |
| 检查或更新 | 比较 GitHub 官方最新 release；明确授权后沿原来源升级 | 可更新状态或“已更新” |
| 配置模型供应商 | 只处理非秘密设置并启动官方认证 | 配置位置和浏览器下一步 |
| 命令不可用 | 检查 PATH、重复副本和配置覆盖 | 阻塞原因与修复方案 |

### 客户如何使用

其他可识别说法包括「opencode 不存在」「更新 OpenCode 到最新」。

1. 客户说“安装 OpenCode”；不要求客户复制终端命令。
2. Agent 先只读检查并展示计划；安装缺失 CLI 不授权更新已有 CLI。
3. 模糊“更新 OpenCode”只显示当前版和最新版；明确“更新到最新”才执行升级。
4. 配置或登录时不索要 API key；有官方 OAuth/浏览器流程就由客户在官方页面完成。
5. 完成后验证版本、帮助命令和无副作用启动，再输出一行固定状态。

### 首次配置与真实认证验证

- `~/.config/opencode` 是配置候选目录；供应商凭据通常由 `opencode auth login` 写入 `~/.local/share/opencode/auth.json`，两者必须分开检查，不能把一个不存在的目录当成已配置。
- 首次配置由 Agent 启动 `opencode auth login`，客户在供应商官方页面完成 OAuth 或在官方交互界面输入凭据；Agent 不接收、不回显 API key。
- 完成后运行 `opencode auth list`，再启动 OpenCode 并执行无副作用的模型/帮助检查；没有供应商凭据时处理结果写“等待供应商登录/配置”。
- 只有需要自定义模型或项目设置时才创建 `~/.config/opencode/opencode.json` 或项目 `opencode.json`；默认配置文件不存在不等于 CLI 安装失败。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-opencode-cli-install -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
