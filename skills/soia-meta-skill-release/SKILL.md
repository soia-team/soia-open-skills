---
name: soia-meta-skill-release
description: 域仓正式发版（dev→main、tag、Release、notes、CHANGELOG）与发布收尾：市场 pin 刷新、客户端更新、旧名清理、WorkBuddy 专家安装、dev 快照试装。触发：「正式发版」「发布技能」「更新插件」「技能发布收尾」「装到 WorkBuddy」「试装 dev」
version: 4.2.0
created_at: 2026-07-21 00:00:00
updated_at: 2026-08-03 20:00:00
created_by: gpt-5.6-terra
updated_by: claude fable 5
dependencies:
  hard: [soia-meta-sync-skills]
---

# soia-meta-skill-release

在技能 PR 已 merge 后完成本机发布收尾：安装或更新变更技能、清理旧名、补全 Codex 链接、同步消费者目录，并用 lock 与版本进行独立对账。触发词：**「发布技能」**、**「发布 X」**、**「技能发布收尾」**、**「release skill」**。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
| --- | --- | --- |
| 发布 merge 后的一个或多个技能 | 安装、更新、软链同步并核对 lock/版本 | 六列发布回执 |
| 重命名或删除旧技能 | 移除旧安装与全部受管目录残留 | 已清理数量与零残留验证 |

### 客户如何使用

先确认目标技能已 merge 到远端仓库；本技能不执行 git、PR、merge、push 或发布远端状态。再提供仓库、技能名单和可选旧名：

```bash
python3 skills/soia-meta-skill-release/scripts/release_skills.py \
  --repo <owner/name> \
  --skills <skill-a,skill-b> \
  --removed <legacy-skill> \
  --dry-run
```

复核 dry-run 后，移除 `--dry-run` 执行。默认面向 `claude-code,codex`，可用 `--agents` 覆盖。版本核对按以下顺序解析本地 checkout：

1. `--repo-dir <repo-path>` 显式路径；
2. 当前进程的 `SOIA_SKILL_REPOS_ROOT/<repo-name>`；
3. 私有 YAML：`--config` → `SOIA_META_SKILL_RELEASE_CONFIG_FILE` → `~/.config/soia-skills/soia-meta-skill-release/config.yml` 中的 `env.SOIA_SKILL_REPOS_ROOT`；
4. v1 私有配置目录只读回退（会向 stderr 输出建议的 `mv` 迁移命令）；
5. 旧版维护者本地目录约定，仅作弃用中的向后兼容回退。

仓库内部仍须采用 `skills/<skill-name>/SKILL.md` 布局。对未来新增仓库，只要 `--repo` 提供对应的任意 `<owner>/<repo-name>`，无需修改脚本。

### 依赖与安装

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

```bash
claude plugin install soia-meta@soia
```

