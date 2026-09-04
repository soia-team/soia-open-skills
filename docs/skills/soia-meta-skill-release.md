# soia-meta-skill-release

> 域仓正式发版（dev→main、tag、Release、notes、CHANGELOG）与发布收尾：市场 pin 刷新、客户端更新、旧名清理、WorkBuddy 专家安装、dev 快照试装

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-skill-release) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「正式发版」「发布技能」「更新插件」「技能发布收尾」「装到 WorkBuddy」「试装 dev」

## 能力与用法

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

## 安装

客户明确选择安装整个 `soia-meta` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-meta@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-meta@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-skills -a <agent> -s soia-meta-skill-release -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
