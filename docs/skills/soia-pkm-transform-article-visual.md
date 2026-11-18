# soia-pkm-transform-article-visual

> 把文章转换为长图、信息图、海报、封面、插画等视觉产物。HTML/CSS 截图为本地默认方案，可选 Open Design 或 Codex 图生成

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-transform-article-visual) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「生成长图」「做成信息图」「转成海报」「生成封面」「做成图片」「export visual」「make infographic」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 文章转长图/信息图/概念图/海报/封面 | 按 `visual_dense` 重组核心概念，写 prompt 落盘并用选定 provider 生成高清图 | PNG/JPEG 路径、分辨率与 `view_image` 验收结果 |
| 切换生成引擎（`local` / `open-design` / `codex-image`） | 优先客户指定，按硬依赖就绪情况执行并在报告中写明真实 provider | prompt 路径与真实渲染通道记录 |

### 客户如何使用

说明来源（vault 路径/URL 先 clip）和目标类型（`long_image` 默认 / `infographic` / `concept_map` / `poster` / `cover` / `illustration`），可选指定 provider 与参考图（仅提取版式语法，不抄内容）。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-transform-article-visual -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
