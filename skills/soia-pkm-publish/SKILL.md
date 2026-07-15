---
name: soia-pkm-publish
description: 把写好的文章草稿适配并发布到多平台——公众号（排版 + 推草稿箱）、X thread、小红书卡片。核心是公众号：按强调密度模型渲染成遵守"微信平台红线"的内联样式 HTML，机械校验通过后调微信 draft/add API 推到草稿箱（只建草稿、绝不自动群发）。Triggers：「发布这篇」「把这篇发成公众号」「一稿多发」「把草稿适配成三个平台」「排版这篇公众号」「publish 这篇」
---

# soia-pkm-publish

PKM 闭环的**发布环节（发）**：把 `compose` 产出的成文草稿，适配成各平台格式并投递。核心场景是**公众号**（排版最费手工），其次 X thread、小红书卡片。

> 蓝本：vault 里一篇关于 Obsidian + AI 公众号排版工作流的归档文章——本 skill 是它的落地实现；不要在公开 skill 中写入个人 vault 的真实路径。

## 客户可读说明

### 这个技能可以做什么

把写好的文章草稿适配并发布到多平台——公众号（排版 + 推草稿箱）、X thread、小红书卡片。核心是公众号：按强调密度模型渲染成遵守"微信平台红线"的内联样式 HTML，机械校验通过后调微信 draft/add API 推到草稿箱（只建草稿、绝不自动群发）

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到 Obsidian/vault 文件变更、终端日志、生成产物路径和最终回执。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. Agent 先判断是否命中本技能，再检查依赖、配置、权限和风险动作。
3. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。
4. 执行后验证真实输出，不用“看起来成功”代替证据。
5. 最终回复必须给客户可见总结：做了什么、日志摘要、文件变化、问题和下一步。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-publish -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-publish/config.yml
SOIA_PKM_PUBLISH_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- 强依赖、可选依赖和第三方 skill 关系必须以本 `SKILL.md` 后续的“依赖 / 前置 / 资源 / 边界”说明为准；没有写清楚时，先补说明或询问客户，不要猜。
- 第三方 skill 只能声明依赖和安装方式，不直接修改第三方 skill 文件。

### 日志与完成回执

每次执行都要让客户看见过程和结果。最低回执格式：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <检查到的输入/配置/依赖，不打印秘密值>
- processed: <数量或范围>
- created/updated: <数量或路径>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <运行过的检查、命令或人工核对点>

问题与下一步：
- <缺 key / 缺依赖 / 需要客户确认 / 建议下一条命令；没有则写“无”>
```

## 动笔前：读个人上下文

适配任何平台前，先读 `00_Obsidian系统/个人说明书.md` §5「各平台定位」，按该平台的**读者与口吻**调措辞。本 skill 内置的是各平台**格式规则**（下文），个人说明书补的是**口吻与读者定位**，两者叠加——格式对不等于口吻对。个人说明书无此文件或缺该平台定义时，回退到通用格式。

## 公众号发布（主流程）

### 微信平台红线（必须遵守）

公众号自带的编辑器（网页粘贴、`draft/add` 接口）会主动过滤/剥离大量 HTML/CSS 写法——
排版好的 HTML 一旦踩中下面的红线，粘贴或推送后样式大概率整段消失。渲染前先照这份
清单自查；`scripts/render_wechat.py` 已按此实现，`scripts/validate_wechat_html.py`
是这份清单的机械校验器（有硬性违规直接 exit 1）。

**不能做（禁用，出现即会被吃掉/剥离）**

- `<div>` —— 微信编辑器不识别，块级容器一律用 `<section>`（多行容器）或 `<p>`（单段）替代。
- `class="..."` / `id="..."` —— 无论是复制粘贴还是接口推送都会被剥离，样式只能靠内联 `style=""` 存活。
- `position` / `float` —— 布局类 CSS 编辑器不支持，用 `margin`/`padding`/`text-align` 等流式布局替代。
- `@media` / `@keyframes` —— 响应式断点和动画规则整段被丢弃，公众号正文既没有断点也用不到动画。
- CSS 变量 `var(--x)` 用法及 `--x: ...` 声明 —— 自定义属性不被支持，颜色/尺寸必须写死字面值
  （本 skill 的替代方案：主题色用 Python 常量在渲染脚本顶部集中定义，而不是 CSS 变量）。
- `<style>...</style>` 整块 —— 内嵌/外部样式表规则一律不生效，样式必须逐个内联在标签的 `style=""` 上。

**必须这样做（强制，否则粘贴后大概率掉样式）**

- 所有样式内联写在 `style=""` 属性里，不依赖任何选择器。
- 每一个可见文字节点都用 `<span style="...">` 包一层——编辑器/复制粘贴经常按"标签边界"取样式，
  裸文字（直接挂在 `<p>`/`<section>`/`<li>` 下、没有再套一层 `<span>`）最容易在粘贴时掉样式。
  `<code>`/`<pre>` 里的等宽文本本身就是"原样展示"，不强制再套。
- 标点风格统一（中文正文建议全角，代码/英文用半角），避免全角半角混排显得凌乱。
- 图片：正文先用 `<img src="...">` 占位，真正发布前必须把图传到微信素材库换成 CDN URL
  （`scripts/publish.py` 负责这一步），本地路径/外链图片在公众号后台大概率显示不出来。
- 代码块：微信不支持真正的语法高亮组件，用内联样式的 `<section>` 包一层
  `<code style="...font-family:monospace...">` 模拟等宽字体 + 背景色的"代码块"观感。

自查顺序：先人工过一遍上面的"不能做"清单，再跑 `validate_wechat_html.py` 做机械复核——
人工 + 脚本双保险，有硬性违规先修渲染结果，通过（exit 0）了才进入推草稿箱一步。

### 排版规则：强调密度模型

三个层级，越往下越"重"、越要控制数量：

| 层级 | 用途 | Markdown / 实现 | 篇幅内数量 |
|------|------|------|------|
| 锚点层 | 标题、全文最重要的判断句（金句） | `#`/`##` 标题；单独成句的结论 | 全篇 ≤5 处（标题+金句合计） |
| 标记层 | 段内关键词/短语高亮，帮读者扫读 | `**加粗**`（主题色）、`==高亮==`（红色加粗） | 每段 1–3 处 |
| 容器层 | 需要跳出正文视觉的内容块 | 引用块 → 金句卡、代码块、图片 | 按需触发，不设硬性上限但不滥用 |

