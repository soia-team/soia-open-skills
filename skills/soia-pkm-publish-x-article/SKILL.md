---
name: soia-pkm-publish-x-article
description: 把成文草稿（Markdown）直传 X/Twitter Articles 草稿箱：解析标题/封面/正文图与分割线，富文本粘贴保格式，倒序插图，机械校验后只存草稿、绝不点发布。需已登录浏览器且订阅含「撰写文章」权益。Triggers：「发成 X Article」「上传到 X 文章」「推到 X 草稿箱」「X Articles draft」「把这篇发 X 长文」
version: 1.1.0
created_at: 2026-07-20 19:30:00
updated_at: 2026-07-21 14:20:00
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

1. 说「把 <文件> 发成 X Article」。首次使用需要登录一次：脚本弹出浏览器窗口，人工登录后长期复用（与 `soia-pkm-publish-x-thread` 共用同一份登录态，任一技能登录过就都不用再登）；账号需订阅含「撰写文章」权益。
2. Agent 先 dry-run 解析并汇报：标题、封面、正文图数量、缺图清单；封面缺失时先问你。
3. 浏览器阶段全程可见（默认走宿主无关的 Playwright 脚本，任何能跑 Python 的环境都一样）；完成后给草稿 URL 和校验清单，由你人工审阅并发布。

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -s soia-pkm-publish-x-article -y
```

- 跨平台 Python 3.9+（macOS / Windows / Linux 均可）：主路线用 Playwright 自带浏览器 + 原生剪贴板 API，不依赖 osascript / sips 等系统专属工具。
  ```bash
  pip install playwright && python -m playwright install chromium
  ```
- 登录态与 `soia-pkm-publish-x-thread` 共用同一份本地 profile 目录（`~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-publish-x-thread/x-profile`，可用 `--profile-dir` / `SOIA_X_PROFILE_DIR` 覆盖）：已经用 `x_post.py login` 登录过就直接可用；未登录时去该技能跑一次 `python3 scripts/x_post.py login`（本技能自身不提供 `login` 子命令，靠共用 profile 免二次登录）。
- 备选路线（宿主恰好提供浏览器控制工具，如 Claude Code 的 claude-in-chrome）需要 macOS，走 `clipboard_x.py`（osascript/sips）；详见下方「备选路线」。没有宿主工具、或在非 macOS 环境，用主路线即可。
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

### 第 2 步：草稿写入 X Articles

**主路线是自带的 Playwright 脚本 `x_article_post.py`，宿主无关**——在 Claude Code、Codex、Gemini CLI、opencode 等任何能跑 Python 的宿主中行为一致，不依赖任何宿主专属浏览器工具；两条路线共享同一套第 3 步机械校验标准。

#### 主路线：scripts/x_article_post.py（宿主无关）

依赖（一次性）：`pip install playwright && python -m playwright install chromium`。

```bash
python3 scripts/x_article_post.py status                     # 检查登录态（与 x_post.py 共用 profile）
python3 scripts/x_article_post.py check                      # 探测 Articles 入口
python3 scripts/x_article_post.py draft /tmp/x_article.json  # 完整草稿：封面→标题→正文→插图→分割线→校验
```

- **登录**：本技能自身不提供 `login` 子命令。未登录时去 `soia-pkm-publish-x-thread` 跑一次 `python3 scripts/x_post.py login`，两边共用同一份本地 profile，登录一次两边都能用。
- `check` 返回四种状态之一：
  - `not_logged_in` → 未登录，按上面指引登录后重试。
  - `no_articles_access` → 账号未开通「撰写文章」权益，或 `/compose/articles` 404；JSON 里带下面这条固定提醒文案。
  - `ok` → 找到可点击的创建入口，可以继续 `draft`。
  - `unknown` → 页面结构与预期不符（可能编辑器改版、也可能是从未验证过的真实 DOM），JSON 附截图路径，不猜测点击；按下方「边界与异常」处理。

  `no_articles_access` 固定提醒文案（**绝不代为订阅**；与脚本 `NO_PREMIUM_MESSAGE` 常量逐字节一致，非改述）：
  > 当前账号未开通含「撰写文章」权益的 X Premium，请到 https://x.com/i/premium_sign_up 开通（2026-07 实测 US$4/月的 Premium 档即含此权益）后再试。

- `draft` 内部第一步就是复用 `check` 的判定：不是 `ok` 立即停并原样返回该状态，不会继续点任何东西。
- 正文图与分割线一律按 `block_index` **从大到小**倒序插入——编辑器是动态文档，先插前面的会移动后面所有锚点，这是硬性正确性要求，不是风格偏好。
- 剪贴板走 Playwright 原生 Clipboard API（`navigator.clipboard.write` + 授予的 clipboard 权限），macOS / Windows / Linux 通用；粘贴键按平台自动选择 Cmd+V（macOS）/ Ctrl+V（其它平台），不依赖 osascript。
- 封面上传走真实文件输入控件（`input[type=file]` + `set_input_files`），比剪贴板/拖拽更稳。
- **没有任何发布相关代码路径**：`x_article_post.py` 里不存在能点击或定位「发布」按钮的代码——这是脚本本身的硬约束，比 `publish-x-thread` 的 draft/send 两档更严格（Articles 场景下 send 这一档根本不存在）。
- 未预期的异常会被整体兜底：产出结构化错误 JSON（错误信息 + 页面 URL/标题 + 截图路径），不会抛裸 traceback，也不会带着异常状态继续瞎点。
- 输出为单行 JSON 回执，任何宿主可机读。

#### 备选路线：宿主浏览器工具

宿主恰好提供浏览器控制（如 Claude Code 的 claude-in-chrome，经浏览器扩展复用用户真实 Chrome 登录态）时可选用，客户零登录成本，页面改版时人工介入也更直观；**没有宿主工具时不得以此为由跳过脚本主路线**。校验标准与主路线完全一致（见第 3 步）。

1. 浏览器面选择：claude-in-chrome（真实 Chrome 已登录）或 Browser pane（未登录则让用户登录，**不代输凭据**）。
2. 导航 `https://x.com/compose/articles`——落地是**草稿列表**页，不是编辑器；直接点「create/撰写」按钮进编辑器（不要等「添加标题」出现，它在点击后才渲染）。
3. 跳到登录页 = 未登录；`/compose/articles` 404 或创作者工作室无「文章」入口 = 账号无 Articles 权益。停下并按固定话术提醒（**绝不代为订阅**，文案同上）。
4. 有封面：点封面上传控件，用文件上传把 `cover_image` 传上去；X 会弹媒体编辑层，**必须点「应用/Apply」**关掉，否则编辑器被遮罩挡住、封面不生效。标题框（placeholder「添加标题/Add title」）输入 `title`。
5. 正文富文本粘贴：
   ```bash
   python3 scripts/clipboard_x.py html --file /tmp/x_article_body.html
   ```
   点编辑器正文区 → `Cmd+V`。标题/加粗/链接/列表/引用由 HTML 剪贴板 flavor 保留。粘贴后抽查首段和末段文字是否都在。
