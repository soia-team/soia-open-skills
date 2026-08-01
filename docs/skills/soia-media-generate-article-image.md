# soia-media-generate-article-image

> 为文章生成封面、小结卡、学习笔记、视觉隐喻海报或高信息密度技能库宣传卡/轮播；按使用场景、视觉机制、美学系统和模型能力组合 Prompt，并完成事实、文字与位图验收

所属：[`soia-media-content`](https://github.com/soia-team/soia-open-media-content-skills) · [技能源码](https://github.com/soia-team/soia-open-media-content-skills/tree/main/skills/soia-media-generate-article-image) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「生成文章图片」「提示词组合」「正文小结图」「康奈尔笔记图」「技能库宣传图」「朋友圈配图」「小红书轮播」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | `image_type` / `preset` | 客户能看到 |
|---|---|---|
| 公众号、X、小红书文章封面 | `cover` / `editorial_research_minimal`、`godot_pixel_metaphor` 或 `auto` | 完整 Prompt、PNG/JPG 封面、视觉验收回执 |
| 正文段落或章节小结图 | `summary_card` / `editorial_summary_card` | 可嵌入正文的编辑式小结卡 |
| 把文章总结成康奈尔笔记 | `learning_note` / `cornell_notes` | A4 竖版康奈尔笔记信息图 |
| 技能库、插件集合宣传图 | `social_card` 或 `carousel` / `social_skill_catalog` | 事实清单、朋友圈单图或小红书轮播、机器验收回执 |
| 插件市场图标、应用图标 | `icon` / `plugin_icon` | 字形设计稿；终稿须矢量重绘，规格见模板 |
| 后续新增文章图片能力 | 优先登记到组合索引的使用场景/视觉机制/美学系统轴 | 只有交付结构或事实契约真正不同才新增 preset |

### 客户如何使用

1. 提供文章路径、完整正文、明确主题或技能仓路径；给出用途、平台、比例和必须逐字出现的文字。
2. 如有参考图，明确每张图是“风格参考”“构图参考”还是“编辑目标”。
3. 指定 `image_type`、交付家族 `preset`、Prompt 家族 `family`、使用场景、信息结构、视觉机制、美学系统、模型适配和 `output_dir`；省略时由 Agent 依据文章与用途推荐，并在生成前说明假设。客户说“直接生成”时可跳过确认。
4. Agent 读取 [模板注册表](references/template-registry.yml)、[组合索引](references/prompt-composition-index.yml)、[家族目录](references/prompt-family-catalog.md) 和对应机制/结构/文字/美学词条；宣传卡先从实际仓库生成 `facts.yml`。若任务是“推荐一个仓库并重点推荐一个技能”，还要完整读取仓库 `README.md` 与重点技能 `SKILL.md`，生成可追溯的 `content-facts.yml`，再为每一张图写完整成品 Prompt。默认由 imagegen 直出整张海报；只有高风险精确字段未通过时才局部确定性校正。
5. 多仓系列先用 [批次清单样例](references/social-card-batch.example.yml) 明确纳入与排除范围；脚本拒绝同一仓同时出现在两边。
6. 生成后必须用 `view_image` 检查比例、构图和参考图；密集宣传卡还要核对语义密度、OCR、CTA、二维码、移动端缩略图、事实指纹和伪证据。失败时重生主视觉或重跑确定性合成源，不直接涂改位图。

插件市场安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

```bash
claude plugin install soia-media-content@soia
```

只要这一个技能时，可用 npx 路线。注意技能会落进共享真源 `~/.agents/skills`；若同时装了插件，同一技能会出现两份索引且各自漂移，建议二选一：

```bash
npx skills add soia-team/soia-open-media-content-skills -g -a '*' -s soia-media-generate-article-image -y
```

## 安装

本技能随 `soia-media-content` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-media-content@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-media-content@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-media-content-skills -g -a '*' -s soia-media-generate-article-image -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
