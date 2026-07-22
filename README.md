<div align="center">

# soia-open-skills

中文 | [English](README.en.md)

> *把「收藏」变成「作品」——AI 时代的个人知识管理技能体系。*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

<br>

**面向 Obsidian 的 `soia-pkm-*` 个人知识管理技能集 + `soia-cwork-*` 企业协作连接能力 + 可公开复用的 `soia-dev-*` 开发 helper**

```bash
npx skills add soia-team/soia-open-skills
```

跨 agent 通用——Claude Code、Cursor、Codex、Antigravity、Gemini、Kimi 都能装。

[闭环框架](#pkm-闭环一篇内容的一生) · [Skills 清单](#skills-清单) · [CWork · 企业协作](#-cwork--企业协作) · [高频技能速览](#高频技能速览) · [PR 协作闭环](#-pr-协作闭环审查--修复--合并) · [安装](#安装) · [Telegram 同步](#telegram-我的收藏同步clip-x) · [设计哲学](#设计哲学)

</div>

---

## PKM 闭环：一篇内容的一生

```
                     soia-pkm 个人知识管理闭环

   收 ────────→ 整理 ───────→ 点 ────────→ 写 ────────→ 发
 ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
 │ clip-x  │  │         │  │         │  │         │  │         │
 │ clip-   │  │organize │  │ distill │  │ compose │  │ publish │
 │  wechat │─→│ 分类/MOC│─→│收藏→观点 │─→│ 观点→文 │─→│ 公众号  │
 │ clip-web│  │ /归位/  │  │(你的看法)│  │ (草稿)  │  │/X/小红书│
 │ clip-   │  │ 补双链  │  │         │  │         │  │         │
 │  drive  │  │         │  │         │  │         │  │         │
 └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
   多源输入                                                  │
      ↑                                                      ▼
      └─────────  飞轮：发布 → 心得喂回 vault → 更好的输入  ──┘

  支撑：soia-pkm-bootstrap-vault-base（一句话从零搭通用 Markdown vault + 接入多 AI）
        soia-pkm-bootstrap-vault-obsidian / soia-pkm-bootstrap-vault-ima（Obsidian / ima 消费端特化）
        soia-pkm-transform-obsidian-pdf/slides/visual/notebook（转化线：按输出类型拆分）
        soia-pkm-reading-plan（读书线：把书单排成可执行阅读计划）
        soia-pkm-library-weread-sync / soia-pkm-library-book-catalog（书库线：微信读书同步 / 本地书目 catalog）
        soia-pkm-alipan-drive-ops（云盘线·原子层：aliyunpan CLI 可靠原子操作）
        soia-pkm-baidu-netdisk-ops（云盘线·原子层：百度官方 baidu-drive / bdpan）
        soia-pkm-alipan-curator（云盘线·顾问层：盘点/整理/索引/学习计划）
        soia-dev-archify-diagrams（文档图表线：Archify JSON IR → README/docs PNG 图）
        soia-dev-drawio-visio-diagrams（Visio/draw.io 线：VSDX 解析 → .drawio 真源 → 升级/渲染）
        soia-dev-github-ops / soia-dev-ai-cli-upgrade（公共开发工具线）
        soia-dev-open-design-ops（Open Design 原子层：daemon / 目录 / 设计系统 / 导出 / resume）
        soia-cwork-feishu-cli（企业协作线：飞书 CLI 只读调研云盘、文档、知识库）
        soia-cwork-processon-diagrams（企业协作线：盘点、预览和导出 ProcessOn 图表）
```

**核心理念**：收藏 ≠ 吸收。大多数人的知识库是"信息坟场"——囤了一大堆，从不回看。`soia-pkm` 把「收藏 → 观点 → 成文 → 发布」这条**从消费到创造**的链路，拆成职责单一、可组合的 skill，让 AI 帮你把囤积的信息真正变成**你自己的**作品。

---

## Skills 清单

> **通用能力（所有 skill 共享）**
> - 🤖 **支持的 AI**：跨 agent 通用——Claude Code、Codex、Cursor、Antigravity、Gemini、Kimi、amp、Warp、Zed 等所有兼容 [skills.sh](https://skills.sh) 标准的 AI。一次写 `SKILL.md`，处处可用。
> - 📚 **适用知识库**：本地 Markdown vault（推荐 PARA 结构；可按需接入 Obsidian 或腾讯 ima）。底层是纯 Markdown + YAML frontmatter，不锁定平台。
> - 🔗 **依赖链**：`clip-*` 是入口（独立可用）→ `organize` / `distill` 需 vault 里有内容 → `compose` 需 distill 的观点 → `publish` 需 compose 的草稿。
> - 🧩 **第三方 skill 口径**：只在本仓库自建 skill 里声明依赖 / 可选增强 / 方法参考，**不改第三方 skill 文件**；具体来源以 `~/.agents/.skill-lock.json` 为准。
> - **状态图例**：✅ 可直接用 · 🟡 可用但需补脚本 / 配凭据

### 📥 收集 · clip 家族

核心价值：把分散在各平台的内容一键收进 vault，是整条闭环的入口——没有稳定的收，后面的整理、提炼、成文都无从谈起。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-clip-x`](./skills/soia-pkm-clip-x/) | X 推文/thread/长文 → vault | ✅ 完全可用（脚本齐全，已多次实测）| 无（Telegram 同步可选）|
| [`soia-pkm-clip-wechat-article`](./skills/soia-pkm-clip-wechat-article/) | 公众号文章 → vault | ✅ 可用（stdlib 抓取、质量门、URL 去重、dry-run、原子写） | 无 |
| [`soia-pkm-clip-web`](./skills/soia-pkm-clip-web/) | 通用网页/博客 → vault | 🟡 SKILL.md 已就绪，抓取脚本待实现 | Python `trafilatura` |
| [`soia-pkm-clip-drive`](./skills/soia-pkm-clip-drive/) | 云盘 PDF/Word → vault | 🟡 SKILL.md 已就绪，导入脚本待实现 | Python `pypdf`/`python-docx` |
| [`soia-pkm-clip-github-repo`](./skills/soia-pkm-clip-github-repo/) | GitHub 开源项目仓库 → vault「开源项目图书馆」索引 | ✅ 可用（脚本齐全：单仓归档 + 批量刷新）| 无（需本机一个 upstream clone 目录）|
| [`soia-pkm-clip-wechat-account`](./skills/soia-pkm-clip-wechat-account/) | 自己管理的公众号已发文章批量 → vault | ✅ 可用（官方 API / 登录态 Cookie 两条路线）| 微信公众号开发凭据或登录态 Cookie |
| [`soia-pkm-clip-douyin`](./skills/soia-pkm-clip-douyin/) | 抖音单条视频 → vault：元数据/文案/互动数入笔记，MP4 落本地 Downloads（不进 vault）| ✅ 可用（脚本齐全：Playwright 拦截签名 API + 下载 + URL 去重）| Python `playwright`（`pip install playwright && python -m playwright install chromium`）|
| [`soia-pkm-clip-rednote`](./skills/soia-pkm-clip-rednote/) | 小红书单篇笔记（图文/视频）→ vault，媒体落本地 Downloads | ✅ 可用（脚本齐全，纯 stdlib 解析 `__INITIAL_STATE__`，无需登录）| 无 |

### 🗂️ 整理

核心价值：把杂乱的存量收藏转成有结构、可检索、能聚合复用的知识——收藏不等于吸收，整理是激活的第一步。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-organize-article-moc`](./skills/soia-pkm-organize-article-moc/) | 分类/补 frontmatter/建两级 MOC/按月归位/补双链 | ✅ 可用（底层脚本 rebuild_moc/backfill 已在用）| vault 里已有归档内容 |

### ✍️ 提炼 → 成文 → 发布

核心价值：闭环里真正的价值转化环节——把别人的信息变成你自己的判断，再把判断写成可发布的作品，这是从"消费"到"创造"的分水岭。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-translate-article-zh`](./skills/soia-pkm-translate-article-zh/) | **外文文章 → 中文版**：quick 直译 / normal 先分析文体术语受众再译（默认）/ refined 加审校+润色；长文机械分块保术语一致；产出独立 `-中文版.md`，绝不覆盖原文 | ✅ 可用（三模式 + 分块脚本齐全）| Python 3（强依赖，跑分块脚本）；PyYAML 可选增强 |
| [`soia-pkm-interpret-article-analysis`](./skills/soia-pkm-interpret-article-analysis/) | **收藏 → AI 解读**：内容总览/核心要点/关键启发/批判视角/延伸阅读五段式，帮你在 `distill` 深挖前先判断值不值得读；产出独立 `-AI解读.md`，不碰原文「我的看法」| ✅ 可用（纯 LLM 解读，无需脚本）| 无强依赖（`clip-*` 系列为常见上游）|
| [`soia-pkm-distill-article-opinion`](./skills/soia-pkm-distill-article-opinion/) | **收藏 → 观点**：读原文 → 一次一问 → 你答 → 「我的看法」（内容是你的，AI 只落字）| ✅ 完全可用（已实战）| vault 里有文章（`clip-*` 产出）|
| [`soia-pkm-compose-article-draft`](./skills/soia-pkm-compose-article-draft/) | **观点 → 文章草稿**（你的观点为骨、摘抄为料）| ✅ 可用（纯 LLM，无需脚本）| `distill` 产出的观点 |
| [`soia-pkm-cover-image`](./skills/soia-pkm-cover-image/) | 为公众号/X/小红书文章生成封面图（五维参数：type/palette/rendering/text/mood），公众号产出可接 `soia-pkm-publish-wechat-draft --cover` | ✅ 可用（后端为 codex CLI 内置生图；未装/未登录会停止并提示，绝不降级）| codex CLI（`codex exec`，需登录）|
| [`soia-pkm-publish-wechat-draft`](./skills/soia-pkm-publish-wechat-draft/) | **文章 → 公众号草稿**：按强调密度模型排版、机械校验并推入草稿箱，绝不自动群发 | 🟡 渲染与校验可用；微信推送需配私有 `config.yml` 凭据 | `compose` 的草稿 + 微信公众号 API |
| [`soia-pkm-publish-x-thread`](./skills/soia-pkm-publish-x-thread/) | **文章 → X thread 文本**：拆成 ≤280 字符的编号推文串，保留链接/代码，人工复制发布 | ✅ 可用（纯 LLM，无 API） | `compose` 的草稿（可选） |
| [`soia-pkm-publish-x-article`](./skills/soia-pkm-publish-x-article/) | **文章 → X Articles 富文本草稿**：解析标题/封面/正文图与分割线，浏览器富文本粘贴保格式、倒序插图，机械校验后只存草稿、绝不点发布 | ✅ 可用（脚本齐全：解析 + 剪贴板 + 发布流程；与 `publish-x-thread` 共用登录态）| 已登录浏览器（Playwright）+ X Premium+「撰写文章」权益 |
| [`soia-pkm-publish-rednote-card`](./skills/soia-pkm-publish-rednote-card/) | **文章 → rednote 笔记文本**：标题、3–5 段短文、话题标签与配图建议，人工复制发布 | ✅ 可用（纯 LLM，无 API） | `compose` 的草稿（可选）；`soia-pkm-cover-image` 可选 |

### 🔁 转化 · 文章 → 产物

核心价值：让同一篇内容适配不同消费场景——同一份素材一次输入，按需路由到 PDF、PPT、长图、播客等多种媒介产出。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-transform-obsidian-pdf`](./skills/soia-pkm-transform-obsidian-pdf/) | **文章 → PDF**：Obsidian 原生导出优先，vault 外降级 pandoc/weasyprint | ✅ 可用 | Obsidian（vault 内）或 pandoc/weasyprint（降级）|
| [`soia-pkm-transform-article-slides`](./skills/soia-pkm-transform-article-slides/) | **文章 → PPT/课件**：本地 HTML deck / PPTX，可选 Open Design / NotebookLM PPT | ✅ 可用 | python-pptx；Open Design / NotebookLM 可选 |
| [`soia-pkm-transform-article-visual`](./skills/soia-pkm-transform-article-visual/) | **文章 → 长图/信息图/海报/封面**：HTML/CSS 截图本地优先，可选 Open Design / Codex imagegen | ✅ 可用 | playwright（截图）；Open Design / Codex imagegen 可选 |
| [`soia-pkm-transform-article-notebooklm`](./skills/soia-pkm-transform-article-notebooklm/) | **文章 → 试卷/闪卡/脑图/播客**：NotebookLM 优先，降级本地 Markdown | ✅ 可用 | NotebookLM 可选；降级无额外依赖 |

