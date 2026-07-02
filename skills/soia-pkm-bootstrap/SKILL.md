---
name: soia-pkm-bootstrap
version: 1.0.0
description: 从零初始化一个 AI-native 的 Obsidian 个人知识库（PKM）。建 PARA 目录骨架 + 各区 AGENTS.md + 模板 + Bases + CSS，引导装 Obsidian 及必要插件，接入多个 AI（Claude Code / Codex 等），并装好 soia-pkm-* 的输入/整理/输出技能。Triggers：「初始化一个知识库」「从零建 vault」「bootstrap 一个 AI 知识库」「帮我搭个 Obsidian 知识库」「新建一个 PKM 库」
---

# soia-pkm-bootstrap

一句话从零起一个 **AI-native 的 Obsidian 知识库**——PARA 骨架 + AGENTS 路由 + Bases + AI 接入 + PKM 闭环技能，开箱即用。

这是 PKM 体系的**元技能（搭建）**：把一套成熟 vault 的最佳实践，固化成任何人可复制的初始化流程。

## 初始化流程（5 步）

### Step 1 — 装 Obsidian 与必要配置

- 下载（免费）：https://obsidian.md/download
- **版本要求**：1.9+（内置 **Bases** 数据库功能，本体系的核心）
- 启用：设置 → 核心插件 → 确认 **Bases** 可用

### Step 2 — 建 vault 骨架

```bash
python3 scripts/init_vault.py <目标 vault 路径>
```

幂等地建出：PARA 目录（`00_系统` / `10_工作台` / `20_资料库` / `30_日志与思考` / `40_阅读与摘抄` / `50_写作与发布` / `90_系统归档`）、各区 `AGENTS.md`、文章模板、`.obsidian/snippets/wide-page.css`、使用手册。已存在的文件不覆盖。

### Step 3 — 接入 AI（多 AI，二选一或都用）

**方式 A（推荐）— 终端 AI CLI 直接操作 vault**
skill 天生跨 agent，装好后 `soia-pkm-*` 同时挂三处并被各 AI 读取：
- Claude Code → `~/.claude/skills/`
- Codex → `~/.codex/skills/`
- 其他（Gemini / Cursor / Kimi / amp …）→ `~/.agents/skills/`

AI 直接读写 vault 的 `.md` 文件，**不依赖 Obsidian 插件**。

**方式 B — Obsidian 内嵌 AI 插件**（不习惯终端的人）
- **Tars**（社区插件）：连 Kimi / Claude / OpenAI API，笔记内 `#Kimi :` 触发 inline 生成
- **Terminal**（polyipseity）：在 Obsidian 内跑 AI CLI，直接操作 vault 文件

### Step 4 — 装 PKM 闭环技能

```bash
npx skills add soia-team/soia-open-skills   # soia-pkm-clip-x / distill / …（自建）
npx skills add Tencent/WeChatReading         # weread（读书线，可选）
```

闭环：`clip-*(收) → organize(整理) → distill(点) → compose(写) → publish(发)`

### Step 5 — 验证

对 AI 说 `归档这条 X：<URL>`，确认落到 `40_阅读与摘抄/10_文章摘抄/`；再说 `给这篇补我的看法` 跑一次提炼。闭环通了即初始化完成。

## Obsidian 插件 / 配置清单

| 类型 | 插件 / 功能 | 必需? | 用途 |
|------|-----------|-------|------|
| 本体 | Obsidian 1.9+ | ✅ | — |
| 核心 | Bases | ✅ | 数据库视图（书库 / 文章库）|
| CSS | `wide-page.css`（本 skill 自带）| 推荐 | 撑满编辑器宽度 |
| AI | Claude Code / Codex CLI | 二选一 | 终端 AI 操作 vault（推荐）|
| AI | Tars（社区）| 二选一 | Obsidian 内连 AI |
| 版本 | Obsidian Git（社区）| 可选 | vault 版本控制 |

> 本体系 **不用 Dataview**（用 Bases）、**不强依赖 Templater**（自带模板够用）。

## 参考实现

当前的 `obsidian-work` vault 就是本 skill 的参考实现；`v2/obsidian-test-vault` 是 `init_vault.py` 跑出来的最小骨架验证。

## 产物

一个能用的 vault + 已接入的多 AI + PKM 闭环技能。之后对 AI 说「归档这条 X」「给这篇补我的看法」即可跑闭环。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
