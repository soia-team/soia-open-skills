# THIRD_PARTY_NOTICES

> Last updated: 2026-07-21（新增 draw.io Desktop、drawio-skill 与 drawio-mcp-server 调研登记）
> 本文件集中声明本仓库各 skill 引用、依赖或参考的第三方项目与服务。
> 除 §0 明确登记的代码改编（携带 `licenses/` 上游 license 副本）外，其余引用属于以下三类之一：接口口径的源码级参考（只读其源码核对参数，不搬运实现）、运行时调用的外部工具/库/skill、在线 API 服务。
>
> 列入标准：仓库文档（`SKILL.md`、README、references）中出现**显式上游链接或安装指令**的第三方。协议列为 GitHub / PyPI / Homebrew 元数据快照（快照日期 2026-07-20），复用前请重新核对上游实时协议。

## 0. 代码改编（携带上游 license 副本）

| 上游 | 协议 | 改编处 | 说明 |
|---|---|---|---|
| [wshuyi/x-article-publisher-skill](https://github.com/wshuyi/x-article-publisher-skill) | MIT（副本：`licenses/wshuyi-x-article-publisher-skill-LICENSE.txt`） | `soia-pkm-publish-x-article/scripts/parse_x_article.py` | Markdown 解析/block_index 定位/HTML 转换逻辑改编自其 `parse_markdown.py`；文件头已注明出处。剪贴板脚本为本仓库独立实现（osascript 路线），未取自上游 |

工作流设计参考（无代码复制）：[mcncarl/yichen-skills](https://github.com/mcncarl/yichen-skills)（非商业协议）的 `yichen-x-article-draft-uploader` —— 借鉴其「封面缺失先中断询问」「上传后机械校验清单」「只存草稿不发布」的流程设计；其代码未阅读复制，自动化路线（agent 驱动浏览器 vs 独立 Playwright + cookie 导出）也与其不同。

## 1. 接口口径参考（源码级阅读，无代码复制）

| 上游 | 协议快照 | 用于 | 引用性质 |
|---|---|---|---|
| [wnma3mz/wechat_articles_spider](https://github.com/wnma3mz/wechat_articles_spider) | Apache-2.0 | `soia-pkm-clip-wechat-account` | 公众号后台 `searchbiz` / `appmsg` 接口参数口径的源码级核对（`ArticlesUrls.py`），未搬运实现 |
| [cv-cat/WechatOAApis](https://github.com/cv-cat/WechatOAApis) | 无 SPDX 识别（NOASSERTION） | `soia-pkm-clip-wechat-account` | `appmsgpublish` / `searchbiz` 接口参数口径的源码级核对（`utils/wx_utils.py`），未搬运实现；因上游无明确协议，保持只读参考边界 |

## 2. 运行时依赖的第三方 CLI / 库 / skill

### 2.1 CLI 工具

| 上游 | 协议快照 | 用于 | 关系 |
|---|---|---|---|
| [tickstep/aliyunpan](https://github.com/tickstep/aliyunpan) | Apache-2.0 | `soia-pkm-alipan-drive-ops` / `soia-pkm-alipan-curator` | 阿里云盘操作的底层 CLI（Homebrew 安装），本仓库只调用不修改 |
| [baidu-netdisk/bdpan-storage](https://github.com/baidu-netdisk/bdpan-storage) | Apache-2.0 | `soia-pkm-baidu-netdisk-ops` | 百度官方 `baidu-drive` Skill 与 `bdpan` CLI，默认后端 |
| [mqhe2007/baidupan-cli](https://github.com/mqhe2007/baidupan-cli) | Apache-2.0 | `soia-pkm-baidu-netdisk-ops` | 可选社区后端（开放平台应用目录测试） |
| [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) | MIT | `soia-pkm-transform-article-notebooklm`（及 slides / visual / obsidian-pdf 的可选路线） | NotebookLM 非官方 Python API/CLI，运行时调用 |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | Apache-2.0 | `soia-dev-open-design-ops` / `soia-dev-design-explorer`（及 transform 家族可选路线） | Open Design 引擎，运行时调用 |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | MIT | `soia-dev-archify-diagrams` | 架构图渲染引擎，运行时调用 |
| [larksuite/cli](https://github.com/larksuite/cli) | MIT | `soia-cwork-feishu-cli` / `soia-cwork-feishu-doc-git-sync` | 飞书官方 lark-cli，运行时调用 |
| [jgraph/drawio-desktop](https://github.com/jgraph/drawio-desktop) | Apache-2.0 | `soia-dev-drawio-visio-diagrams` | VSDX 导入、draw.io XML 转换与 PNG/SVG/PDF/JPG 渲染的本地官方 CLI |
| [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) | Apache-2.0 | `soia-dev-ai-cli-upgrade` / `soia-dev-agent-cli-dispatch` | 被管理/派发的外部 AI CLI |
| [google-antigravity/antigravity-cli](https://github.com/google-antigravity/antigravity-cli) | 无 SPDX 识别 | `soia-dev-ai-cli-upgrade` / `soia-dev-agent-cli-dispatch` 等 | 被管理/派发的外部 AI CLI（agy） |

> `soia-dev-agent-cli-dispatch` 还会派发用户已自行安装的其他 AI CLI（codex / claude / kimi / opencode / qwen 等）。它们是用户环境中的被调度对象、非本仓库分发的依赖，故不逐一列入；列入标准见文件头。

### 2.2 Python 库

| 上游 | 协议快照 | 用于 | 关系 |
|---|---|---|---|
| [trafilatura](https://pypi.org/project/trafilatura/) | Apache-2.0 | `soia-pkm-clip-web` | 正文抽取，运行时调用（与 readability-lxml 互为兜底） |
| [readability-lxml](https://pypi.org/project/readability-lxml/) | Apache-2.0 | `soia-pkm-clip-web` | 正文抽取，运行时调用 |
| [Telethon](https://github.com/LonamiWebs/Telethon) | MIT | `soia-pkm-clip-x` | 可选依赖，仅 Telegram MTProto 收藏同步路线使用 |
| [PyYAML](https://pypi.org/project/PyYAML/) | MIT | `soia-cwork-processon-diagrams` | 可选依赖，仅在读取私有 `config.yml` 路径配置时调用 |

### 2.3 第三方 skill

配合使用、只声明关系不修改其文件（同 README「致谢与相关项目」）：

| 第三方 skill | 上游 | 协议快照 | 关系 |
|---|---|---|---|
| `weread-skills` | [Tencent/WeChatReading](https://github.com/Tencent/WeChatReading) | NOASSERTION（官方入口 <https://weread.qq.com/r/weread-skills>） | `soia-pkm-library-weread-sync` 强依赖；`soia-pkm-reading-plan` 可选增强 |
| `huashu-weread-advisor` | [alchaincyf/huashu-weread](https://github.com/alchaincyf/huashu-weread) | MIT | `soia-pkm-reading-plan` 可选方法论复用；`soia-pkm-distill-article-opinion` 仅参考 alchemy 方法 |
| `huashu-design` | [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | MIT | `soia-dev-design-explorer` 外部强依赖，需单独安装 |
| `book-to-skill` | [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | MIT | 非运行依赖；独立工具 |
| `find-skills` | [vercel-labs/skills](https://github.com/vercel-labs/skills) | 无 SPDX 识别 | 非运行依赖；skill 发现/安装辅助（`npx skills`） |

工作流/能力设计参考（未复制代码）：

| 上游 | 协议快照 | 用于 | 关系 |
|---|---|---|---|
| [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) | MIT | `soia-dev-drawio-visio-diagrams` | 参考 `.drawio` 真源、CLI 渲染和自检闭环；未复制脚本、shape 索引或 skill 正文 |
| [lgazo/drawio-mcp-server](https://github.com/lgazo/drawio-mcp-server) | MIT | `soia-dev-drawio-visio-diagrams` | 可选元素级编辑器能力参考；不复制代码，且明确桌面直连 CSP 限制 |

## 3. 在线 API 服务

| 服务 | 背后项目/提供方 | 协议快照 | 用于 | 关系 |
|---|---|---|---|---|
| `api.fxtwitter.com` | [FxEmbed/FxEmbed](https://github.com/FxEmbed/FxEmbed) | MIT | `soia-pkm-clip-x` | 调用其公共 API 服务抓推文 JSON，不使用其代码 |
| `cdn.syndication.twimg.com` | Twitter/X 公开 syndication 端点 | — | `soia-pkm-clip-x` | fxtwitter 失败时的兜底端点 |
| 微信公众号后台接口（`mp.weixin.qq.com/cgi-bin/*`) | 腾讯 | — | `soia-pkm-clip-wechat-account` | 用户以自己账号的登录态读取自己的数据；接口口径参考见 §1 |
| 微信读书 API | 腾讯 | — | `soia-pkm-library-weread-sync` 等 | 经官方 `weread-skills` 与用户 API Key 调用 |
| ProcessOn Web 与 API 服务 | 北京大麦地信息技术有限公司 | — | `soia-cwork-processon-diagrams` | 通过用户已授权的 Web 登录态浏览/导出；企业 API 服务仅作官方能力说明，不逆向私有接口 |

## 4. 维护规则

1. 新增/修改 skill 时，凡文档中出现新的上游链接、安装指令或 API 端点，必须同步登记本文件对应分类。
2. 协议列是**快照**，不代表实时值；正式复用或分发前以上游仓库 LICENSE / README / manifest 实时核对为准。
3. 无明确协议（NOASSERTION / 无 SPDX）的上游：只可接口口径参考或作为用户侧工具调用，不得复制代码。
4. 一旦发生真正的代码改编：改编文件头注明出处，`licenses/` 存上游 license 副本，并在本文件 §1 升级登记。
