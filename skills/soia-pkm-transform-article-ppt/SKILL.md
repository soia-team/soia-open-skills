---
name: soia-pkm-transform-article-ppt
description: 把文章、Markdown、URL、提纲、数据表或主题转换为以可编辑 PPTX 为核心的演示媒体包，可同时生成封面/插画素材、信息图、逐页预览和 NotebookLM 视觉对照版。适用于「做PPT」「生成PPTX」「转成课件」「做演示文稿」「生成图片素材」「NotebookLM做PPT」「两版PPT对比」「article to deck」「make slides」。
version: 2.0.0
created_at: 2026-07-16 10:58:46
updated_at: 2026-07-22 17:35:20
created_by: claude opus 4.6
updated_by: gpt-5.6-luna
dependencies:
  optional: [soia-dev-open-design-ops]
---

# soia-pkm-transform-article-ppt

把一份 source 转换为可讲、可改、可复验的 PPT 媒体包。默认正式母版是**可编辑 `.pptx`**；视觉素材、信息图和 NotebookLM deck 用来增强理解与展示，不替代内容可编辑性。

## 客户可读说明

### 这个技能可以做什么

| 产物 | 默认角色 | 交付要求 |
|---|---|---|
| 可编辑 PPTX | 正式母版 | 文字、结构和主要图形可修改；完整覆盖 source 主线 |
| 封面图 / 插画 / 背景 | PPT 视觉素材 | 无密集中文；由 imagegen 或等价图片能力生成 |
| 信息图 / 长图 | 独立传播素材，可选 | 中文文字由 HTML/CSS 或 PPT 排版，图片模型只供视觉部件 |
| NotebookLM PPTX | 视觉对照版，可选 | source-grounded；明确标注通常是一页一张图、不易编辑 |
| 预览与 QA | 验收证据 | 全部页面渲染、montage、溢出检查、人工逐页复核 |
| `media-manifest.json` | 生成清单 | 记录 source、provider、预期文件和实际验证，不写登录凭据 |

用户只说「PPT」时，默认交付 `.pptx`。只有用户明确要求兼容旧版 PowerPoint 时才额外转换 `.ppt`，并验证转换结果；不要把 `PPT` 口语请求误解为必须输出旧二进制格式。

### 客户如何使用

提供一种输入即可：文章路径、URL、Markdown、提纲、数据表或主题。最好补充受众、用途、页数、风格和是否需要 NotebookLM。

```text
把 <article.md> 做成给小白讲的 16 页 PPT，生成 3 张无字插画素材
把这个 URL 归档后做成可编辑 PPTX，并用 NotebookLM 再做一版对比
把这篇技术文章做成分享课件，同时给一张 1080x1600 的重点简图
```

provider 未指定且当前是交互会话时，只问一个选择题：

```text
需要可编辑本地版、NotebookLM 视觉版，还是两版对比？
```

用户没有回答或任务不可等待时，默认 `local_editable`；用户说「都试一下」「更漂亮」「做课件并对比」时优先 `hybrid`。

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -a claude-code -a codex -s soia-pkm-transform-article-ppt -y
```

- `local_editable`：优先使用宿主原生 presentations / PowerPoint 能力；Codex 环境优先使用其 Presentations runtime，而不是把 `python-pptx` 写成唯一默认实现。
- `imagegen`：宿主提供图片生成能力时直接调用；不可用时使用用户素材、图标或纯排版，不伪称生成了图片。
- `notebooklm`：需要 NotebookLM CLI 与登录态，见 [references/provider-notebooklm.md](references/provider-notebooklm.md)。
- `open_design`：可选增强；选中后硬依赖 `soia-dev-open-design-ops`，见 [references/provider-open-design.md](references/provider-open-design.md)。

私有配置放在：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-transform-article-ppt/config.yml
```

可用 `SOIA_PKM_ARTICLE_PPT_CONFIG_FILE` 覆盖路径。配置示例见 `config.example.yml`。

### 日志与完成回执

```markdown
完成：<一句话说明正式母版与辅助版本>。

- source: <路径或 URL>
- provider: local_editable | notebooklm | hybrid | open_design
- editable_pptx: <路径、页数、是否可编辑>
- notebooklm_pptx: <路径、页数、是否为图片页；未生成则省略>
- visual_assets: <数量与路径>
- infographic: <路径与尺寸；未生成则省略>
- manifest: <路径>

验证：
- PPTX 实际打开并渲染全部页面
- 预览页数与 PPTX 页数一致
- 无空白页、越界、重叠、乱码和占位符
- source 时间、作者、数字与声明已核对
- 人工逐页检查已完成

限制：<未验证事实、provider 降级或编辑性限制>
```

## 硬边界

1. **正式母版默认可编辑。** NotebookLM 常把每页做成整张图片；除非实测确认，否则不得称为可编辑 PPTX。
2. **图片模型不排密集中文。** imagegen 用于封面、插画、背景和视觉隐喻；标题、术语、数字、表格和来源由 PPT/HTML 后期排版。
3. **每页只有一个主判断。** 页面可以密集，但必须有明确视觉焦点和阅读顺序。
4. **不伪造元数据。** source 页只使用 source 中核实的作者、链接和发布时间；不写猜测的模型名、生成时间、notebook id、artifact id、下载路径或占位符。
5. **外部事实与原文观点分开。** 时间敏感预测、性能数字和企业案例若未独立核实，必须标成「原文观点/未验证」。
6. **文件存在不等于完成。** 没有全量渲染和人工视觉复核，不得交付为完成。
7. prompt、素材和中间 manifest 只落到用户指定输出目录；登录态、cookie、账号信息永不进入输出或回执。

