---
name: soia-meta-skill-release
description: 正式发版与发布收尾；默认只发布，客户明确选择后才转交定向安装。触发：正式发版、发布技能、发布后安装
version: 6.0.1
created_at: 2026-07-22 21:26:01
updated_at: 2026-09-14 15:02:03
created_by: gpt-5.6-terra
updated_by: gpt-6-astra
dependencies:
  optional: [soia-meta-sync-skills]
---

# soia-meta-skill-release

完成正式远端发版与市场 pin 收尾；默认只发布，不修改本机。客户明确选择项目/全局、Agent 与 skill/domain/all 后，才把安装交给 sync owner。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
| --- | --- | --- |
| 发布 merge 后的一个或多个技能 | 远端正式版与市场 pin 收尾 | 发布回执与客户端更新指引 |
| 发布后按客户选择安装 | 转交 sync owner 的明确计划 | project/global、Agent、粒度与 dry-run |

### 客户如何使用

提供仓库、技能范围、发布摘要及本次明确授权。正式发布按下方主流程；`release_skills.py` 只负责本机收口选择，不执行正式远端发布。仅请求安装或试装时才读取[定向安装与客户端更新](references/selected-install.md)。

### 依赖与安装

仅明确选择整域时：Claude Code 使用 `claude plugin install soia-meta@soia`，Codex 使用 `codex plugin add soia-meta@soia`；先按下方官方说明接入市场，命令不构成安装授权。

