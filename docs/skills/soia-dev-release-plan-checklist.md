# soia-dev-release-plan-checklist

> 为互联网软件发版生成发布清单、预检门、灰度验证与发布后核对；适用于上线、部署、回滚规划

所属：[`soia-dev`](https://github.com/soia-team/soia-open-dev-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-skills/tree/main/skills/soia-dev-release-plan-checklist) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「上线前检查什么」「灰度方案」「回滚预案」

## 能力与用法

### 这个技能可以做什么

提供发布目标、版本/分支、环境、变更和服务依赖；信息不全时也可先产出带待确认项的草案。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 上线一个软件版本 | 汇总版本、分支、制品、配置和依赖服务 | 分阶段发布清单与责任待定项 |
| 控制上线风险 | 设计测试、审批、回滚预检门和停止条件 | 可判定通过/阻断的预检表 |
| 灰度后确认结果 | 编排灰度范围、观察指标与验证步骤 | 灰度及发布后验证清单 |

### 客户如何使用

用自然语言说明发布目标，并尽量提供：服务或产品、目标环境、版本与源分支、制品标识、配置变更、依赖服务、期望窗口、审批人和回滚方案。可用下面的最小输入：

```yaml
release:
  product_or_service: <服务或产品>
  environment: <staging|production>
  version: <版本或提交标识>
  source_branch: <分支>
  artifact: <镜像、包或构建产物标识>
  config_changes: [<变更或无>]
  dependencies: [<依赖服务>]
  release_window: <时间窗口或待定>
```

未知信息必须标为“待确认”，不能由 Agent 猜成既定事实。客户确认清单后，按其既有发布平台和权限执行；本技能本身不发布。

## 安装

客户明确选择安装整个 `soia-dev` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-dev-skills -a <agent> -s soia-dev-release-plan-checklist -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
