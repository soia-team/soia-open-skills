# soia-pkm-transform-obsidian-pdf

> 用 Obsidian 原生导出把 vault 内 Markdown 笔记导出为 PDF。vault 外文章降级 pandoc/weasyprint

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-transform-obsidian-pdf) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「转成PDF」「导出PDF」「归档并转PDF」「生成PDF」「export PDF」

## 能力与用法

### 这个技能可以做什么

把 Markdown 文章或已归档 vault 笔记导出为 PDF，使用 Obsidian 原生导出（`Creator: Chromium / Producer: Skia/PDF`）保证中文正确渲染。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取文章、调用 Obsidian 导出或降级本地渲染 | PDF 路径、页数、文件大小 |
| 缺少 Obsidian / vault | 提示降级方案（pandoc / weasyprint） | 降级说明与命令 |
| 执行完成 | 验证 PDF 可打开、页数合理 | 完成回执 + 验证结果 |

### 客户如何使用

1. 说明来源：vault 内已归档笔记路径 / X URL / 网页 URL / 本地 Markdown。
2. 可选：指定输出目录（默认与源文件同目录）。
3. URL 来源先走 `soia-pkm-clip-*` 归档，再执行 PDF 导出。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-transform-obsidian-pdf -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
