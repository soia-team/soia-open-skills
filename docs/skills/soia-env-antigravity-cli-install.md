# soia-env-antigravity-cli-install

> 为新手安装、登录、迁移或按授权更新 Google Antigravity CLI（agy）

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-antigravity-cli-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 agy」「Gemini CLI 迁移」「agy 登录」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 agy | 检查系统架构和已有命令，使用 Google 官方安装入口 | 版本、安装目录和可运行验证 |
| 从 Gemini CLI 迁移 | 分别检查 `gemini` 与 `agy`，按官方迁移说明生成计划 | 哪个是旧命令、哪些配置可迁移、哪些需确认 |
| 检查或更新 | 读取 Google 官方平台清单；明确授权后调用 `agy update` | 当前版、最新版和处理结果 |
| 登录或排错 | 启动官方登录并检查 PATH、凭据库和配置目录 | 浏览器步骤或阻塞原因 |

### 客户如何使用

其他可识别说法包括「安装 Antigravity CLI」「更新 agy 到最新」。

1. 客户说“安装 agy”或“把 Gemini CLI 迁移到 Antigravity”；不要求客户操作终端。
2. Agent 先只读检测 OS、架构、`agy`、`gemini` 和已有配置，再展示计划。只检查不会迁移或更新。
3. 安装请求只授权安装缺失的 `agy`；迁移、覆盖配置、修改 PATH 和管理员权限分别确认。
4. 模糊的“更新 agy”只显示版本；只有“更新到最新”才执行 `agy update`。
5. 登录时客户只在 Google 官方页面确认账号和权限，不把验证码、token 或 cookie 发给 Agent。

### 首次登录与真实配置验证

- `~/.gemini/antigravity-cli` 是候选状态/配置目录；技能必须先检查它是否真实存在，不能因为输出了默认路径就判定 agy 已登录。
- 如果目录尚未创建，Agent 启动官方 `agy` 流程；客户在 Google 官方浏览器页面完成登录、账号选择和权限同意。
- 登录后重新检查 agy 的配置/状态目录、`--version`、`--help` 和无副作用启动；只存在 `gemini` 或只有版本命令可运行时，处理结果仍写“等待首次登录/配置”。
- 迁移请求必须把 `gemini` 和 `agy` 的配置分开核对；不得把 Gemini 的目录存在当成 agy 已配置。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-antigravity-cli-install -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
