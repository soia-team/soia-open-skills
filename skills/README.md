# SOIA Open Skills Catalog

> Generated from `skills/*/SKILL.md` and optional `agents/openai.yaml`.
> Do not edit by hand. Run `python3 scripts/generate_skill_catalog.py`.
> Discoverable by `npx skills add soia-team/soia-open-skills -l`: 25 skills.

## Source Fields

- `SKILL.md` is the canonical cross-agent instruction file. Capabilities, dependencies, setup, workflow steps, logs, and completion summaries must live there.
- `agents/openai.yaml` is optional UI/catalog metadata for OpenAI/Codex-style surfaces and SOIA registry display: `display_name`, `short_description`, and `default_prompt`.
- Claude Code and generic skills.sh-compatible agents must be assumed to consume `SKILL.md`; do not put required workflow steps only in `agents/openai.yaml`.
- Legacy `metadata.json` files are not used to generate this catalog.

## PKM

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-pkm-alipan`](./soia-pkm-alipan/) | 阿里云盘原子操作层：安装/登录 aliyunpan、显式 driveId 双盘操作、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 扫描。作为 curator 的底层依赖 | Use soia-pkm-alipan: 阿里云盘原子操作层：安装/登录 aliyunpan、显式 driveId 双盘操作、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 扫描。作为 curator 的底层依赖 |
| [`soia-pkm-alipan-curator`](./soia-pkm-alipan-curator/) | 阿里云盘资源顾问，在 soia-pkm-alipan 原子操作上提供 inventory/organize/catalog/plan 四类工作流：盘点云盘、整理资源、生成 Obsidian 馆藏索引、基于本次用户提供的学情生成学习计划 | Use soia-pkm-alipan-curator: 阿里云盘资源顾问，在 soia-pkm-alipan 原子操作上提供 inventory/organize/catalog/plan 四类工作流：盘点云盘、整理资源、生成 Obsidian 馆藏索引、基于本次用户提供的学情生成学习计划 |
| [`soia-pkm-bootstrap`](./soia-pkm-bootstrap/) | 初始化 AI-native Obsidian PKM：创建 PARA 目录、AGENTS 规则、模板、Bases、CSS、多 AI 入口，并接入 soia-pkm-* 闭环技能 | Use soia-pkm-bootstrap: 初始化 AI-native Obsidian PKM：创建 PARA 目录、AGENTS 规则、模板、Bases、CSS、多 AI 入口，并接入 soia-pkm-* 闭环技能 |
| [`soia-pkm-clip-drive`](./soia-pkm-clip-drive/) | 把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理 | Use soia-pkm-clip-drive: 把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理 |
| [`soia-pkm-clip-gzh`](./soia-pkm-clip-gzh/) | 批量归档用户自己管理的微信公众号已发文章到 Obsidian vault。支持官方 API、公众号后台接口、登录态 Cookie 三条路线，并按 url 去重 | Use soia-pkm-clip-gzh: 批量归档用户自己管理的微信公众号已发文章到 Obsidian vault。支持官方 API、公众号后台接口、登录态 Cookie 三条路线，并按 url 去重 |
| [`soia-pkm-clip-repo`](./soia-pkm-clip-repo/) | 把 GitHub 开源项目仓库一键归档到 Obsidian vault 的「开源项目图书馆」——clone 上游代码（不进 vault）+ 生成/更新项目卡（分类/语言/访问链接/最近提交自动填，用途/状态/stars/我的笔记留人工）+ 起调研笔记骨架 + 双向链接；也支持批量重跑刷新全部项目卡的自动字段。当用户说「... | Use soia-pkm-clip-repo: 把 GitHub 开源项目仓库一键归档到 Obsidian vault 的「开源项目图书馆」——clone 上游代码（不进 vault）+ 生成/更新项目卡（分类/语言/访问链接/最近提交自动填，用途/状态/stars/我的笔记留人工）+ 起调研笔记骨架 + 双向链接；也支持批量重跑刷新全部项目卡的自动字段。当用户说「... |
| [`soia-pkm-clip-web`](./soia-pkm-clip-web/) | 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内... | Use soia-pkm-clip-web: 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内... |
| [`soia-pkm-clip-wechat`](./soia-pkm-clip-wechat/) | 归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出 | Use soia-pkm-clip-wechat: 归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出 |
| [`soia-pkm-clip-x`](./soia-pkm-clip-x/) | 归档 X/Twitter 推文、thread、Article 到 Obsidian vault。基于 fxtwitter API，单条零配置；可选同步 Telegram 收藏。需要 PDF 时优先用 Obsidian 导出 | Use soia-pkm-clip-x: 归档 X/Twitter 推文、thread、Article 到 Obsidian vault。基于 fxtwitter API，单条零配置；可选同步 Telegram 收藏。需要 PDF 时优先用 Obsidian 导出 |
| [`soia-pkm-compose`](./soia-pkm-compose/) | 把 distill 提炼出的观点写成成文草稿。以用户观点为骨、vault 摘抄为料，生成可继续交给 publish 的文章。可指定公众号/知乎/随笔风格 | Use soia-pkm-compose: 把 distill 提炼出的观点写成成文草稿。以用户观点为骨、vault 摘抄为料，生成可继续交给 publish 的文章。可指定公众号/知乎/随笔风格 |
| [`soia-pkm-cover-image`](./soia-pkm-cover-image/) | 为公众号/X/小红书文章生成封面图。五维参数（type/palette/rendering/text/mood），默认 2.35:1 微信头图比例，产出接 soia-pkm-publish --cover。后端仅用 codex CLI 内置生图，探测不到就询问客户，绝不静默降级、绝不用代码渲染冒充位图 | Use soia-pkm-cover-image: 为公众号/X/小红书文章生成封面图。五维参数（type/palette/rendering/text/mood），默认 2.35:1 微信头图比例，产出接 soia-pkm-publish --cover |
| [`soia-pkm-distill`](./soia-pkm-distill/) | 把 Obsidian vault 里收藏的文章「炼」成你自己的观点。读原文 → 苏格拉底式一次抛一个问题 → 你口述回答 → AI 把你的回答整理成「我的看法」段（内容是你的，AI 只帮落文字，绝不替你想、替你写），写完给你回执。也支持主题聚合：把一个 MOC 下多篇文章的观点提炼成一篇综述 | Use soia-pkm-distill: 把 Obsidian vault 里收藏的文章「炼」成你自己的观点。读原文 → 苏格拉底式一次抛一个问题 → 你口述回答 → AI 把你的回答整理成「我的看法」段（内容是你的，AI 只帮落文字，绝不替你想、替你写），写完给你回执。也支持主题聚合：把一个 MOC 下多篇文章的观点提炼成一篇综述 |
| [`soia-pkm-interpret`](./soia-pkm-interpret/) | 对 vault 里 clip 进来的长文/论文，AI 给出解读：内容总览/核心要点/关键启发/批判视角/延伸阅读五段式，产出独立 `<原文件名>-AI解读.md`，不碰原文`## 我的看法`。distill 苏格拉底提问炼用户观点，interpret 是 AI 解读，帮你判断值不值得深挖。默认快读，说「精读」升级逐节展开 |  |
| [`soia-pkm-library`](./soia-pkm-library/) | 维护 Obsidian 书库：同步微信读书书架、已读/在读记录、划线/想法和单本详情，并生成图书馆/阅读记录/类型总览。微信读书同步强依赖 weread-skills + WEREAD_API_KEY；每次执行必须输出客户可见日志、总结、文件变更和下一步建议。 | Use soia-pkm-library: 同步微信读书书架、阅读记录、划线/想法和单本详情到 Obsidian 书库，并生成总览。执行前检查 weread-skills + WEREAD_API_KEY；执行后输出客户可见日志摘要、文件变更和下一步建议。 |
| [`soia-pkm-maintain`](./soia-pkm-maintain/) | Obsidian vault 维护技能（支撑类）——三个工作流：①周维护（lint 四类体检 + 周简报）②全库地图重生成 ③AI 会话日志接入（Claude Code / Codex 双平台）。底层机械脚本纯 Python stdlib / bash，参数化支持任意 vault 路径，不硬编码具体库 | Use soia-pkm-maintain: Obsidian vault 维护技能（支撑类）——三个工作流：①周维护（lint 四类体检 + 周简报）②全库地图重生成 ③AI 会话日志接入（Claude Code / Codex 双平台）。底层机械脚本纯 Python stdlib / bash，参数化支持任意 vault 路径，不硬编码具体库 |
| [`soia-pkm-organize`](./soia-pkm-organize/) | 整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档 | Use soia-pkm-organize: 整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档 |
| [`soia-pkm-publish`](./soia-pkm-publish/) | 把写好的文章草稿适配并发布到多平台——公众号（排版 + 推草稿箱）、X thread、小红书卡片。核心是公众号：按强调密度模型渲染成遵守\"微信平台红线\"的内联样式 HTML，机械校验通过后调微信 draft/add API 推到草稿箱（只建草稿、绝不自动群发） | Use soia-pkm-publish: 把写好的文章草稿适配并发布到多平台——公众号（排版 + 推草稿箱）、X thread、小红书卡片。核心是公众号：按强调密度模型渲染成遵守\"微信平台红线\"的内联样式 HTML，机械校验通过后调微信 draft/add API 推到草稿箱（只建草稿、绝不自动群发） |
| [`soia-pkm-reading-plan`](./soia-pkm-reading-plan/) | 场景化阅读计划生成器。把一批书（来自文章书单、观点映射或主题）组织成带表格、按真实字数排期的可执行阅读计划。可选用 weread-skills 增强字数/评分/书架核实，缺少时降级估算；可选参考 huashu-weread-advisor 方法论但不依赖它。 | Use soia-pkm-reading-plan: 场景化阅读计划生成器。把一批书组织成带表格、按真实字数排期的可执行阅读计划。可选用 weread-skills 增强字数/评分/书架核实，缺少时降级估算；可选参考 huashu-weread-advisor 方法论但不依赖它。 |
| [`soia-pkm-transform`](./soia-pkm-transform/) | 把 X/公众号/网页/Markdown 文章转换为 PDF、PPT、图片/长图、试卷、脑图、播客、闪卡、报告等产物的公共路由 skill。配置外置，可调用 Obsidian、NotebookLM、Open Design、Codex 文件能力与 publish | Use soia-pkm-transform: 把 X/公众号/网页/Markdown 文章转换为 PDF、PPT、图片/长图、试卷、脑图、播客、闪卡、报告等产物的公共路由 skill。配置外置，可调用 Obsidian、NotebookLM、Open Design、Codex 文件能力与 publish |
| [`soia-pkm-translate`](./soia-pkm-translate/) | 三模式翻译技能（quick 直译 / normal 先分析术语受众再译 / refined 审校润色出版级），把长文机械分块保证术语一致，产出独立译文文件，不覆盖原文。 |  |

