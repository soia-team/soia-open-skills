---
name: soia-pkm-clip-wechat-article
description: 归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出。Triggers：「归档这篇公众号」「clip 这个公众号文章」「存这篇微信文章」
version: 2.0.0
created_at: 2026-07-02 17:57:11
updated_at: 2026-07-16 15:34:25
created_by: claude opus 4.6
updated_by: codex 5.6
---

# soia-pkm-clip-wechat-article

`clip` 家族的**公众号成员**：把公众号文章沉淀进 vault。

## 客户可读说明

### 这个技能可以做什么

归档单篇微信公众号文章到 Obsidian vault：抓取静态 HTML，提取标题、作者、正文、发布时间和配图，按 clip 家族规范落地；需要 PDF 时优先用 Obsidian 导出

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-clip-wechat-article -y
```

当前脚本的配置入口：

```text
OBSIDIAN_VAULT=<vault-path>
OBSIDIAN_ARTICLES=<vault-relative-articles-dir>
```

- CLI `--vault` / `--articles-dir` 优先于环境变量；都未提供时，仅从当前目录向上寻找真实 `.obsidian/` 标志。
- 当前 stdlib 脚本不解析 YAML `config.yml`，也不需要 API key、cookie 或其他凭据；不要创建一个不会生效的配置文件。
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

## 抓取

- 输入：`https://mp.weixin.qq.com/s/...`
- 公众号文章是**静态 HTML**（比 X 好抓，不需 API）：stdlib `urllib.request` 拉页面 → 解析 `#js_content`（正文）、`#activity-name` / `og:title`（标题）、author meta（署名作者）、`#js_name`（公众号名）、`createTime` / `oriCreateTime`（发布时间 fallback）。
- 图片：提取 `data-src` 并保留为远程链接；当前脚本不下载图片，离线化由后续流程处理。
- 脚本：`scripts/archive_wechat.py <url> --vault <path>`（纯 Python 标准库；支持 `--dry-run`、`--json`、URL 去重、正文质量门和原子写）。

```bash
python3 scripts/archive_wechat.py <url> \
  --vault <vault-path> \
  --articles-dir <vault-relative-articles-dir> \
  --dry-run --json
```

先 dry-run 核对标题、作者、发布时间、`body_chars`、图片数与 `content_complete`，再去掉 `--dry-run` 写入。找不到 `#js_content`、正文异常短或命中拦截页关键词时默认拒绝写入；只有客户明确接受不完整归档时才使用 `--allow-incomplete`。

## 落地（clip 家族统一规范）

- 路径：`<vault-articles-dir>/<年>/<月>/YYYY-MM-DD-公众号-<作者>-<标题>.md`
- frontmatter：`tags:[文章摘抄]`、`source: 公众号`、`url`、`author`、`publisher`、`published_at`、`captured_at`、`topics:[]`、`content_complete`
- 正文段：`## 摘要`（AI 补）、`## 原文`、`## 我的看法`（留空）、`## 关联`
- 归档后 AI 补摘要 + topics；脚本已按发布月份归位。

## 验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile scripts/archive_wechat.py
```

仓库维护者从 repo 根运行时，把路径替换为 `skills/soia-pkm-clip-wechat-article/tests` 与 `skills/soia-pkm-clip-wechat-article/scripts/archive_wechat.py`。这两项检查专门防止 SKILL 再次声明一个未随安装包交付的脚本。

## 归档后导出 PDF

用户同时要求「转 PDF / 导出 PDF」时，先完成 Markdown 归档、摘要、topics 与月份归位，再读取并执行 **[references/obsidian-pdf-export.md](references/obsidian-pdf-export.md)**。只要目标文件位于 Obsidian vault 内，就优先调用 Obsidian 自带「导出 PDF」；外部 PDF 引擎只能作为明确降级方案。

## 闭环位置

`★clip-wechat(收) → organize → distill → compose → publish`。与 clip-x/web/drive 共享落地规范，仅源不同。


---

## 完成后回执

**交付顺序**：先把文件落盘，再输出下面的回执，不得反过来；不确定的元数据（如作者、发布时间解析失败）在回执里显式标注"未核实"，不编造。

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
