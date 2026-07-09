---
name: soia-pkm-clip-gzh
description: 批量归档用户自己管理的微信公众号已发文章到 Obsidian vault。支持官方 API、公众号后台接口、登录态 Cookie 三条路线，并按 url 去重。Triggers：「同步我的公众号」「批量拉取我公众号历史文章」「批量归档我的公众号」「导入公众号已发文章」「clip 我的公众号」
---

# soia-pkm-clip-gzh

`clip` 家族的**公众号批量成员**：和 `soia-pkm-clip-wechat`（单篇、贴 URL 归档）不同，这个 skill 面向"把我自己公众号的历史文章一次性拉进 vault"的批量场景。只用于归档**你自己管理**的公众号——不是通用的公众号爬虫。

## 三条路线怎么选

| | 路 A · 官方 API | 路 C · 公众号后台接口 | 路 B · 登录态 Cookie |
|---|---|---|---|
| 覆盖范围 | 只有通过**草稿箱「发布」**发出的文章 | **全部历史**，含手动群发的老文 | **全部历史**，含手动群发的老文 |
| 账号要求 | 需已认证服务号/订阅号 | 任意公众号，只要你能登录后台 | 任意公众号，只要你能登录后台 |
| 凭据 | AppID/AppSecret，长期有效 + IP 白名单 | token/Cookie，几小时过期 | key/pass_ticket/appmsg_token，几小时~几天过期 |
| 凭据抓取难度 | 一次性配置（后台生成） | 抓 1 对值（token+Cookie） | 抓 3 个票据 + Cookie，容易漏抓/配错对 |
| 官方程度 | developers.weixin.qq.com 有文档 | 非官方，社区逆向（源码级核对） | 非官方，社区逆向，未见于官方文档 |
| 脚本 | `scripts/fetch_api.py` | `scripts/fetch_mp.py` | `scripts/fetch_cookie.py` |

**建议**：先跑路 A 探路（凭据搭起来一次成本低，长期可复用于增量同步；多数个人未认证号会直接卡在权限门槛，见下）。要读全部历史（含手动群发的老文），**优先用路 C**——凭据只需抓一对 token/Cookie，比路 B 要配对三个票据更不容易出错，是本 skill 里读自己号历史文章的推荐路线。路 B 保留作为路 C 失效时的备选（例如某天两个接口都改版）。三条路都只在你自己能登录/管理的账号上跑；跑过的账号落地时会按 `url` 自动去重（互相跳过已归档的文章）。

路 C 内部又分两条子路径，脚本按你传不传 `--name`/`--fakeid` 自动选：**不传（默认）走 appmsgpublish，读你自己当前登录的号**；传了 `--name`/`--fakeid` 才走 searchbiz+appmsg，读指定/别人的号——原因见下方路 C 小节。

## 路 A · 官方 API

### 接口依据（2026-07 核对 developers.weixin.qq.com + 微信开放社区，字段名已写进脚本注释）