只要这一个技能时，可用 npx 路线。注意技能会落进共享真源 `~/.agents/skills`；若同时装了插件，同一技能会出现两份索引且各自漂移，建议二选一：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-skill-release -y
```

| 依赖 | 类型 | 用途 | 缺失时怎么处理 |
| --- | --- | --- | --- |
| `npx skills` | 强依赖 | 安装、移除、更新并维护 lock | 停止并报告失败步骤 |
| `soia-meta-sync-skills` | 强依赖 | 同步 SOIA 与 WorkBuddy 软链 | 先安装该技能再重试 |
| Python 3 | 强依赖 | 执行发布脚本 | 安装 Python 3 后重试 |
| PyYAML | 可选依赖 | 读取私有 `config.yml` | 传 `--repo-dir` 或使用当前进程环境变量 |

### 私密信息与中间数据

按本仓 `DATA_STORAGE_SPEC.md`，本技能只读写各 AI 技能安装目录及 `~/.agents/.skill-lock.json`；可选读取仅含本地 checkout 根目录的私有 v2 `config.yml`。复制 [路径配置模板](assets/config.example.yml) 后再填写；不要为了这一个设置修改 `.zprofile`，也不读取或保存凭据、缓存或中间文件。终端回执只显示技能名、版本、链接状态和失败步骤。

### 日志与完成回执

每一步失败即停止，并输出已到达的步骤和下列六列回执：

| 技能 | 动作 | 仓库版本 | 装机版本 | 软链(三处) | 结果 |
| --- | --- | --- | --- | --- | --- |
| `<skill>` | install/update/remove | `<version>` | `<version>` | agents / claude / codex | ok / removed / failed |

## 工作流

交付走插件市场，`--install-mode` 默认 `plugin`。**默认不会向 `~/.agents/skills` 安装任何技能**——那样会与插件副本并存，同一技能出现两份索引且各自漂移。

### `plugin` 模式（默认）

1. 有 `--removed` 时清理 `.agents`、`.claude`、`.soia`、`.workbuddy`、`.codex`、`.pi/agent` 六处同名残留。改名清理在两种模式下都执行：残留的旧名副本会盖过插件更新继续应答。
2. 读取仓库版本填入回执；装机版本记 `-`，软链记 `plugin`，结果记 `published`。
3. 打印用户实际收到改动还需要的步骤：bump 双份 `plugin.json` 的 version → 元仓重生成市场清单并提 PR 合并 → 客户端 `plugin update` → `plugin details` 验证。

### `ask` 模式（`--install-mode ask`，交互式选择）

需要交互终端。执行时询问客户是否安装到本地：输入 `y` 则按 `--agents` 指定的目标走 npx 安装（可现场覆盖 agents 列表，如 `claude-code,pi`）；输入 `n`/回车则等同 `plugin` 模式，只发布不安装。非交互环境（agent 执行脚本）下使用 `ask` 会报错并提示改用 `plugin`/`npx`。

### `npx` 模式（`--install-mode npx`，显式 opt-in）

1. 逐项执行 `npx skills add <repo> -g -a <agents> -s <skill> -y`；`--agents` 支持任意 `npx skills -a` agent id，如 `claude-code`、`codex`、`pi`（Pi 安装到 `~/.pi/agent/skills`）。
2. 有 `--removed` 时执行同参 `npx skills remove`，并清理五处残留。
3. 执行 `npx skills update -g -y`，覆盖交叉引用的连带更新。
4. 遍历 `~/.agents/skills`：对有 `SKILL.md` 且 Codex 侧缺失的技能，创建相对软链；历史实证目录没有 `SKILL.md`，不进入 Codex。
5. 调用已安装的 `soia-meta-sync-skills`，目标为 `soia,workbuddy`。
6. 对账 `~/.agents/.skill-lock.json`：所有新技能必须来自 `--repo`，旧名必须零残留。
7. 按 `--repo-dir` → 进程环境 → 私有 v2 config → 只读 v1 config 回退 → 旧版兼容目录的顺序解析 checkout，并对比每项 `SKILL.md` version 与装机 version。


## 正式发版（dev 分支制）

域仓采用双通道：`dev` 承接日常合并（版本带 `-SNAPSHOT` 声明下个目标，期间不变，
状态身份用 commit SHA）；`main` 永远等于最新正式版。客户说**「正式发版 X」**时执行：

```bash
python3 skills/soia-meta-skill-release/scripts/formal_release.py \
  --repo soia-team/<域仓> --repo-dir <本地路径> --summary "<一句话摘要>" --dry-run
