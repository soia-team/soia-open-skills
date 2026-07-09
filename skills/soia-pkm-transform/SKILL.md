---
name: soia-pkm-transform
description: 把 X/公众号/网页/Markdown 文章转换为 PDF、PPT、图片/长图、试卷、脑图、播客、闪卡、报告等产物的公共路由 skill。配置外置，可调用 Obsidian、NotebookLM、Open Design、Codex 文件能力与 publish。Triggers：「转换文章为」「归档并转成」「生成 PPT/脑图/试卷/图片/播客」
---

# soia-pkm-transform

把一篇文章变成不同产物的公共路由层：PDF、PPT、图片/长图、信息图、试卷、脑图、播客、闪卡、报告、公众号 HTML、小红书卡片等。

它编排 `clip-* -> transform -> publish/maintain`，不替代 clip、publish、NotebookLM、Open Design 或当前 agent 的文件能力。

## 客户可读说明

### 这个技能可以做什么

把 X/公众号/网页/Markdown 文章转换为 PDF、PPT、图片/长图、试卷、脑图、播客、闪卡、报告等产物的公共路由 skill。配置外置，可调用 Obsidian、NotebookLM、Open Design、Codex 文件能力与 publish

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-transform -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-transform/config.yml
SOIA_PKM_TRANSFORM_CONFIG_FILE=<custom-config-path>
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

## 先守住这些边界

- 不写死个人 vault 路径、账号、token、key、cookie、家庭信息或个人目录。
- 配置只来自用户本轮指令、配置文件或环境变量；公共默认必须能在别人机器上工作。
- 秘钥和登录态只放 provider 自己的私有位置，例如 `NOTEBOOKLM_HOME`、微信公众号私有 `config.yml`、agent 密钥流程；不要写进 vault 或开源 skill。
- 不读取 `私有数据.md`、浏览器 cookie、账号配置文件，除非用户明确要求且 provider 官方流程需要。
- 默认是转换，不是总结。只有用户明确说“总结/摘要/TL;DR”时才压缩内容。
- 生成前先抽 source 的章节、概念、案例链和关键判断；产物必须覆盖这张清单的大部分内容。
- 文件存在不等于完成；页数、信息密度、覆盖度、样式和媒介完整性按 [quality-gates.md](references/quality-gates.md) 验收。

## 触发后先判断

1. **来源**：URL 先走对应 clip skill；本地 Markdown/vault 笔记直接读；PDF/Word/PPT 先提取成 article packet。
2. **目标**：`pdf | ppt | image | long_image | infographic | quiz | mindmap | podcast | video | cinematic-video | flashcards | data_table | report | wechat | x_thread | xhs`。
3. **内容模式**：
   - `preserve`：PDF、全文报告、课件，保留章节、例子、清单和关键表述。
   - `learning`：PPT、试卷、闪卡、课程模块。
   - `visual_dense`：长图、信息图、海报，一张图讲清楚。
   - `synthesize`：grounded report / NotebookLM 综合。
   - `summarize`：仅用户明确要求摘要时使用。
4. **provider**：用户指定 > 配置 > 默认路由。缺 provider 时进入 bootstrap，不要只说“没安装”就停。

## 配置发现

配置可选；无配置时按默认路由走。优先级：

1. 用户本轮明确指定的 provider / 输出目录 / 格式 / 参数
2. `SOIA_PKM_TRANSFORM_CONFIG`
3. `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-transform/transform.config.yml`（或 `.yaml` / `.json`）

样例见 [assets/transform.config.example.yml](assets/transform.config.example.yml)。

## 路由表