### 🧰 支撑

核心价值：维护闭环运转所需的基础设施——初始化 vault、维护书库、管理云盘、日常维护和开发工具链，不在闭环主链路上，却是全局能跑起来的地基。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-bootstrap-vault-base`](./skills/soia-pkm-bootstrap-vault-base/) | 初始化知识库中立的 Markdown vault（PARA + AGENTS + 模板 + 多 AI 接入）| ✅ 可用（`init_vault.py` 跑通）| 无（它是起点）|
| [`soia-pkm-bootstrap-vault-obsidian`](./skills/soia-pkm-bootstrap-vault-obsidian/) | Obsidian 特化：启用 Bases、检查 `.obsidian` 配置与 CSS snippets | ✅ 可用 | `soia-pkm-bootstrap-vault-base` |
| [`soia-pkm-bootstrap-vault-ima`](./skills/soia-pkm-bootstrap-vault-ima/) | 腾讯 ima 特化：本地 Markdown vault → ima 知识库单向接入与检索验证 | 🟡 需按 ima 客户端实际界面配置 | `soia-pkm-bootstrap-vault-base` |
| [`soia-pkm-reading-plan`](./skills/soia-pkm-reading-plan/) | 场景化阅读计划（书单/主题 → 按真实字数排期）| ✅ 可用 | `weread-skills` 可选增强真实字数/评分；`huashu-weread-advisor` 可选复用推荐方法论；无第三方强依赖 |
| [`soia-pkm-library-weread-sync`](./skills/soia-pkm-library-weread-sync/) | 微信读书同步：已读书目、划线/想法，以及通过 API 补单本书详情 | ✅ 可用（3 个机械脚本，幂等可重复跑） | 官方 `weread-skills` + `WEREAD_API_KEY` |
| [`soia-pkm-library-book-catalog`](./skills/soia-pkm-library-book-catalog/) | 纯本地书目 catalog：补建待读记录，生成图书馆/阅读记录/分类三份总览 | ✅ 可用（4 个机械脚本，幂等可重复跑） | Python 3 + 本地 vault；不依赖微信读书 |
| [`soia-pkm-maintain`](./skills/soia-pkm-maintain/) | vault 周维护、全库地图重生成、AI 会话日志接入 | ✅ 可用（Python stdlib / bash 脚本）| Obsidian vault，`--vault <path>` 或 `OBSIDIAN_VAULT` |
| [`soia-pkm-alipan-drive-ops`](./skills/soia-pkm-alipan-drive-ops/) | 阿里云盘原子操作层：登录/双盘切换/浏览/移动/重命名/上传下载/容量查询，含输出解析与安全守则 | ✅ 可用（无需脚本，直接驱动 `aliyunpan` CLI）| `aliyunpan` CLI（brew 安装 + 扫码登录）|
| [`soia-pkm-baidu-netdisk-ops`](./skills/soia-pkm-baidu-netdisk-ops/) | 百度网盘原子操作层：基于官方 `baidu-drive` Skill / `bdpan` CLI 的登录、浏览、搜索、传输、文件管理与只读 JSONL 扫描 | ✅ 可用（官方 Skill 为默认依赖；附扫描器和安全守则）| 百度官方 `baidu-drive` Skill；`bdpan` CLI |
| [`soia-pkm-alipan-curator`](./skills/soia-pkm-alipan-curator/) | 云盘资源顾问：盘点核对（inventory）/规范整理（organize）/OB 索引与两类 Excel（catalog）/学习计划（plan）| ✅ 可用（分区缓存式总索引 + 家庭课程导航）| `soia-pkm-alipan-drive-ops`（原子层）；Excel 需宿主 `@oai/artifact-tool` |
| [`soia-dev-archify-diagrams`](./skills/soia-dev-archify-diagrams/) | Archify 图表工作流：架构图 / 数据流 / 工作流 / 时序 / 生命周期图，维护 JSON IR 并导出 README/docs PNG | ✅ 可用（脚本齐全；需本机可用 Archify）| `ARCHIFY_BIN` 或 `ARCHIFY_ROOT`，可选 Playwright/Chrome 导出 PNG |
| [`soia-dev-drawio-visio-diagrams`](./skills/soia-dev-drawio-visio-diagrams/) | 安全盘点 VSDX，转成可编辑 `.drawio` 真源，按受控计划修改页面/文字/样式/几何并导出 PNG/SVG/PDF/JPG | ✅ 可用（stdlib 脚本 + draw.io 30.x 前向验证） | Python 3.10+；转换/渲染需要 draw.io Desktop；MCP 可选 |
| [`soia-dev-github-ops`](./skills/soia-dev-github-ops/) | GitHub 操作工作流：issue / PR / checks / review / run log / release / 协作者权限管理，含 PR 合并前对照仓库自身规则的结构化审查（审查者侧，只出建议不自动合并）和「贴评审 URL 帮我修复」作者侧流程（拉评审→修→push→请求重审，不自动合并），默认走 `gh` 结构化查询和安全确认门 | ✅ 可用（无脚本；命令模板已公共化）| `gh` CLI 已登录；目标 repo 来自 `--repo` / 当前 git remote / `$GITHUB_REPOSITORY`；强依赖 `soia-dev-review-panel`（审查者侧）与 `soia-dev-fix-loop`（作者侧），未安装则停止不降级 |
| [`soia-dev-ai-cli-upgrade`](./skills/soia-dev-ai-cli-upgrade/) | AI/开发 CLI 批量盘点与升级：Codex / Claude / Antigravity (`agy`，消费者 Google 登录后继) / Gemini（仅企业、API Key、Vertex）/ Kimi / Qwen / OpenCode / Cursor / qodercli / mmx | ✅ 可用（脚本齐全；支持 dry-run 和日志）| Node/npm；部分工具使用官方 installer、Homebrew 或自身 updater |
| [`soia-dev-project-scaffold`](./skills/soia-dev-project-scaffold/) | 为新建 Git 项目生成最小 AI 协作基线：可编辑的 `AGENTS.md` + docs 导航目录，写入前确认目标路径 | ✅ 可用（`shells/init-project-baseline.sh` 脚本齐全）| POSIX shell、`mkdir`、`git`（仅检查，不初始化仓库）|
| [`soia-dev-coding-protocol`](./skills/soia-dev-coding-protocol/) | 为工程代码改动建立最小范围、验证前置、anti-fake-fix 与写后复核契约，适用于修复/重构/实现/评审 | ✅ 可用（纯方法论协议，无脚本）| 目标仓库 + 与任务相称的验证手段（测试/lint/类型检查）|
| [`soia-dev-review-panel`](./skills/soia-dev-review-panel/) | 多视角 + 对抗式复核的审查方法论：代码 diff 或技能包都能审，独立视角先各自出候选发现，再逐条尝试推翻，只保留经得住反驳的 | ✅ 可用（纯方法论，无脚本）| 强依赖 `soia-dev-coding-protocol`；可选与 `soia-dev-github-ops` 组合审 PR |
| [`soia-dev-task-execute`](./skills/soia-dev-task-execute/) | 执行任意工程任务的通用闭环：定义边界、最小改动、验证、独立复核与回执 | ✅ 可用（纯方法论闭环，无脚本）| 目标工作区 + 可复现的验证入口 |
| [`soia-dev-fix-loop`](./skills/soia-dev-fix-loop/) | 用五步闭环处理代码审查/测试发现：复现、决策、修复、回归复核与回执 | ✅ 可用（纯方法论闭环，无脚本）| findings + 目标工作区 + 相称的验证入口 |
| [`soia-dev-doc-sync`](./skills/soia-dev-doc-sync/) | 审计并修复任意代码仓 docs/README/CHANGELOG/VERSION 与明确真源之间的事实漂移 | ✅ 可用（纯方法论审计流程，无脚本）| 目标仓库真源的只读访问；可选项目已有 lint/测试/生成器 |
| [`soia-dev-sync-skills`](./skills/soia-dev-sync-skills/) | 将共享技能源以软链接同步到用户明确选择的 AI 工具目录：预览、单项同步、硬依赖闭包、受限清理 | ✅ 可用（`sync_soia_skills.py` 脚本齐全）| Python 3；含 `SKILL.md` 子目录的源目录 |
| [`soia-dev-skill-release`](./skills/soia-dev-skill-release/) | 技能 PR merge 后的发布收尾：安装/更新、旧名清理、Codex 补链、消费者同步、lock 与版本对账 | ✅ 可用（支持 dry-run；六列回执） | Python 3、`npx skills`、`soia-dev-sync-skills` |
| [`soia-dev-prompt-clarity`](./skills/soia-dev-prompt-clarity/) | 中英文提示词技能：从零起草 / 六维诊断优化 / 防误伤改写 / 模糊需求规格化四模式；支持英文原生编写、双语交付和按需精选领域框架 | ✅ 可用（纯方法论输出，无脚本无第三方强依赖）| 无 |
| [`soia-dev-agent-md-advisor`](./skills/soia-dev-agent-md-advisor/) | AGENTS.md / CLAUDE.md / `.claude` 配置设计顾问：审查诊断 / 新项目起草 / 最佳实践问答三模式，六维度体检（长度预算/可执行性/分区路由/重复矛盾/入口一致性/时效）| ✅ 可用（纯方法论诊断，无脚本无强依赖）| 无 |
| [`soia-dev-agent-cli-dispatch`](./skills/soia-dev-agent-cli-dispatch/) | 受控派发任务给外部编码 CLI（codex/agy/gemini/kimi/opencode/qwen 等）：任务边界拆分、防注入 prompt 写法、模型分级矩阵、Anti-Fake-Fix 三步验证 | ✅ 可用（命令模板 + 分级矩阵齐全）| 目标编码 CLI（按需 codex/agy/gemini/kimi/opencode/qwen 等）已安装登录 |
| [`soia-dev-terminal-ops`](./skills/soia-dev-terminal-ops/) | POSIX/macOS/Linux 长任务与 tmux 会话管理：多信号停滞诊断、日志抓取、安全 TERM→复查→KILL | ✅ 可用（纯命令工作流；参数化 session、日志、超时和 fallback） | POSIX shell、`ps`、`kill`；tmux/lsof 按工作流可选 |
| [`soia-dev-design-explorer`](./skills/soia-dev-design-explorer/) | 高保真 HTML 原型、设计变体、deck、动画和设计评审的公共包装层：显式 upstream 路径、用户品牌输入、五分类输出与验证 | ✅ 可用（依赖外部 huashu-design） | `alchaincyf/huashu-design`（MIT，需单独安装） |
| [`soia-dev-open-design-ops`](./skills/soia-dev-open-design-ops/) | Open Design 原子操作层：环境与 daemon、设计系统/项目接入、functional skill/template 查询、HTML/PDF/PPTX/MP4 导出与 session resume | ✅ 可用（stdlib 脚本 + upstream CLI/App） | Open Design checkout；Node 24.x、Corepack、pnpm 10.33.x；私有 `OPEN_DESIGN_HOME` |

Open Design 配置：复制 [`config.example.yml`](./skills/soia-dev-open-design-ops/config.example.yml) 到技能专属私有配置目录，填写 `OPEN_DESIGN_HOME`；本机 checkout、产品 `DESIGN.md` 路径与端口 override 不提交仓库。

百度网盘技能配置：复制 [`config.example.yml`](./skills/soia-pkm-baidu-netdisk-ops/config.example.yml) 到技能专属私有配置目录，在 `provider` 中选择 `official` 或 `community`。社区模式填写百度开放平台的 AppKey、SecretKey、应用名称；不要把密钥提交仓库或发送到聊天。

### 🏢 CWork · 企业协作

`soia-cwork-*` 面向企业日常工作系统，不绑定 Obsidian。它负责连接飞书等协作平台，读取和分析工作文档、云盘、知识库、权限与元数据，也可以把经过授权的工作资料镜像到 Git/Obsidian/VitePress；默认采用只读策略，应用凭据、租户范围和具体授权由使用者配置。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-cwork-feishu-cli`](./skills/soia-cwork-feishu-cli/) | 通过官方 `lark-cli` 以应用凭证（bot）只读盘点飞书云盘、云文档、知识库、评论、权限和元数据 | ✅ 可用（需配置飞书应用凭据并授予目标资源权限） | 飞书官方 `lark-cli`；应用凭证；目标文档/知识库需对应用可见 |
| [`soia-cwork-feishu-doc-git-sync`](./skills/soia-cwork-feishu-doc-git-sync/) | 将飞书知识库按 `node_token` 保留树形结构并增量镜像为 Markdown，接入 Git、Obsidian 与 VitePress；可将明确配置的 Sheet 与多维表格转为 Markdown/保真快照，不默认写回飞书 | ✅ 可用（先执行 dry-run，再建立基线；表格读取需额外授予只读权限并明确范围） | `soia-cwork-feishu-cli`；`lark-cli`；Python 3.10+；PyYAML；Git/VitePress/Obsidian 可选 |
| [`soia-cwork-processon-diagrams`](./skills/soia-cwork-processon-diagrams/) | 复用用户浏览器登录态递归盘点 ProcessOn 到叶子文件，按 VSDX/XMind 默认格式导出，并用可恢复下载队列逐项校验归档 | ✅ 可用（递归、计划、严格串行异步导出、下载进度、同名隔离、阻断证据与本地归档已验证；只有真实可见的安全验证才需用户接管） | ProcessOn 账号与资源权限；浏览器控制；Python 3.10+；draw.io/Visio 技能可选 |
#### 飞书技能最小上手

