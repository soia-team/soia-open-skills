# 技能详情页

全生态 82 个公开技能，每个一页：触发词、产物、用法示例与安装命令。

内容从各技能的 `SKILL.md` 派生，改技能后由 CI 校验是否同步。

[← 返回门户](../../README.md)

## `soia-pkm-vault`　31 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-pkm-alipan-curator`](soia-pkm-alipan-curator.md) | 规划并整理阿里云盘资源，产出可复核的馆藏索引与学习规划 |
| [`soia-pkm-alipan-drive-ops`](soia-pkm-alipan-drive-ops.md) | 执行阿里云盘登录、浏览与文件操作，并为资源整理提供底层能力 |
| [`soia-pkm-baidu-netdisk-ops`](soia-pkm-baidu-netdisk-ops.md) | 百度网盘原子操作与只读 JSONL 扫描适配 |
| [`soia-pkm-bootstrap-vault-base`](soia-pkm-bootstrap-vault-base.md) | 以 plan-first、create-only、可检查的方式初始化平台中立的 AI-native Markdown vault 基座，包含分区下钻规则、工作台生命周期、模板与多 AI 适配层 |
| [`soia-pkm-bootstrap-vault-ima`](soia-pkm-bootstrap-vault-ima.md) | 把已有本地 Markdown vault 接入腾讯 ima 知识库消费端：安装客户端、建立目录映射、用 ima 官方 Skills 配置本地文件夹监控同步并验证检索 |
| [`soia-pkm-bootstrap-vault-obsidian`](soia-pkm-bootstrap-vault-obsidian.md) | 以 dry-run 和保留未知配置的结构化合并方式，把已有 Markdown vault 配置为 Obsidian 消费端，启用 Bases 与可选宽页 CSS |
| [`soia-pkm-clip-douyin`](soia-pkm-clip-douyin.md) | 归档单条抖音视频到 Obsidian vault，并保留本地媒体索引 |
| [`soia-pkm-clip-drive`](soia-pkm-clip-drive.md) | 把云盘/本地的存量资料（PDF/Word/表格/演示文稿/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理；图片正文需显式 OCR |
| [`soia-pkm-clip-github-repo`](soia-pkm-clip-github-repo.md) | 将 GitHub 开源仓库归档为 Obsidian vault 的项目卡和调研笔记 |
| [`soia-pkm-clip-rednote`](soia-pkm-clip-rednote.md) | 将单篇小红书图文或视频笔记归档到 Obsidian vault |
| [`soia-pkm-clip-web`](soia-pkm-clip-web.md) | 归档网页或博客文章到 Obsidian vault，并按统一规范落地 |
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
| [`soia-pkm-reading-plan`](soia-pkm-reading-plan.md) | 把书单、主题或观点映射组织成按字数排期的可执行阅读计划，并落为 Obsidian 笔记 |
| [`soia-pkm-transform-article-notebooklm`](soia-pkm-transform-article-notebooklm.md) | 用 NotebookLM 将文章转换为学习材料 |
| [`soia-pkm-transform-article-ppt`](soia-pkm-transform-article-ppt.md) | 把文章、提纲或主题转换为以可编辑 PPTX 为正式母版的演示媒体包，并支持外置固定模板与机密内容本地隔离 |
| [`soia-pkm-transform-article-visual`](soia-pkm-transform-article-visual.md) | 把文章转换为长图、信息图、海报、封面、插画等视觉产物。HTML/CSS 截图为本地默认方案，可选 Open Design 或 Codex 图生成 |
| [`soia-pkm-transform-obsidian-pdf`](soia-pkm-transform-obsidian-pdf.md) | 用 Obsidian 原生导出把 vault 内 Markdown 笔记导出为 PDF。vault 外文章降级 pandoc/weasyprint |
| [`soia-pkm-translate-article-zh`](soia-pkm-translate-article-zh.md) | 将外文文章按 quick、normal 或 refined 模式翻译成独立中文稿，保持术语一致且不覆盖原文 |

