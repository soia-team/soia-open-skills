<div align="center">

# soia-open-skills

中文 | [English](README.en.md)

> *把「收藏」变成「作品」——AI 时代的个人知识管理技能体系。*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

<br>

**面向 Obsidian 的 `soia-pkm-*` 技能集 + 可公开复用的 `soia-dev-*` 开发 helper**

```bash
npx skills add soia-team/soia-open-skills
```

跨 agent 通用——Claude Code、Cursor、Codex、Antigravity、Gemini、Kimi 都能装。

[闭环框架](#pkm-闭环一篇内容的一生) · [Skills 清单](#skills-清单) · [高频技能速览](#高频技能速览) · [安装](#安装) · [Telegram 同步](#telegram-我的收藏同步clip-x) · [设计哲学](#设计哲学)

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

  支撑：soia-pkm-bootstrap（一句话从零搭 vault + 接入多 AI）
        soia-pkm-transform（转化线：文章 → PDF/PPT/图片/试卷/脑图/播客/闪卡）
        soia-pkm-reading-plan（读书线：把书单排成可执行阅读计划）
        soia-pkm-library（书库线：微信读书同步 + 记录补齐 + 总览生成）
        soia-pkm-alipan（云盘线·原子层：aliyunpan CLI 可靠原子操作）
        soia-pkm-alipan-curator（云盘线·顾问层：盘点/整理/索引/学习计划）
        soia-dev-archify-diagrams（文档图表线：Archify JSON IR → README/docs PNG 图）
        soia-dev-github-ops / soia-dev-ai-cli-upgrade（公共开发工具线）
```

**核心理念**：收藏 ≠ 吸收。大多数人的知识库是"信息坟场"——囤了一大堆，从不回看。`soia-pkm` 把「收藏 → 观点 → 成文 → 发布」这条**从消费到创造**的链路，拆成职责单一、可组合的 skill，让 AI 帮你把囤积的信息真正变成**你自己的**作品。

---

## Skills 清单

> **通用能力（所有 skill 共享）**
> - 🤖 **支持的 AI**：跨 agent 通用——Claude Code、Codex、Cursor、Antigravity、Gemini、Kimi、amp、Warp、Zed 等所有兼容 [skills.sh](https://skills.sh) 标准的 AI。一次写 `SKILL.md`，处处可用。
> - 📚 **适用知识库**：Obsidian vault（推荐 PARA 结构；没有现成的？用 `bootstrap` 一键搭）。底层是纯 Markdown + YAML frontmatter，不锁定平台。
> - 🔗 **依赖链**：`clip-*` 是入口（独立可用）→ `organize` / `distill` 需 vault 里有内容 → `compose` 需 distill 的观点 → `publish` 需 compose 的草稿。
> - 🧩 **第三方 skill 口径**：只在本仓库自建 skill 里声明依赖 / 可选增强 / 方法参考，**不改第三方 skill 文件**；具体来源以 `~/.agents/.skill-lock.json` 为准。
> - **状态图例**：✅ 可直接用 · 🟡 可用但需补脚本 / 配凭据

### 📥 收集 · clip 家族

核心价值：把分散在各平台的内容一键收进 vault，是整条闭环的入口——没有稳定的收，后面的整理、提炼、成文都无从谈起。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-clip-x`](./skills/soia-pkm-clip-x/) | X 推文/thread/长文 → vault | ✅ 完全可用（脚本齐全，已多次实测）| 无（Telegram 同步可选）|
| [`soia-pkm-clip-wechat`](./skills/soia-pkm-clip-wechat/) | 公众号文章 → vault | ✅ 可用（stdlib 抓取、质量门、URL 去重、dry-run、原子写） | 无 |
| [`soia-pkm-clip-web`](./skills/soia-pkm-clip-web/) | 通用网页/博客 → vault | 🟡 SKILL.md 已就绪，抓取脚本待实现 | Python `trafilatura` |
| [`soia-pkm-clip-drive`](./skills/soia-pkm-clip-drive/) | 云盘 PDF/Word → vault | 🟡 SKILL.md 已就绪，导入脚本待实现 | Python `pypdf`/`python-docx` |
| [`soia-pkm-clip-repo`](./skills/soia-pkm-clip-repo/) | GitHub 开源项目仓库 → vault「开源项目图书馆」索引 | ✅ 可用（脚本齐全：单仓归档 + 批量刷新）| 无（需本机一个 upstream clone 目录）|
| [`soia-pkm-clip-gzh`](./skills/soia-pkm-clip-gzh/) | 自己管理的公众号已发文章批量 → vault | ✅ 可用（官方 API / 登录态 Cookie 两条路线）| 微信公众号开发凭据或登录态 Cookie |