```bash
npx @larksuite/cli@latest install
npx skills add larksuite/cli -g -y
```

然后复制 [`assets/config.example.yml`](./skills/soia-cwork-feishu-cli/assets/config.example.yml) 到私有配置目录，填写 `LARK_APP_ID` / `LARK_APP_SECRET`。应用必须在飞书开放平台开启机器人能力、申请最小 tenant 只读权限、配置应用数据权限，并发布应用版本后才能稳定读取远端资源。

- 权限事实源：[`references/permissions.yml`](./skills/soia-cwork-feishu-cli/references/permissions.yml)
- 权限申请流程：[`references/permissions.md`](./skills/soia-cwork-feishu-cli/references/permissions.md)
- 权限入口：`https://open.feishu.cn/app/<APP_ID>/auth`
- 默认身份：应用凭证 `tenant_access_token` / bot；不自动切换到 user OAuth
- 默认边界：只读，不创建、编辑、删除、移动、上传或公开分享飞书内容

### soia-cwork-feishu-doc-git-sync

把飞书知识库同步为本地 Markdown，并让同一份内容同时服务 Git 备份、Obsidian 和 VitePress。默认只读方向是“飞书 → 本地”；`10_knowledge-base/` 由同步程序维护，`20_本地补录/` 保留本地新增内容。明确配置 Sheet 范围后可生成 Markdown 表格和公式/样式/图表元数据快照；明确配置的多维表格可生成受记录上限约束的 Markdown 与 JSON 快照。