默认项目级单技能：`npx skills add soia-team/soia-open-skills -a <explicit-agent> -s soia-meta-skill-release`。Claude Code / Codex 整域插件仅在明确选择后按[官方安装说明](https://github.com/soia-team/soia-open-skills#安装)执行；WorkBuddy 使用[专家安装说明](https://github.com/soia-team/soia-open-skills/blob/main/docs/install/workbuddy.md)，不能由 npx 代装，也不把用户级专家冒称项目级安装。

| 依赖 | 类型 | 用途 | 缺失时怎么处理 |
| --- | --- | --- | --- |
| `npx skills` | 仅安装分支依赖 | 安装、移除、更新并维护 lock | 停止并报告失败步骤 |
| `soia-meta-sync-skills` | 定向安装时依赖 | 接收已确认的 scope、Agent 与粒度并执行同步 | 只发布不受影响；选择安装时先补齐该技能 |
| Git / 已认证 gh CLI | 强依赖 | 仓库与 GitHub 操作 | 报缺失，不自动安装或登录 |
| Python 3 | 强依赖 | 执行发布脚本 | 安装 Python 3 后重试 |
| PyYAML | 可选依赖 | 读取私有 `config.yml` | 传 `--repo-dir` 或使用当前进程环境变量 |

### 私密信息与中间数据

正式发布只读写已批准仓库与远端发布对象，不读取本机技能目录。凭据留在官方登录态，回执不输出秘密。可选非秘密路径配置见 [路径配置模板](assets/config.example.yml)，使用 `~/.config/soia-skills/soia-meta-skill-release/config.yml` 或 `SOIA_META_SKILL_RELEASE_CONFIG_FILE`；不为路径设置修改 shell 配置。安装分支可能写技能目录和 lock，按定向安装参考核对明确授权。

### 日志与完成回执

失败报告已完成部分与阻塞步骤。正式发布回执给版本、SHA、PR/CI、Release、pin 比对及重开 SNAPSHOT；安装只列本次选择的宿主与实际加载结果，不为 remote-only 填装机空表。

## 正式发版（dev 分支制）

> **执行前置：必须有客户当次的明确授权。** 正式发版是对外动作——tag、Release、
> 发版 PR、市场 pin 刷新都会改变外部用户收到的内容。客户要求修 bug 或加功能
> **不等于**要求发版：按本次约定交付到本地、PR 或 `dev`，仅在未授权发布时停下。
> 本次完整发布计划已批准且范围未变时连续完成，不逐命令重复确认。多 AI 并行时未经协调的发版会把他人未完成的工作一并送出
> （2026-08-03 实际发生过）。仅 `--dry-run` 预演无需授权。

域仓采用双通道：`dev` 承接日常合并（版本带 `-SNAPSHOT` 声明下个目标，期间不变，
状态身份用 commit SHA）；`main` 永远等于最新正式版。客户说**「正式发版 X」**时执行：

```bash
python3 skills/soia-meta-skill-release/scripts/formal_release.py \
  --repo soia-team/<域仓> --repo-dir <本地路径> --summary "<一句话摘要>" --dry-run
```

复核 dry-run 及实际附带动作：脚本会创建/强制清理 worktree 并删除分支，这些动作也须在批准范围内；未获清理授权时用同样门禁的手工步骤保留分支/worktree，不运行带清理的写模式。正式顺序如下，失败报告实际停点，不绕过检查：

1. 定稿 PR → dev：各 manifest（claude/codex/codebuddy 独立轨道）摘掉 `-SNAPSHOT`，
   并把 Release Notes **前插 `CHANGELOG.md`**——发版即更新、与 GitHub Release 同源，
   CHANGELOG 跟着插件缓存走，装了插件的用户离线可读
2. **快进推送 dev → main**：`git push origin <dev-sha>:refs/heads/main`，
   先确认已合并 dev HEAD 的 audit 为 success，快进瞬间 main 与 dev 指向同一提交
3. `v<X.Y.Z>` tag 打在该提交并推送
4. `gh release create`（标题 `<插件名> v<X.Y.Z>`）
5. 重开列车 PR → dev：各 manifest **+patch** 进入 `-SNAPSHOT`

随后完成 pin；客户端更新只在另有安装请求时执行。重开后以 main 仍为 dev 祖先及双向 `git rev-list --left-right --count origin/main...origin/dev` 验收，不要求两个 SHA 相等。

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

1. **dev→main 用快进推送，不走 PR 合并**。PR 的三种合并方式都会在 main 上造出
   dev 没有的提交——squash 连祖先关系都断（下次发版必冲突，2026-08-03 pkm/media
   实际发生）、merge 留个 merge 提交、rebase 重写 SHA。只有快进能让 **main 与 dev
   指向同一提交**，分叉在结构上不可能发生。
   - 前提一：`main` 必须是 `dev` 的祖先。脚本发版前校验，不满足即中止并要求先
     sync main→dev（有人绕过流程直接改 main、或历史上走过 merge/squash 时会不满足）。
   - 前提二：dev HEAD 的 `audit` 结论必须是 success。脚本显式查 check-runs——
     **快进不是跳过检查**，推上去的就是那个已通过检查的提交。
   - 仓库保护拒绝快进时报告阻塞，不从发布授权推断修改保护的权限；其余 PR/audit 门不变。
2. **定稿与重开列车之间是不变量破窗期**：第 1 步摘掉 dev 的 `-SNAPSHOT` 后，直到
   第 5 步重开前，dev 都处于违规状态。中断在此区间会静默留下「dev 停在正式版本
   号」。脚本收尾有断言兜底，但**人工介入或中断后必须自查**。
3. **发布门禁**：元仓 `generate_marketplaces.py` 读取待 pin 提交的 manifest，含
   `-SNAPSHOT` 直接拒绝生成清单——SNAPSHOT 结构上到不了任何客户端。

### 批量发布与元仓自身发布

域仓先发布，元仓后发布；元仓定稿候选内同步 `generate_marketplaces.py`、`generate_router_index.py`、`generate_skill_pages.py` 并运行完整 audit。核对默认分支为 main，发现不符先报告，不顺手修改设置。WorkBuddy 正式安装须从 main 正式候选取源，不能从刚重开的 SNAPSHOT 复制。重建 dev、强推、删除分支与修改保护不属于常规发布，须另有明确授权。zsh 手动推送用 `"${sha}:refs/heads/main"`，避免变量修饰符误解析。

### 体检：盘点生态或批量发布时

```bash
python3 scripts/generate_marketplaces.py --help >/dev/null  # 元仓 checkout 内
python3 scripts/check_version_trains.py --repos-root <各仓父目录>
```

查两件事：①版本列车不变量（dev 带 `-SNAPSHOT`、main 不带）②下次发版能否干净
合并。**报告生态状态时必须验这两个不变量，不能只抄版本号**——2026-08-03 的两次
漏判都源于「只看数值对不对，没验规则成不成立」。

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
python3 scripts/generate_marketplaces.py
python3 scripts/generate_router_index.py
python3 scripts/generate_skill_pages.py
```

生成器重新拉取各域仓 main 的最新 sha，改写 `.claude-plugin/marketplace.json`、`.agents/plugins/marketplace.json` 与路由索引。只纳入授权 pin 与对应派生物，检查是否带入范围外变化。已有本次元仓正式候选包含这些变更时复用，不另造重复 pin PR。若 `git status` 无变化，说明清单已是最新，跳到第 5 步。

### 3. 提交 PR 并合并

```bash
git commit --only <本次逐个批准路径> -m "chore(marketplace): refresh sha pins"
git push -u origin <本次分支>
```

```bash
gh pr create --base <元仓规则指定目标分支> --title "chore(marketplace): refresh sha pins" --body "刷新 sha pin 至各域仓最新提交。" --repo soia-team/soia-open-skills
```

等 `audit` 检查通过后合并：

```bash
gh pr checks <PR号> --repo soia-team/soia-open-skills
```

```bash
gh pr merge <PR号> --merge --repo soia-team/soia-open-skills
```

合并方式须保留正式发布所需 main→dev 祖先关系；合并不自动删除分支。

`audit` 中的 marketplace freshness 检查会独立重算一次清单，两边不一致即失败——这道门保证发布出去的 pin 确实指向域仓当前 main。

### 4. 核对 sha pin 已更新

```bash
gh api repos/soia-team/soia-open-skills/contents/.claude-plugin/marketplace.json --jq '.content' | base64 -d | python3 -c "import json,sys;print({p['name']:str(p.get('source',{}).get('sha',''))[:12] for p in json.load(sys.stdin)['plugins']})"
```

与第 1 步的域仓 sha 对比，一致即表示清单已是最新。

> 不要用 `gh workflow run refresh-marketplace.yml`：CI 的 `GITHUB_TOKEN` 无法直推受保护的 main，它建的 PR 也不会触发 `audit` 检查（GitHub 为防递归而抑制），两条路都走不通。市场刷新是发布动作的一部分，由本流程显式完成。

### 5. 客户端更新（仅明确选择后）

发布不自动安装。只有客户已选择项目/全局、Agent、skill/domain/all 与具体目标时，才读[定向安装与客户端更新](references/selected-install.md)的相关宿主部分。完整 source/target/action/删除替换影响计划已展示并明确批准且不变时复用，不重复询问。没有安装请求，不扫描本机目录、不清理缓存。

## 边界与验证

普通发布执行上述真实远端核验；以下维护测试不是每次发布的重复前置。项目正式 CI 和发版门禁不省。

- 本技能负责已获当次明确授权的正式发布、tag/Release 和市场 pin 收口。本机安装或更新只有在客户另行选择并满足安装确认门后执行。发布计划、安装计划或转交下游技能不等于实际完成；分别报告 publish、pin、install 状态。
- `--dry-run` 不执行任何命令或文件写入，只输出计划回执。
- 维护脚本时的前向测试应在临时 HOME 中 mock `subprocess`，覆盖命令顺序、失败即停、五处旧名清理、Codex 补链、lock 分支与 dry-run。

### 发版前置：跨仓安装章节体检

各域仓的 `audit_skills.py` 互不相同，`private-skills` 甚至没有该脚本，因此
「安装章节覆盖三个一等宿主」这条**无法在各仓 CI 内统一校验**。门户仓 CI 只用
`--self` 检查自己那几个技能。

发版前在本机跑一次全量（需要各域仓的工作副本在同一父目录下）：

```bash
python3 <soia-open-skills>/scripts/check_install_sections.py --repos-root <各仓的父目录>
```

它扫 `<repo>/skills/*` 与 `<repo>/*/skills/*`（覆盖 private-skills 的
`workspace/` 与 `harness/` 子仓目录），非零退出即有技能缺一等宿主。
