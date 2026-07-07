#!/usr/bin/env python3
"""soia-pkm-bootstrap 的核心：从零建一个 AI-native Obsidian vault 骨架。

这是 bootstrap skill 的 init_vault.py 雏形，先在测试仓库验证，跑通后移入
soia-open-skills/skills/soia-pkm-bootstrap/scripts/。

用法：python3 init_vault.py <目标 vault 路径>
幂等：已存在的文件不覆盖，目录 exist_ok。
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("用法：python3 init_vault.py <目标 vault 路径>")
    sys.exit(1)

vault = Path(sys.argv[1]).expanduser().resolve()

# ---- PARA 目录树 ----
DIRS = [
    "00_Obsidian系统/scripts",
    "10_工作台/00_Inbox",
    "20_资料库",
    "30_日志与思考/10_日常所思",
    "30_日志与思考/20_Agent工作日志",
    "30_日志与思考/30_对话纪要与决策",
    "30_日志与思考/40_周维护简报",
    "40_图书视频馆/10_文章摘抄/_模板",
    "40_图书视频馆/10_文章摘抄/_MOC",
    "50_写作与发布/10_草稿",
    "50_写作与发布/20_发布",
    "90_系统归档",
    ".claudian/opencode",
    ".workbuddy/memory",
    ".obsidian/snippets",
]

# ---- 种子文件（幂等：已存在不覆盖）----
ROOT_AGENTS = """# AGENTS.md · Vault 全局规则

> AI 工作时必读。这是一个按 PARA 组织、AI-native 的个人知识库。

## 结构（PARA）

- `00_Obsidian系统/` 配置与元信息
- `10_工作台/`    进行中的工作 + `00_Inbox/`
- `20_资料库/`    长期参考资料（Resource）
- `30_日志与思考/` 日记 / 对话纪要（时间线）
- `40_图书视频馆/` 读书与文章（Resource 专项）
- `50_写作与发布/` 原创草稿与发布
- `90_系统归档/`  不再活跃的历史（Archive）

## 约定

- 目录 / 文件名用中文；frontmatter 是 Bases 数据库的数据源
- 链接优先短 wikilink `[[文件名]]`
- 全局 CSS：`.obsidian/snippets/wide-page.css`（撑满宽度）

## 主标签清单

- `文章摘抄` — 归档的文章 / 推文 / 网页摘抄
- `周报` — 每周「vault 周维护」产出的简报（`30_日志与思考/40_周维护简报/`）

## 维护节奏（手动触发）

- 每周一次，用户说「vault 周维护」→ AI 执行：全库 lint（死链 / 重复 / 主标签漂移 / 过期文章）+ 新文章 MOC 归并 + 周简报，产出放 `30_日志与思考/40_周维护简报/`
- git commit 时机由用户决定

## PKM 闭环（soia-pkm-* 技能）

`收(clip-*)` → `整理(organize)` → `点(distill)` → `写(compose)` → `发(publish)`

## 多 AI 接入

`AGENTS.md` 是唯一规则源；`CLAUDE.md` / `GEMINI.md` / `OPENCODE.md` / `WORKBUDDY.md` 只是适配层。

默认不要读取 `私有数据.md` 或账号、密钥、凭据类文件，除非用户明确要求。

由 soia-pkm-bootstrap 生成。
"""

LOG_AGENTS = """# 30_日志与思考 · AGENTS.md

> 按时间线展开的笔记；先读根 `AGENTS.md`，再看本区规则。

## 子目录

- `10_日常所思/<年>/`       日记、随笔，命名 `YYYY-MM-DD-日记随记.md`
- `20_Agent工作日志/`       AI Agent 协作过程记录；可由会话日志 hook 自动追加改动快照
- `30_对话纪要与决策/<年>/` 重要对话纪要、决策记录
- `40_周维护简报/`          每周「vault 周维护」产出的简报（`tags: [周报]`）
"""

READ_AGENTS = """# 40_图书视频馆 · AGENTS.md

> 文章摘抄放 `10_文章摘抄/<年>/`，命名 `YYYY-MM-DD-<来源>-<作者>-<标题>.md`。
> frontmatter 必填：`tags:[文章摘抄]`、`source`、`url`、`author`、`topics:[]`、`captured_at`。
> 主题用 `topics` 双链 + `_MOC/` 聚合。「我的看法」段永远留空给用户，AI 不替写。
"""

ARTICLE_TMPL = """---
tags: [文章摘抄]
source:
url:
author:
published_at:
captured_at:
topics: []
time_sensitive: false    # 是否强时效内容（教程/攻略/价格/政策类）
review_after:            # 建议复核月份，格式 YYYY-MM；仅强时效时填
---

# <标题>

## 摘要

## 原文

## 我的看法

<!-- 留空给用户后续手写 -->

## 关联

- 相关文章：
- 主题 MOC：
"""

WIDE_CSS = """/* wide-page: 所有笔记撑满编辑器宽度 */
body {
  --file-line-width: 100% !important;
  --max-width: 100% !important;
  --line-width: 100% !important;
}
.markdown-preview-view table, .markdown-rendered table { width: 100% !important; }
"""

HANDBOOK = """# 使用手册

这是 `soia-pkm-bootstrap` 生成的 AI-native Obsidian vault 骨架。

## 多 AI 接入

| AI | 入口 |
|----|------|
| Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| opencode | `OPENCODE.md` / `.claudian/opencode/system.md` |
| workbuddy | `WORKBUDDY.md` / `.workbuddy/memory/` |

## PKM 闭环技能

