# soia-pkm-alipan-curator

> 规划并整理阿里云盘资源，产出可复核的馆藏索引与学习规划

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-alipan-curator) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「整理阿里云盘资源」「更新阿里云盘索引」「用网盘资源做学习计划」

## 能力与用法

### 这个技能可以做什么

阿里云盘资源顾问，在 soia-pkm-alipan-drive-ops 原子操作上提供 inventory/organize/catalog/plan 四类工作流：盘点云盘、整理资源、生成 Obsidian 馆藏、增量 Excel 总索引与家庭课程导航、基于本次用户提供的学情生成学习计划

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到 Obsidian/vault 文件变更、终端日志、生成产物路径和最终回执。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

其他可识别说法包括「整理云盘」「云盘盘点」「更新云盘索引」「更新 Excel 总索引」「生成家庭导航 Excel」「给云盘建图书馆」；单个文件的浏览、下载或上传交给 `soia-pkm-alipan-drive-ops`。

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。

## 安装

客户明确选择安装整个 `soia-pkm-vault` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-alipan-curator -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
