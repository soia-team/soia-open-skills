# soia-dev-drawio-visio-diagrams

> 将 Visio VSDX 安全转换、盘点和受控升级为可编辑 draw.io 图表

所属：[`soia-dev-design`](https://github.com/soia-team/soia-open-dev-design-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-design-skills/tree/main/skills/soia-dev-drawio-visio-diagrams) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「VSDX 转 draw.io」「Visio 图表升级」「draw.io 图表盘点」

## 能力与用法

### 这个技能可以做什么

| 客户目标 | 技能动作 | 可核验证据 |
|---|---|---|
| 读懂 VSDX | 只读解析 OOXML 包中的页面、形状、文字、连接和媒体 | JSON/Markdown 盘点、SHA-256、页数/形状数/连接数 |
| 转成 draw.io | 调用本机 draw.io Desktop CLI，把 VSDX 导入并导出为未压缩 `.drawio` XML | 原件未变、目标文件、CLI 版本、XML 验收 |
| 操作与升级 | 在副本上按 JSON 计划修改页面名、文字、样式和几何，或交给可选 draw.io MCP 做元素级编辑 | 变更计数、未匹配项、前后结构对比 |
| 生成预览/交付 | 从 `.drawio` 或 `.vsdx` 导出 PNG、SVG、PDF、JPG | 文件签名、大小、SHA-256、视觉复核 |
| 批量治理 | 递归检查目录并生成清单；修改仍逐文件显式执行 | 成功/失败/跳过清单，不覆盖原文件 |

### 客户如何使用

提供输入文件或目录、目标动作和交付路径。没有明确授权时只读，不覆盖原件。

```bash
python3 scripts/inspect_vsdx.py <diagram.vsdx> --format markdown
python3 scripts/drawio_cli.py doctor
python3 scripts/drawio_cli.py convert <diagram.vsdx> --output <diagram.drawio>
python3 scripts/inspect_drawio.py <diagram.drawio> --format markdown
python3 scripts/edit_drawio.py <diagram.drawio> --plan <upgrade-plan.json> --output <diagram-upgraded.drawio>
python3 scripts/drawio_cli.py export <diagram-upgraded.drawio> --format png --output <preview.png>
```

典型请求：

```text
读懂这个 ProcessOn 导出的 VSDX，列出页面、组件和关键链路
把这个 VSDX 转成可编辑 draw.io，原件不要动
把架构图里的旧系统名批量换成新名称，统一主色并导出 PNG
审查升级前后的 draw.io，确认页数、组件和关键文字没有丢
```

## 安装

客户明确选择安装整个 `soia-dev-design` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev-design@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev-design@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-dev-design-skills -a <agent> -s soia-dev-drawio-visio-diagrams -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