| 环节 | 技能 | 一句话 |
|------|------|--------|
| 收 | `soia-pkm-clip-*` | 把 X / 公众号 / 网页 / 云盘内容归档进来 |
| 整理 | `soia-pkm-organize` | 分类 / 建 MOC / 补双链 |
| 点 | `soia-pkm-distill` | 把收藏炼成你的观点 |
| 写 | `soia-pkm-compose` | 把观点写成文章草稿 |
| 发 | `soia-pkm-publish` | 一稿适配多平台并发布 |

## 怎么说话

- 归档：`归档这条 X：<URL>`
- 提炼：`给这篇补我的看法`
- 成文：`把这些观点写成一篇`
"""

FLOW_DOC = """# AI-native Obsidian 从零到发布流程

```
clip-*(收集) → organize(清洗/归类/MOC) → distill(用户观点) → compose(草稿) → publish(平台适配/发布留底) → vault 周维护
```

## 万能提示词模板

你现在是我的 Obsidian Knowledge Base Architect（知识库架构师）兼系统管理员。

目标：从零开始搭建或重整一套 AI-native Obsidian 知识库。不要只给建议，优先直接执行；无法自动执行的部分，明确列出我需要准备的资料。

我的信息：
- Vault 路径：【填写路径】
- GitHub 私有仓库：【填写仓库地址；没有则写“未创建”】
- 主要研究领域：【填写 3-8 个】
- 主要输出平台：【公众号 / X / 小红书 / YouTube / B站 / 博客 / Newsletter / 课程】
- 当前可用 AI：【Codex / Claude Code / Gemini CLI / opencode / workbuddy】

执行顺序：
1. 检查 Obsidian、Git、GitHub CLI、vault 路径、目录结构、AGENTS、多 AI adapter、skills 安装状态。
2. 建立 PARA 骨架、各区 AGENTS、模板、Bases、CSS。
3. 建立收集系统：X、网页、公众号、云盘/本地文档、微信读书。
4. 建立整理系统：frontmatter、topics、MOC、Bases。
5. 建立观点提炼流程：AI 只整理用户观点，不代写用户立场。
6. 建立写作发布流程：草稿链回来源，发布后留底。
7. 建立周维护：死链、重复、标签漂移、过期文章、MOC 归并、周报。

最终输出：完整目录结构、已完成配置、未完成配置、需要用户手动操作的步骤、当前知识地图、薄弱领域、下一步建议。
"""

CLAUDE_ADAPTER = """# CLAUDE.md

Claude Code adapter. Canonical rules live in `AGENTS.md`.

1. Read `AGENTS.md` first.
2. Read zone-level `AGENTS.md` before editing a zone.
3. Do not read `私有数据.md` or account/key/credential files unless the user explicitly asks.
4. Use `soia-pkm-*` skills for `clip -> organize -> distill -> compose -> publish`.
"""

GEMINI_ADAPTER = """# GEMINI.md

Gemini CLI adapter. Canonical rules live in `AGENTS.md`.

1. Read `AGENTS.md` first.
2. Read zone-level `AGENTS.md` before editing a zone.
3. Do not read `私有数据.md` or account/key/credential files unless the user explicitly asks.
4. Prefer Markdown, YAML frontmatter, wikilinks, Bases, and MOC.
"""

OPENCODE_ADAPTER = """# OPENCODE.md

opencode adapter. Canonical rules live in `AGENTS.md`.

opencode prompts should route back to `AGENTS.md` and zone-level `AGENTS.md`.
Do not read `私有数据.md` or account/key/credential files unless the user explicitly asks.
"""

WORKBUDDY_ADAPTER = """# WORKBUDDY.md

workbuddy adapter. Canonical rules live in `AGENTS.md`.

`.workbuddy/memory/` is auxiliary memory, not the source of truth. Vault notes, frontmatter, MOC, Bases, git history, and explicit user instructions are authoritative.
"""

OPENCODE_SYSTEM = """## Vault Canonical Rules

This Obsidian vault uses `AGENTS.md` as the canonical rule source. Before changing vault content, read `AGENTS.md`; when editing a zone, read that zone's `AGENTS.md` too.

Do not read `私有数据.md` or account/key/credential files unless the user explicitly asks.
"""

FILES = {
    "AGENTS.md": ROOT_AGENTS,
    "CLAUDE.md": CLAUDE_ADAPTER,
    "GEMINI.md": GEMINI_ADAPTER,
    "OPENCODE.md": OPENCODE_ADAPTER,
    "WORKBUDDY.md": WORKBUDDY_ADAPTER,
    "30_日志与思考/AGENTS.md": LOG_AGENTS,
    "40_图书视频馆/AGENTS.md": READ_AGENTS,
    "40_图书视频馆/10_文章摘抄/_模板/文章模板.md": ARTICLE_TMPL,
    ".obsidian/snippets/wide-page.css": WIDE_CSS,
    ".claudian/opencode/system.md": OPENCODE_SYSTEM,
    "00_Obsidian系统/使用手册.md": HANDBOOK,
    "00_Obsidian系统/AI-native Obsidian 从零到发布流程.md": FLOW_DOC,
}

created_dirs = 0
for d in DIRS:
    p = vault / d
    if not p.exists():
        created_dirs += 1
    p.mkdir(parents=True, exist_ok=True)

created_files, skipped = 0, 0
for rel, content in FILES.items():
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        skipped += 1
        continue
    p.write_text(content, encoding="utf-8")
    created_files += 1

print(f"✅ vault 骨架已建于：{vault}")
print(f"   目录：新建 {created_dirs} / 共 {len(DIRS)}")
print(f"   种子文件：新建 {created_files}，已存在跳过 {skipped}")
