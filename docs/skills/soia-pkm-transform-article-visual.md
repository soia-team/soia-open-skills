# soia-pkm-transform-article-visual

> 把文章转换为长图、信息图、海报、封面、插画等视觉产物。HTML/CSS 截图为本地默认方案，可选 Open Design 或 Codex 图生成

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-transform-article-visual) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「生成长图」「做成信息图」「转成海报」「生成封面」「做成图片」「export visual」「make infographic」

## 能力与用法

### 这个技能可以做什么

把 Markdown / vault 文章或 URL 渲染为图片产物：

- **长图**：完整文章内容纵向展开为单张 PNG/JPEG
- **信息图**：核心概念可视化，节点 + 连接 + 标注
- **术语地图 / 路线图**：左侧认知路径 + 右侧视觉隐喻 + 底部结论
- **海报 / 封面**：单张设计稿，强排版重视觉
- **插画 / 封面图**：可选 Codex imagegen 生成配图

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 生成长图 | HTML/CSS 渲染截图，prompt 落盘可重跑 | 图片路径、像素尺寸、预览 |
| 指定 provider | 走对应 provider 流程 | provider 日志 |
| 执行完成 | 验收文件存在、尺寸合理、中文可读 | 完成回执 |

### 客户如何使用

1. 说明来源（URL / vault 路径 / 本地 Markdown）和目标视觉类型（长图/信息图/海报/封面，可选）。
2. 可选：指定 provider（`local` / `open-design` / `codex-image`）、风格、尺寸。
3. URL 来源先 clip 归档再转换。

## 安装

本技能随 `soia-pkm-vault` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-transform-article-visual -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
