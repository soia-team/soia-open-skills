---
name: soia-meta-publish-market
description: 把已正式发版的技能上架到外部市场（腾讯 SkillHub、小红书 Red Skill）：筛选可独立运行的技能、叠加平台 frontmatter、预检后交由客户提交。触发：「上架 SkillHub」「发到 Red Skill」「上架技能市场」
version: 1.5.0
created_at: 2026-08-04 20:00:00
updated_at: 2026-08-08 17:30:00
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
| 上架前检查技能是否就绪 | 打包并对暂存产物跑 R1-R6 就绪门禁 | 逐项通过/警告/硬缺口报告，硬缺口拒绝打包 |

### 客户如何使用

```bash
# 1. 看这个仓哪些技能可以上架
python3 scripts/stage_for_market.py --repo-dir <域仓路径> --list-eligible

# 2. 打包某一个（不会上传；按渠道过滤文件）
python3 scripts/stage_for_market.py --repo-dir <域仓路径> \
  --skill <技能名> --out <暂存目录> --channel skillhub|redskill \
  --display-name "<中文展示名>"

# 3. 发版前咨询：对工作树跑一遍就绪门禁，不留产物（见「上架就绪门禁」）
python3 scripts/stage_for_market.py --repo-dir <域仓路径> \
  --skill <技能名> --out <暂存目录> --allow-unreleased --check-only
```

**打包内容直接从 `origin/main` 导出**，不读工作副本——本地检出在哪个分支都不影响
结果，也就不会因为有人切走分支而误打包未发布内容（多 AI 共用检出时这是常态）。
`main` 上没有该技能、或 main 版本带 `-SNAPSHOT`，一律拒绝打包。

