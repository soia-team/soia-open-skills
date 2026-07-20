# SOIA Open Skills Catalog

> Generated from `skills/*/SKILL.md` and optional `agents/openai.yaml`.
> Do not edit by hand. Run `python3 scripts/generate_skill_catalog.py`.
> Discoverable by `npx skills add soia-team/soia-open-skills -l`: 49 skills.

## Source Fields

- `SKILL.md` is the canonical cross-agent instruction file. Capabilities, dependencies, setup, workflow steps, logs, and completion summaries must live there.
- `agents/openai.yaml` is optional UI/catalog metadata for OpenAI/Codex-style surfaces and SOIA registry display: `display_name`, `short_description`, and `default_prompt`.
- Claude Code and generic skills.sh-compatible agents must be assumed to consume `SKILL.md`; do not put required workflow steps only in `agents/openai.yaml`.
- Legacy `metadata.json` files are not used to generate this catalog.

## PKM

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-pkm-alipan-curator`](./soia-pkm-alipan-curator/) | 阿里云盘资源顾问：盘点、整理、生成 Obsidian 馆藏、增量 Excel 总索引与家庭课程导航 | Use soia-pkm-alipan-curator: 盘点或整理阿里云盘，生成 Obsidian 馆藏、分区缓存式增量 Excel 总索引或家庭课程导航，或基于本次用户提供的学情生成学习计划 |
| [`soia-pkm-alipan-drive-ops`](./soia-pkm-alipan-drive-ops/) | 阿里云盘原子操作层：安装/登录 aliyunpan、显式 driveId 双盘操作、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 扫描。作为 curator 的底层依赖 | Use soia-pkm-alipan-drive-ops: 阿里云盘原子操作层：安装/登录 aliyunpan、显式 driveId 双盘操作、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 扫描。作为 curator 的底层依赖 |
| [`soia-pkm-baidu-netdisk-ops`](./soia-pkm-baidu-netdisk-ops/) | 百度官方 bdpan Skill 适配：浏览、搜索、传输、管理与只读 JSONL 扫描 | Use soia-pkm-baidu-netdisk-ops: 通过百度官方 bdpan Skill 登录、浏览或安全操作百度网盘，并在需要时生成只读 JSONL 扫描。 |
| [`soia-pkm-bootstrap-vault-base`](./soia-pkm-bootstrap-vault-base/) | 初始化知识库中立的 Markdown vault：PARA、AGENTS、模板、多 AI 入口和 PKM 闭环 | Use soia-pkm-bootstrap-vault-base: 初始化通用 Markdown 知识库骨架并接入多 AI 与 PKM 闭环 |
| [`soia-pkm-bootstrap-vault-ima`](./soia-pkm-bootstrap-vault-ima/) | 将本地 Markdown vault 单向接入腾讯 ima 知识库 | Use soia-pkm-bootstrap-vault-ima: 将这个 Markdown vault 的指定目录同步到腾讯 ima 知识库并验证检索 |
| [`soia-pkm-bootstrap-vault-obsidian`](./soia-pkm-bootstrap-vault-obsidian/) | 配置 Obsidian 消费端：启用 Bases、CSS snippets 和可选插件 | Use soia-pkm-bootstrap-vault-obsidian: 配置这个 Markdown vault 的 Obsidian、Bases 和 CSS |
| [`soia-pkm-clip-drive`](./soia-pkm-clip-drive/) | 把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理 | Use soia-pkm-clip-drive: 把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理 |
| [`soia-pkm-clip-github-repo`](./soia-pkm-clip-github-repo/) | 把 GitHub 开源项目仓库一键归档到 Obsidian vault 的「开源项目图书馆」——clone 上游代码（不进 vault）+ 生成/更新项目卡（分类/语言/访问链接/最近提交自动填，用途/状态/stars/我的笔记留人工）+ 起调研笔记骨架 + 双向链接；也支持批量重跑刷新全部项目卡的自动字段。当用户说「... | Use soia-pkm-clip-github-repo: 把 GitHub 开源项目仓库一键归档到 Obsidian vault 的「开源项目图书馆」——clone 上游代码（不进 vault）+ 生成/更新项目卡（分类/语言/访问链接/最近提交自动填，用途/状态/stars/我的笔记留人工）+ 起调研笔记骨架 + 双向链接；也支持批量重跑刷新全部项目卡的自动字段。当用户说「... |
| [`soia-pkm-clip-web`](./soia-pkm-clip-web/) | 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内... | Use soia-pkm-clip-web: 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内... |
| [`soia-pkm-clip-wechat-account`](./soia-pkm-clip-wechat-account/) | 批量归档用户自己管理的微信公众号已发文章到 Obsidian vault。支持官方 API、公众号后台接口、登录态 Cookie 三条路线，并按 url 去重 | Use soia-pkm-clip-wechat-account: 批量归档用户自己管理的微信公众号已发文章到 Obsidian vault。支持官方 API、公众号后台接口、登录态 Cookie 三条路线，并按 url 去重 |
| [`soia-pkm-clip-wechat-article`](./soia-pkm-clip-wechat-article/) | 归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出 | Use soia-pkm-clip-wechat-article: 归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出 |
| [`soia-pkm-clip-x`](./soia-pkm-clip-x/) | 归档 X/Twitter 推文、thread、Article 到 Obsidian vault。基于 fxtwitter API，单条零配置；可选同步 Telegram 收藏。需要 PDF 时优先用 Obsidian 导出 | Use soia-pkm-clip-x: 归档 X/Twitter 推文、thread、Article 到 Obsidian vault。基于 fxtwitter API，单条零配置；可选同步 Telegram 收藏。需要 PDF 时优先用 Obsidian 导出 |
| [`soia-pkm-compose-article-draft`](./soia-pkm-compose-article-draft/) | 把 distill 提炼出的观点写成成文草稿，生成可继续交给 publish-* 家族的文章。可指定公众号/知乎/随笔风格 | Use soia-pkm-compose-article-draft: 把 distill 提炼出的观点写成成文草稿，后续按目标平台交给 publish-* 家族。 |
| [`soia-pkm-cover-image`](./soia-pkm-cover-image/) | 为公众号/X/小红书文章生成封面图。五维参数（type/palette/rendering/text/mood），公众号产出接 soia-pkm-publish-wechat-draft --cover。后端仅用 codex CLI 内置生图，探测不到就询问客户，绝不静默降级、绝不用代码渲染冒充位图 | Use soia-pkm-cover-image: 为公众号/X/小红书文章生成封面图；公众号产出接 soia-pkm-publish-wechat-draft --cover。 |
| [`soia-pkm-distill-article-opinion`](./soia-pkm-distill-article-opinion/) | 把 Obsidian vault 里收藏的文章「炼」成你自己的观点。读原文 → 苏格拉底式一次抛一个问题 → 你口述回答 → AI 把你的回答整理成「我的看法」段（内容是你的，AI 只帮落文字，绝不替你想、替你写），写完给你回执。也支持主题聚合：把一个 MOC 下多篇文章的观点提炼成一篇综述 | Use soia-pkm-distill-article-opinion: 把 Obsidian vault 里收藏的文章「炼」成你自己的观点。读原文 → 苏格拉底式一次抛一个问题 → 你口述回答 → AI 把你的回答整理成「我的看法」段（内容是你的，AI 只帮落文字，绝不替你想、替你写），写完给你回执。也支持主题聚合：把一个 MOC 下多篇文章的观点提炼成一篇综述 |
| [`soia-pkm-interpret-article-analysis`](./soia-pkm-interpret-article-analysis/) | 对 vault 里 clip 进来的长文/论文，AI 给出解读：内容总览/核心要点/关键启发/批判视角/延伸阅读五段式，产出独立的“原文件名-AI解读.md”，不碰原文的“我的看法”段。distill 苏格拉底提问炼用户观点，interpret 是 AI 解读，帮你判断值不值得深挖。默认快读，说「精读」升级逐节展开 |  |
| [`soia-pkm-library-book-catalog`](./soia-pkm-library-book-catalog/) | 纯本地、幂等地补建待读记录并生成图书馆、阅读记录和按类型总览，不依赖微信读书。 | Use soia-pkm-library-book-catalog: 补建待读记录、重新生成图书馆总览或整理本地书库；只读取和写入 vault，不需要微信读书配置。 |
| [`soia-pkm-library-weread-sync`](./soia-pkm-library-weread-sync/) | 同步微信读书已读书目与划线，并通过微信读书 API 补单本书详情；需要 weread-skills 和 WEREAD_API_KEY。 | Use soia-pkm-library-weread-sync: 同步微信读书书架、已读书目或划线，或补一下指定书的详情；执行前检查 weread-skills + WEREAD_API_KEY。 |
| [`soia-pkm-maintain`](./soia-pkm-maintain/) | Obsidian vault 维护技能（支撑类）——三个工作流：①周维护（lint 四类体检 + 周简报）②全库地图重生成 ③AI 会话日志接入（Claude Code / Codex 双平台）。底层机械脚本纯 Python stdlib / bash，参数化支持任意 vault 路径，不硬编码具体库 | Use soia-pkm-maintain: Obsidian vault 维护技能（支撑类）——三个工作流：①周维护（lint 四类体检 + 周简报）②全库地图重生成 ③AI 会话日志接入（Claude Code / Codex 双平台）。底层机械脚本纯 Python stdlib / bash，参数化支持任意 vault 路径，不硬编码具体库 |
| [`soia-pkm-organize-article-moc`](./soia-pkm-organize-article-moc/) | 整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档 | Use soia-pkm-organize-article-moc: 整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档 |
| [`soia-pkm-publish-rednote-card`](./soia-pkm-publish-rednote-card/) | 把文章改写成小红书 rednote 笔记：标题、3–5 段短文、标签和配图建议。 | Use soia-pkm-publish-rednote-card: 把这篇文章改成小红书笔记，给我标题、短文、话题标签和配图建议。 |
| [`soia-pkm-publish-wechat-draft`](./soia-pkm-publish-wechat-draft/) | 把文章排版成符合微信公众号限制的 HTML，校验后推入草稿箱；只建草稿，绝不自动群发。 | Use soia-pkm-publish-wechat-draft: 把这篇文章排版成公众号文章，校验后推到草稿箱。 |
| [`soia-pkm-publish-x-article`](./soia-pkm-publish-x-article/) | 把 Markdown 成文直传 X Articles 草稿箱：富文本粘贴、封面与正文图按原位插入，只存草稿绝不发布。 | Use soia-pkm-publish-x-article: 把这篇 Markdown 长文上传到 X Articles 草稿箱，封面用文首第一张图，校验通过后给我草稿 URL。 |
| [`soia-pkm-publish-x-thread`](./soia-pkm-publish-x-thread/) | 把成文草稿拆成 ≤280 字符的 X thread 文本，人工复制发布，不接 X API。 | Use soia-pkm-publish-x-thread: 把这篇文章拆成带 (1/N) 编号的 X 推文串，保留链接和代码完整性。 |
| [`soia-pkm-reading-plan`](./soia-pkm-reading-plan/) | 场景化阅读计划生成器。把一批书（来自文章书单、观点映射或主题）组织成带表格、按真实字数排期的可执行阅读计划。可选用 weread-skills 增强字数/评分/书架核实，缺少时降级估算；可选参考 huashu-weread-advisor 方法论但不依赖它。 | Use soia-pkm-reading-plan: 场景化阅读计划生成器。把一批书组织成带表格、按真实字数排期的可执行阅读计划。可选用 weread-skills 增强字数/评分/书架核实，缺少时降级估算；可选参考 huashu-weread-advisor 方法论但不依赖它。 |
| [`soia-pkm-transform-article-notebooklm`](./soia-pkm-transform-article-notebooklm/) | 用 NotebookLM 把文章转换为试卷、闪卡、脑图、播客、学习笔记等学习类产物，降级为本地 Markdown |  |
| [`soia-pkm-transform-article-slides`](./soia-pkm-transform-article-slides/) | 把文章、提纲、要点列表、数据表或主题转换为 PPT / PPTX / HTML 演示文稿或课件。本地 HTML deck 优先，可选 Open Design 或 NotebookLM PPT |  |
| [`soia-pkm-transform-article-visual`](./soia-pkm-transform-article-visual/) | 把文章转换为长图、信息图、海报、封面、插画等视觉产物。HTML/CSS 截图为本地默认方案，可选 Open Design 或 Codex 图生成 |  |
| [`soia-pkm-transform-obsidian-pdf`](./soia-pkm-transform-obsidian-pdf/) | 用 Obsidian 原生导出把 vault 内 Markdown 笔记导出为 PDF。vault 外文章降级 pandoc/weasyprint |  |
| [`soia-pkm-translate-article-zh`](./soia-pkm-translate-article-zh/) | 三模式翻译技能（quick 直译 / normal 先分析术语受众再译 / refined 审校润色出版级），把长文机械分块保证术语一致，产出独立译文文件，不覆盖原文。 |  |

## CWork

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-cwork-feishu-cli`](./soia-cwork-feishu-cli/) | 分开核对知识库/Wiki与云盘/Drive权限，再用官方 lark-cli 只读调研。 | 用 soia-cwork-feishu-cli 先区分飞书知识库和云盘，再分别核对应用身份 Bot 与用户 OAuth 的最小只读权限，最后只读调研，不要修改远端内容。 |
| [`soia-cwork-feishu-doc-git-sync`](./soia-cwork-feishu-doc-git-sync/) | 同步飞书知识库到 Markdown、Git、Obsidian 和 VitePress | 使用 soia-cwork-feishu-doc-git-sync，以只读镜像模式检查并同步指定飞书知识库到本地 Git 知识库。 |
| [`soia-cwork-processon-diagrams`](./soia-cwork-processon-diagrams/) | 浏览、导出并校验归档 ProcessOn 图表。 | Use $soia-cwork-processon-diagrams to inventory this ProcessOn team space, inspect selected diagrams, export approved files without changing remote content, and finalize browser-reported downloads into configured delivery and manifest directories. |

