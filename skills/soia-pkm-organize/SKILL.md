---
name: soia-pkm-organize
description: 整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档。Triggers：「整理文章库」「补 topics」「重建 MOC」「把这些收藏归类」「organize 一下」「归位到月份」
version: 1.0.0
created_at: 2026-07-02 17:57:11
updated_at: 2026-07-15 18:27:15
created_by: claude opus 4.6
updated_by: claude opus 4.6
---

# soia-pkm-organize

PKM 闭环的**整理环节**：把杂乱的收藏规整成结构化、可检索、能聚合的知识。专治"一大堆归档躺在黑洞里没被激活"。

## 客户可读说明

### 这个技能可以做什么

整理 Obsidian 文章库——补 frontmatter（topics/captured_at/author）、按主题双链归类、建/更新两级 MOC、按月份归位、补双链。底层调 rebuild_moc.py / backfill 等脚本，上层用 LLM 判断分类。用于激活存量收藏、规整新归档

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到 Obsidian/vault 文件变更、终端日志、生成产物路径和最终回执。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. Agent 先判断是否命中本技能，再检查依赖、配置、权限和风险动作。
3. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。
4. 执行后验证真实输出，不用“看起来成功”代替证据。
5. 最终回复必须给客户可见总结：做了什么、日志摘要、文件变化、问题和下一步。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-organize -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-organize/config.yml
SOIA_PKM_ORGANIZE_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- 强依赖、可选依赖和第三方 skill 关系必须以本 `SKILL.md` 后续的“依赖 / 前置 / 资源 / 边界”说明为准；没有写清楚时，先补说明或询问客户，不要猜。
- 第三方 skill 只能声明依赖和安装方式，不直接修改第三方 skill 文件。

### 日志与完成回执

每次执行都要让客户看见过程和结果。最低回执格式：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <检查到的输入/配置/依赖，不打印秘密值>
- processed: <数量或范围>
- created/updated: <数量或路径>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <运行过的检查、命令或人工核对点>

问题与下一步：
- <缺 key / 缺依赖 / 需要客户确认 / 建议下一条命令；没有则写“无”>
```

## ⚠️ 整理前置规程（必读，外部配置）

任何「整理 / 重组知识库某一块」的任务（不限文章库），**开工前先加载并严格遵循** [`references/知识库整理规程.yml`](references/知识库整理规程.yml)：**先探明现状（只读，摸清用户已有的结构/约定/模板，发现同类先并入不另起）→ 再提最小方案给用户拍板 → 确认后才批量执行**。

规程是**外部配置、与本 skill 解耦**——改规程改那个 yml，不写死在本文里。核心红线：不先探明就动手必返工；已有成熟结构还另起一套是重复造轮子；空模板/瞎猜分类/一次性批量生成再让用户挑错都是浪费。

## 做什么

1. **补 frontmatter**：缺 `topics` / `captured_at` / `author` 的补上。
2. **主题归类**：读文章内容，判断该挂哪些 `topics`（双链）；**优先复用已有主题**（查 `_MOC/`），避免造重复主题。
3. **建 / 更新 MOC**：跑 `rebuild_moc.py` 重建两级主题地图（一级分类 → 二级 topic）。
4. **按月归位**：`clip` 原生落 `<年>/`，把文章按文件名日期归到 `<年>/<月>/`。
5. **补双链**：文章间、文章 ↔ 书 ↔ 日志的关联。

## 底层脚本（机械层，organize 调用）

- `scripts/rebuild_moc.py`：扫全部文章 topics，重建 `_MOC/` 两级地图。支持 `--vault`/`OBSIDIAN_VAULT` 指定库路径，分类表可用 `_MOC/.categories.json` 按库覆盖默认值（见脚本 `--help`）。
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
