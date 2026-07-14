---
name: soia-pkm-alipan
description: 阿里云盘原子操作层：安装/登录 aliyunpan、显式 driveId 双盘操作、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 扫描。作为 curator 的底层依赖。Triggers：「看下云盘」「云盘里有什么」「登录阿里云盘」「下载云盘文件」「云盘登录过期了」「全盘扫描云盘」
---

# soia-pkm-alipan — 阿里云盘原子操作层

## 客户可读说明

### 这个技能可以做什么

阿里云盘原子操作层：安装/登录 aliyunpan、显式 driveId 双盘操作、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 扫描。作为 curator 的底层依赖

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-alipan -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-alipan/config.yml
SOIA_PKM_ALIPAN_CONFIG_FILE=<custom-config-path>
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

## 定位

对标 weread-skills 之于微信读书：只提供**可靠的原子操作**，不做业务判断。整理策略、学习计划等高阶活交给 `soia-pkm-alipan-curator`。

## 接入三步（新用户引导）

```bash
# 1. 安装（macOS，brew 官方 formula）
brew install aliyunpan          # 更新: brew upgrade aliyunpan
# 2. 登录（扫码，需用户本人在终端操作）
aliyunpan login
# 3. 验证
aliyunpan who && aliyunpan quota
```

## 双盘模型（关键概念）

一个账号两个盘，**共享同一容量配额**（用 `aliyunpan quota` 看总量）：
- **备份盘** / **资源库**：`aliyunpan drive` 列出各盘 DriveID
- 所有 `ls/mv/rename` 只作用于**当前盘**；跨盘移动 CLI 不支持，需在 App 里手动操作
- ⚠️ **不要用 `aliyunpan drive <driveId>` 做全局切换**：该命令写全局配置，多代理/多脚本并发时会互相污染当前盘上下文。铁律是**每条命令都显式带 `--driveId`**（如 `aliyunpan ls --driveId <id> "/路径"`），而不是切换后再跑无盘参数的命令。详见 `references/ops-playbook.md` 一.5。

## 常用命令

| 操作 | 命令 | 注意 |
|---|---|---|
| 列目录 | `aliyunpan ls "/路径"` | 中文路径加引号 |
| 移动 | `aliyunpan mv "/源" "/目标目录/"` | 支持多源；只能同盘 |
| 重命名 | `aliyunpan rename "/旧全路径" "/新全路径"` | 必须同目录内 |
| 建目录 | `aliyunpan mkdir "/路径"` | 一次一个最稳 |
| 删除 | `aliyunpan rm "/路径"` | 进回收站，30 天可恢复 |
| 下载 | `aliyunpan download "/路径" --saveto <本地目录>` | 大文件耗时，告知用户 |
| 容量 | `aliyunpan quota` | 87%+ 时提醒用户清理 |

## 输出解析（脚本化必读）

`ls` 输出为表格：`序号 · 文件大小(目录为"-") · 日期 时间 · 名称(目录以/结尾，可能带尾随空格)`。
提取目录名的可靠 sed：

```bash
aliyunpan ls "$DIR" </dev/null 2>/dev/null | \
  sed -nE 's#^[[:space:]]+[0-9]+[[:space:]]+-[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}[[:space:]]+(.*)$#\1#p' | \
  sed -E 's#[[:space:]]+$##; s#/$##'
```

- 循环内所有 aliyunpan 命令加 `</dev/null`，防止其吞掉 while 循环的 stdin
- 批量操作后**必须终态验证**（重新 ls 对照），逐条回显"✓/✗"

## 安全守则（实战教训，必守）

1. **工具输出不可盲信**：出现物理不可能的结果（同目录同名多项、行数与字节矛盾）→ 疑似输出被污染，换通道交叉验证（Read vs Bash），或请用户在 App 亲眼核对后再继续。
2. **删除/覆盖前先看**：`rm` 前先 `ls` 确认内容；同名冲突会自动加 `(1)` 后缀——移动前查目标是否已存在，避免产生 `xxx(1)` 重复目录。
3. **高危操作留人**：清空目录、批量删除、跨盘手动迁移，列清单请用户确认或亲手操作。
4. **凭据**：登录态属于 aliyunpan provider，默认在 `~/.config/aliyunpan/`，不要搬进 skill，也不要 cat 打印 token。若需要改登录态目录，只把 `ALIYUNPAN_CONFIG_DIR` 这个 override 放进本技能私有配置：
   `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-alipan/config.yml`（见 `config.example.yml`）。
5. **删除/移动/重命名前先确认**：命中路径、显式技能调用、任何默认配置都只是推荐输入，不构成跳过确认的理由；唯一跳过条件是客户当前这句话明确说"直接删/不用确认"，跳过后要在回执里说明本次沿用的范围假设。
6. **批量前先小样本探测**：批量 `mv`/`rm`/`rename` 前，先用最小样本（如 1 条）跑一遍并汇报预计总量，客户确认规模无误后再放开全量执行，不要对着未知规模的目录直接下手。

## 深入实战手册

以下场景遇到时先读 `references/ops-playbook.md`（2026-07 云盘整理战役实战沉淀），不要重新试错：
- 安装/登录细节：两步授权+扫码流程、登录态约 3 天过期的症状与处理、非交互环境（无真 TTY）取二维码链接的技巧（伪终端 pty / 长驻进程读 stdout）
- `--driveId` 显式传参铁律：为什么绝不能用 `aliyunpan drive <id>` 切全局盘（多代理并发会互相污染当前盘上下文）
- 批量操作实战坑：批量 rename 的 cd 依赖坑与恢复方法、`ll` 输出里的 FILE ID 与直达链接拼法、移动改名不改 file_id 但跨盘移动会换 file_id、删除进回收站 30 天且回收站清空才真正释放配额
- 全盘 JSONL 爬虫：**已脚本化为 `scripts/scan_drive.py`**（参数化 DFS + 线程池 + 重试 + 断点续扫 + 聚合剪枝 + 敏感目录不下钻）；输出保留目录名原始连续空格，并记录 file_id、大小与 SHA-1。用法见 ops-playbook §三。**完整图书馆流水线** = `scan_drive.py`（实盘→JSONL）→ alipan-curator 的 `gen_catalog.py`（JSONL→折叠树总览+全文检索）。登录瞬断、历史解析器折叠特殊空格两坑的处理见 ops-playbook。`scan_drive.py` 产出的 `.errors`/`.progress` sidecar 刻意与 `--out` 主产出同目录、同生命周期——断点续扫（`--resume`）靠 sidecar 定位进度、质量核对要和主产出对得上，这是设计而非遗漏，不要挪去临时目录
- 防代理卡死纪律：长内容一律脚本落文件、对话回复限 15 行