```text
同步飞书知识库到 Git，并生成 VitePress/Obsidian 可查看的本地镜像
先 dry-run，确认节点数、权限和输出目录，再执行同步
```

配置模板、权限分层、按 ID 增量同步、表格/多维表格镜像和事件边界见 [`soia-cwork-feishu-doc-git-sync`](./skills/soia-cwork-feishu-doc-git-sync/)。表格默认不读取，附件二进制下载须单独确认；工作簿导出仍需另行确认。双向同步需要另行确定文档归属、冲突策略和飞书写权限，不能把只读镜像当作双向同步。

### soia-cwork-processon-diagrams

使用客户已登录的 ProcessOn 浏览器盘点个人/团队空间、读取图表标题与可见内容，并通过官方“浏览/下载”菜单导出。客户在浏览器中手动输入用户名、密码和验证码；技能不保存凭据。下载前从审计 checkpoint 生成计划并初始化 `download-progress.json`；每份下载经校验、原子归档和 manifest 后才 `record`，失败/阻断单列，重启后从 `next` 继续。

```text
盘点这个 ProcessOn 团队空间：<team-url>
把“系统架构”文件夹递归盘点到叶子文件，并把流程图默认导出为 Visio
把浏览器下载的文件校验后归档到配置的交付目录
解析这些 ProcessOn POS 文件并整理图中文字
```

