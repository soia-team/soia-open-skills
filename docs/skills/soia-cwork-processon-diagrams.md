# soia-cwork-processon-diagrams

> 安全盘点并按授权导出、校验和归档 ProcessOn 图表

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-cwork-processon-diagrams) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

ProcessOn 盘点、导出架构图、批量下载图表

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 递归盘点团队空间与增量对比 | 递归至叶子目录分批审计 checkpoint，或对两份已审计快照运行差分 | 目录/文件树、遗漏差集、权限缺口、增量清单与审计回执 |
| 受控批量导出与无复制归档 | 在独立专用 headless context 内下载至受管 staging，校验后按同盘 move 归档并支持尾单监督续跑 | 下载格式/尺寸/SHA-256、`download-progress.json`、碰撞确认与监督状态 |
| 解析已有本地导出文件 | 用 `inspect_processon_export.py` 提取 POS、XMind、SVG、图片与 PDF 标题/节点/校验值 | 结构化内容清单；VSDX 编辑/升级交给 draw.io 或 Visio 处理 |

### 客户如何使用

- 「初始化盘点这个 ProcessOn 团队空间，只读，不下载：`<team-url>`」
- 「对比两次已审计快照做增量盘点，只列新增、变更与待确认移除候选。」
- 「按已审计计划导出已确认流程图为 VSDX、思维导图为 XMind，归档到 `<output-dir>`。」
- 「解析 `<export-dir>` 里的 POS/XMind，或核对下载清单。」

未指定格式时，流程图默认 `.vsdx`、思维导图默认 `.xmind`（建议同留 `.pos` 原生备份），无法确认的类型只入待人工确认清单；首次登录由客户在独立弹窗手动完成。

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
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-cwork-processon-diagrams -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