6. 插图与分割线（都按 block_index **从大到小**倒序）：对每张 `content_images[i]`：
   ```bash
   python3 scripts/clipboard_x.py image <path> --max-bytes 3000000
   ```
   用 `after_text` 找到目标段落 → 点击 → **按 End 键**把光标推到段落尾（防止点进段内链接）→ `Cmd+V` 粘贴 → 等「正在上传媒体/Uploading」消失再插下一张。分割线（`dividers[]`，同样倒序）：X 忽略 `<hr>`，必须点对应位置后用编辑器「插入 > 分割线」菜单。

   > 倒序原因：编辑器是动态文档，先插前面的会移动后面所有锚点。

### 第 3 步：机械校验（不过全部就不算完成）

| 校验项 | 标准 |
|---|---|
| 标题 | 编辑器标题 == JSON `title` |
| 正文首/末句 | 都能在编辑器中找到 |
| 媒体数 | 编辑器内图片数 == 封面(0/1) + `content_images` 数 |
| 分割线数 | == `dividers` 数 |
| 草稿状态 | `autosave_confirmed`：插图/分割线全部处理完后，先等一段时间给（假定存在的）防抖自动保存生效，再尝试观测「已保存/Saved」提示；`draft_url`：记录草稿 URL |

主路线的 `draft` 子命令在 JSON 回执的 `checks` 字段里已经把这五项跑完（`draft_url`/`autosave_confirmed` 拿不到确切结果时诚实给 `null`/`false`，不编造；`autosave_confirmed: false` 不等于失败，只是没能确认，按上方「边界与异常」处理）；备选路线需要人工或宿主浏览器工具逐项核对。