ProcessOn 面向普通账号没有公开的团队文件 REST API；企业 API 服务属于另行购买的嵌入/格式转换能力。格式矩阵、递归完整性、浏览器执行边界、路径配置、下载归档和本地 POS/XMind/VSDX 检查脚本见 [`soia-cwork-processon-diagrams`](./skills/soia-cwork-processon-diagrams/)。VSDX 的深度理解与升级交给 [`soia-dev-drawio-visio-diagrams`](./skills/soia-dev-drawio-visio-diagrams/)。

---

## 高频技能速览

闭环里最常被直接调用的 11 个 skill，逐个给最小可用示例。命令里的路径占位符统一用 `<vault路径>`；实际路径按你本机 vault 位置替换。

### soia-pkm-clip-x

把 X/Twitter 的推文、thread、X Article 一键归档进 Obsidian vault；基于 fxtwitter 公开 API，单条零配置，可选批量同步 Telegram「我的收藏」。

```bash
python3 archive_x.py <推文URL>
python3 archive_x.py <推文URL> --force                    # 覆盖已归档
python3 archive_x.py <推文URL> --vault <vault路径>         # 覆盖环境变量
python3 sync_telegram_export.py <telegram导出json路径> --dry-run   # 预览批量同步
```

**典型输出**：在 vault 文章目录下新增一篇 Markdown，frontmatter 补全作者、发布时间、话题双链、语言标记，`## 我的看法` 留空待补。

### soia-pkm-organize-article-moc

整理 vault 里杂乱的存量收藏——补 frontmatter、按主题建双链归类、重建两级 MOC、按月份归位文件。

```bash
python3 scripts/rebuild_moc.py --vault <vault路径>
python3 scripts/backfill_reading_records.py --vault <vault路径>
```

**典型输出**：终端汇报本次处理了多少篇文章、补齐了哪些 topics、MOC 更新情况、归位了多少个文件。

### soia-pkm-distill-article-opinion

把收藏的文章「炼」成你自己的观点：AI 一次只抛一个问题，你口述回答，AI 只负责把回答整理成通顺的第一人称文字，绝不替你下判断。

```text
给这篇补我的看法
把「Agent 开发」这个主题炼成观点
```

**典型输出**：文章的 `## 我的看法` 段落被写入一段基于你口述整理成文的第一人称观点；主题聚合模式则在草稿目录生成一篇观点综述。

### soia-pkm-compose-article-draft

把 distill 提炼出的观点写成一篇可发布的成文草稿，以你的观点为骨架、vault 里的摘抄为论据。

```text
把这些观点写成一篇
把「X 主题」写成文章
```

**典型输出**：草稿目录下新增一篇带 `tags:[草稿]` frontmatter 的成文 Markdown，附大纲、字数统计与修改建议。

### soia-pkm-publish-wechat-draft

把成文草稿排版成遵守微信平台限制的内联样式 HTML，机械校验通过后推入公众号草稿箱，绝不自动群发。

```bash
python3 scripts/render_wechat.py --file <article.md> --output <out.html>
python3 scripts/validate_wechat_html.py --file <out.html>
python3 scripts/publish.py --article <article.md> --cover <cover.png> --dry-run
python3 scripts/archive.py --article <article.md> --url <发布后的文章链接>
```

**典型输出**：微信公众号后台生成一篇草稿（未群发），终端提示"确认无误后手动群发，群发完成后回来跑 archive 归档"。

### soia-pkm-publish-x-thread

把成文草稿拆成带 `(1/N)` 编号的 X thread 文本，每条不超过 280 字符，保留代码和链接完整性；只产出文本，客户人工复制发布，不接 X API。

