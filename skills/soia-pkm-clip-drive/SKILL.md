---
name: soia-pkm-clip-drive
description: 把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理。Triggers：「导入云盘资料」「把这批 PDF 导进来」「clip 这个文档」「整理云盘」
---

# soia-pkm-clip-drive

`clip` 家族的**云盘成员**：把网盘 / 本地的存量资料（PDF、DOCX 等）导入 vault。区别于抓网页，它处理**本地 / 云盘文件**。

## 客户可读说明

### 这个技能可以做什么

把云盘/本地的存量资料（PDF/Word/文档）批量导入 Obsidian vault。提取文本、生成资料笔记，归入资料库或文章摘抄，再交给 organize 整理

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-clip-drive -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-drive/config.yml
SOIA_PKM_CLIP_DRIVE_CONFIG_FILE=<custom-config-path>
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

## 处理

- 输入：文件路径 / 目录（PDF、DOCX、TXT、Markdown）
- 提取：`pypdf` / `pdfplumber`（PDF）、`python-docx`（Word）提取文本；原文件留到 `_附件/`。
- 大批量：目录批处理，每个文件 → 一篇笔记。
- 脚本：`scripts/import_drive.py <路径> --vault <path> [--recursive]`。

## 落地

- 资料 / 参考类 → `<vault-resources-dir>/<主题>/`；文章类 → `<vault-articles-dir>/`（由配置或 CLI 参数决定）。
- frontmatter：`tags:[资料]` 或 `[文章摘抄]`、`source: 云盘/pdf`、`original_path`、`captured_at`、`topics:[]`。
- 导入后**必走 `organize`**：云盘资料通常量大又杂，靠 organize 分类 / 建 MOC / 去重。

## 闭环位置

`★clip-drive(收) → organize（云盘资料尤其依赖整理） → distill → …`。


---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接的下一个 skill）。