### 第 4 步：回执

草稿 URL + 校验清单逐项结果 + 「请人工审阅后自行点击发布」。**任何情况下不点发布。**

## 格式支持边界

| 元素 | 处理 |
|---|---|
| H2/H3、加粗、斜体、链接、有序/无序列表、引用 | 原生保留 |
| 代码块 | 转引用块（X 不支持 `<pre>`） |
| 表格 / mermaid | X 不支持：先手工转成 PNG 图插入，或接受降级丢失；解析器原样透传文字 |
| `---` 分割线 | 编辑器 Insert/插入 菜单插入（主路线见 `x_article_post.py` 的 `insert_divider_at`，备选路线见第 2 步步骤 6） |
| H1 | 只作标题，不进正文 |

## 边界与异常

| 场景 | 处理 |
|---|---|
| 跳登录页 | 停，让用户在浏览器登录后重试；不碰凭据 |
| 无 Articles 入口（/compose/articles 404 或无创建入口） | 停，按第 2 步固定话术提醒并给开通直链 <https://x.com/i/premium_sign_up>；绝不代为订阅；主路线对应 `check`/`draft` 的 `no_articles_access` 状态 |
| 页面结构无法确定属于以上哪种情况 | 停，如实报告为 `unknown`（主路线自动附截图 + 页面 URL/标题），不强行归类、不猜测点击 |
| 缺图 | 第 1 步闸门拦截，给清单 |
| 无封面 | 闸门提醒，明确同意才继续 |
| 粘贴后格式丢失 | 检查剪贴板路径（主路线看 JSON 里的 `warnings`；备选路线检查剪贴板脚本输出）；重试一次；仍失败则报告实际效果，不硬说成功 |
| 图片上传卡住 | 等待上传指示消失（主路线有 15s 超时上限）；超时则截图报告，不盲目继续 |
| 分割线插入失败 | 不中止整份草稿：主路线把失败项计入 `warnings`（含 `block_index`/`after_text`），其余内容照常完成 |
| X 编辑器改版找不到控件 | 停下报告页面实况，不猜测点击 |
| `draft` 中途失败后重试 | 主路线每次调用都会重新点「create」新建一篇文章，不会续写/去重上一次失败的草稿；重试前若怀疑上次已部分写入，先去 X 的 Articles 草稿列表人工检查并清理重复/半成品草稿，重试只会新增一篇，不会自动合并或覆盖 |
| `checks.autosave_confirmed` 为 false | 说明脚本没能观测到「已保存/Saved」提示——内容可能已粘贴但未必已持久化；`warnings` 会同步提示；不要仅凭 `ok: true` 判定成功，需人工打开 `checks.draft_url` 核实 |

## 脚本规格（scripts/）

| 脚本 | 职责 | 依赖 |
|---|---|---|
| `parse_x_article.py` | MD → JSON（标题/封面/图/分割线/HTML）；改编自 wshuyi/x-article-publisher-skill（MIT，见仓库 THIRD_PARTY_NOTICES） | stdlib |
| `x_article_post.py` | 宿主无关 Playwright 主路线：登录态复用（与 `x_post.py` 共用同一 profile）、Articles 入口探测（`check`：not_logged_in/no_articles_access/ok/unknown）、全自动草稿（`draft`：封面→标题→正文→插图→分割线→机械校验）、跨平台剪贴板（Playwright 原生 Clipboard API，无 osascript）；无任何发布代码路径 | `pip install playwright && python -m playwright install chromium` |
| `clipboard_x.py` | 备选路线专用：HTML/图片上 macOS 剪贴板（osascript；`--max-bytes` 超限自动降采样临时副本） | stdlib + macOS osascript/sips |

## 验证与测试

脚本层 fixture 前向测试（不需要 X 账号，改脚本后必跑，`parse_x_article.py`/`clipboard_x.py` 本次未改动，标准不变）：