### soia-pkm-publish-rednote-card

把成文草稿改写成 rednote（小红书）笔记：吸睛标题、3–5 段短文、话题标签和配图建议；只产出文本，客户人工复制发布，不接平台 API。

### soia-pkm-transform-obsidian-pdf

转化家族按目标产物拆成 4 个独立 skill（2026-07-16 由旧的单一 `soia-pkm-transform` 拆分而成，拆分记录见 [`AGENTS.md`](./AGENTS.md)）：PDF 用本技能，PPT/课件见 [`soia-pkm-transform-article-slides`](./skills/soia-pkm-transform-article-slides/)，长图/信息图/海报见 [`soia-pkm-transform-article-visual`](./skills/soia-pkm-transform-article-visual/)，试卷/闪卡/脑图/播客见 [`soia-pkm-transform-article-notebooklm`](./skills/soia-pkm-transform-article-notebooklm/)。这里只给使用量最大的 PDF 分支做示例，其余 3 个的命令示例见各自 `references/`。

用 Obsidian 原生导出把 vault 内 Markdown 笔记导出为 PDF；vault 外文章降级 pandoc/weasyprint。

```text
把这篇转成 PDF
归档并转 PDF
```

**典型输出**：PDF 落在源文件同目录（或指定输出目录），终端回执含页数、文件大小和 Obsidian 导出器（`Creator: Chromium / Producer: Skia/PDF`）验证结果；缺 Obsidian 时提示 pandoc/weasyprint 降级命令。

### soia-pkm-library-weread-sync

同步微信读书书架与划线，并通过微信读书 API 补单本书详情；3 个机械脚本幂等、可重复跑。

```bash
python3 sync_weread_to_library.py --vault <vault路径>
python3 sync_weread_highlights.py --all
python3 enrich_book_details.py <书名>
```

**典型输出**：终端汇报新增/更新书卡、阅读记录、划线或详情阶段的成功/跳过/失败数，并建议交给 book-catalog 生成本地总览。

### soia-pkm-library-book-catalog

纯本地、幂等、可重复运行地维护书目视图和阅读记录，不调用微信读书 API。

```bash
python3 backfill_reading_records.py --vault <vault路径>
python3 gen_library_md.py --vault <vault路径>
python3 gen_records_md.py --vault <vault路径>
python3 gen_genre_library_md.py --vault <vault路径> --base <书库相对路径>
```

**典型输出**：终端汇报补建记录和三份总览的扫描/创建/跳过/失败数；可用 `--output <预览路径>` 先预览，不覆盖 vault 原文件。

### soia-cwork-feishu-cli

以应用凭证和 bot 身份只读调研飞书 Wiki、云盘和工作文档。首次使用时，技能会先按目标提醒需要申请的最小权限，并检查应用是否已经发布、bot 是否能看到目标资源。

```text
调研飞书云盘和知识库，先提醒我需要开通哪些权限
读取这个飞书 Wiki：<wiki-url>
盘点我可见的飞书知识空间和节点层级，不要修改远端内容
```

**重要边界**：应用权限通过不等于 bot 自动获得所有资源；文档所有者或知识库管理员可能还要把应用加入协作者或授权可见范围。权限错误应优先按 CLI 返回的 `missing_scopes` 和 `console_url` 补申请，不要扩大到写权限。

---

## 🔀 PR 协作闭环（审查 → 修复 → 合并）

团队里"有人提 PR、有人审、审完让作者改、改完再合"这条链路，由三个开发技能配套支撑，**全程 AI 不替任何人做"合并"这个终局决定**——合不合始终是审查者一条独立消息里的显式指令。

### 一句话闭环

```
审查者说"审核这个 PR"
  → AI 多视角 + 对抗式复核出分档建议（决定权在审查者）
  → 审查者说"发到 PR 上" → AI 发成 PR 评审意见
  → 作者贴评审 URL 说"帮我修复"
  → AI 拉意见 + 逐条修 + push + 请求重审
  → 审查者再审 → 审查者说"合并" → AI 合并
```

### 三个角色怎么用

| 角色 | 说什么 | 背后技能 | 产出 |
|---|---|---|---|
| **审查者** 审 PR | 「审核这个 PR 该不该合 <PR URL>」 | `soia-dev-github-ops`（审查者侧）+ `soia-dev-review-panel` | 一句话结论 + 按 🔴阻断/🟡应改分档、带证据等级的发现清单；**只出建议不自动合并** |
| **审查者** 回复意见 | 「把这些意见发到 PR 上」 | `soia-dev-github-ops` | `gh pr review --request-changes` / `gh pr comment`，作者收到带文件行号的评审 |
| **作者** 修复 | 「帮我修复这个 PR <评审 URL>」 | `soia-dev-github-ops`（作者侧）+ `soia-dev-fix-loop` | 拉评审（正文+行内+会话评论三端点）→ checkout → 逐条 fix/reject/defer → push → 请求重审；**作者侧同样绝不自动合并** |
| **审查者** 合并 | 「合并」（看完发现后的下一条消息） | `soia-dev-github-ops` | `gh pr merge`，CI 绿 + 显式确认后才执行 |

### 三条硬规则

- **建议 ≠ 合并**：审查产出永远是建议；即使同一句话预授权了合并，AI 也会先把分档发现摆出来，等下一条消息才合。
- **作者不合自己被 `CHANGES_REQUESTED` 的 PR**：即使作者有 write/admin 权限，合并仍是审查者的决定。
- **每条意见都有交代**：作者侧对每条评审意见必须给出 fix / reject（带反驳证据）/ defer（带后续位置）之一，不静默跳过。