## `soia-env`　17 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-env-ai-cli-upgrade`](soia-env-ai-cli-upgrade.md) | 审计并按授权升级多款 AI CLI，先预演并核验结果 |
| [`soia-env-antigravity-cli-install`](soia-env-antigravity-cli-install.md) | 为新手安装、登录、迁移或按授权更新 Google Antigravity CLI（agy） |
| [`soia-env-claude-cli-install`](soia-env-claude-cli-install.md) | 为小白安装、登录与授权更新 Anthropic Claude Code CLI |
| [`soia-env-codex-install`](soia-env-codex-install.md) | 为新手安装、验证或按授权更新 OpenAI Codex CLI |
| [`soia-env-codex-setup-support`](soia-env-codex-setup-support.md) | 诊断并支持 Codex 桌面版与 CLI 的安装、登录、性能和存储问题 |
| [`soia-env-deepcode-cli-install`](soia-env-deepcode-cli-install.md) | 为小白安装、配置与授权更新开源 Deep Code Agent CLI（lessweb/deepcode-cli） |
| [`soia-env-environment-setup`](soia-env-environment-setup.md) | 从零规划并验证面向新手的开发环境，协调所需安装技能 |
| [`soia-env-kimi-cli-install`](soia-env-kimi-cli-install.md) | 面向小白检查、安装、登录和按明确授权更新 Moonshot AI Kimi Code CLI；识别官方独立安装与 npm 来源，默认只报告版本和产品自动更新状态 |
| [`soia-env-network-diagnose`](soia-env-network-diagnose.md) | 只读诊断安装 AI 工具前的环境问题：网络侧检查 DNS、HTTPS、代理、证书、官方源和超时；本机侧按 Node/Python/Rust/Go/包管理器/Shell 分类盘点运行时，推导当前机器能装哪些 AI CLI，并用固定七列列表汇报 |
| [`soia-env-node-install`](soia-env-node-install.md) | 为新手安装、验证或按授权更新 Node.js 与 npm |
| [`soia-env-open-skills-install`](soia-env-open-skills-install.md) | 在 Claude Code、Codex、WorkBuddy 上安装或更新 SOIA 开源技能，支持全部/单插件/单技能粒度与指定宿主 |
| [`soia-env-opencode-cli-install`](soia-env-opencode-cli-install.md) | 为新手安装、登录、配置或按授权更新 OpenCode CLI |
| [`soia-env-pi-cli-install`](soia-env-pi-cli-install.md) | 为小白安装、配置与授权更新 Pi（pi-coding-agent）CLI |
| [`soia-env-python-install`](soia-env-python-install.md) | 为新手安装、验证或按授权更新 Python 与 pip |
| [`soia-env-qoder-cli-install`](soia-env-qoder-cli-install.md) | 面向小白检查、安装、登录和按明确授权更新 Qoder CLI；识别官方独立安装、Homebrew 与 npm 来源，默认只报告版本和自动更新设置 |
| [`soia-env-storage-cleanup`](soia-env-storage-cleanup.md) | 面向小白统计 SOIA 受管配置、状态、缓存和临时目录的空间占用，生成可清理清单并提醒删除风险；只有客户看过最新清单并明确授权后才执行删除，随后复核实际释放空间 |
| [`soia-env-workbuddy-install`](soia-env-workbuddy-install.md) | 为新手安装、验证或按授权更新 WorkBuddy 桌面客户端 |

## `soia-dev`　12 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-dev-agent-cli-dispatch`](soia-dev-agent-cli-dispatch.md) | 受控调度外部 AI Agent CLI，选择已验证模型、隔离工作目录并回传模型、用量、费用与验证证据 |
| [`soia-dev-agent-md-advisor`](soia-dev-agent-md-advisor.md) | AI 项目指令与配置设计顾问，提供诊断、起草和改写建议 |
| [`soia-dev-coding-protocol`](soia-dev-coding-protocol.md) | 为普通工程代码改动建立最小范围、验证前置、anti-fake-fix 与写后复核契约；适用于修复、重构、实现和评审 |
| [`soia-dev-doc-sync`](soia-dev-doc-sync.md) | 审计并修复任意代码仓的 docs、README、CHANGELOG、VERSION 与明确真源之间的事实漂移；先建立真源优先级与证据，再按依赖顺序同步派生文档 |
| [`soia-dev-fix-loop`](soia-dev-fix-loop.md) | 用五步闭环处理代码审查或测试发现：复现、决策、修复、回归复核与回执，防止遗漏、假修复和无证据收口 |
| [`soia-dev-github-ops`](soia-dev-github-ops.md) | GitHub gh CLI 运维、PR 合规审查与修复 |
| [`soia-dev-project-scaffold`](soia-dev-project-scaffold.md) | 为任意新 Git 项目生成最小 AI 协作基线：可编辑的 AGENTS.md 和 docs 导航目录；在写入前确认目标路径 |
| [`soia-dev-release-plan-checklist`](soia-dev-release-plan-checklist.md) | 为互联网软件发版生成发布清单、预检门、灰度验证与发布后核对；适用于上线、部署、回滚规划 |
| [`soia-dev-review-panel`](soia-dev-review-panel.md) | 从多视角对代码 diff 或技能包进行对抗式复核，只读且不编辑、合并或发布 |
| [`soia-dev-task-execute`](soia-dev-task-execute.md) | 执行任意工程任务的通用闭环：定义边界、实施最小改动、验证、独立复核与回执。适用于代码、配置、文档和维护任务 |
| [`soia-dev-terminal-ops`](soia-dev-terminal-ops.md) | 管理 POSIX/macOS/Linux 上的长任务、tmux 后台会话、日志抓取、停滞诊断与安全恢复；杀进程前用日志、CPU、网络多信号交叉判断，并走 TERM→复查→KILL 门 |
| [`soia-dev-test-draft-doc`](soia-dev-test-draft-doc.md) | 从需求、PRD 或变更说明生成测试计划、测试用例与验收对照；适用于测试设计、回归清单和质量评审 |