```

复核 dry-run 计划后去掉 `--dry-run` 执行。脚本按序完成五步，每步失败即停：

1. 定稿 PR → dev：各 manifest（claude/codex/codebuddy 独立轨道）摘掉 `-SNAPSHOT`，
   并把 Release Notes **前插 `CHANGELOG.md`**——发版即更新、与 GitHub Release 同源，
   CHANGELOG 跟着插件缓存走，装了插件的用户离线可读
2. 发版 PR dev → main：正文为同一份 Release Notes 草稿（`generate_release_notes.py`
   按 conventional 前缀归类上个 tag 以来的提交）
3. `v<X.Y.Z>` tag 打在 main HEAD 并推送
4. `gh release create`（标题 `<插件名> v<X.Y.Z>`）
5. 重开列车 PR → dev：各 manifest **+patch** 进入 `-SNAPSHOT`

随后继续本技能既有的 pin 刷新与客户端更新流程（下节）。

### 版本号怎么定

重开列车默认 **+patch**（1.11.0 → `1.11.1-SNAPSHOT`）——刚发完版还不知道下一版
是修 bug 还是加技能，默认 +minor 等于预判「必有新功能」，实证会虚高：v1.11.0 实
际只修了一个显示缺陷，按语义应是 1.10.1。与 Maven release 惯例一致。

**发版前按内容确认版本**：加了新技能/新能力 → 手工把 dev 改成 minor（如
`1.12.0-SNAPSHOT`）；有破坏性变更 → major。改完再跑发版，脚本以 dev 的版本为准。

**技能自身版本要单独 bump**：`plugin.json` 是插件（交付单元）的版本，每个
`skills/<name>/SKILL.md` 的 frontmatter `version` 是该技能自己的版本，两者独立。
改了某个技能的正文或脚本，就要 bump 那个技能的 `version` 和 `updated_at`——
CI 的 `check_skill_versions.py` 会拦（2026-08-03 漏过一次：改了 skill-release 的
脚本与正文，技能版本却停在 4.1.0）。

### 三条不可回退的发版约束（都由事故推导，勿改）

1. **发版 PR（dev→main）必须 merge commit，不能 squash**。squash 造出与 dev 无
   祖先关系的新提交，merge base 停在旧点，两边对同一批文件各自演进，下次发版 PR
   必然 CONFLICTING，只能靠人工 sync PR 补救。
2. **定稿与重开列车之间是不变量破窗期**：第 1 步摘掉 dev 的 `-SNAPSHOT` 后，直到
   第 5 步重开前，dev 都处于违规状态。中断在此区间会静默留下「dev 停在正式版本
   号」。脚本收尾有断言兜底，但**人工介入或中断后必须自查**。
3. **发布门禁**：元仓 `generate_marketplaces.py` 读取待 pin 提交的 manifest，含
   `-SNAPSHOT` 直接拒绝生成清单——SNAPSHOT 结构上到不了任何客户端。

### 体检：随时可跑，盘点必跑

```bash
python3 scripts/generate_marketplaces.py --help >/dev/null  # 元仓 checkout 内
python3 scripts/check_version_trains.py --repos-root <各仓父目录>
```

查两件事：①版本列车不变量（dev 带 `-SNAPSHOT`、main 不带）②下次发版能否干净
合并。**报告生态状态时必须验这两个不变量，不能只抄版本号**——2026-08-03 的两次
漏判都源于「只看数值对不对，没验规则成不成立」。

## 试装 dev（本地验证快照版）

触发词：**「试装 dev」**、**「本地装 dev 版」**。dev 快照只做本地验证，绝不常驻安装。

- **Claude Code（推荐，会话级）**：`claude --plugin-dir <域仓本地路径>` 启动会话，
  当前检出（dev 时即 SNAPSHOT 版）被加载为插件，退出即卸、不污染安装态；可叠加
  多个 `--plugin-dir`。只验证不开会话时用
  `claude --plugin-dir <路径> plugin details <插件名>`（`--plugin-dir` 必须在
  `plugin` 子命令之前）。
- **WorkBuddy**：本地 checkout 切到 dev 后运行
  `install_workbuddy_experts.py <插件名>`——脚本复制本地 checkout，装出的专家即
  SNAPSHOT 版，界面版本号可直接分辨。
- **Codex**：无会话级机制，**禁止**把 dev/SNAPSHOT 常驻安装——SNAPSHOT 会进入
  客户端版本比较路径，这正是发布门禁在市场侧拦截的场景。

## 插件发布与更新流程（域仓改动后）

技能改动合并到域仓 main 后，插件用户不会立即拿到——市场清单里的 sha pin 仍指向旧提交。执行以下步骤完成发布。

### 1. 确认域仓改动已合并

```bash
gh api repos/soia-team/<域仓>/commits/main --jq '.sha'
```

### 2. 在元仓重新生成市场清单

元仓 main 受分支保护（必须走 PR + `audit` 必过 + `enforce_admins`），因此刷新只能以 PR 形式提交，不能直推。在元仓 checkout 中执行：

```bash
git checkout main && git pull && git checkout -b chore/refresh-marketplace
```

```bash
python3 scripts/generate_marketplaces.py && python3 scripts/generate_router_index.py
```

两个脚本重新拉取各域仓 main 的最新 sha，改写 `.claude-plugin/marketplace.json`、`.agents/plugins/marketplace.json` 与路由索引。若 `git status` 无变化，说明清单已是最新，跳到第 5 步。

### 3. 提交 PR 并合并

```bash
git add -A && git commit -m "chore(marketplace): refresh sha pins" && git push -u origin chore/refresh-marketplace
```

```bash
gh pr create --title "chore(marketplace): refresh sha pins" --body "刷新 sha pin 至各域仓最新提交。" --repo soia-team/soia-open-skills
```

等 `audit` 检查通过后合并：

```bash
gh pr checks <PR号> --repo soia-team/soia-open-skills
```

```bash
gh pr merge <PR号> --squash --delete-branch --repo soia-team/soia-open-skills
```

`audit` 中的 marketplace freshness 检查会独立重算一次清单，两边不一致即失败——这道门保证发布出去的 pin 确实指向域仓当前 main。

### 4. 核对 sha pin 已更新

```bash
gh api repos/soia-team/soia-open-skills/contents/.claude-plugin/marketplace.json --jq '.content' | base64 -d | python3 -c "import json,sys;print({p['name']:str(p.get('source',{}).get('sha',''))[:12] for p in json.load(sys.stdin)['plugins']})"
```

与第 1 步的域仓 sha 对比，一致即表示清单已是最新。

> 不要用 `gh workflow run refresh-marketplace.yml`：CI 的 `GITHUB_TOKEN` 无法直推受保护的 main，它建的 PR 也不会触发 `audit` 检查（GitHub 为防递归而抑制），两条路都走不通。市场刷新是发布动作的一部分，由本流程显式完成。

### 5. 指导客户端更新

Claude Code：**先记录安装清单**，收尾要对账——`plugin update` 对未安装的插件会直接失败，卸载重装类操作也容易漏装：

```bash
claude plugin list | grep soia > /tmp/claude-soia-before.txt && cat /tmp/claude-soia-before.txt
```

```bash
claude plugin marketplace update soia
```

```bash
claude plugin update <域插件名>@soia
```

收尾对账，缺失的逐个 `plugin install` 补回：

```bash
claude plugin list | grep soia | diff /tmp/claude-soia-before.txt -
```

更新后需重启 Claude Code 生效。已开启 `autoUpdate` 的用户会在下次启动时自动完成这两步。

> `claude plugin details <名>` 对私有市场的插件要带市场后缀（`<名>@<市场>`），不带会报「not installed」，容易误判成插件丢失。核对安装状态用 `plugin list` 更可靠。

Codex：**先记录当前安装清单**——下面要删缓存，删错粒度会连带卸掉同市场的其他插件：

```bash
codex plugin list | grep '@soia' > /tmp/soia-installed-before.txt && cat /tmp/soia-installed-before.txt
```

**只删市场暂存**（`marketplace add` 会复用旧克隆，不删就拉不到新增的资源文件）：

```bash
rm -rf ~/.codex/.tmp/marketplaces/soia
```

**插件缓存只删目标那一个**，`soia` 是市场名不是插件名，`rm -rf ~/.codex/plugins/cache/soia` 会把该市场下**全部 8 个插件**一起删掉：

```bash
rm -rf ~/.codex/plugins/cache/soia/<域插件名>
```

```bash
codex plugin marketplace add soia-team/soia-open-skills
```

```bash
codex plugin add <域插件名>@soia
```

**收尾比对安装清单**，确认没有连带损失；有缺失就逐个 `plugin add` 补回：

```bash
codex plugin list | grep '@soia' | diff /tmp/soia-installed-before.txt -
```

Codex 无自动更新机制，必须手动执行。跳过删暂存这一步会出现「命令报成功、内容还是旧的」——2026-07-27 实际踩过：corp 市场的暂存停在没有 `assets/icon.svg` 的旧版本，`composerIcon` 指向不存在的文件，界面回退成通用图标，排查时误判为路径写错。

### 6. WorkBuddy 专家（客户在用 WorkBuddy 时才做）

WorkBuddy 是 Electron 桌面端，**没有 CLI**——不存在 `workbuddy plugin install`，
也没有能指向我们 GitHub 的市场通道。所以这一步由脚本代劳，不要去找对等命令：

```bash
python3 skills/soia-meta-skill-release/scripts/install_workbuddy_experts.py --dry-run
```

确认计划后执行（不带参数装全部，也可只给要装的插件名）：

```bash
python3 skills/soia-meta-skill-release/scripts/install_workbuddy_experts.py
```

脚本把域仓 checkout 复制进 `my-experts/plugins/<插件名>`，再调 WorkBuddy 官方
`register_expert.py` 注册。三条实测约束决定了只能这么做：

| 约束 | 实测结论 |
|---|---|
| 目录 | 自建专家只认硬编码的 `my-experts`，应用内出现 38 处；别处放了不显示 |
| 软链 | 不行。官方 `validate_expert.py` 对路径 `resolve()`，穿透后判定「不在专家目录下」 |
| 远端 | 市场条目 `source` 只能是路径字符串，没有 sha pin 层；`expert/install` 深链要 `sharecode`，走官方云 |

装完**必须让客户重启 WorkBuddy**，否则新专家不出现在【专家·技能·连接器 → 我的专家】。

验证：召唤该专家后问「你有多少个可用技能」，该域技能应全部在场；不召唤时不在场。

### 7. 回收旧版本缓存

两家客户端在 `plugin update` 后都只新增版本目录，**不回收旧的**；Claude 的 `.in_use` 标记也不可靠（实测同一插件新旧两个版本都带这个文件）。不清理会线性堆积，并干扰排查——用 `find` 找资源会匹配到多个版本目录，`ls` 统计技能数会得出离谱结果。

```bash
python3 skills/soia-meta-skill-release/scripts/prune_plugin_cache.py
```

预演确认无误后执行：

```bash
python3 skills/soia-meta-skill-release/scripts/prune_plugin_cache.py --apply
```

按语义化版本取最高值保留，其余删除；非语义化版本目录（如官方插件的 `latest`）一律跳过。缓存随时可由市场重新拉取，删错也只是多下一次。

### 8. 验证

```bash
claude plugin list
```

```bash
codex plugin list
```

确认目标插件版本已变化、状态为 enabled。

### 域仓与插件对照

| 域仓 | 插件名 |
|---|---|
| soia-open-dev-skills | soia-dev |
| soia-open-dev-design-skills | soia-dev-design |
| soia-open-pkm-vault-skills | soia-pkm-vault |
| soia-open-media-content-skills | soia-media-content |
| soia-open-cwork-office-skills | soia-cwork-office |
| soia-open-edu-course-skills | soia-edu-course |
| soia-open-env-skills | soia-env |
| soia-open-skills | soia-meta |

## 边界与验证

- 只做 merge 后的本机收尾；发布前 merge 由调用方完成。
- `--dry-run` 不执行任何命令或文件写入，只输出计划回执。
- 前向测试应在临时 HOME 中 mock `subprocess`，覆盖命令顺序、失败即停、五处旧名清理、Codex 补链、lock 分支与 dry-run。
