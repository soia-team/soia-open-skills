---
name: soia-pkm-alipan-drive-ops
description: 阿里云盘原子操作层：安装/登录 aliyunpan、显式 driveId 双盘操作、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 扫描。作为 curator 的底层依赖。Triggers：「看下云盘」「云盘里有什么」「登录阿里云盘」「下载云盘文件」「云盘登录过期了」「全盘扫描云盘」
version: 2.2.1
created_at: 2026-07-02 23:02:39
updated_at: 2026-07-20 23:28:35
created_by: claude opus 4.6
updated_by: Claude Fable 5
---

# soia-pkm-alipan-drive-ops — 阿里云盘原子操作层

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-alipan-drive-ops -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-alipan-drive-ops/config.yml
SOIA_PKM_ALIPAN_DRIVE_OPS_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- 强依赖、可选依赖和第三方 skill 关系必须以本 `SKILL.md` 后续的“依赖 / 前置 / 资源 / 边界”说明为准；没有写清楚时，先补说明或询问客户，不要猜。
- 第三方 skill 只能声明依赖和安装方式，不直接修改第三方 skill 文件。

### 私有配置加载与命令入口

以下命令从本 skill 目录执行；若当前目录不同，请将 `scripts/run_with_env.py` 换成 `<skill-dir>/scripts/run_with_env.py`。运行 `aliyunpan` 时，优先使用本技能的包装器加载私有配置，再执行命令：

```bash
python3 scripts/run_with_env.py -- aliyunpan who
python3 scripts/run_with_env.py -- aliyunpan quota
python3 scripts/run_with_env.py -- aliyunpan ls --driveId "$DRIVE_ID" "/目标目录/"
```

包装器只会启动 `aliyunpan`、`aliyunpan.exe` 或 basename 为两者之一的绝对路径；它会拒绝 `env`、shell 和其他任意命令。包装器会读取本技能私有 `config.yml` 的 `env:` 映射，并在子进程中加载
`ALIYUNPAN_CONFIG_DIR`。这样 Homebrew 安装的 `aliyunpan` 也会使用同一份指定登录态，避免与默认的 `~/.config/aliyunpan/` 形成两套会话。配置文件只应由包装器读取；`alipan_env.py` 仅供脚本作为模块加载，直接运行时不会输出配置。不要执行 `cat config.yml`、`env`、`printenv` 或 `set -x` 来排查配置。