### 安装（作者和审查者都装这一条即可）

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-github-ops -y
```

会自动带上硬依赖 `soia-dev-review-panel`（审查者侧多视角复核）与 `soia-dev-fix-loop`（作者侧修复引擎）。技能宿主无关，Codex / Gemini CLI / Claude Code 等都能用。

---

## 安装

```bash
npx skills add soia-team/soia-open-skills
```

会把 `skills/` 下所有 skill 装到你 agent 的目录，**跨 agent 通用**（Claude Code / Codex / Cursor / Antigravity / Gemini / Kimi …）。装后直接说：

| 你说 | 触发 |
|------|------|
| `归档这条 X：<URL>` | clip-x |
| `归档这个项目 <github url>` | clip-repo |
| `整理文章库` / `重建 MOC` | organize |
| `给这篇补我的看法` | distill |
| `把这些观点写成一篇` | compose |
| `转换文章为 PPT` / `把这篇转成脑图` | transform |
| `把这篇发成公众号` | publish |
| `从零搭个知识库` | soia-pkm-bootstrap-vault-base |
| `配置 Obsidian` / `启用 Bases` | soia-pkm-bootstrap-vault-obsidian |
| `接入 ima` / `同步到 ima 知识库` | soia-pkm-bootstrap-vault-ima |
| `给 README 画一张架构图` / `用 Archify 重画流程图` | soia-dev-archify-diagrams |
| `读懂这个 VSDX` / `把 Visio 转成 draw.io 并升级` | soia-dev-drawio-visio-diagrams |
| `查这个 PR checks` / `看最近 GitHub Actions 失败原因` / `给 xxx 加协作者权限` / `审核这个 PR 该不该合` / `帮我修复这个 PR`（贴评审 URL）| soia-dev-github-ops |
| `多角度审一下这个改动` / `用几个视角复查` / `对抗式复核一下` / `审一下这个技能包` | soia-dev-review-panel |
| `升级本机 AI CLI` / `dry-run 看 codex/claude 版本` | soia-dev-ai-cli-upgrade |
| `监控这个长任务` / `判断进程是否真的卡住` | soia-dev-terminal-ops |
| `做高保真 HTML 原型` / `评审这个视觉方向` | soia-dev-design-explorer |
| `启动 Open Design daemon` / `把这个 deck 导出 PPTX` | soia-dev-open-design-ops |
| `调研飞书云盘/知识库` / `读取飞书工作文档` | soia-cwork-feishu-cli |
| `同步飞书知识库到 Git/Obsidian/VitePress` | soia-cwork-feishu-doc-git-sync |
| `递归盘点 ProcessOn 团队空间` / `默认导出 ProcessOn Visio` | soia-cwork-processon-diagrams |

Antigravity CLI 的命令是 `agy`：全局技能目录为
`~/.gemini/antigravity-cli/skills/`，workspace 技能目录为 `.agents/skills/`。
消费者 Google OAuth 从 Gemini CLI 迁到 Antigravity；Gemini 企业、API Key、
Vertex AI 通道仍保留，不能用 alias 把 `gemini` 静默替换成 `agy`。

### 配置 vault 路径

```yaml
# ~/.config/soia-skills/soia-open-skills/<skill-type>/<skill-name>/config.yml
env:
  OBSIDIAN_VAULT: "<vault-path>"
  OBSIDIAN_ARTICLES: "<vault-relative-articles-dir>"
```

### 配置飞书应用凭证

飞书凭证只放在技能专属私有配置中，不提交仓库、不写入 vault，也不要放进命令行参数或聊天：

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-feishu-cli/config.yml
```

配置模板和权限申请步骤见 [`soia-cwork-feishu-cli`](./skills/soia-cwork-feishu-cli/)。

知识库镜像同步使用独立配置：

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-feishu-doc-git-sync/config.yml
```

不要把企业知识库 URL、节点 token 或应用密钥提交到公开 skill 仓库。

或每次调脚本时用 `--vault` 覆盖。每个 skill 只读自己的 skill-specific 配置目录，避免多个技能共享一个大配置文件。

---

## Telegram 我的收藏同步（clip-x）

`clip-x` 的杀手锏：把手机随手转发到 Telegram「我的收藏」的 X 链接，一行命令批量归档。

**推荐路径：JSON 导出**（合规、零风控、不需 API 凭证）

1. Telegram Desktop → Settings → Advanced → Export Telegram data → 勾「私聊」+ 选 **Machine-readable JSON** → 导出。
2. 得到 `result.json`。
3. 跑同步（自动 URL 去重，已归档的跳过）：

```bash
python3 ~/.claude/skills/soia-pkm-clip-x/scripts/sync_telegram_export.py \
  "$HOME/Downloads/Telegram Desktop/ChatExport_XXXX/result.json" --dry-run   # 预览
python3 ~/.claude/skills/soia-pkm-clip-x/scripts/sync_telegram_export.py \
  "<path>"                                                                     # 实跑
```

高阶的 MTProto API 路径（国内不推荐，有风控）见 [clip-x 的 SKILL.md](./skills/soia-pkm-clip-x/SKILL.md)。

---

## 设计哲学

1. **收藏 ≠ 吸收**：闭环的命脉是 `distill`——把别人的文章变成**你自己的**判断。收藏一万条不如吸收一条。
2. **观点是你的，AI 只落字**：`distill` / `compose` 绝不替你编造观点，缺料就问。产出的是你的作品，不是 AI 的总结。
3. **Vault 不分子目录，靠多维索引**：文章按年扁平存放，主题聚合靠 frontmatter `topics:[[]]` + `_MOC/` + [Bases](https://help.obsidian.md/bases)，不靠文件夹。
4. **机器层 + AI 层双轨**：脚本管拉取 / 去重 / 规范化（机器段），LLM 管摘要 / 判主题 / 提炼（用户段），用段标题合同字符串通信，互不覆盖。
5. **职责单一、可组合**：每个 skill 只做一件事，串成闭环；扩展靠新建 skill + 依赖声明，**不改第三方 skill**（`npx skills check` 会覆盖）。
6. **跨 agent**：一次写 `SKILL.md`，所有支持 skills 标准的 AI 都能用。

---

## 命名规范

命名使用 `<domain>-<对象>` 的全小写 kebab-case：

- `soia-pkm-*`：个人知识管理，围绕 Obsidian vault 的收集、整理、提炼、成文与发布。
- `soia-cwork-*`：企业协作，连接飞书等工作系统，处理工作文档、云盘、知识库和协作元数据。
- `soia-dev-*`：可公开复用的开发与工程工具。
- `soia-design-*` / `soia-gov-*` / `soia-meta-*`：设计、治理和元技能域。

## 仓库结构

```
soia-open-skills/
├── AGENTS.md
├── README.md
├── LICENSE · CONTRIBUTING.md
├── SKILL_SPEC.md              ← public skill 规范
├── scripts/audit_skills.py    ← 本仓库技能审计
├── scripts/generate_skill_catalog.py ← 生成 skills/README.md 与可选 registry JSON
├── templates/skill-template/  ← 新 skill 起手模板
└── skills/                    ← npx skills 扫描此目录
    ├── README.md              ← 从 SKILL.md / agents/openai.yaml 生成的技能总目录
    ├── soia-cwork-feishu-cli/
    ├── soia-cwork-feishu-doc-git-sync/
    ├── soia-cwork-processon-diagrams/
    ├── soia-dev-agent-cli-dispatch/
    ├── soia-dev-agent-md-advisor/
    ├── soia-dev-ai-cli-upgrade/
    ├── soia-dev-archify-diagrams/
    ├── soia-dev-coding-protocol/
    ├── soia-dev-design-explorer/
    ├── soia-dev-doc-sync/
    ├── soia-dev-drawio-visio-diagrams/
    ├── soia-dev-fix-loop/
    ├── soia-dev-github-ops/
    ├── soia-dev-open-design-ops/
    ├── soia-dev-project-scaffold/
    ├── soia-dev-prompt-clarity/
    ├── soia-dev-review-panel/
    ├── soia-dev-skill-release/
    ├── soia-dev-sync-skills/
    ├── soia-dev-task-execute/
    ├── soia-dev-terminal-ops/
    ├── soia-pkm-alipan-curator/
    ├── soia-pkm-alipan-drive-ops/
    ├── soia-pkm-baidu-netdisk-ops/
    ├── soia-pkm-bootstrap-vault-base/
    ├── soia-pkm-bootstrap-vault-ima/
    ├── soia-pkm-bootstrap-vault-obsidian/
    ├── soia-pkm-clip-douyin/
    ├── soia-pkm-clip-drive/
    ├── soia-pkm-clip-github-repo/
    ├── soia-pkm-clip-rednote/
    ├── soia-pkm-clip-web/
    ├── soia-pkm-clip-wechat-account/
    ├── soia-pkm-clip-wechat-article/
    ├── soia-pkm-clip-x/
    ├── soia-pkm-compose-article-draft/
    ├── soia-pkm-cover-image/
    ├── soia-pkm-distill-article-opinion/
    ├── soia-pkm-interpret-article-analysis/
    ├── soia-pkm-library-book-catalog/
    ├── soia-pkm-library-weread-sync/
    ├── soia-pkm-maintain/
    ├── soia-pkm-organize-article-moc/
    ├── soia-pkm-publish-rednote-card/
    ├── soia-pkm-publish-wechat-draft/
    ├── soia-pkm-publish-x-article/
    ├── soia-pkm-publish-x-thread/
    ├── soia-pkm-reading-plan/
    ├── soia-pkm-transform-article-notebooklm/
    ├── soia-pkm-transform-article-slides/
    ├── soia-pkm-transform-article-visual/
    ├── soia-pkm-transform-obsidian-pdf/
    └── soia-pkm-translate-article-zh/