`--channel redskill` 时 **`--display-name` 是必填**，缺省直接拒跑，原因见
[展示名与平台主键](#展示名与平台主键必填)。

打包后由**客户本人**执行投递命令——见下方两个渠道。

### 依赖与安装

| 依赖 | 类型 | 缺失时怎么处理 |
|---|---|---|
| Python 3 | 强依赖 | 安装后重试 |
| `skillhub` CLI | SkillHub 渠道 | 见下方安装命令；未装则只做打包与预检说明 |
| SkillHub 实名认证 + API Token | SkillHub 渠道 | 未认证无法创建 Token，也无法发布；提示客户先完成 |
| `@xhs/skillhub-upload` | Red Skill 渠道（路径 A） | 未装则改走网页上传（路径 B），或提示客户先装 |
| 浏览器登录态 | Red Skill 渠道（路径 B） | 客户在小红书创作服务平台自行操作 |

## 两条硬规则（决定了本技能怎么筛选和改写）

装整个域（Claude Code 与 Codex 共用同一份域插件）：

```bash
claude plugin marketplace add soia-team/soia-open-skills
claude plugin install soia-meta@soia
```

只装这一个技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-publish-market -y
```

**WorkBuddy** 的装载单位是角色化专家而不是插件，`npx skills add -a '*'` 覆盖不到它，需要单独安装，见 [docs/install/workbuddy.md](https://github.com/soia-team/soia-open-skills/blob/main/docs/install/workbuddy.md)。

### 1. 只上架零 hard 依赖的技能

外部市场的用户**不会同时装我们仓里的同伴技能**。声明了 `dependencies.hard`
的技能到了那边是断链的——装了也跑不起来。脚本按此自动筛选，遇到 hard 依赖
直接拒绝打包并说明原因。`optional` 依赖不阻断，但应在简介里写一句「配合
某某技能效果更好」。

### 2. 只有正式版能上市场（硬门禁）

市场拿到的是最终用户直接使用的东西，必须是已发版内容。脚本**直接从
`origin/main` 导出**，而不是校验工作副本——后者依赖检出在哪个分支，不可靠。

| 情况 | 结果 |
|---|---|
| main 上有该技能且版本无 `-SNAPSHOT` | 导出并打包 |
| main 上没有该技能 | 拒绝：「尚未发版，不能上架」 |
| main 版本带 `-SNAPSHOT` | 拒绝：「不是正式版」 |

`--allow-unreleased` 仅供本地演练，**不得用于真实上架**。

### 4. 上架就绪门禁（打包后机器检查）

外部市场会用 AI 评测上架的技能，历史评语点名过的缺口类型在打包阶段就要被机器
查出来——有硬缺口直接拒绝打包，不让它流到市场上去挨评。门禁细节见下方
[上架就绪门禁](#上架就绪门禁)。

## 上架就绪门禁

外部市场（腾讯 SkillHub 等）会用 AI 评测上架的技能。历史评语点名过几类缺口——
没有能力边界、没有触发词、没有真实输出样例、没有测试保障、依赖源全境外——这些
**在打包阶段就被机器检查出来**，有硬缺口直接拒绝打包，不让它流到市场上去挨评。

`stage_for_market.py` 打包后对**暂存产物**（不是仓库）跑五道检查：

| 编号 | 检查 | 等级 | 判据 | 修复指引 |
|---|---|---|---|---|
| R1 | 能力边界 | 硬缺口 | SKILL.md 没有含「不负责」/「能力边界」的标题节 | 补一节「不负责什么」，用两三行说清不做什么 |
| R2 | 触发词 | 硬缺口 | frontmatter `description` 不含「触发」/「Triggers」 | 在 description 里写明触发场景，例如「触发：…」 |
| R3 | 输出样例 | 硬缺口 | 没有含真实数据的「样例/示例」小节；全是 `<占位符>` 的表格不算 | 给出一节真实输入→输出的样例表格 |
| R4 | 测试证据 | 硬缺口 | `tests/` 里没有只引用本技能与标准库的专属自包含测试；或有但进包后跑不起来 | 给技能写一个自包含的最小测试：只引用本技能包内文件与标准库；引用其他技能名的共享测试不进包 |
| R5 | 境外源提示 | 警告 | 包内只有境外 URL（无 `.cn`/npmmirror 等境内源） | 优先替换为国内可访问的安装源或镜像 |
| R6 | 安全预检 | 硬缺口 | 包内含疑似凭据样式串（npm_/ghp_/xox 等前缀+长随机段）、以 `npm_` 开头的小写标识符（安全扫描按密钥前缀误报，云鼎 2026-08-08 实报 ai-cli-upgrade 健康度 47）、或 pipe-to-shell 命令字样（`curl … \| sh`） | 真凭据移除、占位符换明显假值；标识符更名避开前缀；安装建议改「下载→审阅→本地执行」表述 |

门禁行为：逐项打印通过/警告/硬缺口；存在**硬缺口** → 删除暂存目录并拒绝打包
（退出码 1）；只有警告 → 照常产出。R4 只收「专属」测试——只引用本技能包内
文件与标准库的自包含测试，会**拷贝进包**作为证据，并在包的布局里实跑；引用
其他技能名的跨技能共享测试不进包（归仓级 CI 管），只在报告里提示跳过。

本门禁不预测评测分数，只消除历史评语点名过的缺口类型。

### 咨询用法：--check-only

```bash
# 对工作树做就绪检查（不导出 main、不留暂存产物，只出报告）
python3 scripts/stage_for_market.py --repo-dir <域仓路径> \
  --skill <技能名> --out <暂存目录> --allow-unreleased --check-only
```

`--check-only` 走完整个打包+门禁流程后删除暂存产物，只留报告——适合在 PR 阶段
先跑一遍咨询，不必等发版。与 `--allow-unreleased` 组合即「对工作树做咨询检查」。

### 3. slug 用仓内技能名，展示名用中文

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

## 渠道二：小红书 Red Skill

Red Skill 有**两条上传路径**，都由小红书官方工具承担投递，本技能只负责前置打包。

### 路径 A：官方 uploader 技能（推荐，AI 驱动）

小红书发布了 `@xhs/skillhub-upload` —— 一个 CLI + 配套技能，由 AI 助手驱动完成
授权、打包、上传与提交。**不要自己实现上传逻辑**：接口与字段由平台方维护，
自造一份必然漂移。

一次性准备（客户自行执行）：

```bash
npm install -g "https://fe-video-qc.xhscdn.com/fe-platform-file/104101b83221qt9bu7k0653u0hejenq0004pf88k9rpr6a.tgz"
```

安装**不会自动注册技能**，还要把包内的 SKILL.md 复制进 agent 的技能目录：

```bash
mkdir -p <agent-skills-dir>/skillhub-upload
cp "$(npm root -g)/@xhs/skillhub-upload/skill/SKILL.md" \
   <agent-skills-dir>/skillhub-upload/SKILL.md
```

之后把本技能产出的暂存目录交给它：

> 请按照 https://redskill.xiaohongshu.net/uploader.md 中的说明帮我把
> `<暂存目录>/<技能名>` 上传到小红书 SkillHub

官方技能接手后的流程（了解即可，不由我们实现）：`whoami` 查授权 →
`login --agent` 出授权链接与用户码（手机浏览器打开跳 App）→ 拉实时标签列表 →
问 source（原创/转载）与 tag → `publish --dry-run --agent` 出待提交载荷供审阅 →
用户明确说「提交」后才真实提交。

要点：**Skill ID 是平台主键、跨版本不可改名**，dry-run 阶段若提示无法自动派生，
需慎重确认后用 `--identifier` 指定。

#### 实测要点（2026-08-05 跑通全链得到）

**Red Skill 有文件类型白名单，SkillHub 没有。** 同一份技能目录，SkillHub
`--dry-run` 直接通过，Red Skill 却报
`目录中包含不支持上传的文件：agents/openai.yaml，请移除后重试`——它只收
`.md/.txt/.html/.css/.js/.py/.json/.xml`，我们的 `agents/openai.yaml`（Codex
界面元数据）不在其中。因此打包必须带 `--channel redskill` 做剔除；剔除后
dry-run 通过，payload 里 `version` 正是 main 的正式版号。

**CLI 输出是 `RESULT_JSON:` 结构化行。** 实测 PATH 上的 `skillhub-upload`
shim 在某些环境下吞掉输出（命令静默、退出码 0），直接调
`node "$(npm root -g)/@xhs/skillhub-upload/cli/index.mjs" <子命令>` 才能看到。
排障时先用这条确认，别把静默当成功。

**`--dry-run` 不需要授权**，只有真提交才需要；所以预检可以随时跑。

**CLI 只支持首发，更新版本走网页。** 实测 2026-08-06：技能 1.2.0 审核通过、
生效中后，用 CLI 对同一 Skill ID 提交 1.3.1 被拒
`SUBMIT_REJECTED: Skill ID 已被占用`（首发响应里的 `first_version: true` 也是
旁证）。已上架技能的版本更新走创作平台 Builder hub → 该技能 → **更新版本** →
上传本技能打好的文件夹/zip；打包仍由本技能完成，上传由客户本人执行。

**`login` 会用 refresh token 自动续期，`publish` 不会。** access token 过期后
`publish` 直接报 `NEED_LOGIN`；此时先跑一次 `login --agent`——有未过期的
refresh token 时它静默续期返回 `loggedIn: true`，无需重新扫码授权。

**标签是实时拉取的**，不要硬编码——实测当前为效率工具 / 内容创作 / 学习成长 /
职场办公 / 编程开发 / 生活决策 / 金融理财 / 其它，但以拉到的为准。

#### 展示名与平台主键（必填）

**`name` 不能落到仓内技能名上。** 2026-08-06 首次真提交被拒：
`SUBMIT_REJECTED: 名称长度不符合要求`——载荷的 `name` 取自 frontmatter 的
`soia-env-network-diagnose`（25 字符），超了平台限制；改成「网络诊断助手」后通过。
官方 uploader 的取值优先级是 `flags.name || metadata.name || identifier`
（`submit.mjs`），所以正确做法是投递时传 `--name`，**不动仓内 frontmatter**——
改 frontmatter 会连带影响 identifier 派生与仓内技能身份。

平台的长度上限未公开，我们只知道 25 被拒、6 通过。因此不猜阈值，改用一条确定性
约束：**`--channel redskill` 必须给 `--display-name`，缺省直接拒跑**。长英文技能名
对市场读者本来也没有意义。

**`--identifier` 要显式钉住。** Skill ID 是平台主键、跨版本不可改名。不显式指定时
它由 frontmatter 的 `name` 派生，将来一旦改名就会在平台上**另建一个新技能**，而不是
更新原有的。所以投递命令固定带 `--identifier <仓内技能名>`。

**`--yes` 不覆盖最后一道确认门。** `confirmBeforeSubmit` 是无条件的：从 stdin 读一行，
必须是字面量 `submit`，空输入按取消处理。这是平台设计的人工闸门，必须客户明确说提交
后才应答；`edit` 后跟 `key=value` 行可在确认阶段改 `name`/`identifier`/`version`/
`description`/`detail`/`tag`。

### 路径 B：网页上传

创作服务平台 → Builder hub → Red Skill → 上传 Skill → **上传文件**。两步：
① 上传源码 ② 填写信息。

| 约束 | 值 |
|---|---|
| 接受形态 | 含 `SKILL.md` 的**文件夹**或 **zip** |
| 文件类型 | `.md/.txt/.html/.css/.js/.py/.json/.xml` 等代码与配置 |
| 单文件上限 | 10 MB |
| 总大小上限 | 30 MB |
| 必选项 | 内容来源（原创 / 转载）、勾选《Skill 发布安全规范》 |

我们的技能目录（SKILL.md + scripts + references）天然满足这些约束。

### 与 media 域的配合

`soia-media-publish-rednote-card` 产的笔记可挂载对应的 Skill 卡片——内容讲场景、
卡片直接转化，是同一平台内的闭环。

## 不负责什么

- **不代客户执行 `publish` 或点上传**。这两个动作会把内容送到外部平台并进入
  审核记录，必须由客户本人执行。本技能只做打包与预检。
- **不上架未发版内容**。只从域仓 `main`（正式版）打包；dev 快照带 `-SNAPSHOT`。
- **不改仓内技能**。打包在暂存目录进行，不回写源仓；要改依赖或描述请走正常
  PR 流程，发版后再上架。
- **不自造上传实现**。Red Skill 的投递由官方 `@xhs/skillhub-upload` 承担，
  SkillHub 由官方 `skillhub` CLI 承担；平台接口与字段由它们维护，我们只做
  前置筛选与打包，避免自造一份必然漂移的副本。
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
- `--channel redskill` 缺 `--display-name` 时退出码非零，且不产出暂存目录
- redskill 的投递命令同时带 `--name` 与 `--identifier`，且给出的是 `--dry-run` 形态
- 就绪门禁 R1-R6 各项都有**一正一反**的用例：缺边界节/触发词/真实样例/专属测试；R6 覆盖 pipe-to-shell 字样、npm_ 前缀标识符、凭据样式串三反例与大写环境变量/词中 npm_ 不误伤两正例
  被拒，补齐后放行；全境外 URL 记警告不阻断，含 npmmirror 等境内源则无警告
- R4 只拷「专属」测试（只引用本技能与标准库）进包并在包布局实跑；布局耦合的
  测试会被抓出来拒包；引用其他技能名的跨技能共享测试不进包，只在报告里提示
- `--check-only` 跑完整个流程后不留暂存产物
