---
name: soia-meta-publish-market
description: 把已正式发版的技能上架到外部市场（腾讯 SkillHub、小红书 Red Skill）：筛选可独立运行的技能、叠加平台 frontmatter、预检后交由客户提交。触发：「上架 SkillHub」「发到 Red Skill」「上架技能市场」
version: 1.0.0
created_at: 2026-08-04 20:00:00
updated_at: 2026-08-04 20:00:00
created_by: claude fable 5
updated_by: claude fable 5
---

# soia-meta-publish-market

把**已经正式发版**的技能投递到外部市场。与插件市场（`soia` marketplace）不同，
外部市场一次只收一个技能，用户拿到的是**孤立的一份**——所以上架不是复制粘贴，
需要先筛选和改写。

> **执行前置：必须有客户当次的明确授权，且只上架已发版内容。**
> 上架是对外动作，且外部平台一旦收录就有审核与展示记录，撤回成本高于插件市场。
> 客户说「改一下这个技能」不等于「上架它」。另外**只投递 `main` 上的正式版**：
> dev 快照带 `-SNAPSHOT`，上架等于把开发中状态发给陌生用户。
> `--dry-run` 预检与 `--list-eligible` 盘点无需授权。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 看哪些技能能上架 | 扫全仓，按 hard 依赖筛选 | 逐技能的可否上架与原因 |
| 上架某个技能到 SkillHub | 打包 → 叠加平台字段 → `--dry-run` 预检 → 交客户提交 | 暂存路径、预检结果、待执行命令 |
| 发到小红书 Red Skill | 打包并给出上传指引 | 暂存路径与上传入口说明 |
| 更新已上架的技能 | 保持 slug 不变重新打包，提示填写变更说明 | 版本对比与 changelog 建议 |

### 客户如何使用

```bash
# 1. 看这个仓哪些技能可以上架
python3 scripts/stage_for_market.py --repo-dir <域仓路径> --list-eligible

# 2. 打包某一个（不会上传）
python3 scripts/stage_for_market.py --repo-dir <域仓路径> \
  --skill <技能名> --out <暂存目录> --display-name "<中文展示名>"
```

打包后由**客户本人**执行投递命令——见下方两个渠道。

### 依赖与安装

| 依赖 | 类型 | 缺失时怎么处理 |
|---|---|---|
| Python 3 | 强依赖 | 安装后重试 |
| `skillhub` CLI | SkillHub 渠道 | 见下方安装命令；未装则只做打包与预检说明 |
| SkillHub 实名认证 + API Token | SkillHub 渠道 | 未认证无法创建 Token，也无法发布；提示客户先完成 |
| 浏览器登录态 | Red Skill 渠道 | 客户在小红书创作服务平台自行操作 |

## 两条硬规则（决定了本技能怎么筛选和改写）

### 1. 只上架零 hard 依赖的技能

外部市场的用户**不会同时装我们仓里的同伴技能**。声明了 `dependencies.hard`
的技能到了那边是断链的——装了也跑不起来。脚本按此自动筛选，遇到 hard 依赖
直接拒绝打包并说明原因。`optional` 依赖不阻断，但应在简介里写一句「配合
某某技能效果更好」。

### 2. slug 用仓内技能名，展示名用中文

`slug` 必须全网唯一，我们的技能名已带 `soia-` 前缀，天然满足，且与仓内名
一一对应、便于追溯；`displayName` 另给中文可读名，面向普通用户。

```yaml
slug: soia-env-network-diagnose          # = 仓内技能名，勿改
displayName: 网络诊断助手                  # 中文，面向市场读者
summary: <一句话简介，缺省取 description>
license: MIT
```

平台字段**叠加**在原 frontmatter 之上，不替换——仓内的 `name`/`version`/
`created_by` 等字段保留，实测与平台字段共存不冲突。

## 渠道一：腾讯 SkillHub（CLI）

### 一次性准备（客户自行完成）

1. 手机号登录 <https://skillhub.cn> → 个人中心完成**实名认证**（未认证不能建 Token）
2. 个人中心 → API keys → 创建 → 复制 `skh_` 开头的 Token（**只显示一次**）
3. 安装 CLI 并登录：

```bash
curl -fsSL https://skillhub.cn/install/install.sh | bash -s -- --cli-only
```

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

```bash
skillhub login --key <你的Token> --host https://api.skillhub.cn
```

`skillhub auth whoami` 应输出 userId / handle / role 三行。

### 投递

```bash
skillhub publish <暂存目录>/<技能名> --dry-run
```

看到 `✓ Dry-run passed: <slug>@<version>` 表示格式合规。确认后由客户执行：

```bash
skillhub publish <暂存目录>/<技能名> --changelog "首次发布"
```

返回 `✓ Published: skillId=xxx status=pending_review` 即进入审核。更新时保持
slug 不变、改 version，`--changelog` 写本次变更。

**注意**：`publish` 是对外发布动作，本技能不代客户执行；预检 `--dry-run` 可代跑。

### 常见失败

| 现象 | 原因 |
|---|---|
| `403 请先完成实名认证` | 认证未完成 |
| `409 slug 已被占用` | 该 slug 全网已存在，换名 |
| `401 invalid api key` | Token 失效，重建 |

## 渠道二：小红书 Red Skill（浏览器）

入口：创作服务平台 → **Builder hub → Red Skill → 上传 Skill**。审核通过后可在
发布笔记页挂载，或通过评论区 `+` 号发出；用户在笔记里点「去使用」直接调用。

**上传表单的字段要求尚未实测**——「上传 Skill」按钮触发的是本地文件选择器，
表单结构无法从页面读取。首次上传时请记录实际要求（接受目录还是压缩包、有哪些
必填字段、审核周期），补进本节。

与 media 域的配合：`soia-media-publish-rednote-card` 产的笔记可以挂载对应的
Skill 卡片——内容讲场景、卡片直接转化，是同一平台内的闭环。

## 不负责什么

- **不代客户执行 `publish` 或点上传**。这两个动作会把内容送到外部平台并进入
  审核记录，必须由客户本人执行。本技能只做打包与预检。
- **不上架未发版内容**。只从域仓 `main`（正式版）打包；dev 快照带 `-SNAPSHOT`。
- **不改仓内技能**。打包在暂存目录进行，不回写源仓；要改依赖或描述请走正常
  PR 流程，发版后再上架。
- **不管插件市场**。`soia` marketplace 的 pin 刷新属 `soia-meta-skill-release`。

## 私密信息与中间数据

- **不读取、不回显、不存储 API Token**。登录由客户执行 `skillhub login` 完成，
  凭据存在 CLI 自己的配置里；本技能只调用 `skillhub auth whoami` 确认登录态。
- 暂存目录默认放系统临时目录，不进仓库；打包产物随时可重新生成。

## 日志与完成回执

| 技能 | 渠道 | slug | 版本 | 预检 | 状态 |
|---|---|---|---|---|---|
| `<skill>` | SkillHub / Red Skill | `<slug>` | `<version>` | passed / failed | 待客户提交 / 已提交待审核 |

## 前向测试

- `--list-eligible` 能正确区分零 hard 依赖与有 hard 依赖的技能
- 对有 hard 依赖的技能执行打包时报错并说明原因，不产出暂存目录
- 打包后 frontmatter 同时含平台字段与原字段，正文一字不改
- `--display-name` 缺省时回落到原 `name`，`--summary` 缺省时回落到 `description`
