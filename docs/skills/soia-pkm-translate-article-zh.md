# soia-pkm-translate-article-zh

> 将外文文章按 quick、normal 或 refined 模式翻译成独立中文稿，保持术语一致且不覆盖原文

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-translate-article-zh) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「翻译这篇」「精翻」「继续润色」

## 能力与用法

### 这个技能可以做什么

三种模式覆盖从"先看看大概意思"到"要发布级质量"的完整翻译需求；长文自动分块并跨块保持术语一致；产出永远是原文旁边的一个新文件，不覆盖、不污染原文。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 快速看懂一篇外文文章大意（quick） | 直接翻译，不做额外分析 | 一份直译版全文 |
| 一篇普通文章的可读译文（normal，默认） | 先分析文体/术语/受众，再据此翻译 | 一份自然流畅的译文全文 |
| 出版级质量的重要文章（refined） | 分析 → 翻译 → 审校（只诊断）→ 润色（应用修正） | 诊断说明 + 最终润色版全文 |
| 长文（超过分块阈值） | 用机械脚本按标题/段落切块，术语表贯穿所有块 | 分块数量、术语表命中数，最终仍是一份合并后的完整译文 |
| 翻译 vault 里已归档的英文文章 | 继承原 frontmatter，加 `translated_from` 等字段 | `<原文件名>-<目标语言>版.md`，与原文件同目录，原文件保持不变 |

### 客户如何使用

1. 提供要翻译的文件路径（典型是 `soia-pkm-clip-x` / `soia-pkm-clip-web` 归档在 vault 里的外文文章），或直接粘贴文本；顺手说明目标语言 / 模式 / 受众（不说就用 config 默认或本技能内置默认：`zh-CN` / `normal` / `general`）。
2. **首次对某个文件执行翻译前**，Agent 必须先报告"将翻译 `<文件>` 到 `<目标语言>`，模式 `<quick/normal/refined>`"，等待客户确认，除非客户已经明确说"直接翻""不用确认"。目标语言/模式/受众只要有一项来自 config 默认值而非客户本次显式指定，都算"推荐输入"，同样需要走这一步确认。
3. Agent 判定或使用客户指定的模式（quick / normal / refined），按 [三种模式](#三种模式) 执行。
4. 长文（超过 `chunk_threshold`，默认 4000 词）先跑 `scripts/chunk_markdown.py` 机械分块，术语表贯穿所有块保持一致；短文直接在当前上下文整篇翻译。细节见 [references/chunk-workflow.md](references/chunk-workflow.md)。
5. **clip 归档双语模板注意（实测教训 2026-07-10）**：clip-x/clip-web 归档笔记是「摘要+原文+中文译文+我的看法」多段模板，整篇喂分块脚本会把已有中文译文一并计词——词数虚胖（实测 4431 vs 真实待译 1517），更长的文章会被误判切块且边界可能横跨"原文"与"已有译文"两个语义区。对这类文件：先只截取 `## 原文` 小节（到下一个 `##` 标题为止）存临时文件再喂脚本；是否触发分块以**待译段**词数为准，不以整篇为准。
5. 翻译永远**先落盘、后汇报**：产出 `<原文件名>-<目标语言>版.md` 落在原文件同目录，frontmatter 继承原文并追加 `translated_from` 等字段，绝不覆盖原文件。
6. 最终回复必须给客户完整回执：模式、块数、术语表命中数、产出文件路径、剩余风险。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-translate-article-zh -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
