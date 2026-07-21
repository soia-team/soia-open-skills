---
name: soia-pkm-publish-x-article
description: 把成文草稿（Markdown）直传 X/Twitter Articles 草稿箱：解析标题/封面/正文图与分割线，富文本粘贴保格式，倒序插图，机械校验后只存草稿、绝不点发布。需已登录浏览器且订阅含「撰写文章」权益。Triggers：「发成 X Article」「上传到 X 文章」「推到 X 草稿箱」「X Articles draft」「把这篇发 X 长文」
version: 1.0.3
created_at: 2026-07-20 19:30:00
updated_at: 2026-07-21 11:20:00
created_by: claude fable 5
updated_by: claude fable 5
---

# soia-pkm-publish-x-article

把 Obsidian/本地 Markdown 成文草稿直传 X Articles 草稿箱，补齐 publish 家族的 X 长文出口（`publish-x-thread` 产推文串文本，本技能产富文本长文草稿）。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把一篇 Markdown 长文发到 X Articles | 解析标题/封面/正文图 → 浏览器里新建草稿 → 富文本粘贴 → 按原位插图 → 机械校验 | 浏览器实时操作过程、草稿 URL、校验清单和最终回执 |
| 文章没有封面图 | 停下来提醒（X Article 无封面观感差），明确同意后才无封面继续 | 提醒与确认问题 |
| 缺依赖/未登录/无 Premium+ | 停止并明确指出缺什么 | 登录/开通指引，不代填任何凭据 |

**安全底线**：只保存草稿，**绝不点击「发布/Publish」**；登录态只留在浏览器里，不导出 cookie、不写任何凭据到磁盘。

### 客户如何使用

1. 说「把 <文件> 发成 X Article」；确保浏览器已登录 X 且账号订阅含「撰写文章」权益。
2. Agent 先 dry-run 解析并汇报：标题、封面、正文图数量、缺图清单；封面缺失时先问你。
3. 浏览器阶段全程可见；完成后给草稿 URL，由你人工审阅并发布。

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -s soia-pkm-publish-x-article -y
```

- macOS + Python 3.9+（纯 stdlib；剪贴板走 osascript，图片降采样走系统自带 sips）
- 浏览器面二选一：**claude-in-chrome**（推荐，复用你真实 Chrome 的 X 登录态）或内置 Browser pane（首次需在其中登录 X）
- X 账号需含「撰写文章」权益的 Premium 订阅（2026-07 购买页显示 US$4 的 Premium 档即含；以 X 购买页实时权益表为准）
- 无私有 config.yml：本技能不接触任何 key/cookie

### 日志与完成回执

执行完必须输出：做了什么、草稿 URL、校验结果（逐项）、跳过/失败项、下一步（人工审阅发布）。

## 定位与闭环

`compose-article-draft` 产成文 → 本技能推 X Articles 草稿（对标 `publish-wechat-draft` 之于公众号）。「只建草稿绝不发布」与公众号侧同一条安全哲学。

## 触发词

| 用户说 | 动作 |
|---|---|
| 「发成 X Article」「上传 X 文章」「推到 X 草稿箱」 | 完整流程（解析 → 上传 → 校验） |
| 「先看看这篇能不能发 X」 | 只跑解析 dry-run，汇报不动浏览器 |
| 「发条 X/发个推」（普通短帖） | **不归本技能**：短帖/thread 文本用 `soia-pkm-publish-x-thread`；本技能只做 Articles 长文草稿 |

## 工作流

### 第 1 步：解析（不动浏览器）

```bash
python3 scripts/parse_x_article.py <article.md> > /tmp/x_article.json
python3 scripts/parse_x_article.py <article.md> --html-only > /tmp/x_article_body.html
```

JSON 字段：`title` / `cover_image`（仅当文章以图片开头）/ `content_images[]`（含 `block_index` 与 `after_text`）/ `dividers[]` / `html` / `missing_images`。

**两道闸门，先过再动浏览器：**
1. `missing_images > 0` → 停，把缺图清单给用户（可用 `--search-dir` 指定补找目录）。
2. `cover_image` 为 null → 停，提醒「X Article 无封面观感差，建议在文首加一张图」；用户明确说不加才继续（此时全部图片按正文图处理）。

### 第 2 步：进入编辑器

1. 浏览器面选择：优先 claude-in-chrome（真实 Chrome 已登录）；否则 Browser pane（未登录则让用户登录，**不代输凭据**）。
   ⚠️ **宿主依赖现状**：浏览器阶段目前依赖宿主提供的浏览器工具，在无浏览器工具的宿主（Codex、Gemini CLI 等）中只能完成第 1 步解析；宿主无关的 Playwright 路线（同 `soia-pkm-publish-x-thread` 的 `x_post.py` 方案）在计划中，届时共用同一登录 profile。
2. 导航 `https://x.com/compose/articles`——落地是**草稿列表**页，不是编辑器；直接点「create/撰写」按钮进编辑器（不要等「添加标题」出现，它在点击后才渲染）。
3. 跳到登录页 = 未登录；`/compose/articles` 404 或创作者工作室无「文章」入口 = 账号无 Articles 权益。停下并按固定话术提醒（**绝不代为订阅**）：
   > 当前账号未开通含「撰写文章」权益的 X Premium，请到 <https://x.com/i/premium_sign_up> 开通（2026-07 实测 US$4/月的 Premium 档即含此权益）后再试。