- 锚点层「全篇 ≤5 处」是硬约束，标题和金句合计计数，不是每种各 5 处。
- 标记层沿用原三级强调里的 L1/L2：`**...**` 是短语级强调（主题色加粗），`==...==` 是结论/
  警告/关键数字级强调（红色加粗），两者合计每段 1–3 处，避免通篇加粗看起来像广告文案。
- 容器层按内容形态触发，不是为了"凑视觉丰富度"——有引用才用金句卡、有代码才用代码块。
- 总强调占比（标记层文字量 / 全文字数）仍建议 **<15%**。禁背景色 / 框（容器层例外）。
- 文章类型：frontmatter `workflow_type: tech`（有代码/表格）或 `editorial`（纯文字）；
  `render_wechat.py` 目前是统一简洁主题，`render.py`（早期简版）保留 tech/editorial 两风格。
- 配图：Alt 为空 → 图下不显示 caption；Alt 有内容 → 写清图里是什么（别用"配图""截图"这种无信息词）。

### 6 步流程

1. **检查** frontmatter 的 `workflow_type`。
2. **强调润色**：AI 按密度模型给全文标 `**` / `==` / 引用块，核对锚点层 ≤5、标记层每段 1–3。
3. **渲染**：`scripts/render_wechat.py` 把 Markdown → 遵守"微信平台红线"的内联样式 HTML。
4. **校验**：`scripts/validate_wechat_html.py` 机械复核红线——有硬性违规先回到渲染结果/
   脚本修，通过（exit 0）才能进入下一步；warning 不阻塞，但建议顺手清一遍。
5. **推草稿箱前先确认**：默认执行前确认风格、封面、发布账号这几项——显式调用本 skill、
   命中 `workflow_type` 默认配置，都只是推荐输入，不构成跳过确认的理由；唯一的跳过条件
   是客户当前这句话明确说"直接推/不用确认"，跳过后要在回执里说明本次沿用的假设。
   确认通过后 `scripts/publish.py` → 调微信 `draft/add` 建草稿（图片传 CDN、传封面）。
6. **人工确认发布后** → `scripts/archive.py` 标记已发布、记链接、更新日志。

### 脚本规格（scripts/）

- `render_wechat.py [--file <in.md>] [--output <out.html>]`（不传 `--file` 则读 stdin，
  不传 `--output` 则打印到 stdout）：当前推荐渲染器，只用微信平台红线允许的标签/内联
  样式；`**…**` → 主题色加粗，`==…==` → 红色加粗，`>` 引用 → 金句卡，代码块 → 内联
  样式 `<section>` 模拟，每个文字节点套 `<span>`。主题色是脚本顶部的 Python 常量，不是
  CSS 变量。
- `validate_wechat_html.py [--file <html>] [--json]`（不传 `--file` 则读 stdin）：机械
  校验上面「微信平台红线」，报告每条违规的行号 + 类型；硬性违规（div/class/id/
  position/float/media/keyframes/css 变量/`<style>` 块）exit 1，干净 exit 0；裸文字
  节点降级为 warning，不阻塞。纯 `html.parser` 实现，无第三方依赖。