| 接口 | 方法 | 请求 | 响应关键字段 | 依据 |
|---|---|---|---|---|
| 获取 access_token | GET | `/cgi-bin/token?grant_type=client_credential&appid=&secret=` | `access_token`, `expires_in` | [官方文档](https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html)（已取到完整请求/响应示例） |
| 获取成功发布列表 | POST | `/cgi-bin/freepublish/batchget?access_token=`，body `{offset,count,no_content}` | `total_count`,`item_count`,`item[].article_id`,`item[].update_time`,`item[].content.news_item[].{title,author,digest,content,content_source_url,thumb_media_id,show_cover_pic,need_open_comment,only_fans_can_comment,url,is_deleted}` | [官方文档](https://developers.weixin.qq.com/doc/service/api/public/api_freepublish_batchget)（抓取时未能取到完整示例正文，字段名已与微信开放社区多个独立帖子交叉核对一致——**建议先用 `--dry-run --limit 3` 实测校准一次**） |
| 获取永久素材列表 | POST | `/cgi-bin/material/batchget_material?access_token=`，body `{type:"news",offset,count}`（count 官方标注 1-20） | `total_count`,`item_count`,`item[].media_id`,`item[].update_time`,`item[].content.news_item[].{title,thumb_media_id,show_cover_pic,author,digest,content,url,content_source_url}` | [官方文档](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_batchgetmaterial)（已取到完整请求/响应示例） |

### ⚠️ 覆盖范围限制（务必先读）

- `freepublish/batchget` **只返回通过草稿箱「发布」动作发出的文章**。只走过"群发"但没点过"发布"的内容、以及草稿箱功能上线前的旧版图文消息，官方目前**没有任何 API** 能拿到——这不是本 skill 的实现缺陷，是微信开放社区多个帖子交叉确认过的平台限制。
- `material/batchget_material`（type=news）返回的是永久图文素材；据社区反馈，一篇文章一旦经草稿箱正式「发布」，可能就从这个素材列表里消失。两个接口是**互补关系**，取并集也不等于"全部已发布历史"。
- 「发布能力」相关接口文档注明：**自 2025-07 起，个人主体账号、企业主体未认证账号、以及不支持认证的账号，这些接口的调用权限会被回收**。多数个人订阅号大概率整条路线都跑不通，需要已认证服务号/订阅号（同 `soia-pkm-publish` 的 `draft/add` 一样的账号门槛）。
- 结论：路 A 更适合"抽查/核对/增量同步已发布内容"，不要指望它是"全量备份"。要读全部历史（含手动群发的老文）优先用路 C，路 B 作为备选。

### 凭据与限制

- `WECHAT_APP_ID` / `WECHAT_APP_SECRET`：获取路径、IP 白名单配置同 `soia-pkm-publish` SKILL.md「如何获取并配置微信公众号 AppID / AppSecret」一节，不重复贴——两个 skill 用同一套公众号开发凭据。
- 私有配置自动探测：`$SOIA_PKM_CLIP_GZH_CONFIG_FILE`（或兼容别名 `$SOIA_PKM_CLIP_GZH_ENV_FILE`）> `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-gzh/config.yml`。配置文件使用 YAML `env:` 映射，示例见 `config.example.yml`；秘钥不进 vault、不进这个开源 skill 仓库。

### 用法

```bash
python3 scripts/fetch_api.py [--out <vault内相对目录>] [--limit N] [--dry-run] \
    [--vault <path>] [--account-name <公众号显示名>] [--force] [--page-size 20]
```

- `--dry-run`：只拉列表打印，不写文件——**首次跑强烈建议先 dry-run**，核对 `total_count`/`item_count` 和拿到的篇数是否符合预期（尤其 `freepublish/batchget` 字段未 100% 核实到官方示例正文）。
- `--account-name`：两个接口都不返回公众号昵称，给文件名/来源信息用；不传则文件名里用"公众号"占位。
- `--force`：按 `url` 已归档的文章默认跳过，加这个才会覆盖重写。

## 路 C · 公众号后台接口（推荐：读自己号全部历史）

复用 mp.weixin.qq.com **后台**（作者登录后台，非读者端 profile_ext）的接口，和路 B 一样能读全部历史（含手动群发的老文），但凭据只需抓一对 token/Cookie，比路 B 要配对三个票据（key/pass_ticket/appmsg_token）更不容易出错。

路 C 内部有两条子路径，`scripts/fetch_mp.py` 按你是否传 `--name`/`--fakeid` 自动切换：

| | 默认（不传 `--name`/`--fakeid`） | 传 `--name` 或 `--fakeid` |
|---|---|---|
| 接口 | `appmsgpublish`（作者端「发表记录」） | `searchbiz`（名→fakeid）+ `appmsg?action=list_ex`（fakeid→列表） |
| 读的是谁的号 | **你自己当前登录的这个账号**，不需要指定名字/fakeid | 指定名称/fakeid 对应的账号（可以是别的、你也管理的号） |
| 适用场景 | 最常见场景：就是想备份自己号 | 你以某账号登录后台，但要读的是另一个你也管理、且知道名称/fakeid 的号 |
| 验证状态 | **已实测**：2026-07-09 真实账号跑通，`ret=0`，`total_count=152` | 源码级核对，未见官方文档，标记「待用户实测校准」 |

**为什么默认路径不用 `searchbiz`**：`searchbiz` 是按名字模糊搜索公众号列表，设计给"找到别人的号"用；用自己公众号的名字去搜，经常搜不到自己（返回空列表），不适合当"我已经登录、我就是这个号"的默认路径。`appmsgpublish` 直接读的是当前登录态对应账号的发表记录，不存在这个问题。

### 接口依据（源码级核对 + appmsgpublish 已实测）

| 接口 | 方法 | 请求 | 响应关键字段 | 依据 |
|---|---|---|---|---|
| appmsgpublish（默认，读自己号） | GET | `/cgi-bin/appmsgpublish`，params `sub=list&begin=<0,20,40,...>&count=20&type=101_1&free_publish_type=1&sub_action=list_ex&token=&lang=zh_CN&f=json&ajax=1` | `base_resp.ret`；`publish_page`（**JSON 字符串**，`json.loads` 后为 `{total_count, publish_list[]}`）；每条 `publish_list[].publish_info`（**又是一层 JSON 字符串**），`json.loads` 后为 `{appmsgex[]}`，每条 `appmsgex[]` 含 `title/link/update_time/digest` | [cv-cat/WechatOAApis — utils/wx_utils.py](https://github.com/cv-cat/WechatOAApis/blob/master/utils/wx_utils.py) 源码级核对，**并于 2026-07-09 由用户在真实账号上实测验证通过** |
| searchbiz（名 → fakeid） | GET | `/cgi-bin/searchbiz`，params `action=search_biz&begin=0&count=5&query=<公众号名>&token=&lang=zh_CN&f=json&ajax=1` | `base_resp.ret`，`list[].{alias,fakeid,nickname,round_head_img,service_type}` | [wnma3mz/wechat_articles_spider — ArticlesUrls.py::official_info()](https://github.com/wnma3mz/wechat_articles_spider/blob/master/wechatarticles/ArticlesUrls.py) 与 [cv-cat/WechatOAApis — utils/wx_utils.py::get_fakeid_params()](https://github.com/cv-cat/WechatOAApis/blob/master/utils/wx_utils.py) 两个独立仓库参数完全一致 |
| appmsg（fakeid → 文章列表） | GET | `/cgi-bin/appmsg`，params `action=list_ex&begin=<0,5,10,...>&count=5&fakeid=<fakeid>&type=9&query=&token=&lang=zh_CN&f=json&ajax=1` | `base_resp.ret`，`app_msg_cnt`，`app_msg_list[].{aid,appmsgid,cover,digest,itemidx,link,title,update_time}`（**不含 author 字段**） | [wnma3mz/wechat_articles_spider — ArticlesUrls.py::__get_articles_data()](https://github.com/wnma3mz/wechat_articles_spider/blob/master/wechatarticles/ArticlesUrls.py) |

`appmsgpublish` 和 `appmsg?action=list_ex` 不是同一个接口、响应结构和分页步长都不同——应该是 mp 后台新旧两版前端各自调用的接口，脚本里是两套独立实现（`list_own_account()` vs `fetch_article_list()`），不能混用。

### ⚠️ 限制与风险（务必先读）

- **非官方接口**：和路 B 一样没有官方文档背书，随时可能被调整。`appmsgpublish` 虽然已实测通过，同样不是官方文档收录的接口。
- **仅用于归档你自己管理的公众号**：`--name` 命中后会打印 nickname/fakeid 并提示确认，不是你自己的号就 Ctrl+C 中断；默认路径读的就是当前登录账号本身，不存在认错号的问题。
- **token/Cookie 会过期**：社区报告通常几小时失效，无刷新机制，过期后 `base_resp.ret` 会返回非 0（脚本已按下表给出针对性提示，两条子路径共用同一套提示，社区逆向交叉核对，未见官方文档，仍属「待用户实测校准」）：

  | `ret` | 含义 | 处理 |
  |---|---|---|
  | `200003` | invalid session | token/cookie 已过期，重新登录后台抓包替换 |
  | `200013` | freq control | 触发限流，社区报告通常需要等待较长时间，别立刻重跑 |
  | `200040` | invalid csrf token | token 和 Cookie 疑似不是同一次登录会话抓的 |

- **两条子路径列表接口都不返回 author 字段**：落地时 `author` 用 `--account-name` / `WECHAT_ACCOUNT_NAME` 兜底，不保证等于文章真实署名作者，需要精确作者请人工核对原文页。
- **限流风险**：脚本默认每页/每篇请求间隔 `--sleep 3` 秒；社区报告即使 5 秒/页的节流，抓到近千篇量级仍可能触发 `freq control`，批量抓取整年历史建议配合 `--limit` 分批跑。

### 凭据获取

登录 `mp.weixin.qq.com` 后台，随便打开一篇文章编辑页或文章列表页，F12 打开浏览器开发者工具「网络」面板，从**地址栏 URL** 里复制 `token` 参数、从请求头复制完整 `Cookie` 字符串。按 `config.example.yml` 填进私有 `config.yml` 的 `env.WECHAT_MP_TOKEN` / `env.WECHAT_MP_COOKIE`。

⚠️ 注意 `token` 要取地址栏 URL 里的那个（数字串），**不是**「网络」面板里某个请求参数名叫 `appmsg_token` 的那个票据——两者是不同的票据，`appmsgpublish` 认的是地址栏 `token`。

### 用法

```bash
# 默认：不传 --name/--fakeid，读你自己当前登录的账号（appmsgpublish，推荐）
python3 scripts/fetch_mp.py [--out <目录>] [--limit N] [--dry-run] \
    [--vault <path>] [--account-name <显示名>] [--force] [--sleep 3] [--page-size 20]

# 传 --name 或 --fakeid：读指定/别人的号（searchbiz + appmsg?action=list_ex）
python3 scripts/fetch_mp.py --name <公众号名> [--out <目录>] [--limit N] [--dry-run] \
    [--vault <path>] [--account-name <显示名>] [--force] [--sleep 3] [--page-size 5]
```

- **不传 `--name`/`--fakeid`（默认，推荐）**：读你自己当前登录的账号，走 `appmsgpublish`，`--page-size` 默认 20。
- **传 `--name` 与 `--fakeid`（二选一）**：走 `searchbiz`+`appmsg?action=list_ex`，`--page-size` 默认 5；`--name` 会先跑 `searchbiz` 搜索、取第一个匹配结果；已知 `fakeid` 时直接传 `--fakeid` 跳过搜索这一步更稳。
- `--dry-run`：只翻页拉列表打印标题+链接，**不抓正文、不写文件**——比路 B 的 dry-run 更快（路 B 的 dry-run 仍会抓完全部正文），首次跑建议先 dry-run 核对篇数和标题是否符合预期。
- `--page-size` 不传时按走的子路径自动取默认值（自己号 20 / 指定号 5），两个都是已验证/社区实测的稳定值，别调大。
- 每条列表项拿到 `link` 后，脚本直接 GET 文章公开页面解析 `#js_content`（和路 B / `soia-pkm-clip-wechat` 单篇归档同一套正文抓取思路，不需要额外 cookie）。

## 路 B · 登录态 Cookie

### 接口依据（非官方，社区逆向，交叉核对）

```
GET https://mp.weixin.qq.com/mp/profile_ext
    ?action=getmsg&__biz=<biz>&f=json&offset=<offset>&count=10&is_ok=1
    &scene=124&uin=<uin,通常固定777>&key=<key>&pass_ticket=<pass_ticket>
    &wxtoken=&appmsg_token=<appmsg_token>&x5=0
Header: Cookie: <登录态 Cookie>

响应：{"ret":0,"errmsg":"ok","msg_count":N,"can_msg_continue":0|1,
       "general_msg_list":"<JSON 字符串，需二次 json.loads>","next_offset":N,...}
general_msg_list 解析后：
  {"list":[{"comm_msg_info":{"datetime":<unix ts>},
            "app_msg_ext_info":{"title","author","content_url","is_multi",
              "multi_app_msg_item_list":[同字段的合集子项]}}]}
```

依据来源：多篇独立技术博客（博客园/CSDN/知乎，2019-2024）对同一接口的逆向记录交叉核对，字段名彼此一致，但**均非官方文档**，developers.weixin.qq.com 未收录此接口。脚本已按此实现并写进代码注释，仍标记为「待用户实测校准」——第一次跑务必 `--dry-run --limit 3`。

> 提示：给用户的原始需求里附了一个参考实现链接（`zjp1997720/wechat-article-search`）；实测那个项目实际调用的是搜狗微信搜索（`weixin.sogou.com`），并没有用 cookie 抓 `profile_ext` 的技术路线，和"读全部历史"的目标不匹配，所以路 B 没有照抄它，改成上面这套被多方独立复现过的 `profile_ext` 方案。

### ⚠️ 限制与风险（务必先读）

- **非官方接口**：没有官方文档背书，微信随时可能调整实现让它失效；出问题没有官方支持渠道。
- **仅用于归档你自己管理的公众号**：多篇参考资料都提示这类逆向调用"建议仅用于学习研究目的"，抓取他人公众号历史文章可能违反微信服务条款。这个脚本设计为你自己账号的自助备份，不要用来抓别人的号。
- **票据会过期**：`key`/`pass_ticket`/`appmsg_token` 是会话票据，社区报告从几小时到几天不等；没有刷新机制，过期后报错就得重新登录抓包替换。
- **有限流风险**：脚本默认每次请求间隔 `--sleep 1.5` 秒，别调太快；批量抓取整年历史建议分批（配合 `--limit`）跑，别一次性拉几百篇。

### 凭据获取

登录 `mp.weixin.qq.com` 后台，打开该公众号任意一篇历史文章（或 `profile_ext?action=home`），在浏览器开发者工具「网络」面板里找同域请求，从请求 URL 里复制 `__biz`/`key`/`pass_ticket`/`appmsg_token`，从请求头复制完整 `Cookie` 字符串。按 `config.example.yml` 填进私有 `config.yml`。

### 用法

```bash
python3 scripts/fetch_cookie.py --biz <__biz> [--out <目录>] [--limit N] [--dry-run] \
    [--vault <path>] [--account-name <显示名>] [--force] [--sleep 1.5]
```

- 列表接口每页 10 条（社区实测上限），脚本自动按 `can_msg_continue`/`next_offset` 翻页。
- 每条列表项拿到 `content_url` 后，脚本直接 GET 文章公开页面解析 `#js_content`（和 `soia-pkm-clip-wechat` 单篇归档同一套正文抓取思路，不需要额外 cookie）。
- `--dry-run` 依然会翻完整个列表、抓完全部正文再打印（不写文件），量大时耗时较长——想快速核对列表本身，先看 stderr 里逐页打印的 `拿到 N 条，累计 M`。

## 落地规范（三条路共用）

- **中转区，不是终点**：落到 vault 的**收件箱层**，不是 `soia-pkm-organize` 归位后的最终位置——`organize` 上线前先囤在这里，之后随"作品库重构"一起归位到 40/50 区。
- 默认输出目录：`Inbox/gzh-articles/<年>/`（vault 内相对路径，代码里的通用默认值）。这个 vault 建议设为你自己的中转区，例如 `<vault-inbox-dir>/gzh-articles/`——用 `--out <vault-relative-dir>` 或私有配置里的 `env.OBSIDIAN_GZH_OUT` 覆盖（默认值刻意不硬编码具体中文路径，遵守本仓库 [SKILL_SPEC.md](../../SKILL_SPEC.md) 的"no hardcoded personal paths"规则）。
- 文件名：`<出版日期>-公众号-<账号显示名>-<标题>.md`，同名冲突时按 url 特征加短后缀。
- frontmatter：`tags:[公众号原创, 待归位]`、`source: 公众号自有`、`url`、`title`、`author`、`published_at`、`captured_at`、`route: api|cookie|mp-backend`、`content_complete`、`topics: []`（`topics` 是本 skill 相对用户原始字段清单多加的一项，方便后续 `organize` 直接补分类，无内容时留空数组，不影响其他字段）。
- 正文：HTML → Markdown 走 stdlib `html.parser`（零第三方依赖，和这个仓库其它脚本一致），不保证 100% 还原排版，复杂内联样式/公众号专属组件会被拍平成纯文本+图片链接。`content_complete: false` 表示正文抓取失败或为空，需要人工核对原文链接。
- 幂等：三个脚本都按 `url` 在 `out_dir` 下递归查找是否已归档，已存在则默认跳过（`--force` 才覆盖），三条路交替跑不会重复落地同一篇。

## 归档后

按 clip 家族惯例，AI 后续可以：
1. 逐篇补「## 摘要」（30-80 字）。
2. 判断/回填 frontmatter `topics`。
3. 等作品库重构落定后，交给 `organize` 从 `Inbox/gzh-articles` 批量归位。

## 闭环位置

```
★clip-gzh(批量收) → organize(归位/分类) → distill(收藏→观点) → compose(观点→文) → publish(发)
```

和 `soia-pkm-clip-wechat`（单篇归档）互补：clip-wechat 处理"看到一篇转发链接，随手存一篇"；clip-gzh 处理"批量迁入我自己公众号的历史存量"。两者落地规范不完全一致（clip-gzh 多了 `route`/`content_complete` 字段），暂不合并，等作品库重构时一并评估是否收敛成一套。
