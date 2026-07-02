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
    "00_系统/scripts",
    "10_工作台/00_Inbox",
    "20_资料库",
    "30_日志与思考",
    "40_阅读与摘抄/10_文章摘抄/_模板",
    "40_阅读与摘抄/10_文章摘抄/_MOC",
    "50_写作与发布/10_草稿",
    "50_写作与发布/20_发布",
    "90_系统归档",
    ".obsidian/snippets",
]

# ---- 种子文件（幂等：已存在不覆盖）----
ROOT_AGENTS = """# AGENTS.md · Vault 全局规则

> AI 工作时必读。这是一个按 PARA 组织、AI-native 的个人知识库。

## 结构（PARA）

- `00_系统/`      配置与元信息
- `10_工作台/`    进行中的工作 + `00_Inbox/`
- `20_资料库/`    长期参考资料（Resource）
- `30_日志与思考/` 日记 / 对话纪要（时间线）
- `40_阅读与摘抄/` 读书与文章（Resource 专项）
- `50_写作与发布/` 原创草稿与发布
- `90_系统归档/`  不再活跃的历史（Archive）

## 约定

- 目录 / 文件名用中文；frontmatter 是 Bases 数据库的数据源
- 链接优先短 wikilink `[[文件名]]`
- 全局 CSS：`.obsidian/snippets/wide-page.css`（撑满宽度）

## PKM 闭环（soia-pkm-* 技能）

`收(clip-*)` → `整理(organize)` → `点(distill)` → `写(compose)` → `发(publish)`

由 soia-pkm-bootstrap 生成。
"""

READ_AGENTS = """# 40_阅读与摘抄 · AGENTS.md

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

FILES = {
    "AGENTS.md": ROOT_AGENTS,
    "40_阅读与摘抄/AGENTS.md": READ_AGENTS,
    "40_阅读与摘抄/10_文章摘抄/_模板/文章模板.md": ARTICLE_TMPL,
    ".obsidian/snippets/wide-page.css": WIDE_CSS,
    "00_系统/使用手册.md": HANDBOOK,
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
