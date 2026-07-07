---
name: soia-pkm-alipan
version: 1.0.0
description: 阿里云盘原子操作层 — 安装/登录 aliyunpan CLI（含登录态过期处理、非交互环境取码技巧）、备份盘与资源库双盘切换（--driveId 显式传参）、目录浏览、移动/重命名/删除、下载上传、容量查询、全盘 JSONL 爬虫扫描方法论。是 soia-pkm-alipan-curator（整理顾问/学习计划）的底层依赖。当用户说「看下云盘」「云盘里有什么」「登录阿里云盘」「下载云盘文件」「云盘登录过期了」「全盘扫描一下云盘」时触发。
---

# soia-pkm-alipan — 阿里云盘原子操作层

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
4. **凭据**：登录态在 `~/.config/aliyunpan/`（或 `ALIYUNPAN_CONFIG_DIR`），不要 cat 打印 token。

## 深入实战手册

以下场景遇到时先读 `references/ops-playbook.md`（2026-07 云盘整理战役实战沉淀），不要重新试错：
- 安装/登录细节：两步授权+扫码流程、登录态约 3 天过期的症状与处理、非交互环境（无真 TTY）取二维码链接的技巧（伪终端 pty / 长驻进程读 stdout）
- `--driveId` 显式传参铁律：为什么绝不能用 `aliyunpan drive <id>` 切全局盘（多代理并发会互相污染当前盘上下文）
- 批量操作实战坑：批量 rename 的 cd 依赖坑与恢复方法、`ll` 输出里的 FILE ID 与直达链接拼法、移动改名不改 file_id 但跨盘移动会换 file_id、删除进回收站 30 天且回收站清空才真正释放配额
- 全盘 JSONL 爬虫方法论：Python DFS 遍历 + nohup 后台 + 断点续扫 + progress 心跳 + errors 落盘的完整设计，以及登录瞬断成批报错、目录名含特殊空格报"指定目录不存在"两大坑的处理方式，和海量碎片区（>200 文件）的聚合剪枝规则
- 防代理卡死纪律：长内容一律脚本落文件、对话回复限 15 行