### 🗂️ 整理

核心价值：把杂乱的存量收藏转成有结构、可检索、能聚合复用的知识——收藏不等于吸收，整理是激活的第一步。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-organize`](./skills/soia-pkm-organize/) | 分类/补 frontmatter/建两级 MOC/按月归位/补双链 | ✅ 可用（底层脚本 rebuild_moc/backfill 已在用）| vault 里已有归档内容 |

### ✍️ 提炼 → 成文 → 发布

核心价值：闭环里真正的价值转化环节——把别人的信息变成你自己的判断，再把判断写成可发布的作品，这是从"消费"到"创造"的分水岭。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-translate`](./skills/soia-pkm-translate/) | **外文文章 → 中文版**：quick 直译 / normal 先分析文体术语受众再译（默认）/ refined 加审校+润色；长文机械分块保术语一致；产出独立 `-中文版.md`，绝不覆盖原文 | ✅ 可用（三模式 + 分块脚本齐全）| Python 3（强依赖，跑分块脚本）；PyYAML 可选增强 |
| [`soia-pkm-interpret`](./skills/soia-pkm-interpret/) | **收藏 → AI 解读**：内容总览/核心要点/关键启发/批判视角/延伸阅读五段式，帮你在 `distill` 深挖前先判断值不值得读；产出独立 `-AI解读.md`，不碰原文「我的看法」| ✅ 可用（纯 LLM 解读，无需脚本）| 无强依赖（`clip-*` 系列为常见上游）|
| [`soia-pkm-distill`](./skills/soia-pkm-distill/) | **收藏 → 观点**：读原文 → 一次一问 → 你答 → 「我的看法」（内容是你的，AI 只落字）| ✅ 完全可用（已实战）| vault 里有文章（`clip-*` 产出）|
| [`soia-pkm-compose`](./skills/soia-pkm-compose/) | **观点 → 文章草稿**（你的观点为骨、摘抄为料）| ✅ 可用（纯 LLM，无需脚本）| `distill` 产出的观点 |
| [`soia-pkm-cover-image`](./skills/soia-pkm-cover-image/) | 为公众号/X/小红书文章生成封面图（五维参数：type/palette/rendering/text/mood），产出接 `publish --cover` | ✅ 可用（后端为 codex CLI 内置生图；未装/未登录会停止并提示，绝不降级）| codex CLI（`codex exec`，需登录）|
| [`soia-pkm-publish`](./skills/soia-pkm-publish/) | **一稿 → 多平台**：公众号排版+推草稿箱 / X thread / 小红书 | 🟡 渲染 `render.py` 可用；微信推送需配私有 `config.yml` 凭据 | `compose` 的草稿 + 微信公众号 API |

### 🔁 转化 · 文章 → 产物

