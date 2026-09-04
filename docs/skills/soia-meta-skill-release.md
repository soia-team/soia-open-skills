# soia-meta-skill-release

> 正式发版与发布收尾；默认只发布，客户明确选择后才转交定向安装

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-skill-release) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

正式发版、发布技能、发布后安装

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
| --- | --- | --- |
| 发布 merge 后的一个或多个技能 | 远端正式版与市场 pin 收尾 | 发布回执与客户端更新指引 |
| 发布后按客户选择安装 | 转交 sync owner 的明确计划 | project/global、Agent、粒度与 dry-run |

### 客户如何使用

正式远端发版使用本文后半的 `formal_release.py`；下列 `release_skills.py` 只负责发布后的本机收口选择。先提供仓库、技能名单和可选旧名：

```bash
python3 skills/soia-meta-skill-release/scripts/release_skills.py \
  --repo <owner/name> \
  --skills <skill-a,skill-b> \
  --removed <legacy-skill> \
  --dry-run
```

复核 dry-run 后，移除 `--dry-run` 执行。默认 `remote-only`，不选择任何 Agent；要安装时必须明确 scope、Agent、skill/domain/all 与目标。版本核对按以下顺序解析本地 checkout：

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
