# soia-cwork-feishu-cli

> 用飞书官方 lark-cli 以最小权限只读调研 Wiki、Drive 与文档，或把知识库只读同步为本地 Markdown

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-cwork-feishu-cli) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「调研飞书知识库」「读取飞书云盘」「配置飞书 CLI」「同步飞书知识库」「飞书备份到 Git」「规划双向同步」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 调研飞书 Wiki 与云盘结构 | 分离 Wiki 与 Drive 接口，按 bot（或授权后 user）盘点空间、节点、文档类型与权限 | 结构化盘点、已访问范围、bot 不可见缺口与证据命令 |
| 读取、总结或评估迁移飞书文档 | 识别 URL 类型并按 `lark-doc` 规则读取正文与大纲 | 文档摘要、引用位置与迁移限制 |
| 初始化与诊断 `lark-cli` 凭证 | 用 stdin 安全写入应用 profile，校验身份、token、scope 与错误码 | 脱敏连通性状态与最小需开 scope/发布指南 |
| 同步飞书知识库到本地 / Git | 以 bot 只读增量镜像为 Markdown，保留层级、来源与同步元数据 | 镜像目录、同步清单、失败清单与验收结果 |

### 客户如何使用

- 「用飞书 CLI 盘点我可见的知识库层级和云盘文档类型，不要修改任何内容。」
- 「读取这个飞书 Wiki 页面，评估适合迁移到哪类本地知识库。」
- 「检查 `lark-cli` 认证报错并列出最小需开通权限。」
- 「把这个飞书知识空间按增量模式同步成本地 Markdown 并做完整性验收。」

## 安装

客户明确选择安装整个 `soia-cwork-office` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-cwork-office@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-cwork-office@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-cwork-feishu-cli -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
