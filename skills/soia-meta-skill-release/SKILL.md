---
name: soia-meta-skill-release
description: 技能 PR 合并后完成安装、旧名清理、多 AI 软链与 lock 对账，并执行插件市场刷新与客户端更新。触发：「发布技能」「更新插件」「技能发布收尾」
version: 3.2.0
created_at: 2026-07-21 00:00:00
updated_at: 2026-07-29 14:14:06
created_by: gpt-5.6-terra
updated_by: claude opus 5
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

1. 有 `--removed` 时清理 `.agents`、`.claude`、`.soia`、`.workbuddy`、`.codex` 五处同名残留。改名清理在两种模式下都执行：残留的旧名副本会盖过插件更新继续应答。
2. 读取仓库版本填入回执；装机版本记 `-`，软链记 `plugin`，结果记 `published`。
3. 打印用户实际收到改动还需要的步骤：bump 双份 `plugin.json` 的 version → 元仓重生成市场清单并提 PR 合并 → 客户端 `plugin update` → `plugin details` 验证。

### `npx` 模式（`--install-mode npx`，显式 opt-in）

1. 逐项执行 `npx skills add <repo> -g -a <agents> -s <skill> -y`。
2. 有 `--removed` 时执行同参 `npx skills remove`，并清理五处残留。
3. 执行 `npx skills update -g -y`，覆盖交叉引用的连带更新。
4. 遍历 `~/.agents/skills`：对有 `SKILL.md` 且 Codex 侧缺失的技能，创建相对软链；历史实证目录没有 `SKILL.md`，不进入 Codex。
5. 调用已安装的 `soia-meta-sync-skills`，目标为 `soia,workbuddy`。
6. 对账 `~/.agents/.skill-lock.json`：所有新技能必须来自 `--repo`，旧名必须零残留。
7. 按 `--repo-dir` → 进程环境 → 私有 v2 config → 只读 v1 config 回退 → 旧版兼容目录的顺序解析 checkout，并对比每项 `SKILL.md` version 与装机 version。


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

Claude Code：

```bash
claude plugin marketplace update soia
```

```bash
claude plugin update <域插件名>@soia
```

更新后需重启 Claude Code 生效。已开启 `autoUpdate` 的用户会在下次启动时自动完成这两步。

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

### 6. 回收旧版本缓存

两家客户端在 `plugin update` 后都只新增版本目录，**不回收旧的**；Claude 的 `.in_use` 标记也不可靠（实测同一插件新旧两个版本都带这个文件）。不清理会线性堆积，并干扰排查——用 `find` 找资源会匹配到多个版本目录，`ls` 统计技能数会得出离谱结果。

```bash
python3 skills/soia-meta-skill-release/scripts/prune_plugin_cache.py
```

预演确认无误后执行：

```bash
python3 skills/soia-meta-skill-release/scripts/prune_plugin_cache.py --apply
```

按语义化版本取最高值保留，其余删除；非语义化版本目录（如官方插件的 `latest`）一律跳过。缓存随时可由市场重新拉取，删错也只是多下一次。

### 7. 验证

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
