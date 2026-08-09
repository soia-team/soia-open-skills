# soia-env-codex-install

> 为新手安装、验证或按授权更新 OpenAI Codex CLI

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-codex-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 Codex CLI」「更新 Codex CLI」「Codex 命令不存在」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 Codex | 检查依赖、安装官方包、验证命令 | Codex CLI 固定状态列表和安装目录 |
| 检查 Codex 更新 | 识别实际生效的 CLI 来源并比较版本，不自动更新 | 当前版本、最新版本和来源 |
| 更新 Codex 到最新 | 客户明确要求最新版后，沿用原来源更新 | 中间状态、更新结果、安装方式和配置目录 |
| 登录 Codex | 启动官方登录流程 | 可点击的官方授权步骤，不显示密钥 |
| Codex 找不到 | 诊断 PATH、npm 全局目录和 shell | 修复建议或需要确认的变更 |

### 客户如何使用

“安装 Codex”只授权安装缺失的独立 CLI，不授权更新已装版本；“检查更新”或模糊的“更新 Codex”只做版本审计并询问是否更新到最新。只有客户明确说“更新 Codex 到最新”“升级到最新版”或同等指令才调用升级执行；管理员权限、切换来源或修改 PATH 仍需单独确认。

### 首次登录与真实配置验证

`配置文件目录`只显示 `CODEX_HOME` 或默认候选路径，必须同时检查 `config_status`，不能把 `~/.codex` 直接当成已登录；未登录时用独立 CLI 同一绝对路径执行 `codex --login`，客户在官方页面完成授权，登录后复核 `login status`/`--version`/`--help`/`config_status`。细则见 [operations.md](references/operations.md)。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-codex-install -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