| 目标 | 默认 provider | 需要读取 |
|------|---------------|----------|
| PDF | Obsidian 原生导出（vault Markdown，`preserve`）或本地 PDF | [provider-soia-local.md](references/provider-soia-local.md) |
| PPT/PPTX | local presentation / HTML deck | [prompt-ppt.md](references/prompt-ppt.md)，可选 Open Design / NotebookLM |
| 长图/信息图 | local HTML/CSS screenshot | [prompt-infographic.md](references/prompt-infographic.md)，可选 Open Design / NotebookLM |
| 封面/插画 | imagegen / Codex image | [prompt-codex-image.md](references/prompt-codex-image.md) |
| quiz/flashcards/mindmap/report | NotebookLM 或 local markdown | [prompt-notebooklm.md](references/prompt-notebooklm.md) 或 [provider-soia-local.md](references/provider-soia-local.md) |
| podcast/video/cinematic-video/data-table | NotebookLM | [provider-notebooklm.md](references/provider-notebooklm.md) |
| 公众号/X/小红书 | `soia-pkm-publish` | publish skill |

Provider 总入口见 [providers.md](references/providers.md)。Open Design 是增强 provider，不是硬依赖；见 [provider-open-design.md](references/provider-open-design.md)。

## 目标专用 prompt

不同产物必须用不同 prompt，不要用“总结成 PPT/生成图片”这种泛化提示词。

- PPT / 课件：[prompt-ppt.md](references/prompt-ppt.md)
- 长图 / 信息图 / 海报：[prompt-infographic.md](references/prompt-infographic.md)
- Codex image / imagegen：[prompt-codex-image.md](references/prompt-codex-image.md)
- Open Design handoff：[prompt-open-design.md](references/prompt-open-design.md)
- 视觉报告：[prompt-report.md](references/prompt-report.md)
- NotebookLM 总路由：[prompt-notebooklm.md](references/prompt-notebooklm.md)，再按 artifact 读取 `prompt-notebooklm-*.md`

## 可直接运行的脚本

```bash
python3 scripts/resolve_config.py
python3 scripts/resolve_route.py --target ppt --provider notebooklm --json
python3 scripts/notebooklm_health.py --ensure-home --json
python3 scripts/notebooklm_artifact_matrix.py --article <article.md> --out-dir <out> --targets all --run --json
python3 scripts/local_artifact_smoke.py --article <article.md> --out-dir <out> --strict --json
python3 scripts/validate_artifact_quality.py --article <article.md> --out-dir <out> --strict --json
```

脚本只处理通用路径和公共 provider 流程；不要把个人 vault 路径写进脚本。

## 工作流

1. 解析请求：来源、目标、格式、受众、是否先归档。
2. 获取文章：URL 走 clip；本地文件形成 article packet。
3. 选模式和 recipe：先定 `content_mode`，再跑 `resolve_route.py` 或读 [output-recipes.md](references/output-recipes.md)。
4. 检查 provider：NotebookLM、Open Design、Obsidian、发布链路都先跑健康检查；不可用就按对应 provider bootstrap。
5. 生成产物：只写到用户指定目录、当前项目或 vault 的 `outputs/transform/<YYYY>/<文章stem>/`。
6. 验证：先跑 `validate_artifact_quality.py` 或等价检查，再按 [quality-gates.md](references/quality-gates.md) 人眼复核覆盖度、页数/信息块数、可打开、可读、可解析、无明显乱码/重叠/空白。
7. 回写链接：源文章在 vault 内且配置允许时，只追加 `## 转化产物` 链接，不改原文。
8. 回执：列来源、content_mode、provider、输出文件、验证结果、失败/降级原因。

## 验收门

- PDF：能打开，页数合理；需要视觉时抽页渲染。
- PPT/PPTX：能打开或渲染预览；检查文字溢出、重叠、空白页。
- 图片/长图：尺寸合理、中文可读、无截断。
- quiz/flashcards：题目、答案、解析数量一致。
- mindmap：JSON / Mermaid / Markdown 可解析。
- NotebookLM：记录 notebook id、artifact id/下载路径；失败目标也要逐项记录。
- Open Design：区分 plugin apply、artifact create、export；缺 desktop renderer 时不能声称已导出。

公共匿名用例见 [examples.md](references/examples.md)。
