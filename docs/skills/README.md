# 技能详情页

全生态 47 个公开技能，每个一页：触发词、产物、用法示例与安装命令。

内容从各技能的 `SKILL.md` 派生，改技能后由 CI 校验是否同步。

[← 返回门户](../../README.md)

## `soia-pkm-vault`　27 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-pkm-alipan-curator`](soia-pkm-alipan-curator.md) | 规划并整理阿里云盘资源，产出可复核的馆藏索引与学习规划 |
| [`soia-pkm-alipan-drive-ops`](soia-pkm-alipan-drive-ops.md) | 执行阿里云盘登录、浏览与文件操作，并为资源整理提供底层能力 |
| [`soia-pkm-baidu-netdisk-ops`](soia-pkm-baidu-netdisk-ops.md) | 百度网盘原子操作与只读 JSONL 扫描适配 |
| [`soia-pkm-bootstrap-vault-base`](soia-pkm-bootstrap-vault-base.md) | 以 plan-first、create-only、可检查的方式初始化平台中立的 AI-native Markdown vault 基座，包含分区下钻规则、工作台生命周期、模板与多 AI 适配层 |
| [`soia-pkm-bootstrap-vault-obsidian`](soia-pkm-bootstrap-vault-obsidian.md) | 以 dry-run 和保留未知配置的结构化合并方式，把已有 Markdown vault 配置为 Obsidian 消费端，启用 Bases 与可选宽页 CSS |
| [`soia-pkm-clip-douyin`](soia-pkm-clip-douyin.md) | 归档单条抖音视频到 Obsidian vault，并保留本地媒体索引 |
| [`soia-pkm-clip-drive`](soia-pkm-clip-drive.md) | 把云盘/本地文件或受控 PDF URL 批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理；图片正文需显式 OCR |
| [`soia-pkm-clip-github-repo`](soia-pkm-clip-github-repo.md) | 将 GitHub 开源仓库归档为 Obsidian vault 的项目卡和调研笔记 |
| [`soia-pkm-clip-rednote`](soia-pkm-clip-rednote.md) | 将单篇小红书图文或视频笔记归档到 Obsidian vault |
| [`soia-pkm-clip-web`](soia-pkm-clip-web.md) | 归档网页、博客文章或公开播客节目到 Obsidian vault；可同时保留 shownotes 与本地音频 |
| [`soia-pkm-clip-wechat-account`](soia-pkm-clip-wechat-account.md) | 批量归档用户自己管理的微信公众号已发文章到 Obsidian vault。支持官方 API、公众号后台接口、登录态 Cookie 三条路线，并按 url 去重 |
| [`soia-pkm-clip-wechat-article`](soia-pkm-clip-wechat-article.md) | 归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出 |
| [`soia-pkm-clip-x`](soia-pkm-clip-x.md) | 将单条 X/Twitter 推文、thread 或 Article 归档到 Obsidian vault |
| [`soia-pkm-clip-x-profile`](soia-pkm-clip-x-profile.md) | 面向公开 X 账号的有限范围检索与研究：采集帖子窗口，按时间、关键词、主题、媒体、模型线索和内容条件筛选，输出账号概览、时间段总结、主题分析与可审计结果，并支持将明确选定的结果交给下游技能继续处理 |
| [`soia-pkm-distill-article-opinion`](soia-pkm-distill-article-opinion.md) | 通过苏格拉底式逐问，把用户对 vault 文章的回答整理成其本人观点，并写入「我的看法」或主题综述 |
| [`soia-pkm-extract-vault-knowledge`](soia-pkm-extract-vault-knowledge.md) | 从整个 Markdown/Obsidian 知识库或指定模块的工作台、冻结证据、文章、项目研究与历史语料中，提炼去状态、可复用且带来源的长期知识，同时保留原始证据并隔离敏感信息 |
| [`soia-pkm-interpret-article-analysis`](soia-pkm-interpret-article-analysis.md) | 为 vault 长文或论文生成独立 AI 解读，帮助判断是否值得深挖，且不改原文或代写用户观点 |
| [`soia-pkm-library-book-catalog`](soia-pkm-library-book-catalog.md) | 纯本地、幂等、可重复运行地维护 Obsidian 书库：补建待读记录并重新生成图书馆、阅读记录和按类型总览，不依赖微信读书 |
| [`soia-pkm-library-weread-sync`](soia-pkm-library-weread-sync.md) | 同步微信读书已读书目与划线到 Obsidian 书库，并调用微信读书 API 补单本书详情 |
| [`soia-pkm-log-agent-sessions`](soia-pkm-log-agent-sessions.md) | 为 Claude Code、Codex 等本地 AI 接入最小化 vault 会话改动快照，支持去重、dry-run、既有 notify 合并和安全卸载 |
| [`soia-pkm-maintain-vault-health`](soia-pkm-maintain-vault-health.md) | 只读检查整个 Markdown/Obsidian 知识库或指定模块的健康状态，审计死链、歧义文件名、标签策略与过期内容，并按授权重建地图或健康简报 |
| [`soia-pkm-manage-vault-lifecycle`](soia-pkm-manage-vault-lifecycle.md) | 规划并安全执行整个 Markdown/Obsidian 知识库，或知识库中指定模块的盘点、整理、改名、迁移、归档与清理 |
| [`soia-pkm-organize-article-moc`](soia-pkm-organize-article-moc.md) | 将 Obsidian 文章库按元数据、主题双链、月份和两级 MOC 规范化整理 |
| [`soia-pkm-query-vault`](soia-pkm-query-vault.md) | 以只读方式搜索整个 Markdown/Obsidian 知识库或指定模块，检索文件名、正文、frontmatter、标签、反向链接、代码与附件，并按来源层级返回可核验结果 |
| [`soia-pkm-transform-article-notebooklm`](soia-pkm-transform-article-notebooklm.md) | 用 NotebookLM 将文章转换为学习材料 |
| [`soia-pkm-transform-article-visual`](soia-pkm-transform-article-visual.md) | 把文章转换为长图、信息图、海报、封面、插画等视觉产物。HTML/CSS 截图为本地默认方案，可选 Open Design 或 Codex 图生成 |
| [`soia-pkm-translate-article-zh`](soia-pkm-translate-article-zh.md) | 将外文文章按 quick、normal 或 refined 模式翻译成独立中文稿，保持术语一致且不覆盖原文 |

