---
name: soia-meta-skill-release
description: 技能 PR 合并后完成安装、旧名清理、多 AI 软链与 lock 对账，并执行插件市场刷新与客户端更新。触发：「发布技能」「更新插件」「技能发布收尾」
version: 2.1.1
created_at: 2026-07-21 00:00:00
updated_at: 2026-07-27 10:57:16
created_by: gpt-5.6-terra
updated_by: gpt-5.6-sol
dependencies:
  hard: [soia-meta-sync-skills]
---

# soia-meta-skill-release

在技能 PR 已 merge 后完成本机发布收尾：安装或更新变更技能、清理旧名、补全 Codex 链接、同步消费者目录，并用 lock 与版本进行独立对账。触发词：**「发布技能」**、**「发布 X」**、**「技能发布收尾」**、**「release skill」**。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
| --- | --- | --- |
| 发布 merge 后的一个或多个技能 | 刷新插件市场，并安装、更新、同步和核对版本 | workflow URL、客户端指令与六列发布回执 |
| 更新域插件 | 核对域仓 main 与市场 sha pin，指导 Claude/Codex 更新 | pin 对账结果与插件版本 |
| 重命名或删除旧技能 | 移除旧安装与全部受管目录残留 | 已清理数量与零残留验证 |

### 客户如何使用

先确认目标技能已 merge 到远端仓库；本技能不执行 git、PR、merge 或 push。用户说「发布技能」或「更新插件」即授权按下方插件发布流程刷新市场清单；再提供仓库、技能名单、域插件名和可选旧名：

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-skill-release -y
```

| 依赖 | 类型 | 用途 | 缺失时怎么处理 |
| --- | --- | --- | --- |
| `npx skills` | 强依赖 | 安装、移除、更新并维护 lock | 停止并报告失败步骤 |
| `soia-meta-sync-skills` | 强依赖 | 同步 SOIA 与 WorkBuddy 软链 | 先安装该技能再重试 |
| Python 3 | 强依赖 | 执行发布脚本 | 安装 Python 3 后重试 |
| PyYAML | 可选依赖 | 读取私有 `config.yml` | 传 `--repo-dir` 或使用当前进程环境变量 |
| GitHub CLI `gh` | 插件发布强依赖 | 核对合并、触发并验证市场刷新 | 完成 `gh auth login` 后重试 |
| Claude/Codex CLI | 客户端更新依赖 | 更新并验证对应客户端插件 | 只输出适用客户端的安装与验证指令 |

### 私密信息与中间数据

按本仓 `DATA_STORAGE_SPEC.md`，本技能只读写各 AI 技能安装目录及 `~/.agents/.skill-lock.json`；可选读取仅含本地 checkout 根目录的私有 v2 `config.yml`。复制 [路径配置模板](assets/config.example.yml) 后再填写；不要为了这一个设置修改 `.zprofile`，也不读取或保存凭据、缓存或中间文件。终端回执只显示技能名、版本、链接状态和失败步骤。

### 日志与完成回执

每一步失败即停止，并输出已到达的步骤和下列六列回执：

| 技能 | 动作 | 仓库版本 | 装机版本 | 软链(三处) | 结果 |
| --- | --- | --- | --- | --- | --- |
| `<skill>` | install/update/remove | `<version>` | `<version>` | agents / claude / codex | ok / removed / failed |

## 插件发布流程（域仓改动后）

用户说「发布技能」或「更新插件」且域仓改动已经完成评审时，封装执行以下步骤。`<domain-repo>` 是域仓名，`<pr>` 是域仓 PR 号或 URL，`<插件>` 是市场中的域插件名。任一步证据不一致即停止，不把等待刷新或未验证写成成功。

### 1. 确认域仓改动已合并到 main

```bash
gh pr view <pr> --repo soia-team/<domain-repo> \
  --json state,mergedAt,mergeCommit,url
gh api repos/soia-team/<domain-repo>/commits/main --jq .sha
```

只有 PR `state` 为 `MERGED`、`mergedAt` 非空，且目标改动能在 `main` 提交中确认时继续。记录域仓 `main` 的完整 SHA 为 `<domain-main-sha>`。

### 2. 触发元仓市场清单刷新

```bash
gh workflow run refresh-marketplace.yml \
  --repo soia-team/soia-open-skills
```

这是远端状态变更；只在用户已经要求「发布技能」或「更新插件」后执行。不得触发其他 workflow，也不得合并刷新产生的 PR。

### 3. 等待并确认 workflow 成功

```bash
gh run list --repo soia-team/soia-open-skills \
  --workflow refresh-marketplace.yml --limit 1 \
  --json databaseId,status,conclusion,createdAt,url
gh run watch <run-id> --repo soia-team/soia-open-skills --exit-status
```

确认列出的 run 是本次触发的新 run，再用其 `databaseId` 作为 `<run-id>` 等待。只有 `status=completed` 且 `conclusion=success` 才继续；回执保留真实 run URL。

### 4. 确认 sha pin 已更新

```bash
domain_sha="$(gh api repos/soia-team/<domain-repo>/commits/main --jq .sha)"
market_sha="$(
  gh api repos/soia-team/soia-open-skills/contents/.claude-plugin/marketplace.json \
    -H 'Accept: application/vnd.github.raw+json' |
  jq -r --arg repo "soia-team/<domain-repo>" \
    '.plugins[] | select(.source | type == "object") |
     select(.source.repo == $repo) | .source.sha'
)"
test -n "$market_sha" && test "$domain_sha" = "$market_sha"
```

比较完整 SHA，不只比较前缀。插件条目不存在、SHA 为空或两者不等都算失败；报告两侧实际值，不继续指导客户更新。

### 5. 指导客户端更新

Claude Code：

```bash
claude plugin marketplace update soia
claude plugin update <插件>@soia
```

更新后必须完全退出并重启 Claude Code，才能让新技能与指令生效。

Codex：

```bash
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add <插件>@soia
```

只给客户实际使用的客户端指令；不要把 Claude 与 Codex 的命令混用，也不要声称尚未执行的客户端更新已经完成。

### 6. 验证客户端版本

```bash
claude plugin list
codex plugin list
```

在对应列表中确认 `<插件>@soia` 已存在并显示期望版本。最终回执包含域仓 PR、域仓 `main` SHA、workflow URL 与结论、marketplace sha pin、客户端、插件名和观察到的版本；无法在客户机器执行时明确标记为「待客户验证」。

## 工作流

1. 逐项执行 `npx skills add <repo> -g -a <agents> -s <skill> -y`。
2. 有 `--removed` 时执行同参 `npx skills remove`，并清理 `.agents`、`.claude`、`.soia`、`.workbuddy`、`.codex` 五处同名残留。
3. 执行 `npx skills update -g -y`，覆盖交叉引用的连带更新。
4. 遍历 `~/.agents/skills`：对有 `SKILL.md` 且 Codex 侧缺失的技能，创建相对软链；历史实证目录没有 `SKILL.md`，不进入 Codex。
5. 调用已安装的 `soia-meta-sync-skills`，目标为 `soia,workbuddy`。
6. 对账 `~/.agents/.skill-lock.json`：所有新技能必须来自 `--repo`，旧名必须零残留。
7. 按 `--repo-dir` → 进程环境 → 私有 v2 config → 只读 v1 config 回退 → 旧版兼容目录的顺序解析 checkout，并对比每项 `SKILL.md` version 与 `~/.agents/skills` 装机 version。


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