- `render.py <in.md> <out.html> [--style tech|editorial]`：早期简版渲染器（tech/
  editorial 双风格），未做红线校验/`<span>` 包裹，保留给还需要 tech 风格表格/代码高亮
  的场景——用它渲染完，正式发布前也务必先过 `validate_wechat_html.py`。
- `publish.py --article <md> --cover <png> [--dry-run]`：渲染 → 传图 / 封面到微信 CDN → `draft/add` 建草稿。凭据从私有 `config.yml` 的 `env.WECHAT_APP_ID` / `env.WECHAT_APP_SECRET` 读。
- `archive.py --article <md> --url <link>`：frontmatter 置 `status: 已发布` + 记日期 / 链接 + 追加日志。

> 首次搭 <1 小时（规则 15 分 + AI 生成脚本 20 分 + Skill 文档 10 分），之后每篇排版 ≈ 0。

## ⚠️ 安全规则（必守）

- **只建草稿，绝不自动群发**——群发必须用户在公众号后台手动点。
- 凭据存 skill-specific 私有 `config.yml`（`WECHAT_APP_ID` / `WECHAT_APP_SECRET`），**不提交 Git**。
- 需先在 developers.weixin.qq.com / mp 后台启用开发 API、配 IP 白名单。

## 如何获取并配置微信公众号 AppID / AppSecret

- **入口**：微信公众平台 https://mp.weixin.qq.com，用该公众号绑定的**管理员微信扫码登录**。
- **前提条件**：`draft/add` 等接口只对**已认证的订阅号/服务号**开放；未认证的个人订阅号没有这些接口权限，调用会直接报类似 `48001 api unauthorized`。
- **取 AppID / AppSecret 的路径**：登录后台 → 左侧菜单最下方「设置与开发」→「开发」→「基本配置」（旧版菜单是「开发」→「开发接口管理」→「基本配置」）→ 页面上「公众号开发信息」区块：
  - **开发者ID（AppID）**：直接可见、可复制，对应下面的 `WECHAT_APP_ID`。
  - **开发者密码（AppSecret）**：点「重置」，管理员扫码确认后才显示，**只显示这一次**，当场复制保存，对应 `WECHAT_APP_SECRET`；重置会让旧 secret 立即失效，别处如果还在用会一并断掉。
- **IP 白名单（关键，漏了必失败）**：同一张「基本配置」页里有「IP白名单」，必须把实际调用 API 的机器的**公网 IP** 加进去，否则换 access_token 时会报 `40164 invalid ip`。本地跑就先查一下本机公网 IP（如 `curl ifconfig.me`），换网络后要记得更新。
- **放哪**：秘钥只放私有 `config.yml`，不进 vault、不进这个开源 skill 仓库、也不进 shell 启动文件。`publish.py` 已接入 `scripts/publish_env.py`，跑起来会**自动探测并加载** `$SOIA_PKM_PUBLISH_CONFIG_FILE`（或兼容别名 `$SOIA_PKM_PUBLISH_ENV_FILE`）以及默认路径 `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-publish/config.yml`，**无需手动 source**：

  ```
  # ~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-publish/config.yml
  env:
    WECHAT_APP_ID: "wx************"
    WECHAT_APP_SECRET: "********************************"
  ```

  ```
  # 直接跑，脚本自己会读私有 config.yml
  python3 scripts/publish.py --article xxx.md --cover xxx.png
  ```

  （凭据放在非默认路径时：`SOIA_PKM_PUBLISH_CONFIG_FILE=/你的/路径/config.yml python3 scripts/publish.py ...`。）

- **自检**：配好后可以先让 AI「用这份凭据换一次 access_token 看通不通」，通了再往下走 render → validate → 推草稿箱这条主流程。

## 其他平台（简版适配）

- **X thread**：长文按逻辑拆成 (1/N)，首条抓钩子、末条给 CTA，每条 ≤280 字。
- **小红书**：提炼成卡片式——标题党（带 emoji）+ 3–5 段短文 + 话题标签 + 配图建议。

## 执行后回执

推完草稿后告诉用户：① 草稿在公众号后台（哪篇、什么风格）② 提醒"确认无误后你手动群发" ③ 群发后回来说一声，我跑 archive 归档。X / 小红书版同理告知产出位置。

## 闭环位置

```
clip(收) → organize(整理) → distill(点) → compose(写) → ★publish(发)
```

上游 `compose` 给成文草稿；`publish` 负责多平台适配 + 投递，是闭环最后一环。凭据与"手动群发"这道人工闸门由用户把控。