## 工作流

### 1. 建立内容合同

读取完整 source，提取：`main_verdict`、受众任务、章节、概念、案例链、关键判断、易混点、风险与待核实事实。URL 先归档或保存稳定 source；只有主题时先形成内容提纲。

运行规划脚本生成可审计清单：

```bash
python3 scripts/media_bundle.py plan \
  --article <article.md> \
  --out-dir <output-dir> \
  --provider hybrid \
  --image-count 3 \
  --main-verdict "<一句主判断>"
```

路径与 manifest 契约见 [references/media-bundle-contract.md](references/media-bundle-contract.md)。

### 2. 选择 provider 和交付范围

按「用户明确指定 > 私有配置 > 交互选择 > 默认 `local_editable`」决定。具体选择规则见 [references/provider-selection.md](references/provider-selection.md)。

`hybrid` 的职责固定：

- 本地版承担内容完整性、编辑性和正式交付。
- NotebookLM 版承担快速视觉叙事和对照实验。
- imagegen 只承担有明确页面用途的视觉素材。

### 3. 先做 slide plan，再做视觉

读取 [references/prompt-ppt.md](references/prompt-ppt.md)。逐页计划至少包含：判断式标题、页面任务、source anchor、视觉形式、讲稿/备注、覆盖概念。先攻击计划：是否遗漏主线、是否连续多页同构、是否把结论埋掉。

### 4. 生成有用途的图片素材

需要视觉锚点时读取 [references/prompt-image-assets.md](references/prompt-image-assets.md)。通常生成 2-4 张：封面主视觉、核心机制图、关键案例/场景图。每张图必须绑定具体页码或信息图区域；不生成纯装饰库存图。

图片生成后先查看原图，再放进 PPT。若方向、对象关系、文字或数字错误，修改 prompt 重新生成；不要用遮盖层掩饰语义错误。

### 5. 生成正式可编辑 PPTX

使用宿主 presentations 能力或 Open Design 生成。遵循当前宿主的演示文稿技能与 runtime 说明。PPTX 中的中文文本、流程箭头、表格、页码、来源应保持可编辑；位图只用于照片、插画、纹理和必要的复杂视觉。

固定设计要求：

- 中长文默认 14-18 页；短文 8-12 页；用户指定时服从并记录压缩风险。
- 至少 4 种页面轮廓：封面、地图、流程、对比/矩阵、完整速查、案例、练习、来源等。
- 不连续使用同一套卡片网格；不把页面章节做成漂浮卡片。
- 标题表达判断，正文提供结构和证据；不写「背景介绍」「核心观点」这类空标题。
- 颜色承担语义，不用单一蓝紫或装饰渐变覆盖整套。

### 6. 可选生成 NotebookLM 对照版

读取 [references/provider-notebooklm.md](references/provider-notebooklm.md) 和 [references/prompt-notebooklm-ppt.md](references/prompt-notebooklm-ppt.md)。生成后必须按 artifact id 下载，防止同一 notebook 有多个 deck 时拿错版本。

NotebookLM 失败、排队或登录缺失不影响本地正式母版；但回执必须写明真实状态。若输出包含占位符、运行元数据、错误中文或 source 外事实，修改 prompt 后重新生成。

### 7. 生成可选信息图

需要「一张图讲清楚」时读取 [references/prompt-infographic.md](references/prompt-infographic.md)。先生成无字视觉部件，再用 HTML/CSS 或 PPT 排版中文，保持主判断、流程方向和术语层级一致。

### 8. 双层验收

先跑机械检查，再做人工视觉检查：

```bash
python3 scripts/media_bundle.py validate \
  --manifest <output-dir>/media-manifest.json \
  --visual-reviewed \
  --source-facts-reviewed \
  --strict \
  --json
```

详细标准见 [references/quality-gates.md](references/quality-gates.md)。任何一页失败都回到对应源文件、HTML 或 prompt 修复，再重新渲染；不能只改完成回执。

### 9. 交付与回链

把正式母版、辅助版本、图片和 manifest 放在同一输出目录。若 source 位于可写知识库且已有「关联/派生产物」区域，更新链接；不要在多个文件复制同一份产物清单。

## 按需读取

- 输出目录和 manifest：[references/media-bundle-contract.md](references/media-bundle-contract.md)
- provider 选择：[references/provider-selection.md](references/provider-selection.md)
- 可编辑 PPT 计划与提示词：[references/prompt-ppt.md](references/prompt-ppt.md)
- imagegen 素材：[references/prompt-image-assets.md](references/prompt-image-assets.md)
- 信息图：[references/prompt-infographic.md](references/prompt-infographic.md)
- NotebookLM：[references/provider-notebooklm.md](references/provider-notebooklm.md)、[references/prompt-notebooklm-ppt.md](references/prompt-notebooklm-ppt.md)
- Open Design：[references/provider-open-design.md](references/provider-open-design.md)、[references/prompt-open-design.md](references/prompt-open-design.md)
- 质量门：[references/quality-gates.md](references/quality-gates.md)
- 典型调用：[references/examples.md](references/examples.md)