```

每个 skill 一个文件夹，独立 `SKILL.md`（frontmatter 含 `name` + `description`）+ 自己的 `scripts/`。
公开仓不使用 `metadata.json`；需要展示给 agent/UI 的补充信息放 `agents/openai.yaml`。

### `agents/openai.yaml` 谁会用？

`SKILL.md` 是所有 AI 的权威入口：能力说明、依赖、配置、安装步骤、运行流程、日志要求、完成总结都必须写在这里。
`agents/openai.yaml` 只是可选的展示 / 发现元数据，不能承载只有某个 AI 才能看到的必需流程。

| 使用方 | 如何使用 |
|---|---|
| Claude Code | 读取已安装 skill 目录里的 `SKILL.md`。它不直接依赖 `agents/openai.yaml`，所以强依赖、安装步骤、缺 key 提示必须写进 `SKILL.md`。 |
| Codex / OpenAI 类界面 | 读取 `SKILL.md` 执行；可用 `agents/openai.yaml` 的 `display_name`、`short_description`、`default_prompt` 做更友好的搜索、列表和默认提示。 |
| SOIA | 以 `SKILL.md` 为准；需要 v7 registry 时运行 `python3 scripts/generate_skill_catalog.py --registry-out <soia-repo>/runtime/registry/skills`，生成器会合并 `SKILL.md` 与可选 `agents/openai.yaml`。 |
| 其他 skills.sh 兼容 AI | 默认只假设能读 `SKILL.md`。如果某个 AI 确实需要专属元数据，再新增 `agents/<agent>.yaml` 并在这里说明消费方。 |

维护规则：必需指令不得只写在 `agents/openai.yaml`；修改 `SKILL.md` 或 `agents/openai.yaml` 后，重新运行 `python3 scripts/generate_skill_catalog.py`。

新增 skill 先复制模板：

```bash
cp -R templates/skill-template skills/your-skill-name
mv skills/your-skill-name/SKILL.md.template skills/your-skill-name/SKILL.md
python3 scripts/generate_skill_catalog.py
python3 scripts/audit_skills.py
```

---

## 致谢与相关项目

配合使用的第三方 skill（本仓库只声明关系，不修改其文件；`npx skills check` 可能覆盖第三方本地修改）：

| 第三方 skill | 上游 | 本仓库关系 |
|---|---|---|
| `weread-skills` | [Tencent/WeChatReading](https://github.com/Tencent/WeChatReading) | `soia-pkm-library-weread-sync` 微信读书同步与详情脚本的**强依赖**；`soia-pkm-reading-plan` 的可选数据增强 |
| `huashu-weread-advisor` | [alchaincyf/huashu-weread](https://github.com/alchaincyf/huashu-weread) | `soia-pkm-reading-plan` 可选复用其选书/推荐方法论；`soia-pkm-distill-article-opinion` 只参考 alchemy 方法，不运行依赖 |
| `huashu-design` | [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | `soia-dev-design-explorer` 的外部强依赖；需单独安装，当前上游采用 MIT |
| `book-to-skill` | [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 非运行依赖；用于把书籍/文档转成 skill 的独立工具 |
| `find-skills` | [vercel-labs/skills](https://github.com/vercel-labs/skills) | 非运行依赖；用于发现/安装 skill 的辅助工具 |

完整的第三方引用清单（接口口径参考 / 运行时 CLI·库·skill / 在线 API 服务，含协议快照与维护规则）见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。

## 贡献

欢迎 PR / issue。加 skill 请：① 先读 [SKILL_SPEC.md](./SKILL_SPEC.md) ② 从 [templates/skill-template](./templates/skill-template/) 复制 ③ 放 `skills/<name>/` ④ 有 `SKILL.md`（仅 `name` + `description`，description 尽量 ≤200 字）⑤ 路径 / key / 个人数据全用 CLI 参数、环境变量或 skill-specific `config.yml`，严禁硬编码 ⑥ 跑 `python3 scripts/generate_skill_catalog.py && python3 scripts/audit_skills.py` ⑦ 至少 1 个端到端用例。详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## License

[MIT](./LICENSE) — 自由 fork、改造、商用，请保留 attribution。第三方引用声明见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。

## 维护者

**soia-team** · [GitHub](https://github.com/soia-team)
