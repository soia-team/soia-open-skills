---
name: soia-pkm-bootstrap
description: 从零初始化一个 AI-native 的 Obsidian 个人知识库（PKM）。建 PARA 目录骨架 + 各区 AGENTS.md + 模板 + Bases + CSS，接入 Codex、Claude Code、Gemini CLI、opencode、workbuddy 多 AI 适配层，并装好 soia-pkm-* 的输入/整理/输出技能。Triggers：「初始化一个知识库」「从零建 vault」「bootstrap 一个 AI 知识库」「帮我搭个 Obsidian 知识库」「新建一个 PKM 库」「让 Obsidian 支持多种 AI」
---

# soia-pkm-bootstrap

一句话从零起一个 **AI-native 的 Obsidian 知识库**——PARA 骨架 + AGENTS 路由 + Bases + AI 接入 + PKM 闭环技能，开箱即用。

这是 PKM 体系的**元技能（搭建）**：把一套成熟 vault 的最佳实践，固化成任何人可复制的初始化流程。

## 初始化流程（5 步 + 1 可选）

### Step 1 — 装 Obsidian 与必要配置

- 下载（免费）：https://obsidian.md/download
- **版本要求**：1.9+（内置 **Bases** 数据库功能，本体系的核心）
- 启用：设置 → 核心插件 → 确认 **Bases** 可用

### Step 2 — 建 vault 骨架

```bash
python3 scripts/init_vault.py <目标 vault 路径>
python3 scripts/init_vault.py <目标 vault 路径> --config <你的配置.json>
```

幂等地建出：目录骨架、各区 `AGENTS.md`、文章模板、`.obsidian/snippets/wide-page.css`、使用手册、多 AI 入口文件。已存在的文件默认不覆盖。

目录和种子文件来自 `scripts/default_config.json`，不要改脚本写死个人需求。需要自定义时：

```bash
python3 scripts/init_vault.py --print-default-config > my-vault-config.json
# 修改 my-vault-config.json 后：
python3 scripts/init_vault.py <目标 vault 路径> --config my-vault-config.json
```

配置支持 JSON（零依赖）和 YAML（需本机装 PyYAML）。`scripts/example_custom_config.json` 演示了如何增删目录、替换某个种子文件。

### Step 3 — 接入多 AI

`AGENTS.md` 是唯一规则源；其他入口只做适配，不另立一套规范。

| AI | 入口 | 说明 |
|----|------|------|
| Codex | `AGENTS.md` | 原生读取根规则与子目录规则 |
| Claude Code | `CLAUDE.md` | 回读 `AGENTS.md`，可加载 `~/.claude/skills/` |
| Gemini CLI | `GEMINI.md` | 回读 `AGENTS.md`，可使用 `gemini skills` 或共享 `~/.agents/skills/` |
| opencode | `OPENCODE.md` / opencode system prompt | 回读 `AGENTS.md`，适合 Obsidian 内/CLI 协作 |
| workbuddy | `WORKBUDDY.md` / `.workbuddy/memory/` | 记忆只存长期事实，不替代 vault 正文 |

skill 跨 agent 的安装约定：
- Claude Code → `~/.claude/skills/`
- Codex → `~/.codex/skills/`
- Gemini / opencode / workbuddy 等 → 优先共用 `~/.agents/skills/`

AI 直接读写 vault 的 `.md` 文件，**不依赖 Obsidian 插件**。

**Obsidian 内嵌 AI 插件**（不习惯终端的人）
- **Tars**（社区插件）：连 Kimi / Claude / OpenAI API，笔记内 `#Kimi :` 触发 inline 生成
- **Terminal**（polyipseity）：在 Obsidian 内跑 AI CLI，直接操作 vault 文件

### Step 4 — 装 PKM 闭环技能

```bash
npx skills add soia-team/soia-open-skills   # soia-pkm-clip-x / distill / maintain / …（自建）
npx skills add Tencent/WeChatReading         # weread（读书线，可选）
```

闭环：`clip-*(收) → organize(整理) → distill(点) → compose(写) → publish(发)`
支撑：`soia-pkm-maintain`（周维护 lint + 简报；会话日志自动接入见 Step 6，可选）

### Step 5 — 验证

对 AI 说 `归档这条 X：<URL>`，确认落到你配置里的文章摘抄目录；再说 `给这篇补我的看法` 跑一次提炼。闭环通了即初始化完成。

### Step 6 — 接入会话日志（可选）

装完 PKM 技能后，问用户是否要接入 AI 会话日志——自动把每次会话的改动快照追加进你配置的日志目录：

- **必须先征得用户同意**，不要静默改配置
- Claude Code 场景：在 `.claude/settings.json` 加 `SessionEnd` hook
- Codex 场景：改 `config.toml` 的 notify wrapper
- 具体步骤见 `soia-pkm-maintain` skill 的 `references/session-log-setup.md`

## Obsidian 插件 / 配置清单

| 类型 | 插件 / 功能 | 必需? | 用途 |
|------|-----------|-------|------|
| 本体 | Obsidian 1.9+ | ✅ | — |
| 核心 | Bases | ✅ | 数据库视图（书库 / 文章库）|
| CSS | `wide-page.css`（本 skill 自带）| 推荐 | 撑满编辑器宽度 |
| AI CLI | Codex / Claude Code / Gemini CLI / opencode / workbuddy | 推荐 | 多 AI 直接操作 vault |
| AI | Tars（社区）| 二选一 | Obsidian 内连 AI |
| 版本 | Obsidian Git（社区）| 可选 | vault 版本控制 |

> 本体系 **不用 Dataview**（用 Bases）、**不强依赖 Templater**（自带模板够用）。

## 参考实现

本 skill 的参考实现应使用脱敏示例 vault；本地验证可用 `init_vault.py` 跑一个最小骨架，不在开源说明中写个人 vault 名称或本机路径。

## 从零到发布的工作流

初始化完成后，完整路径是：

```
clip-*(收集) → organize(清洗/归类/MOC) → distill(用户观点) → compose(草稿) → publish(平台适配/发布留底) → vault 周维护
```

提示词模板原则：
- 让用户提供 vault 路径、GitHub 私有仓库、研究领域、输出平台、可用 AI。
- 先检查环境，再建目录；不要跳过验证。
- 明确要求 AI 建立 `AGENTS.md` + 多 AI adapter，而不是把规则散在各工具里。
- 要求资料保留原文和来源，观点只写用户自己的。
- 最终输出已完成、未完成、需用户手动做的事、知识地图、薄弱领域、下一步建议。

## 产物

一个能用的 vault + 已接入的多 AI + PKM 闭环技能。之后对 AI 说「归档这条 X」「整理主题地图」「给这篇补我的看法」「把这些观点写成一篇」「发布这篇」即可跑闭环。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