## Development

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-dev-agent-md-advisor`](./soia-dev-agent-md-advisor/) | AGENTS.md / CLAUDE.md / GEMINI.md 与 .claude 配置设计顾问：审查诊断、新项目起草、最佳实践问答三种模式，六维度诊断长度预算/可执行性/分区路由/重复矛盾/入口一致性/时效。 | Use soia-dev-agent-md-advisor: 审查我的 AGENTS.md/CLAUDE.md 配置，按六维度给我一份问题清单和改写建议，先别动手改，等我确认。 |
| [`soia-dev-ai-cli-upgrade`](./soia-dev-ai-cli-upgrade/) | Audit and upgrade AI/developer CLIs such as codex, claude, gemini, kimi, qwen, opencode, cursor, qodercli, and mmx with dry-run reports and logs. | Use soia-dev-ai-cli-upgrade: Audit and upgrade AI/developer CLIs such as codex, claude, gemini, kimi, qwen, opencode, cursor, qodercli, and mmx with dry-run reports and logs. |
| [`soia-dev-archify-diagrams`](./soia-dev-archify-diagrams/) | Create architecture and workflow diagrams with Archify. | Use soia-dev-archify-diagrams to create or update technical diagrams with JSON IR, validated HTML, and README PNG previews. |
| [`soia-dev-github-ops`](./soia-dev-github-ops/) | Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates. | Use soia-dev-github-ops: Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates. |
| [`soia-dev-prompt-clarity`](./soia-dev-prompt-clarity/) | 通用提示词技能：从零按七要素写结构化提示词、按六维诊断优化已有提示词、防误伤改写被安全分类器误判的正当请求；信息不足先澄清再产出。 | Use soia-dev-prompt-clarity: 帮我处理这个提示词需求——先判定是新写、优化还是防误伤改写；信息不足先给我一份一次问全的澄清清单，再产出可直接使用的提示词和逐条说明。 |

## Registry Export

Generate v7 SOIA registry manifests from the same sources when needed:

```bash
python3 scripts/generate_skill_catalog.py --registry-out <soia-repo>/runtime/registry/skills
```