## `soia-dev-design`　6 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-dev-archify-diagrams`](soia-dev-archify-diagrams.md) | 用 Archify 将架构、数据流和流程说明生成可维护 JSON 图表及 PNG 预览 |
| [`soia-dev-design-draft-prd`](soia-dev-design-draft-prd.md) | 起草互联网通用 PRD、产品需求文档与用户故事；适用于一句话需求补全、功能范围和验收标准梳理 |
| [`soia-dev-design-explorer`](soia-dev-design-explorer.md) | 基于 Open Design（经 soia-dev-open-design-ops）做高保真 HTML 原型、设计变体、幻灯片、动画探索与设计评审；要求用户品牌输入、五分类输出落点与可复现验证 |
| [`soia-dev-drawio-visio-diagrams`](soia-dev-drawio-visio-diagrams.md) | 将 Visio VSDX 安全转换、盘点和受控升级为可编辑 draw.io 图表 |
| [`soia-dev-officecli-ops`](soia-dev-officecli-ops.md) | 以 OfficeCLI 安全读取、复制后修改并验证 DOCX、XLSX、PPTX |
| [`soia-dev-open-design-ops`](soia-dev-open-design-ops.md) | 提供供上层设计流程调用的 Open Design 原子操作与运行保障 |

## `soia-media-content`　6 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-media-compose-article-draft`](soia-media-compose-article-draft.md) | 把 distill 提炼出的观点写成成文草稿。以用户观点为骨、vault 摘抄为料，生成可继续交给 publish 的文章。可指定公众号/知乎/随笔风格 |
| [`soia-media-generate-article-image`](soia-media-generate-article-image.md) | 将文章、开源项目、品牌 Logo 或公开 X Prompt Deck 编译为可验收的图片与矢量资产，按组合轴生成 Prompt 并完成事实、文字和视觉验收 |
| [`soia-media-publish-rednote-card`](soia-media-publish-rednote-card.md) | 把成文草稿改写成 rednote（小红书）笔记：生成吸睛标题（可带 emoji）、3–5 段短文、话题标签和配图建议；获客户当次授权时可代其在创作服务平台网页端完成发布。不接平台 API、不用第三方逆向包 |
| [`soia-media-publish-wechat-draft`](soia-media-publish-wechat-draft.md) | 把成文草稿排版成符合微信公众号限制的内联样式 HTML，机械校验通过后推入微信公众号草稿箱；只建草稿，绝不自动群发 |
| [`soia-media-publish-x-article`](soia-media-publish-x-article.md) | 将 Markdown 成文上传到 X Articles 草稿箱并校验格式，只保存草稿 |
| [`soia-media-publish-x-thread`](soia-media-publish-x-thread.md) | 将成文草稿改写为带编号、符合字数限制的 X thread，并可按授权存草稿 |

## `soia-meta`　5 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-meta-find-skill`](soia-meta-find-skill.md) | 按需检索 SOIA 全生态技能并加载——剪藏网盘/知识提炼/新媒发布/编码审查与终端操作/设计图表/产品PRD/软件测试/软件发版/办公协作/教育课程/环境安装/生态管理。说出需求即可检索、定位并按需读入对应技能 |
| [`soia-meta-prompt-clarity`](soia-meta-prompt-clarity.md) | 起草、诊断并规格化中英文提示词，保留用户意图、语言与安全边界 |
| [`soia-meta-publish-market`](soia-meta-publish-market.md) | 把已正式发版的技能上架到外部市场（腾讯 SkillHub、小红书 Red Skill）：筛选可独立运行的技能、叠加平台 frontmatter、预检后交由客户提交 |
| [`soia-meta-skill-release`](soia-meta-skill-release.md) | 域仓正式发版（dev→main、tag、Release、notes、CHANGELOG）与发布收尾：市场 pin 刷新、客户端更新、旧名清理、WorkBuddy 专家安装、dev 快照试装 |
| [`soia-meta-sync-skills`](soia-meta-sync-skills.md) | 将一个共享技能源以软链接同步到用户明确选择的 AI 工具目录；支持预览、单项同步、硬依赖闭包和受限清理 |

## `soia-cwork-office`　3 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-cwork-feishu-cli`](soia-cwork-feishu-cli.md) | 通过飞书官方 lark-cli 以最小权限只读调研 Wiki、Drive 与文档 |
| [`soia-cwork-feishu-doc-git-sync`](soia-cwork-feishu-doc-git-sync.md) | 将飞书知识库或云文档以应用身份只读同步为本地 Markdown，保留目录、来源和同步元数据，并可接入 Git、Obsidian 与 VitePress；当用户要求同步飞书知识库、备份到 Git、在本地查看或规划双向同步时使用 |
| [`soia-cwork-processon-diagrams`](soia-cwork-processon-diagrams.md) | 安全盘点并按授权导出、校验和归档 ProcessOn 图表 |

## `soia-edu-course`　2 个技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-edu-compose-lesson-plan`](soia-edu-compose-lesson-plan.md) | 按课程大纲编写可执行教案与讲义结构；适用于“教案”“讲义”“课堂活动”等请求 |
| [`soia-edu-design-course-outline`](soia-edu-design-course-outline.md) | 从主题、受众和课时约束设计课程大纲；适用于“课程大纲”“教学目标”“课时规划”等请求 |

