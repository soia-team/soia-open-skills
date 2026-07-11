---
name: soia-pkm-clip-web
description: 把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内优先调用 Obsidian 自带 PDF 导出。Triggers：「归档这个网页」「clip 这个链接」「存这篇博客」
---

# soia-pkm-clip-web

`clip` 家族的**通用网页成员**：把博客 / 网页文章沉淀进 vault。

## 客户可读说明

### 这个技能可以做什么

把任意网页/博客文章一键归档到 Obsidian vault。用正文抽取（readability/trafilatura）提取标题/正文/作者，按 clip 家族统一规范落地。当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，归档后在 Obsidian vault 内优先调用 Obsidian 自带 PDF...

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-clip-web -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-web/config.yml
SOIA_PKM_CLIP_WEB_CONFIG_FILE=<custom-config-path>
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

## 抓取

- 输入：任意文章 URL（博客 / Substack / Medium / 新闻 / 知乎等）
- 正文抽取：`trafilatura` 或 `readability-lxml` 抽正文（去广告 / 导航），提取标题、作者、发布时间。
- 抓不到正文 → `content_complete: false`，**绝不静默截断**。
- 抓取与落地当前由 agent 按本节流程手工执行（专用归档脚本待补充到本 skill 的 `scripts/`）。
- 手机端可用 Obsidian Web Clipper 落到 `<vault-inbox-dir>/`，再由本 skill 迁入。

## 抓取质量强制复核

脚本退出码 0 不等于抓取成功——有些站点会把登录墙、导航壳或反爬拦截页当正常响应返回，脚本不会报错。**写入 vault 前必须亲读产物**，核对：标题是否匹配原页面（不是"登录""访问异常"这类站点通用标题）、正文是否为完整文章（不是导航栏/侧边栏堆砌，也不是清一色链接）、字数是否与原文体量大致相符。

失败信号清单（命中任一条即判定失败，不得直接交付）：
- 出现"登录""请先登录""verify you are human"等登录墙/验证关键词
- 正文明显过短（应为长文却只有几十字）
- 正文几乎全是链接、没有实质叙述文字

命中失败信号时换策略（换 `readability-lxml`/`trafilatura` 互为兜底、提示用户手动登录后重试、或如实标 `content_complete: false` 并提醒人工核对原文），而不是把拦截页当正文写进 vault。

## 落地（clip 家族统一规范）

- 路径：`<vault-articles-dir>/<年>/YYYY-MM-DD-<来源>-<作者>-<标题>.md`（来源如 博客 / Substack / Medium）
- frontmatter 同 clip 家族；正文 `## 摘要 / 原文 / 我的看法 / 关联`。
- 归档后补摘要 + topics；走 `organize` 归位。

## 归档后导出 PDF

用户同时要求「转 PDF / 导出 PDF」时，先完成 Markdown 归档、摘要、topics 与月份归位，再读取并执行 **[references/obsidian-pdf-export.md](references/obsidian-pdf-export.md)**。只要目标文件位于 Obsidian vault 内，就优先调用 Obsidian 自带「导出 PDF」；外部 PDF 引擎只能作为明确降级方案。

## 闭环位置

`★clip-web(收) → organize → distill → compose → publish`。


---

## 完成后回执

**交付顺序**：先把文件落盘，再输出下面的回执，不得反过来；不确定的元数据（如作者、发布时间解析失败）在回执里显式标注"未核实"，不编造。

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
