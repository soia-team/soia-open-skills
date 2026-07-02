---
name: soia-pkm-organize
version: 1.0.0
description: 整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档。Triggers：「整理文章库」「补 topics」「重建 MOC」「把这些收藏归类」「organize 一下」「归位到月份」
---

# soia-pkm-organize

PKM 闭环的**整理环节**：把杂乱的收藏规整成结构化、可检索、能聚合的知识。专治"一大堆归档躺在黑洞里没被激活"。

## 做什么

1. **补 frontmatter**：缺 `topics` / `captured_at` / `author` 的补上。
2. **主题归类**：读文章内容，判断该挂哪些 `topics`（双链）；**优先复用已有主题**（查 `_MOC/`），避免造重复主题。
3. **建 / 更新 MOC**：跑 `rebuild_moc.py` 重建两级主题地图（一级分类 → 二级 topic）。
4. **按月归位**：`clip` 原生落 `<年>/`，把文章按文件名日期归到 `<年>/<月>/`。
5. **补双链**：文章间、文章 ↔ 书 ↔ 日志的关联。

## 底层脚本（机械层，organize 调用）

- `rebuild_moc.py`：扫全部文章 topics，重建 `_MOC/` 两级地图。
- `backfill_reading_records.py`：书库 → 阅读记录补齐（读书线）。
- 按月归位：`mv <年>/*.md <年>/<月>/`（按文件名日期）。

> organize = **LLM 判断分类 / 综述 + 机械层脚本批量执行**。脚本负责确定性批量操作；LLM 负责"这篇属于什么主题""这个 MOC 的核心判断是什么"。

## 分类原则

- topic 优先复用已有（查 `_MOC/`），不轻易造新主题。
- 映射写死在 `rebuild_moc.py` 的分类表（不靠 AI 每次猜）——改归类就改表再重跑。

## 回执

整理后告知：处理了多少篇、补了哪些 topics、MOC 更新情况、归位了多少文件。

## 闭环位置

```
clip(收) → ★organize(整理) → distill(点) → compose(写) → publish(发)
```

上游 `clip` 收进来（可能杂乱、落在年份根目录）；`organize` 规整；下游 `distill` 在规整的库上提炼。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
