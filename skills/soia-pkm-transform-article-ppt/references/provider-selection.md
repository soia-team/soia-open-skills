# Provider Selection

## 决策表

| 目标 | Provider | 推荐理由 | 主要限制 |
|---|---|---|---|
| 正式可编辑母版 | `local_editable` | 内容、中文、结构和后期修改最可控 | 需要宿主演示文稿能力与人工设计判断 |
| 快速视觉课件 | `notebooklm` | source-grounded，插画和页面叙事快 | 通常一页一张图，修改成本高 |
| 既要可改又要视觉对照 | `hybrid` | 本地版做母版，NotebookLM 做灵感/展示版 | 生成时间更长，需要 NotebookLM 登录 |
| 已有 Open Design 环境/模板 | `open_design` | 适合模板化高保真设计与 HTML/PPTX fidelity | 依赖独立 ops skill 和环境健康检查 |

## 选择顺序

1. 用户本轮明确指定。
2. 私有配置 `defaults.provider`。
3. 交互会话问一次：可编辑本地版、NotebookLM 视觉版、还是两版对比。
4. 无法等待回答时默认 `local_editable`。

以下意图可直接推断：

- 「以后还要改」「公司模板」「需要可编辑」→ `local_editable`。
- 「NotebookLM 做」「快速出课件」→ `notebooklm`。
- 「都试一下」「比较哪个好」「漂亮但也要能改」→ `hybrid`。
- 「用 Open Design」「沿用 DESIGN.md/模板」→ `open_design`。

## 图片策略不是 PPT provider

`imagegen` 是视觉素材 provider，不是整套 PPT 的文本排版 provider。无论 PPT 走哪条路径，都可以按需生成 2-4 张有页码用途的视觉素材。

高密度中文图使用 `local_visual`：HTML/CSS 或 PPT 排版后截图。不要把 imagegen、NotebookLM infographic 与最终中文排版混为一谈。

## 降级

- NotebookLM 不可用：保留本地母版，报告认证/队列问题；用户只要 NotebookLM 时停止该路径。
- imagegen 不可用：使用用户素材、图标或纯排版，减少装饰，不伪造图片产物。
- presentations 不可用：可交 HTML/PDF deck，但必须说明不是可编辑 PPTX。
- Open Design 不可用：停止 Open Design 路径；只有用户同意才改走本地或 hybrid。

