---
name: soia-meta-skill-release
description: 正式发版 SOIA 技能仓并刷新市场 pin，默认不装机。触发：正式发版、发布技能、刷新市场 pin
version: 6.0.2
created_at: 2026-07-22 21:26:01
updated_at: 2026-09-30 13:14:57
created_by: gpt-5.6-terra
updated_by: claude opus 5.5
dependencies:
  optional: [soia-meta-sync-skills]
---

# soia-meta-skill-release

完成正式远端发版与市场 pin 收尾；默认只发布，不改本机。客户明确选择项目/全局、Agent 与 skill/domain/all 后，才把安装交给 sync owner。

**授权前置：** 正式发版会改变外部用户收到的内容（tag、Release、发版 PR、市场 pin），须有客户当次的明确授权。修 bug 或加功能不等于要求发版：按约定交付到本地、PR 或 `dev` 后停下。已批准且范围未变的完整发布计划连续完成，不逐命令重问。多 AI 并行时未经协调的发版会把他人未完成的工作一并送出。只有 `--dry-run` 预演无需授权。

## 客户可读说明

### 这个技能可以做什么

- 发布 merge 后的一个或多个技能：远端正式版与市场 pin 收尾，给发布回执与客户端更新指引。
- 发布后按客户选择安装：转交 sync owner 的明确计划（project/global、Agent、粒度与 dry-run）。

### 客户如何使用

提供仓库、技能范围、发布摘要及本次明确授权。正式发布按下方主流程；`release_skills.py` 只负责本机收口选择，不做正式远端发布。只有请求安装或试装时才读[定向安装与客户端更新](references/selected-install.md)。

### 依赖与安装

强依赖 Git、已认证的 gh CLI 与 Python 3，缺失即报告，不自动安装或登录；PyYAML 可选（读私有 `config.yml`，缺时传 `--repo-dir` 或用进程环境变量）。安装分支另需 `npx skills` 与 `soia-meta-sync-skills`，只发布不受影响。