直接运行 `aliyunpan <command>` 仍保持兼容，适用于使用 provider 默认登录态的场景；但配置了私有 `ALIYUNPAN_CONFIG_DIR` 后，优先使用上面的包装器，避免命令落到另一套登录态。日志和回复中只能说明配置是否存在或命令是否成功，**不得打印 token、cookie、session 或任何环境变量的值**。

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
python3 scripts/run_with_env.py -- aliyunpan login
# 3. 验证
python3 scripts/run_with_env.py -- aliyunpan who
python3 scripts/run_with_env.py -- aliyunpan quota
```

如果尚未配置私有 `ALIYUNPAN_CONFIG_DIR`，上述登录和验证命令也可以直接写成 `aliyunpan login`、`aliyunpan who` 和 `aliyunpan quota`。

## 登录失效的远程协作恢复

当云盘命令返回「尝试登录失败，请使用 login 命令进行重新登录」，即判定登录态失效；这不是要求用户到 agent 所在终端扫码的硬阻塞。按以下流程远程恢复：

1. 在非交互环境以 pty 启动 `python3 scripts/run_with_env.py -- aliyunpan login`，并保持其 stdin 可读；**不得**将 stdin 重定向为 `</dev/null`，否则登录程序在“按 Enter 继续”处读到 EOF 而失败。用已验证的 `tail -f` 保活方案与完整命令见 [ops-playbook §1.4](references/ops-playbook.md#14-非交互环境取登录链接标准恢复流程)。
2. 从 pty 输出按“到空格为止”完整抓取授权链接，不能用字符白名单正则截取：`scope` 参数含 `:`、`,`。仅把完整链接推送给本任务的授权用户本人，绝不打印 token、cookie、session 或其他凭据。
3. 明确告知链接仅 **5 分钟**有效；过期后重新启动登录并发送**新链接**，不要让用户重试旧链接。用户在浏览器完成授权与扫码两步后，确认已完成。
4. 收到用户确认后才向保活 stdin 喂一个 Enter，使登录进程继续；随后用 `python3 scripts/run_with_env.py -- aliyunpan who` 验证返回 UID，并清理对应的 `tail -f` 辅助进程。
5. 长任务以已有 ledger、progress 或断点续跑机制衔接；等待授权期间优先推进不依赖云盘的工作，不要空等或从头重跑。若失效发生在高密度并发 listing，续扫须降低 workers，并遵守批量 listing 至少 300 ms 的节流；详见 [ops-playbook「API 限流与 429 纪律」](references/ops-playbook.md#25-api-限流与-429-纪律2026-07-17-调研及本-run-校准)。

纪律：绝不尝试读取、复制或转发登录凭据文件；授权链接只可发给该任务的授权用户本人。

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
   `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-alipan-drive-ops/config.yml`（见 `config.example.yml`）。
   运行命令优先使用 `python3 scripts/run_with_env.py -- aliyunpan <command>` 加载该 override；任何日志、诊断输出和最终回执都不得打印 token 或 env 值。
5. **删除/移动/重命名前先确认**：命中路径、显式技能调用、任何默认配置都只是推荐输入，不构成跳过确认的理由；唯一跳过条件是客户当前这句话明确说"直接删/不用确认"，跳过后要在回执里说明本次沿用的范围假设。
6. **批量前先小样本探测**：批量 `mv`/`rm`/`rename` 前，先用最小样本（如 1 条）跑一遍并汇报预计总量，客户确认规模无误后再放开全量执行，不要对着未知规模的目录直接下手。
7. **限流先服从再恢复**：批量写操作按每次 200–300 ms 节流，批量 listing 不低于每次 300 ms；收到 429 时读取 `x-retry-after` 并等待，绝不连续重试。详见 ops-playbook 的「API 限流与 429 纪律」。

## 深入实战手册

以下场景遇到时先读 `references/ops-playbook.md`（2026-07 云盘整理战役实战沉淀），不要重新试错：
- 安装/登录细节：两步授权+扫码流程、登录态约 3 天过期的症状与处理，以及非交互环境标准远程恢复的第一步（伪终端 pty / 长驻进程读 stdout）；完整恢复流程见上文「登录失效的远程协作恢复」
- `--driveId` 显式传参铁律：为什么绝不能用 `aliyunpan drive <id>` 切全局盘（多代理并发会互相污染当前盘上下文）
- 批量操作实战坑与限流纪律：批量 rename 的 cd 依赖坑、API 桶与 429 等待、`ll` 输出里的 FILE ID 与直达链接拼法、移动改名不改 file_id 但跨盘移动会换 file_id、删除进回收站 30 天且回收站清空才真正释放配额
- 全盘 JSONL 爬虫：**已脚本化为 `scripts/scan_drive.py`**（参数化 DFS + 线程池 + 重试 + 断点续扫 + 聚合剪枝 + 敏感目录不下钻）；输出保留目录名原始连续空格，并记录 file_id、大小与 SHA-1。同名兄弟目录会各自标记 `ambiguous_name: true` 且全部不下钻，`.errors` sidecar 同步记录 `AMBIGUOUS_NAME`，使消费端 fail-closed；必须先 rename 消歧，再定向重扫该子树。用法见 ops-playbook §三。**完整图书馆流水线** = `scan_drive.py`（实盘→JSONL）→ alipan-curator 的 `gen_catalog.py`（JSONL→折叠树总览+全文检索）。登录瞬断、历史解析器折叠特殊空格与同名遮蔽三坑的处理见 ops-playbook。`scan_drive.py` 产出的 `.errors`/`.progress`/`.done` sidecar 刻意与 `--out` 主产出同目录、同生命周期——断点续扫（`--resume`）靠 sidecar 定位进度（`.done` 逐行记录已完整列出的目录，是续扫的权威断点）、质量核对要和主产出对得上，这是设计而非遗漏，不要挪去临时目录
- 防代理卡死纪律：长内容一律脚本落文件、对话回复限 15 行