核心价值：让同一篇内容适配不同消费场景——同一份素材一次输入，按需路由到 PDF、PPT、长图、播客等多种媒介产出。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-transform`](./skills/soia-pkm-transform/) | **文章 → 多产物**：PDF / PPT / 图片长图 / 试卷 / 脑图 / 播客 / 闪卡 / 报告；公共路由层，可选调用 Obsidian、NotebookLM、Codex 内置文档/图片/PPT 能力与 `publish` | ✅ 可用（路由 skill + 配置模板；具体产物取决于本机 provider） | vault 文章或 URL；NotebookLM / Obsidian / Codex 内置能力按需可选 |

### 🧰 支撑

核心价值：维护闭环运转所需的基础设施——初始化 vault、维护书库、管理云盘、日常维护和开发工具链，不在闭环主链路上，却是全局能跑起来的地基。

| skill | 说明 | 现在能用? | 依赖 |
|-------|------|----------|------|
| [`soia-pkm-bootstrap`](./skills/soia-pkm-bootstrap/) | 从零初始化 AI-native vault（PARA + AGENTS + 模板 + Bases + CSS + 多 AI 接入）| ✅ 可用（`init_vault.py` 跑通）| 无（它是起点）|
| [`soia-pkm-reading-plan`](./skills/soia-pkm-reading-plan/) | 场景化阅读计划（书单/主题 → 按真实字数排期）| ✅ 可用 | `weread-skills` 可选增强真实字数/评分；`huashu-weread-advisor` 可选复用推荐方法论；无第三方强依赖 |
| [`soia-pkm-library`](./skills/soia-pkm-library/) | 维护书库：微信读书同步（书目/划线）+ 补书详情 + 补待读记录 + 生成图书馆/阅读记录/分类三份总览 | ✅ 可用（7 个机械脚本，幂等可重复跑）| 同步类脚本强依赖官方 `weread-skills` + `WEREAD_API_KEY`；本地总览脚本只依赖 vault |
| [`soia-pkm-maintain`](./skills/soia-pkm-maintain/) | vault 周维护、全库地图重生成、AI 会话日志接入 | ✅ 可用（Python stdlib / bash 脚本）| Obsidian vault，`--vault <path>` 或 `OBSIDIAN_VAULT` |
| [`soia-pkm-alipan`](./skills/soia-pkm-alipan/) | 阿里云盘原子操作层：登录/双盘切换/浏览/移动/重命名/上传下载/容量查询，含输出解析与安全守则 | ✅ 可用（无需脚本，直接驱动 `aliyunpan` CLI）| `aliyunpan` CLI（brew 安装 + 扫码登录）|
| [`soia-pkm-alipan-curator`](./skills/soia-pkm-alipan-curator/) | 云盘资源顾问：盘点核对（inventory）/规范整理（organize）/索引落 OB（catalog）/孩子学习计划（plan）| ✅ 可用（纯方法论层，命令全走 alipan）| `soia-pkm-alipan`（原子层）|
| [`soia-dev-archify-diagrams`](./skills/soia-dev-archify-diagrams/) | Archify 图表工作流：架构图 / 数据流 / 工作流 / 时序 / 生命周期图，维护 JSON IR 并导出 README/docs PNG | ✅ 可用（脚本齐全；需本机可用 Archify）| `ARCHIFY_BIN` 或 `ARCHIFY_ROOT`，可选 Playwright/Chrome 导出 PNG |
| [`soia-dev-github-ops`](./skills/soia-dev-github-ops/) | GitHub 操作工作流：issue / PR / checks / review / run log / release，默认走 `gh` 结构化查询和安全确认门 | ✅ 可用（无脚本；命令模板已公共化）| `gh` CLI 已登录；目标 repo 来自 `--repo` / 当前 git remote / `$GITHUB_REPOSITORY` |
| [`soia-dev-ai-cli-upgrade`](./skills/soia-dev-ai-cli-upgrade/) | AI/开发 CLI 批量盘点与升级：Codex / Claude / Antigravity (`agy`，消费者 Google 登录后继) / Gemini（仅企业、API Key、Vertex）/ Kimi / Qwen / OpenCode / Cursor / qodercli / mmx | ✅ 可用（脚本齐全；支持 dry-run 和日志）| Node/npm；部分工具使用官方 installer、Homebrew 或自身 updater |
| [`soia-dev-prompt-clarity`](./skills/soia-dev-prompt-clarity/) | 通用提示词技能：从零七要素起草 / 六维诊断优化 / 防误伤改写 / 模糊需求扩展成可验证规格 四模式，信息不足先澄清再产出 | ✅ 可用（纯方法论输出，无脚本无第三方强依赖）| 无 |
| [`soia-dev-agent-md-advisor`](./skills/soia-dev-agent-md-advisor/) | AGENTS.md / CLAUDE.md / `.claude` 配置设计顾问：审查诊断 / 新项目起草 / 最佳实践问答三模式，六维度体检（长度预算/可执行性/分区路由/重复矛盾/入口一致性/时效）| ✅ 可用（纯方法论诊断，无脚本无强依赖）| 无 |
| [`soia-dev-agent-cli-dispatch`](./skills/soia-dev-agent-cli-dispatch/) | 受控派发任务给外部编码 CLI（codex/agy/gemini/kimi/opencode/qwen 等）：任务边界拆分、防注入 prompt 写法、模型分级矩阵、Anti-Fake-Fix 三步验证 | ✅ 可用（命令模板 + 分级矩阵齐全）| 目标编码 CLI（按需 codex/agy/gemini/kimi/opencode/qwen 等）已安装登录 |

---

## 高频技能速览

闭环里最常被直接调用的 7 个 skill，逐个给最小可用示例。命令里的路径占位符统一用 `<vault路径>`；实际路径按你本机 vault 位置替换。

### soia-pkm-clip-x

把 X/Twitter 的推文、thread、X Article 一键归档进 Obsidian vault；基于 fxtwitter 公开 API，单条零配置，可选批量同步 Telegram「我的收藏」。

```bash
python3 archive_x.py <推文URL>
python3 archive_x.py <推文URL> --force                    # 覆盖已归档
python3 archive_x.py <推文URL> --vault <vault路径>         # 覆盖环境变量
python3 sync_telegram_export.py <telegram导出json路径> --dry-run   # 预览批量同步
```

**典型输出**：在 vault 文章目录下新增一篇 Markdown，frontmatter 补全作者、发布时间、话题双链、语言标记，`## 我的看法` 留空待补。