## Development

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-dev-agent-cli-dispatch`](./soia-dev-agent-cli-dispatch/) | Host-agnostic external AI model/CLI dispatch for coding, review, analysis, research, documentation, and content tasks, with explicit or automatic model/reasoning selection, Token/cost receipts, model-integrity checks, qu... | Use soia-dev-agent-cli-dispatch to send this task to an external AI model/CLI (codex/claude/agy/gemini/kimi/opencode/qwen), keeping Antigravity consumer auth separate from Gemini enterprise/API-key/Vertex lanes, honoring explicit model/reasoning choices or verified auto-routing, then report requested vs actual model, detailed Token usage, API-equivalent cost, validation evidence, and recovery state. |
| [`soia-dev-agent-md-advisor`](./soia-dev-agent-md-advisor/) | AGENTS.md / CLAUDE.md / GEMINI.md 与 .claude 配置设计顾问：审查诊断、新项目起草、最佳实践问答三种模式，六维度诊断长度预算/可执行性/分区路由/重复矛盾/入口一致性/时效。 | Use soia-dev-agent-md-advisor: 审查我的 AGENTS.md/CLAUDE.md 配置，按六维度给我一份问题清单和改写建议，先别动手改，等我确认。 |
| [`soia-dev-ai-cli-upgrade`](./soia-dev-ai-cli-upgrade/) | Audit and upgrade AI CLIs, using agy for consumer Google login and Gemini only for supported non-consumer lanes. | Use soia-dev-ai-cli-upgrade to audit or upgrade my AI CLIs; treat agy as the consumer Google-login successor and keep Gemini opt-in for supported enterprise, API Key, or Vertex lanes. |
| [`soia-dev-archify-diagrams`](./soia-dev-archify-diagrams/) | Create architecture and workflow diagrams with Archify. | Use soia-dev-archify-diagrams to create or update technical diagrams with JSON IR, validated HTML, and README PNG previews. Ask for or infer the delivery directory, pass --output-dir explicitly for repository/proposal outputs, and use ~/Downloads/soia-dev-archify-diagrams/ only as the safe default. |
| [`soia-dev-coding-protocol`](./soia-dev-coding-protocol/) | 为普通工程代码改动建立最小范围、验证前置、anti-fake-fix 与写后复核契约；适用于修复、重构、实现和评审。 |  |
| [`soia-dev-design-explorer`](./soia-dev-design-explorer/) | Create and verify hi-fi prototypes, decks, animations, and design reviews | Use $soia-dev-design-explorer with soia-dev-open-design-ops checks, user-provided brand inputs, a classified output destination, and verifiable delivery evidence. |
| [`soia-dev-doc-sync`](./soia-dev-doc-sync/) | 审计并修复任意代码仓的 docs、README、CHANGELOG、VERSION 与明确真源之间的事实漂移；先建立真源优先级与证据，再按依赖顺序同步派生文档。 |  |
| [`soia-dev-fix-loop`](./soia-dev-fix-loop/) | 用五步闭环处理代码审查或测试发现：复现、决策、修复、回归复核与回执，防止遗漏、假修复和无证据收口。 |  |
| [`soia-dev-github-ops`](./soia-dev-github-ops/) | Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates. | Use soia-dev-github-ops: Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates. |
| [`soia-dev-open-design-ops`](./soia-dev-open-design-ops/) | Operate Open Design daemon, catalogs, design systems, exports, and session resume | Use $soia-dev-open-design-ops to check my Open Design environment, start the local daemon safely, query real catalogs, and run a source-backed export or resume workflow. |
| [`soia-dev-project-scaffold`](./soia-dev-project-scaffold/) | 为任意新 Git 项目创建最小 AI 协作基线。 | Use $soia-dev-project-scaffold to create a minimal AGENTS.md and docs baseline for a new Git project. |
| [`soia-dev-prompt-clarity`](./soia-dev-prompt-clarity/) | 中英文提示词编写、诊断、防误伤改写与可验证规格化 | Use $soia-dev-prompt-clarity to turn my request into a clear, directly usable prompt; preserve my chosen prompt and explanation languages, and use a named framework only when it materially improves the result. |
| [`soia-dev-skill-release`](./soia-dev-skill-release/) | 完成 merge 后技能的本机安装、软链、lock 与版本发布收尾。 | Use $soia-dev-skill-release to finish local release cleanup for merged skill names from an owner/name repository. |
| [`soia-dev-sync-skills`](./soia-dev-sync-skills/) | 将共享技能目录以软链接同步到用户选择的 AI 工具目录。 | Use $soia-dev-sync-skills to preview and sync a shared skill source to explicitly selected AI tool directories. |
| [`soia-dev-task-execute`](./soia-dev-task-execute/) | 执行任意工程任务的通用闭环：定义边界、实施最小改动、验证、独立复核与回执。适用于代码、配置、文档和维护任务。 |  |
| [`soia-dev-terminal-ops`](./soia-dev-terminal-ops/) | Monitor long-running POSIX jobs and recover stalled processes safely | Use $soia-dev-terminal-ops to monitor this long-running command, diagnose progress with multiple signals, and apply the TERM-to-KILL confirmation gates if recovery is needed. |

## Registry Export

Generate v7 SOIA registry manifests from the same sources when needed:

```bash
python3 scripts/generate_skill_catalog.py --registry-out <soia-repo>/runtime/registry/skills
```
