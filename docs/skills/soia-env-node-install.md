# soia-env-node-install

> 为新手安装、验证或按授权更新 Node.js 与 npm

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-node-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 Node.js」「更新 Node.js」「node 命令不存在」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 Node.js | 识别系统/架构、选择官方 LTS、安装并验证 | Node/npm 版本和路径状态 |
| 检查 Node.js 更新 | 识别安装来源、比较项目约束与最新 Active LTS，不自动更新 | 当前版本、最新版本和来源 |
| 更新 Node.js 到最新 | 客户明确要求最新版后沿原来源更新 | 中间状态、版本变化和回滚边界 |
| npm 不可用 | 检查 PATH、npm prefix 和权限 | 阻塞原因与安全修复方案 |
| 为 Codex 准备环境 | 先验证 Node/npm，再交给 Codex 技能 | 可继续执行的 readiness 状态 |

### 客户如何使用

其他可识别说法包括「更新 Node 到最新」「安装 npm」「npm 超时」；纯网络故障优先交给 `soia-env-network-diagnose`。

1. 说目标项目、操作系统和是否需要特定 Node 大版本；不确定时默认选择最新官方 Active LTS，不固定写死一个永久版本号。
2. Agent 先检查现有 `node`、`npm` 和项目配置，不自动卸载旧版本。
3. 发现新版本时只汇报；只说“更新 Node”时先询问是否更新到最新，客户明确选择最新版后才执行。
4. 展示安装来源、版本和 PATH 影响；需要管理员权限时单独确认。
5. 安装或明确授权的更新过程中持续显示并记录检查、计划、执行、验证和终态。

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
npx skills add soia-team/soia-open-env-skills -a <agent> -s soia-env-node-install -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