1. 造一篇含 frontmatter title、文首封面图、2 张正文图（png+jpg）、`---` 分割线、代码块、有序/无序列表、链接的测试文章。
2. `parse_x_article.py` 断言：`title` 取自 frontmatter；`cover_image` 为绝对路径且指向文首图；`content_images[].block_index` 递增、`after_text` 无 `___CODE___` 标记且已剥 markdown 记号；删掉文首图后 `cover_image` 为 null（闸门语义）。
3. `clipboard_x.py html` 后 `osascript -e 'clipboard info'` 必须含 `«class HTML»`；`image` 对 png/jpg 分别产出 `«class PNGf»`/`JPEG picture`；`--max-bytes` 超限走 sips 临时副本且**原文件字节数不变**。

`x_article_post.py` 经过一轮实现 + 三镜头独立对抗审查（安全 / 正确性 / 跨平台）后按发现修复：新增 `wait_for_autosave_signal`（插图与分割线全部处理完、正式关闭浏览器前，先等防抖自动保存生效再尝试观测「已保存/Saved」，结果写进 `checks.autosave_confirmed`，观测不到时给出警告而不是默默继续——修复"关闭时机可能早于持久化，却仍报告 `ok:true`"的阻断级问题）、分割线锚点找不到时回退到正文编辑区（与正文图片一致，避免落在上一次操作残留的光标位置）、封面文件上传失败时降级为警告而非中止整份草稿、媒体数量校验改为限定 `role="main"` 区域内计数（避免导航栏头像等页面级 `<img>` 污染计数）。跨平台镜头审查无发现。

`x_article_post.py`——**本次 PR 合并前实际跑过的**：
1. `python3 -m py_compile` + `ast.parse` 语法校验通过；`importlib` 实际执行模块顶层代码（正则编译等）无异常。
2. 人工审阅 + `grep -in "publish\|发布"` 全文核对：命中的都是注释/文档字符串/路径名，没有一处命中 `.click()`/`.press()` 调用——验证「没有任何发布代码路径」这条硬约束。
3. **`status`/`check` 已用真实 X 账号（本机共享登录态）实测通过**：`status` 正确报告 `logged_in: true`；`check` 对一个已知未订阅 Premium 的账号正确返回 `no_articles_access`，`message` 字段与脚本 `NO_PREMIUM_MESSAGE` 常量逐字节核对一致；直接抓取该页面验证了分类命中路径——标题 `未找到页面 / X`、正文含「该页面不存在」，命中 `NOT_FOUND_TEXT_MARKERS` 里的「页面不存在」子串（走的是 body-text 匹配分支，不是标题 `"404"` 匹配，也不是碰运气命中 Premium-upsell 兜底分支）。

`x_article_post.py`——**本次 PR 合并前尚未跑、如实留给后续验证的**（不打包成"已测试"）：
1. `check` 的 `ok` 分支与完整 `draft` 流程（封面上传、标题、正文富文本粘贴、按 `block_index` 倒序插图、分割线菜单插入、`autosave_confirmed` 观测、机械校验）——需要一个订阅含「撰写文章」权益的真实 Premium 账号，目前没有可用账号验证；`find_create_control` / `find_title_input` / `find_body_editor` / `SAVED_INDICATOR_RE` / 分割线菜单等选择器全部是文本/角色定位的合理猜测，未在真实编辑器 DOM 上验证过，第一次真实跑很可能命中「X 编辑器改版找不到控件」或 `autosave_confirmed: false` 这类边界，需要按页面实况更新选择器与本文档。
2. 跨平台剪贴板路径中 Windows/Linux 上的 `navigator.clipboard.write` + `Control+V` ——本次开发环境是 macOS，只验证了 `sys.platform` 平台判断逻辑本身，未在 Windows/Linux 真机上跑过。

浏览器端到端标准不变：以第 3 步机械校验五项全绿（含 `autosave_confirmed: true`）+ 草稿 URL 为通过标准；选择器因编辑器改版失效时，以页面实况为准更新本文档的选择器描述。

## 完成后回执

1. **做了什么**：一句话 + 草稿 URL。
2. **校验清单**：第 3 步逐项结果；未通过项如实标注。
3. **下一步**：人工审阅后自行发布；建议配 `soia-pkm-cover-image` 生成封面。
