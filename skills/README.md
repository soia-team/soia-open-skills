# SOIA Open Skills Catalog

> Generated from `skills/*/SKILL.md` and optional `agents/openai.yaml`.
> Do not edit by hand. Run `python3 scripts/generate_skill_catalog.py`.
> Discoverable by `npx skills add soia-team/soia-open-skills -l`: 20 skills.

## Source Fields

- `SKILL.md` provides canonical skill name and trigger description.
- `agents/openai.yaml` may provide human-facing display text and default prompt.
- Legacy `metadata.json` files are not used to generate this catalog.

## PKM

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-pkm-alipan`](./soia-pkm-alipan/) | 阿里云盘原子操作层 — 安装/登录 aliyunpan CLI（含登录态过期处理、非交互环境取码技巧）、备份盘与资源库双盘切换（--driveId 显式传参）、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 爬虫扫描方法论。是 soia-pkm-alipan-curator（整理顾问/学习计划）的底层依赖。当用户说「看下云盘」「云盘里有什么」「登录阿里云盘」「下载云盘文件」「云盘登录过期了」「全盘扫描一下云盘」时触发... |  |
| [`soia-pkm-alipan-curator`](./soia-pkm-alipan-curator/) | 阿里云盘资源顾问 — 在 soia-pkm-alipan 原子层之上提供四类工作流：盘点云盘生成核对清单（inventory）、按规范整理目录（organize，含受众三分/学段序号化/杂包必拆/SHA1查重/广告清理方法论）、把资源地图落成 Obsidian 图书馆式索引（catalog，浏览总览+全文检索+精选卡三样，脚本 gen_catalog.py 只在本 skill）、基于用户本次提供的学情用云盘已有资源生成学习计划（plan... |  |
| [`soia-pkm-bootstrap`](./soia-pkm-bootstrap/) | 从零初始化一个 AI-native 的 Obsidian 个人知识库（PKM）。建 PARA 目录骨架 + 各区 AGENTS.md + 模板 + Bases + CSS，接入 Codex、Claude Code、Gemini CLI、opencode、workbuddy 多 AI 适配层，并装好 soia-pkm-* 的输入/整理/输出技能 |  |
| [`soia-pkm-clip-drive`](./soia-pkm-clip-drive/) | 把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理 |  |
| [`soia-pkm-clip-gzh`](./soia-pkm-clip-gzh/) | 把用户自己管理的微信公众号已发文章批量拉取进 Obsidian vault。两条技术路线：官方 API（freepublish/batchget + material/batchget_material，仅覆盖通过草稿箱「发布」的文章，需已认证账号）与登录态 Cookie（非官方 profile_ext 接口，能读全部历史含手动群发的老文，但票据几小时~几天会过期） |  |
| [`soia-pkm-clip-repo`](./soia-pkm-clip-repo/) | 把 GitHub 开源项目仓库一键归档到 Obsidian vault 的「开源项目图书馆」——clone 上游代码（不进 vault）+ 生成/更新项目卡（分类/语言/访问链接/最近提交自动填，用途/状态/stars/我的笔记留人工）+ 起调研笔记骨架 + 双向链接；也支持批量重跑刷新全部项目卡的自动字段。当用户说「归档这个项目 <url>」「归档下这个仓库」「clip 这个 repo」「重新生成开源项目卡」时触发。 |  |
| [`soia-pkm-clip-web`](./soia-pkm-clip-web/) | 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内优先调用 Obsidian 自带 PDF 导出 |  |
| [`soia-pkm-clip-wechat`](./soia-pkm-clip-wechat/) | 把微信公众号文章一键归档到 Obsidian vault。抓 mp.weixin.qq.com 的静态 HTML，提取标题/作者/正文/发布时间/配图，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内优先调用 Obsidian 自带 PDF 导出 |  |
| [`soia-pkm-clip-x`](./soia-pkm-clip-x/) | 把 X (Twitter) 推文 / thread / Article 长文一键归档到 Obsidian vault。基于 fxtwitter API，零配置、无需 X API key。支持 Telegram 我的收藏批量同步（JSON 导出路径，零风险）。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内优先调用 Obsidian 自带 PD... |  |
| [`soia-pkm-compose`](./soia-pkm-compose/) | 把 distill 提炼出的观点（单篇「我的看法」或主题综述）写成一篇成文草稿。以你的观点为骨、vault 摘抄为料，润色成文章，落 <vault-path>。可指定风格（公众号/知乎/随笔）。绝不凭空编造观点 |  |
| [`soia-pkm-distill`](./soia-pkm-distill/) | 把 Obsidian vault 里收藏的文章「炼」成你自己的观点。读原文 → 苏格拉底式一次抛一个问题 → 你口述回答 → AI 把你的回答整理成「我的看法」段（内容是你的，AI 只帮落文字，绝不替你想、替你写），写完给你回执。也支持主题聚合：把一个 MOC 下多篇文章的观点提炼成一篇综述 |  |
| [`soia-pkm-library`](./soia-pkm-library/) | 维护 Obsidian 书库（图书馆书目 + 阅读记录）——同步微信读书已读书目与划线、补单本书详情、补建待读记录、重新生成图书馆总览/阅读记录总览/按类型总览三份 markdown 视图。底层是 7 个机械脚本（幂等、可重复跑），参数化支持任意 vault 路径与分类表 |  |
| [`soia-pkm-maintain`](./soia-pkm-maintain/) | Obsidian vault 维护技能（支撑类）——三个工作流：①周维护（lint 四类体检 + 周简报）②全库地图重生成 ③AI 会话日志接入（Claude Code / Codex 双平台）。底层机械脚本纯 Python stdlib / bash，参数化支持任意 vault 路径，不硬编码具体库 |  |
| [`soia-pkm-organize`](./soia-pkm-organize/) | 整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档 |  |
| [`soia-pkm-publish`](./soia-pkm-publish/) | 把写好的文章草稿适配并发布到多平台——公众号（排版 + 推草稿箱）、X thread、小红书卡片。核心是公众号：按强调密度模型渲染成遵守"微信平台红线"的内联样式 HTML，机械校验通过后调微信 draft/add API 推到草稿箱（只建草稿、绝不自动群发） |  |
| [`soia-pkm-reading-plan`](./soia-pkm-reading-plan/) | 场景化阅读计划生成器。把一批书（来自文章书单、文章观点映射、或一个主题）组织成带表格、按真实字数排期的可执行阅读计划，落地成 Obsidian 笔记。可选联动微信读书 skill 拿真实字数/评分/书架做交叉核实。当用户说「做个读书计划」「按 XX 场景排个计划」「把这篇文章的书单排成计划」「这篇文章的观点对应哪些书」「帮我规划下半年读什么」时触发。 |  |
| [`soia-pkm-transform`](./soia-pkm-transform/) | 把 X/公众号/网页/Markdown 文章转换为 PDF、PPT、图片/长图、试卷、脑图、播客、闪卡、报告等产物的公共路由 skill。配置外置，可调用 Obsidian、NotebookLM、Open Design、Codex 文件能力与 publish |  |

## Development

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-dev-ai-cli-upgrade`](./soia-dev-ai-cli-upgrade/) | Audit and upgrade AI/developer CLIs such as codex, claude, gemini, kimi, qwen, opencode, cursor, qodercli, and mmx with dry-run reports and logs. |  |
| [`soia-dev-archify-diagrams`](./soia-dev-archify-diagrams/) | Create architecture and workflow diagrams with Archify. | Use soia-dev-archify-diagrams to create or update technical diagrams with JSON IR, validated HTML, and README PNG previews. |
| [`soia-dev-github-ops`](./soia-dev-github-ops/) | Use gh CLI for GitHub issue, PR, checks, review, workflow run, and release operations with structured JSON output and safety gates. |  |

## Registry Export

Generate v7 SOIA registry manifests from the same sources when needed:

```bash
python3 scripts/generate_skill_catalog.py --registry-out <soia-repo>/runtime/registry/skills
```