### 第 3 步：封面 + 标题

1. 有封面：点封面上传控件，用文件上传把 `cover_image` 传上去；X 会弹媒体编辑层，**必须点「应用/Apply」**关掉，否则编辑器被遮罩挡住、封面不生效。
2. 标题框（placeholder「添加标题/Add title」）输入 `title`。

### 第 4 步：正文富文本粘贴

```bash
python3 scripts/clipboard_x.py html --file /tmp/x_article_body.html
```

点编辑器正文区 → `Cmd+V`。标题/加粗/链接/列表/引用由 HTML 剪贴板 flavor 保留。粘贴后抽查首段和末段文字是否都在。

### 第 5 步：插图与分割线（都按 block_index **从大到小**倒序）

对每张 `content_images[i]`（倒序）：

```bash
python3 scripts/clipboard_x.py image <path> --max-bytes 3000000
```

1. 用 `after_text` 在编辑器里找到目标段落，点击它。
2. **按 End 键**把光标推到段落尾（防止点进段内链接）。
3. `Cmd+V` 粘贴 → 等「正在上传媒体/Uploading」消失再插下一张。

分割线（`dividers[]`，同样倒序）：X 忽略 `<hr>`，必须点对应位置后用编辑器「插入 > 分割线」菜单。

> 倒序原因：编辑器是动态文档，先插前面的会移动后面所有锚点。

### 第 6 步：机械校验（不过全部就不算完成）

| 校验项 | 标准 |
|---|---|
| 标题 | 编辑器标题 == JSON `title` |
| 正文首/末句 | 都能在编辑器中找到 |
| 媒体数 | 编辑器内图片数 == 封面(0/1) + `content_images` 数 |
| 分割线数 | == `dividers` 数 |
| 草稿状态 | 出现「已保存/Saved」autosave 标记；记录草稿 URL |

### 第 7 步：回执

草稿 URL + 校验清单逐项结果 + 「请人工审阅后自行点击发布」。**任何情况下不点发布。**

## 格式支持边界

| 元素 | 处理 |
|---|---|
| H2/H3、加粗、斜体、链接、有序/无序列表、引用 | 原生保留 |
| 代码块 | 转引用块（X 不支持 `<pre>`） |
| 表格 / mermaid | X 不支持：先手工转成 PNG 图插入，或接受降级丢失；解析器原样透传文字 |
| `---` 分割线 | 菜单插入（见第 5 步） |
| H1 | 只作标题，不进正文 |

## 边界与异常

| 场景 | 处理 |
|---|---|
| 跳登录页 | 停，让用户在浏览器登录后重试；不碰凭据 |
| 无 Articles 入口（/compose/articles 404） | 停，按第 2 步固定话术提醒并给开通直链 <https://x.com/i/premium_sign_up>；绝不代为订阅 |
| 缺图 | 第 1 步闸门拦截，给清单 |
| 无封面 | 闸门提醒，明确同意才继续 |
| 粘贴后格式丢失 | 检查剪贴板脚本输出；重试一次；仍失败则报告实际效果，不硬说成功 |
| 图片上传卡住 | 等待上传指示消失；超时则截图报告，不盲目继续 |
| X 编辑器改版找不到控件 | 停下报告页面实况，不猜测点击 |

## 脚本规格（scripts/）

| 脚本 | 职责 | 依赖 |
|---|---|---|
| `parse_x_article.py` | MD → JSON（标题/封面/图/分割线/HTML）；改编自 wshuyi/x-article-publisher-skill（MIT，见仓库 THIRD_PARTY_NOTICES） | stdlib |
| `clipboard_x.py` | HTML/图片上剪贴板（osascript；`--max-bytes` 超限自动降采样临时副本） | stdlib + macOS osascript/sips |

## 验证与测试

脚本层 fixture 前向测试（不需要 X 账号，改脚本后必跑）：

1. 造一篇含 frontmatter title、文首封面图、2 张正文图（png+jpg）、`---` 分割线、代码块、有序/无序列表、链接的测试文章。
2. `parse_x_article.py` 断言：`title` 取自 frontmatter；`cover_image` 为绝对路径且指向文首图；`content_images[].block_index` 递增、`after_text` 无 `___CODE___` 标记且已剥 markdown 记号；删掉文首图后 `cover_image` 为 null（闸门语义）。
3. `clipboard_x.py html` 后 `osascript -e 'clipboard info'` 必须含 `«class HTML»`；`image` 对 png/jpg 分别产出 `«class PNGf»`/`JPEG picture`；`--max-bytes` 超限走 sips 临时副本且**原文件字节数不变**。

浏览器端到端（需真实 X Premium+ 登录态）：用上述测试文章走完整流程，以第 6 步校验清单全绿 + 草稿 URL 为通过标准；X 编辑器改版导致控件变化时，以页面实况为准更新本文选择器描述。

## 完成后回执

1. **做了什么**：一句话 + 草稿 URL。
2. **校验清单**：第 6 步逐项结果；未通过项如实标注。
3. **下一步**：人工审阅后自行发布；建议配 `soia-pkm-cover-image` 生成封面。