## `soia-dev`　9 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-dev-agent-cli-dispatch`](soia-dev-agent-cli-dispatch.md) | 派任务给外部 AI CLI 进程并核验模型、额度与产物；宿主内置 subagent 不用本技能 |
| [`soia-dev-audit-ui`](soia-dev-audit-ui.md) | 只读验收界面，技术证据与 UX/视觉判断分开报告 |
| [`soia-dev-design-ui`](soia-dev-design-ui.md) | 设计界面结构、交互状态与视觉并交接实现，守住已批准的品牌与样式 |
| [`soia-dev-enforce-coding-protocol`](soia-dev-enforce-coding-protocol.md) | 给工程改动加范围、权限与验证底线，不另起流程 |
| [`soia-dev-github-ops`](soia-dev-github-ops.md) | 查询和操作 GitHub PR、CI、Release 与协作者权限 |
| [`soia-dev-govern-architecture`](soia-dev-govern-architecture.md) | 设计或审查架构方案、核对长期漂移，明确职责、契约、事实真源与迁移边界 |
| [`soia-dev-implement-task`](soia-dev-implement-task.md) | 实现工程需求、定位修复缺陷或处理已授权 findings |
| [`soia-dev-review-code`](soia-dev-review-code.md) | 只读审查固定的代码候选或技能包，分开报告规格符合性与工程问题 |
| [`soia-dev-show-task-html`](soia-dev-show-task-html.md) | 用户要求时把任务进度、调用关系或数据流画成最小视图，复杂布局才出 HTML；普通问答与常规回执不用 |

## `soia-cwork-office`　7 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-cwork-feishu-cli`](soia-cwork-feishu-cli.md) | 用飞书官方 lark-cli 以最小权限只读调研 Wiki、Drive 与文档，或把知识库只读同步为本地 Markdown |
| [`soia-cwork-processon-diagrams`](soia-cwork-processon-diagrams.md) | 安全盘点并按授权导出、校验和归档 ProcessOn 图表 |
| [`soia-media-compose-article-draft`](soia-media-compose-article-draft.md) | 把 distill 提炼出的观点写成成文草稿。以用户观点为骨、vault 摘抄为料，生成可继续交给 publish 的文章。可指定公众号/知乎/随笔风格 |
| [`soia-media-generate-article-image`](soia-media-generate-article-image.md) | 将文章、开源项目、品牌 Logo 或公开 X Prompt Deck 编译为可验收的图片与矢量资产，按组合轴生成 Prompt 并完成事实、文字和视觉验收 |
| [`soia-media-publish-rednote-card`](soia-media-publish-rednote-card.md) | 把成文草稿改写成 rednote（小红书）笔记：生成吸睛标题（可带 emoji）、3–5 段短文、话题标签和配图建议；获客户当次授权时可代其在创作服务平台网页端完成发布。不接平台 API、不用第三方逆向包 |
| [`soia-media-publish-wechat-draft`](soia-media-publish-wechat-draft.md) | 把成文草稿排版成符合微信公众号限制的内联样式 HTML，机械校验通过后推入微信公众号草稿箱；只建草稿，绝不自动群发 |
| [`soia-media-publish-x`](soia-media-publish-x.md) | 成文发 X：拆成编号 thread 并按授权存草稿，或把 Markdown 传到 X Articles 草稿箱并校验 |

## `soia-meta`　4 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-meta-find-skill`](soia-meta-find-skill.md) | 按需求查找合适的 SOIA 技能，未安装时只收集安装选择，不代替技能执行任务 |
| [`soia-meta-prompt-clarity`](soia-meta-prompt-clarity.md) | 起草、诊断并规格化中英文提示词，保留用户意图、语言与安全边界 |
| [`soia-meta-skill-release`](soia-meta-skill-release.md) | 正式发版 SOIA 技能仓并刷新市场 pin，默认不装机 |
| [`soia-meta-sync-skills`](soia-meta-sync-skills.md) | 按明确范围把共享技能目录软链到项目或宿主，写入前先 dry-run |

