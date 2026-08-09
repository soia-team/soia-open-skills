# soia-env-codex-setup-support

> 诊断并支持 Codex 桌面版与 CLI 的安装、登录、性能和存储问题

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-codex-setup-support) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「Codex 打不开」「Codex 变慢」「检查 logs_2.sqlite」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 交付形式 |
|---|---|---|
| 安装或验证 Codex | 检查版本、来源、桌面宿主和 CLI | 结果表 + 下一步 |
| 检查 Codex 更新 | 分别识别桌面应用与 CLI 的版本、来源和更新入口，不自动更新 | 当前版本、最新版本和建议 |
| 更新 Codex 到最新 | 客户明确要求最新版后分别更新桌面应用或 CLI | 中间状态、登录/签名复核和失败回滚边界 |
| Codex 变慢或卡住 | 按资源、日志、网络和工作区分类 | 分类表 + 证据 |
| 检查 SSD 健康 | 只读读取 SMART 和空间信息 | 健康度表 + 风险说明 |
| 检查 `logs_2.sqlite` | 只读比较文件、WAL、ID 速率和热点 | 写入风险表 + 处置边界 |

### 客户如何使用

直接描述目标，例如“检查磁盘健康”“Codex 变慢”“检查 logs_2.sqlite”。Agent 默认只读，发现新版本只汇报；只说“更新 Codex”时先询问是否更新到最新。登录、系统授权、安装和数据隔离会单独说明并请求确认。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-codex-setup-support -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
