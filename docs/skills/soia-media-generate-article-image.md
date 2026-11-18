# soia-media-generate-article-image

> 将文章、开源项目、品牌 Logo 或公开 X Prompt Deck 编译为可验收的图片与矢量资产，按组合轴生成 Prompt 并完成事实、文字和视觉验收

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-media-generate-article-image) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 公众号全套配图（首图 + 分享图 + 正文图） | 生成 `2.35:1` 首图（中央 `1:1` 分享安全区必检）、可选 `5:2` X 封面，并按「流程图 / 预览证据图 / 意境分隔图」克制规划 1–3 张正文图 | 成套高清 PNG、中央 `1:1` 裁切复核、文字与垂直重心验收及插入位置清单 |
| 长文转「45 秒一图读懂」手机海报 | 提炼核心主张与 3–4 组要点，严控全图可见正文 ≤220 字且无孤字成行 | `3:4` 或 `4:5` 竖版信息海报、Prompt 与字数预算核验 |
| 国风 / 人文随笔意境封面与插图 | 调用中国传统构图 20 式（平远法、一河两岸式、边角式、折枝式、计白当黑等）与 742 种中华传统色 | 宣纸水墨质感封面/插图，无色彩 HEX 参数泄露 |
| 康奈尔学习笔记信息图（1–6 页） | 运行 `resolve_cornell_pagination.py` 按知识模块自适应分页（每页 6–10 个模块，左上角 `NN/TT` 页码） | 高密度单页或系列 PNG、系列 `manifest.yml` |
| 开源仓库推荐 / 小红书轮播 / 品牌 Logo | 提取仓库/技能真实事实生成宣传卡或 `3:4` 轮播；插件图标与品牌 Logo 先出方向稿再确定性 SVG 矢量重绘 | 事实清单、通过 OCR/二维码校验的卡片，或 SVG 母版 + 彩色/单色/反白变体 |
| 公开 X Prompt Deck 进化导入 | 拆分基础视觉系统、主题佐料与系列变量，转化为本技能可复用的组合轴 | `evolution.yml`、`series-index.yml`、`bibles/` 与重编译 `prompts/` |

### 客户如何使用

用自然语言说明**来源（文章路径/主题/仓库）、用途或投放平台、张数与必须逐字出现的文字**，内部轴与默认值由 Agent 自动推导并回显确认：

- 「帮这篇公众号文章生成一张 `2.35:1` 首图（平远法 + 中华传统色）和 2 张正文配图，主标题写『行至半山，止息内耗』。」
- 「把这篇文章压成一张 45 秒能看懂的 `3:4` 竖版手机海报，采用方法框架型结构。」
- 「把这篇长文做成康奈尔笔记信息图；如果有参考图，按参考图的版式密度分页。」

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
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-media-generate-article-image -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