### soia-pkm-organize

整理 vault 里杂乱的存量收藏——补 frontmatter、按主题建双链归类、重建两级 MOC、按月份归位文件。

```bash
python3 scripts/rebuild_moc.py --vault <vault路径>
python3 scripts/backfill_reading_records.py --vault <vault路径>
```

**典型输出**：终端汇报本次处理了多少篇文章、补齐了哪些 topics、MOC 更新情况、归位了多少个文件。

### soia-pkm-distill

把收藏的文章「炼」成你自己的观点：AI 一次只抛一个问题，你口述回答，AI 只负责把回答整理成通顺的第一人称文字，绝不替你下判断。

```text
给这篇补我的看法
把「Agent 开发」这个主题炼成观点
```

**典型输出**：文章的 `## 我的看法` 段落被写入一段基于你口述整理成文的第一人称观点；主题聚合模式则在草稿目录生成一篇观点综述。

### soia-pkm-compose

把 distill 提炼出的观点写成一篇可发布的成文草稿，以你的观点为骨架、vault 里的摘抄为论据。

```text
把这些观点写成一篇
把「X 主题」写成文章
```

**典型输出**：草稿目录下新增一篇带 `tags:[草稿]` frontmatter 的成文 Markdown，附大纲、字数统计与修改建议。

### soia-pkm-publish

把成文草稿适配并发布到多平台——公众号排版推草稿箱、X thread、小红书卡片；公众号是主流程，渲染成遵守微信平台限制的内联样式 HTML，机械校验通过后才建草稿，绝不自动群发。

```bash
python3 scripts/render_wechat.py --file <article.md> --output <out.html>
python3 scripts/validate_wechat_html.py --file <out.html>
python3 scripts/publish.py --article <article.md> --cover <cover.png> --dry-run
python3 scripts/archive.py --article <article.md> --url <发布后的文章链接>
```

**典型输出**：微信公众号后台生成一篇草稿（未群发），终端提示"确认无误后手动群发，群发完成后回来跑 archive 归档"。

### soia-pkm-transform

把文章转换成 PDF、PPT、长图、试卷、脑图、播客、闪卡、报告等多种产物的公共路由层，按目标格式自动路由到不同 provider（Obsidian 原生导出、NotebookLM、Open Design 等）。

```bash
python3 scripts/resolve_route.py --target ppt --provider notebooklm --json
python3 scripts/notebooklm_artifact_matrix.py --article <article.md> --out-dir <输出目录> --targets all --run --json
python3 scripts/validate_artifact_quality.py --article <article.md> --out-dir <输出目录> --strict --json
```

