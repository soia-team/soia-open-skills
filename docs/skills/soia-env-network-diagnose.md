# soia-env-network-diagnose

> 只读诊断安装 AI 工具前的环境问题：网络侧检查 DNS、HTTPS、代理、证书、官方源和超时；本机侧按 Node/Python/Rust/Go/包管理器/Shell 分类盘点运行时，推导当前机器能装哪些 AI CLI，并用固定七列列表汇报

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-network-diagnose) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「网络不通」「下载失败」「npm/pip 超时」「证书错误」「安装卡住」「装之前先检查环境」「这台机器能装什么」「有没有装 node」。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装下载失败 | 探测官方 HTTPS、DNS、证书和延迟 | 可达/不可达、错误类别和下一步 |
| npm/pip 超时 | 区分网络、代理、包源和命令参数 | 不泄露 token 的诊断摘要 |
| 不知道是否能联网 | 执行最小只读检查 | 检查过的源数量和结论 |
| 装之前先体检 | 按类别盘点本机运行时 | Node/Python/Rust/Go/包管理器/Shell 的可用性与版本 |
| 这台机器能装什么 AI CLI | 用运行时结果对照各安装技能的渠道依赖 | 可安装 / 待复核 / 被阻塞，以及具体缺口 |

### 客户如何使用

1. 用自然语言描述失败的工具、错误提示和系统类型；不要求先运行命令。
2. Agent 先检查当前网络和官方源，不读取浏览器 cookie 或私有代理密码。
3. 诊断完成后，只有客户明确授权才调整代理、DNS 或证书，优先提供官方图形界面路径；修复后重新探测相同源。

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
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-network-diagnose -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
