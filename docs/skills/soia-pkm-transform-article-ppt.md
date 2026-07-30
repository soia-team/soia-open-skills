# soia-pkm-transform-article-ppt

> 把文章、提纲或主题转换为以可编辑 PPTX 为正式母版的演示媒体包，并支持外置固定模板与机密内容本地隔离

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-transform-article-ppt) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「做 PPT」「生成 PPTX」「转成课件」「按公司模板做周报」

## 能力与用法

### 这个技能可以做什么

| 产物 | 默认角色 | 交付要求 |
|---|---|---|
| 可编辑 PPTX | 正式母版 | 文字、结构和主要图形可修改；完整覆盖 source 主线 |
| 封面图 / 插画 / 背景 | PPT 视觉素材 | 无密集中文；由 imagegen 或等价图片能力生成 |
| 信息图 / 长图 | 独立传播素材，可选 | 中文文字由 HTML/CSS 或 PPT 排版，图片模型只供视觉部件 |
| NotebookLM PPTX | 视觉对照版，可选 | source-grounded；明确标注通常是一页一张图、不易编辑 |
| 预览与 QA | 验收证据 | 全部页面渲染、montage、溢出检查、人工逐页复核 |
| 规划与审稿合同 | 质量证据 | Claim Ledger、内容/设计计划、Contract Card、Signature Proof、双 Lens 审稿和宿主验收 |
| `media-manifest.json` | 生成清单 | 记录 source、provider、预期文件和实际验证，不写登录凭据 |

用户只说「PPT」时，默认交付 `.pptx`。只有用户明确要求兼容旧版 PowerPoint 时才额外转换 `.ppt`，并验证转换结果；不要把 `PPT` 口语请求误解为必须输出旧二进制格式。

### 客户如何使用

提供一种输入即可：文章路径、URL、Markdown、提纲、数据表或主题。最好补充受众、用途、页数、风格和是否需要 NotebookLM。

```text
把 <article.md> 做成给小白讲的 16 页 PPT，生成 3 张无字插画素材
把这个 URL 归档后做成可编辑 PPTX，并用 NotebookLM 再做一版对比
把这篇技术文章做成分享课件，同时给一张 1080x1600 的重点简图
把这篇复杂技术文章做成 16 页中文 PPTX，thorough 审稿，并用 PowerPoint 做最终中文验收
```

provider 未指定且当前是交互会话时，只问一个选择题：

```text
需要可编辑本地版、NotebookLM 视觉版，还是两版对比？
```

用户没有回答或任务不可等待时，默认 `local_editable`；用户说「都试一下」「更漂亮」「做课件并对比」时优先 `hybrid`。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-transform-article-ppt -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