单技能 `npx skills add soia-team/soia-open-skills -a <explicit-agent> -s soia-meta-skill-release`；整域 `claude plugin install soia-meta@soia` 或 `codex plugin add soia-meta@soia`（先接入市场），完整步骤见[官方安装说明](https://github.com/soia-team/soia-open-skills#安装)；WorkBuddy 见[专家安装说明](https://github.com/soia-team/soia-open-skills/blob/main/docs/install/workbuddy.md)，不由 npx 代装，用户级专家不冒称项目级安装。命令不构成安装授权。

### 私密信息与中间数据

正式发布只读写已批准仓库与远端发布对象，不读取本机技能目录。凭据留在官方登录态，回执不输出秘密。可选非秘密路径配置见[路径配置模板](assets/config.example.yml)，位置 `~/.config/soia-skills/soia-meta-skill-release/config.yml` 或 `SOIA_META_SKILL_RELEASE_CONFIG_FILE`；不为路径设置改 shell 配置。安装分支可能写技能目录和 lock，按定向安装参考核对明确授权。

### 日志与完成回执

失败时报告已完成部分与阻塞步骤。正式发布回执给版本、SHA、PR/CI、Release、pin 比对及重开 SNAPSHOT；安装只列本次选择的宿主与实际加载结果，remote-only 不填装机空表。

## 正式发版（dev 分支制）

`dev` 承接日常合并（版本带 `-SNAPSHOT` 声明下个目标，期间不变，状态身份用 commit SHA）；`main` 永远等于最新正式版。客户说「正式发版 X」时先预演：

```bash
python3 skills/soia-meta-skill-release/scripts/formal_release.py \
  --repo soia-team/<域仓> --repo-dir <本地路径> --summary "<一句话摘要>" --dry-run
```

复核 dry-run 与附带动作：写模式会创建并强制清理 worktree、合并时删除分支，这些也须在批准范围内；没有清理授权时按同样门禁手工执行并保留分支/worktree。顺序如下，失败报告实际停点，不绕过检查：

1. 定稿 PR → dev：各 manifest（claude/codex/codebuddy 独立轨道）摘掉 `-SNAPSHOT`，Release Notes 前插 `CHANGELOG.md`（与 GitHub Release 同源，随插件缓存离线可读）。
2. 确认 dev HEAD 的 `audit` 为 success 后快进推送：`git push origin <dev-sha>:refs/heads/main`（zsh 手推写 `"${sha}:refs/heads/main"`，避免变量修饰符误解析）。
3. `v<X.Y.Z>` tag 打在该提交并推送。
4. `gh release create`，标题 `<插件名> v<X.Y.Z>`。
5. 重开列车 PR → dev：各 manifest +patch 进入 `-SNAPSHOT`。

随后刷新市场 pin；客户端更新只在另有安装请求时做。验收以 main 仍为 dev 祖先及双向 `git rev-list --left-right --count origin/main...origin/dev` 为准，不要求两个 SHA 相等。

### 不可回退的约束

1. **dev→main 只用快进，不走 PR 合并。** squash 断祖先（下次发版必冲突）、merge 多出 merge 提交、rebase 改 SHA；只有快进让 main 与 dev 指向同一提交。前提：`main` 是 `dev` 的祖先（不满足即中止，先 sync main→dev），且 dev HEAD 的 `audit` 为 success——快进不是跳过检查。仓库保护拒绝快进时报告阻塞，不从发布授权推断修改保护的权限。
2. **第 1 步到第 5 步之间 dev 停在正式版本号，是不变量破窗期。** 脚本收尾有断言兜底，人工介入或中断后必须自查。
3. **SNAPSHOT 到不了客户端。** 元仓 `generate_marketplaces.py` 遇到待 pin 提交的 manifest 含 `-SNAPSHOT` 直接拒绝生成清单。

### 版本号

- 重开列车默认 +patch（`1.11.0` → `1.11.1-SNAPSHOT`），刚发完版不预判下一版有新功能。发版前按内容上调：加了新技能/新能力就手工把 dev 改到 minor，破坏性变更改 major；脚本以 dev 的版本为准。
- 技能自身版本独立于插件版本：改了某技能的正文或脚本就 bump 该技能的 `version` 与 `updated_at`，CI 的 `check_skill_versions.py` 会拦。

### 批量发布与元仓自身发布

域仓先发，元仓后发；元仓定稿候选内同步 `generate_marketplaces.py`、`generate_router_index.py`、`generate_skill_pages.py` 并跑完整 audit。默认分支不是 main 时先报告，不顺手改设置。WorkBuddy 正式安装从 main 正式候选取源，不从刚重开的 SNAPSHOT 复制。重建 dev、强推、删除分支与修改保护不属于常规发布，须另有明确授权。

### 体检：盘点生态或批量发布前

在元仓 checkout 内运行：

```bash
python3 scripts/check_version_trains.py --repos-root <各仓父目录>
python3 scripts/check_install_sections.py --repos-root <各仓父目录>
```

前者验版本列车不变量（dev 带 `-SNAPSHOT`、main 不带）与下次发版能否干净合并——报告生态状态时要验规则是否成立，不只抄版本号。后者跨仓检查每个技能的「依赖与安装」是否覆盖 Claude Code 插件、npx 与 WorkBuddy 三个一等宿主（各域仓 CI 只能 `--self` 查自己，私有仓没有该脚本），非零退出即有缺口。

## 市场 pin 刷新

域仓改动合到 main 后，插件用户要等市场清单的 sha pin 更新才拿到。元仓 main 受保护，刷新只能走 PR：重跑三个生成器、只纳入授权 pin 与派生物、`audit` 通过后合并、再核对远端 pin 等于域仓 main；命令见[市场 pin 刷新](references/marketplace-pin.md)。已有本次元仓正式候选包含这些变更时复用，不另开重复 pin PR。

## 客户端更新（仅明确选择后）

发布不自动安装。客户已选定项目/全局、Agent、skill/domain/all 与具体目标时，才读[定向安装与客户端更新](references/selected-install.md)的相关宿主部分；完整 source/target/action/删除替换影响计划已展示并明确批准且未变时复用，不重复询问。没有安装请求就不扫描本机目录、不清理缓存。

## 边界与验证

- 发布计划、安装计划或转交下游技能不等于实际完成；publish、pin、install 状态分别报告。
- `--dry-run` 不执行任何命令或文件写入，只输出计划回执。普通发布做真实远端核验，项目正式 CI 与发版门禁不省。
- 维护脚本时的前向测试在临时 HOME 中 mock `subprocess`，覆盖命令顺序、失败即停、五处旧名清理、Codex 补链、lock 分支与 dry-run。
