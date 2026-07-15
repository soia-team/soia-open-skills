---
name: soia-pkm-baidupan
description: 百度网盘原子操作层：基于百度官方 baidu-drive Skill 与 bdpan CLI，完成登录、目录浏览、搜索、上传下载、分享转存、移动复制、重命名、建目录和只读 JSONL 扫描；记忆备份/恢复交由官方 Skill 处理。Triggers：「看下百度网盘」「百度网盘里有什么」「登录百度网盘」「下载百度网盘文件」「扫描百度网盘」「备份记忆」「查看记忆备份」「恢复记忆」
---

# soia-pkm-baidupan — 百度网盘原子操作层

## 客户可读说明

本技能把百度官方 `baidu-drive` Skill 和 `bdpan` CLI 接入 PKM 工作流，负责安全的百度网盘原子操作与只读资源扫描。

## 定位

本技能是 PKM 层的百度网盘适配器，默认使用百度官方公开的 [`baidu-drive`](https://github.com/baidu-netdisk/bdpan-storage/tree/main/skills/baidu-drive) Skill 及其 `bdpan` CLI。上游 Skill 负责 CLI 安装、授权和基础命令；本技能补充面向 PKM 的安全边界、只读扫描和标准 JSONL 输出。

它不负责自动整理目录、生成馆藏或制定学习计划；这些应由上层 curator 技能消费扫描结果。

## 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 登录或验证百度网盘 | 检查 `bdpan`、版本和登录态；按官方脚本完成授权 | 官方授权地址、非敏感状态和验证结果；不显示 token 或配置文件 |
| 查目录或搜索文件 | 使用 `ls --json` / `search --json` | 远端范围、条目和失败原因 |
| 传输或管理文件 | 上传、下载、分享、转存、移动、复制、重命名、建目录 | 预期范围、执行结果、冲突策略和终态核对 |
| 建立全盘索引输入 | 运行只读 DFS，生成 JSONL 及 `.errors`/`.progress`/`.done` sidecar | 扫描统计、错误数量和产出位置 |

官方 `bdpan` 有意不提供删除命令。本技能不通过其他客户端补充删除，也不使用网页 Cookie、BDUSS 或未公开接口。

### 客户如何使用

用自然语言说明目标，并提供远端虚拟路径（如 `/资料`）和必要的本地目标路径。Agent 会先检查依赖和登录态；涉及上传、下载、分享、转存或远端整理时，会先展示精确范围和冲突策略，再在获得确认后执行并回读验证。

## 依赖与安装

优先安装百度官方上游 Skill：

```bash
npx skills add https://github.com/baidu-netdisk/bdpan-storage/skills --skill baidu-drive
```

随后严格按上游 `baidu-drive/SKILL.md` 操作：

1. 由上游 `scripts/install.sh` 安装 `bdpan`（当前上游安装器版本需以仓库为准；安装脚本从百度 CDN 下载，执行前应审查脚本和网络来源）。
2. 登录只使用上游 `scripts/login.sh`。不要让 Agent 直接执行 `bdpan login`，也不要代替用户输入账号、密码、验证码或授权码。
3. 运行 `bdpan whoami` 验证登录态。

上游 Skill 的路径是它自己的安装目录，不要把本技能目录误当成上游目录；缺少上游 Skill 时应停止并提示安装依赖。安装、登录和更新都需要用户明确意图，不要静默执行，也不要使用 `--yes` 绕过确认。

本技能不需要 AppKey、SecretKey、`BAIDUPAN_APP_NAME` 或自建 OAuth 配置。社区项目 [`mqhe2007/baidupan-cli`](https://github.com/mqhe2007/baidupan-cli) 只作为备选参考，不是默认后端；详见 [provider-cli.md](references/provider-cli.md)。

## 私密配置与路径合同

- 官方 provider 配置由 `bdpan` 自己维护在 `~/.config/bdpan/config.json`。Agent 不读取、不打印、不复制该文件，也不主动设置 `BDPAN_CONFIG_PATH`、`BDPAN_BIN` 或 `BDPAN_INSTALL_DIR`。
- 官方应用隔离根是 `/apps/bdpan/`；用户可见名称通常是 `我的应用数据/bdpan/`。对用户展示和命令输入使用相对路径或本技能虚拟路径，例如 `/资料`、`/资料/a.pdf`，不要把完整 provider 前缀暴露给用户。
- 禁止路径包含 `..` 或 `~`，也不要把本地绝对路径当成远端路径。写入前检查源、目标父目录和冲突策略。
- `bdpan` 的 JSON 字段以 `fs_id`、`server_filename`、`isdir`、`size`、`md5`、`server_mtime` 为主；解析器仅兼容等价大小写字段，不解析人类表格。

## 标准工作流

### 1. 安装与登录

```bash
command -v bdpan
bdpan version
bdpan whoami
```

若 `bdpan` 不存在，先请用户确认，再运行上游安装脚本。若登录失效，运行上游 `scripts/login.sh`，不要直接调用 `bdpan login`。登录后再次执行 `bdpan whoami`；不要把授权码或 token 写入回执。

### 2. 只读操作

```bash
bdpan ls --json
bdpan ls 资料 --json
bdpan search "关键词" --json
bdpan whoami
```

优先读取已有扫描/索引产物；只有没有可用产物时才扫描远端。目录不存在、权限不足、非零退出码或扫描出现 `LIST_FAIL` 时，不得把结果说成“空目录”。

### 3. 远端写操作

先用 `ls --json` 检查源和目标父目录，再明确确认精确范围、冲突策略和是否允许部分成功：

```bash
bdpan mkdir 资料/新目录
bdpan mv 资料/旧名 资料/
bdpan cp 资料/a.pdf 备份/
bdpan rename 资料/旧名 新名
```

所有写操作都要在执行后重新列受影响目录或核对目标。`share` 会调用可能收费的能力，必须单独提醒并获得确认：

```bash
bdpan share 资料/a.pdf --period 7 --json
bdpan transfer '<share-url>' -p '<提取码>' --json
```

### 4. 上传与下载

```bash
bdpan upload <local-file> 资料/
bdpan download 资料/a.pdf <local-file>
bdpan download '<share-url>' <local-dir> -p '<提取码>'
```

单文件上传的远端目标需包含文件名；目录上传以 `/` 结尾。覆盖、大文件、批量任务和分享转存都要先确认，完成后核对本地文件存在性、大小，必要时独立计算哈希。终端超时不等于传输失败，应先查询任务/目标状态再决定是否重试。

### 5. 全盘只读 JSONL 扫描

扫描器只调用 `bdpan ls --json`，将条目归一化为 `path`、`name`、`id`、`dir`、`size`、`sha1`，并保留 `md5`、`mtime`：

```bash
python3 <skill-path>/scripts/scan_drive.py \
  --root / \
  --out <user-output-dir>/baidupan-scan.jsonl \
  --workers 4 --resume
```

可重复使用 `--root /资料` 限制范围；使用 `--no-descend <目录名>` 跳过目录递归；使用 `--resume` 通过 sidecar 跳过已完成目录。扫描本身不修改远端。

收尾必须检查进程退出码、主 JSONL、`.errors`、`.done` 和统计。存在错误时交付“部分扫描”，不要交付“全盘完成”。

## 记忆备份与恢复提醒

官方 `baidu-drive` Skill 内置记忆备份/恢复；这不是另一个必须安装的 Baidu Drive Backup Plugin。只有当前环境属于 KimiClaw、MaxClaw、QClaw 或 OpenClaw 时，才按上游 Skill 的能力处理：

- “备份记忆”“把记忆存到网盘” → `backup`。
- “查看记忆备份”“备份列表” → `list`。
- “恢复记忆”“还原记忆”“恢复 2026-03-16 的备份” → `restore`；必须先确认日期，不能默认恢复最新备份。
- “帮我记住……”“整理/清理记忆”是本地记忆操作，不触发网盘备份；“备份代码/文件”也不是记忆备份。
- 记忆操作必须调用上游 Skill 自己的 `scripts/memory-backup.sh`，不能裸调用 `bdpan upload/download`。恢复前的本地 safety-net、manifest 和环境检测由上游脚本负责；本技能不复制这些脚本，也不读取记忆文件。
- 如果当前不是上述四种环境，明确说明不支持，不执行任何备份/恢复命令。

上游脚本路径以实际安装的 `baidu-drive` Skill 为准，不要把 `<skill-path>` 替换成本技能目录。

## 与 curator 的边界

本技能只负责 provider 连接、原子操作和标准化扫描输入；不复制 `soia-pkm-alipan-curator` 的阿里云盘特定动作。两个 provider 可以共享 curator 消费的 JSONL 合同，但不应把百度官方 CLI、阿里云盘 CLI 和高风险整理决策合并到一个触发器中。未来若需要百度版 curator，应复用上层的 inventory/catalog/plan 思路，并通过 provider adapter 注入能力。

## 日志与完成回执

每次执行都要回报：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <CLI/版本/登录态检查，不打印秘密值>
- processed: <远端路径或扫描范围；数量如可得>
- created/updated: <数量或用户指定产物>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <whoami/ls/本地字节数/扫描 sidecar 等证据>

问题与下一步：
- <缺依赖、待确认事项或建议命令；没有则写“无”>
```

## 验证证据

- 静态：`quick_validate.py skills/soia-pkm-baidupan`、`scripts/audit_skills.py`、`git diff --check`。
- 前向：`tests/test_baidupan_scan.py` 用临时 fake `bdpan` 子进程验证官方 JSON 字段、两层目录转换、干净 JSONL、`.errors` 和 `.done` sidecar。
- 未做：未使用真实百度账号做端到端上传、分享或转存测试；真实运行仍需按官方登录、用户确认和终态复核门禁执行。