**典型输出**：在指定输出目录生成对应格式的产物文件，并附验收报告（页数、覆盖度、是否可打开可解析）。

### soia-pkm-library

维护 Obsidian 书库：同步微信读书书架与划线、补单本书详情、补待读记录、重新生成图书馆/阅读记录/分类三份总览；7 个机械脚本全部幂等、可重复跑。

```bash
python3 sync_weread_to_library.py --vault <vault路径>
python3 sync_weread_highlights.py --all
python3 backfill_reading_records.py
python3 gen_library_md.py
python3 gen_records_md.py
```

**典型输出**：终端汇报新增书卡数、新增阅读记录数、失败数，并给出下一步建议（如重新生成总览、同步划线）。

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
| `从零搭个知识库` | bootstrap |
| `给 README 画一张架构图` / `用 Archify 重画流程图` | soia-dev-archify-diagrams |
| `查这个 PR checks` / `看最近 GitHub Actions 失败原因` | soia-dev-github-ops |
| `升级本机 AI CLI` / `dry-run 看 codex/claude 版本` | soia-dev-ai-cli-upgrade |

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

`soia-pkm-<环节>-<对象>`，全小写 kebab-case。`soia-pkm-*` 是 SOIA 技能体系的第四个域（与 `soia-design-*` / `soia-dev-*` / `soia-gov-*` 平级），专管个人知识管理。

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
    ├── soia-pkm-clip-x/       ├── soia-pkm-clip-wechat/
    ├── soia-pkm-clip-gzh/     ├── soia-pkm-clip-web/
    ├── soia-pkm-clip-drive/   ├── soia-pkm-clip-repo/
    ├── soia-pkm-organize/     ├── soia-pkm-distill/
    ├── soia-pkm-compose/      ├── soia-pkm-publish/
    ├── soia-pkm-transform/    ├── soia-pkm-bootstrap/
    ├── soia-pkm-reading-plan/ ├── soia-pkm-library/
    ├── soia-pkm-maintain/     ├── soia-pkm-alipan/
    ├── soia-pkm-alipan-curator/
    ├── soia-pkm-translate/    ├── soia-pkm-interpret/
    ├── soia-pkm-cover-image/
    ├── soia-dev-archify-diagrams/
    ├── soia-dev-github-ops/
    ├── soia-dev-ai-cli-upgrade/
    ├── soia-dev-prompt-clarity/
    ├── soia-dev-agent-md-advisor/
    └── soia-dev-agent-cli-dispatch/
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
| `weread-skills` | [Tencent/WeChatReading](https://github.com/Tencent/WeChatReading) | `soia-pkm-library` 微信读书同步类脚本的**强依赖**；`soia-pkm-reading-plan` 的可选数据增强 |
| `huashu-weread-advisor` | [alchaincyf/huashu-weread](https://github.com/alchaincyf/huashu-weread) | `soia-pkm-reading-plan` 可选复用其选书/推荐方法论；`soia-pkm-distill` 只参考 alchemy 方法，不运行依赖 |
| `book-to-skill` | [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 非运行依赖；用于把书籍/文档转成 skill 的独立工具 |
| `find-skills` | [vercel-labs/skills](https://github.com/vercel-labs/skills) | 非运行依赖；用于发现/安装 skill 的辅助工具 |

## 贡献

欢迎 PR / issue。加 skill 请：① 先读 [SKILL_SPEC.md](./SKILL_SPEC.md) ② 从 [templates/skill-template](./templates/skill-template/) 复制 ③ 放 `skills/<name>/` ④ 有 `SKILL.md`（仅 `name` + `description`，description 尽量 ≤200 字）⑤ 路径 / key / 个人数据全用 CLI 参数、环境变量或 skill-specific `config.yml`，严禁硬编码 ⑥ 跑 `python3 scripts/generate_skill_catalog.py && python3 scripts/audit_skills.py` ⑦ 至少 1 个端到端用例。详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## License

[MIT](./LICENSE) — 自由 fork、改造、商用，请保留 attribution。

## 维护者

**soia-team** · [GitHub](https://github.com/soia-team)
