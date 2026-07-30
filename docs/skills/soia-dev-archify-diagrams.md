# soia-dev-archify-diagrams

> 用 Archify 将架构、数据流和流程说明生成可维护 JSON 图表及 PNG 预览

所属：[`soia-dev-design`](https://github.com/soia-team/soia-open-dev-design-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-design-skills/tree/main/skills/soia-dev-archify-diagrams) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「用 Archify 画」「Archify 架构图」「Archify 时序图」

## 能力与用法

### 这个技能可以做什么

Draw, improve, validate, or publish Archify architecture / data-flow / sequence / lifecycle diagrams with JSON IR and PNG previews

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到执行计划、命令输出摘要、代码/文档变更、验证结果和风险说明。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。

### 输出目录契约

输出目录按以下优先级解析：

1. 命令行 `--output-dir <path>`；
2. 进程环境变量或私有配置中的 `ARCHIFY_OUTPUT_DIR`；
3. 安全默认值 `~/Downloads/soia-dev-archify-diagrams/`。

`--output-dir` 可以是绝对路径或相对当前工作目录的路径。技能不会把用户交付物默认写入当前目录，也不会把 `~/.soia/workspaces/` 当作通用输出目录。

按交付场景显式指定目录：

- 仓库 README / 文档：`--output-dir assets/diagrams`；
- 已明确确认的 SOIA proposal：`--output-dir <workspace>/proposals/<proposal-id>/design/diagrams`；
- 普通临时预览或未指定项目目录：使用上述 `~/Downloads/soia-dev-archify-diagrams/` 默认值。

使用 `--png-only` 时，HTML 只作为输出目录内的临时中间文件，PNG 导出成功后会删除 HTML；不使用 `--png-only` 时保留 HTML，便于浏览器预览和排错。

## 安装

本技能随 `soia-dev-design` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev-design@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev-design@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-dev-design-skills -g -a '*' -s soia-dev-archify-diagrams -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
