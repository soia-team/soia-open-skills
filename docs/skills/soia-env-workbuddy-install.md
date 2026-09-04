# soia-env-workbuddy-install

> 为新手安装、验证或按授权更新 WorkBuddy 桌面客户端

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-workbuddy-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 WorkBuddy」「更新 WorkBuddy」「WorkBuddy 下载」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 WorkBuddy | 识别系统/架构并打开官方下载安装入口 | 官方下载链接和安装状态 |
| 检查 WorkBuddy 更新 | 识别已安装版本、来源和签名，不自动更新 | 当前版本、最新版本和签名 |
| 更新 WorkBuddy 到最新 | 客户明确要求最新版后沿用官方更新路径 | 中间状态、签名和启动验证 |
| WorkBuddy 打不开 | 检查安装结果、签名提示、网络和版本 | 可复现的阻塞类别与下一步 |
| 不会登录 | 引导官方界面登录 | 客户自己完成授权，不交出密码 |

### 客户如何使用

其他可识别说法包括「更新 WorkBuddy 到最新」「安装腾讯龙虾」「WorkBuddy 打不开」。

1. 说“安装 WorkBuddy”并说明系统；Agent 先确认系统和芯片架构。
2. Agent 只使用官方 `workbuddy.cn` 下载入口，不下载来路不明的 DMG/EXE。
3. 已安装时发现新版本只汇报；只说“更新 WorkBuddy”时先询问是否更新到最新，明确选择最新版后才执行。
4. 客户在系统安装器中完成打开、拖拽、权限和登录；Agent 不要求客户使用终端。
5. 安装或明确授权的更新过程中持续显示并记录检查、计划、执行、验证和终态。

### 首次启动与真实可用性验证

- 应用文件存在只代表“已安装”，不代表登录、服务授权和工作区已经可用。
- 安装完成后由 Agent 启动 WorkBuddy，客户在官方图形界面完成登录、验证码、系统安全提示和服务授权；Agent 不代填密码。
- Agent 重新检查应用启动、账号状态和一次无副作用工作区操作；其中任一步未完成，运行状态写“未验证”，处理结果写“等待首次登录/授权”，不伪报“正常”。

### 装完之后

本技能只负责**客户端本身**。把 SOIA 技能装进 WorkBuddy 是另一件事，
由 `soia-meta-skill-release` 负责——客户说「装到 WorkBuddy」即可触发。

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
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-workbuddy-install -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
