<div align="center">

# SOIA Skills 生态门户

中文 | [English](README.en.md)

规范真源、跨仓总目录、公开路由清单，以及 3 个生态级 meta 技能。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

</div>

## 这个仓库现在是什么

`soia-open-skills` 是 SOIA Skills 生态的门户仓，不再集中承载所有领域技能。领域技能按职责发布在独立仓库；本仓只保留：

- `soia-meta-sync-skills`、`soia-meta-skill-release`、`soia-meta-prompt-clarity`；
- 全生态统一的技能与数据存储规范、模板和审计工具；
- 14 个公开仓的拓扑总览；
- 由 12 个公开路由源生成的机器可读清单。

查找技能时先看 [`routing/routing-manifest.json`](routing/routing-manifest.json)，再从条目中的 `repo` 和 `skillPath` 安装或查看技能。

## 14 仓拓扑

| 仓库 | 一句话职责 | 安装 / 查看示例 |
|---|---|---|
| [`soia-open-skills`](https://github.com/soia-team/soia-open-skills) | 生态门户、规范真源、公开路由与 meta 技能 | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-sync-skills -y` |
| [`soia-open-env-skills`](https://github.com/soia-team/soia-open-env-skills) | 小白开发环境诊断、安装与升级支持 | `npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-environment-setup -y` |
| [`soia-open-pkm-clip-skills`](https://github.com/soia-team/soia-open-pkm-clip-skills) | 网页、社交内容与云盘资料的剪藏和原子操作 | `npx skills add soia-team/soia-open-pkm-clip-skills -g -a '*' -s soia-pkm-clip-web -y` |
| [`soia-open-pkm-vault-skills`](https://github.com/soia-team/soia-open-pkm-vault-skills) | Markdown vault 的初始化、整理、提炼、转化与书库维护 | `npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-bootstrap-vault-base -y` |
| [`soia-open-media-content-skills`](https://github.com/soia-team/soia-open-media-content-skills) | 文章写作、封面制作与公众号/X/小红书发布 | `npx skills add soia-team/soia-open-media-content-skills -g -a '*' -s soia-media-compose-article-draft -y` |
| [`soia-open-cwork-office-skills`](https://github.com/soia-team/soia-open-cwork-office-skills) | 飞书、ProcessOn 等企业协作与办公连接能力 | `npx skills add soia-team/soia-open-cwork-office-skills -g -a '*' -s soia-cwork-feishu-cli -y` |
| [`soia-open-dev-coding-skills`](https://github.com/soia-team/soia-open-dev-coding-skills) | 编码协议、任务闭环、代码审查、修复与 GitHub 操作 | `npx skills add soia-team/soia-open-dev-coding-skills -g -a '*' -s soia-dev-task-execute -y` |
| [`soia-open-dev-design-skills`](https://github.com/soia-team/soia-open-dev-design-skills) | Open Design、Archify、draw.io/Visio 与 Office 设计产线 | `npx skills add soia-team/soia-open-dev-design-skills -g -a '*' -s soia-dev-open-design-ops -y` |
| [`soia-open-dev-ts-skills`](https://github.com/soia-team/soia-open-dev-ts-skills) | 技术支持、终端长任务诊断与通用运维 | `npx skills add soia-team/soia-open-dev-ts-skills -g -a '*' -s soia-dev-terminal-ops -y` |
| [`soia-open-safe-skills`](https://github.com/soia-team/soia-open-safe-skills) | 代码安全审计与公开漏洞情报跟踪 | `npx skills add soia-team/soia-open-safe-skills -g -a '*' -s soia-safe-audit-fix-codebase -y` |
| [`soia-open-edu-course-skills`](https://github.com/soia-team/soia-open-edu-course-skills) | 课程大纲、教案讲义与测评技能孵化 | `npx skills add soia-team/soia-open-edu-course-skills -l --full-depth` |
| [`soia-open-dev-product-skills`](https://github.com/soia-team/soia-open-dev-product-skills) | 产品/产品经理语境的 PRD、用户故事与需求评审技能孵化 | `npx skills add soia-team/soia-open-dev-product-skills -l --full-depth` |
| [`soia-open-dev-testing-skills`](https://github.com/soia-team/soia-open-dev-testing-skills) | 互联网通用的测试用例、测试文档与 QA 流程技能孵化 | `npx skills add soia-team/soia-open-dev-testing-skills -l --full-depth` |
| [`soia-open-dev-release-skills`](https://github.com/soia-team/soia-open-dev-release-skills) | 互联网通用的软件发版清单与发布验证技能孵化 | `npx skills add soia-team/soia-open-dev-release-skills -l --full-depth` |

全部 14 个公开仓都是当前路由生成器的输入；产品、测试与发版孵化仓在发布首个公开技能前不产生路由条目。私有仓不进入公开清单；公司私有增量由 corp 仓自己的路由数据维护。行业定制流程版（保险 BA/TS 等）由维护者私有仓承载，不开源。

通用安装格式：

```bash
npx skills add soia-team/<repo> -l --full-depth
npx skills add soia-team/<repo> -g -a '*' -s <skill-name> -y
```

## 留存的 3 个 meta 技能

| Skill | 用途 | 安装 |
|---|---|---|
| [`soia-meta-sync-skills`](skills/soia-meta-sync-skills/) | 把已安装的共享技能源安全同步到用户明确选择的 AI 工具目录；支持 dry-run、硬依赖闭包和受限清理 | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-sync-skills -y` |
| [`soia-meta-skill-release`](skills/soia-meta-skill-release/) | 完成技能 merge 后的安装、旧名清理、软链与 lock/version 对账 | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-skill-release -y` |
| [`soia-meta-prompt-clarity`](skills/soia-meta-prompt-clarity/) | 起草、诊断和规格化中英文提示词，保留用户选择的语言与边界 | `npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-prompt-clarity -y` |

本仓技能的生成目录见 [`skills/README.md`](skills/README.md)。

## 规范真源

所有公开技能仓以本仓为统一规范来源：

- [`SKILL_SPEC.md`](SKILL_SPEC.md)：技能结构、命名、frontmatter、客户可读契约与验证要求；
- [`DATA_STORAGE_SPEC.md`](DATA_STORAGE_SPEC.md)：配置、凭据、状态、缓存、临时文件与输出的存储边界；
- [`templates/skill-template/`](templates/skill-template/)：新技能模板；
- [`scripts/audit_skills.py`](scripts/audit_skills.py)：公开技能审计真源；
- [`scripts/generate_skill_catalog.py`](scripts/generate_skill_catalog.py)：仓内 catalog 生成器；
- [`scripts/scaffold_repo_baseline.py`](scripts/scaffold_repo_baseline.py)：技能仓基线脚手架。

领域仓可以保留同步副本，但规范冲突时以本仓版本为准。

## 公开路由清单

[`routing/routing-manifest.json`](routing/routing-manifest.json) 的每个条目包含：

```json
{
  "skill_name": "soia-meta-sync-skills",
  "repo": "soia-open-skills",
  "skillPath": "skills/soia-meta-sync-skills",
  "visibility": "public"
}
```

重新生成：

```bash
python3 scripts/generate_routing_manifest.py
```

在门户瘦身 PR 尚未合并时，可用本地 3 个 meta 技能预览门户条目，其余仓仍通过 `gh api` 读取：

```bash
python3 scripts/generate_routing_manifest.py --local-portal-root .
```

生成器只纳入公开仓；私有与公司专属技能由其所属私有仓维护增量路由，不写入本文件。

## 维护与验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/generate_skill_catalog.py --check
python3 scripts/check_readme_coverage.py
python3 scripts/audit_skills.py --strict
git diff --check
```

第三方依赖边界见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。提交遵循短分支 → PR → CI → merge，不直接推送受保护的 `main`。

---

**soia-team** · [GitHub](https://github.com/soia-team)
