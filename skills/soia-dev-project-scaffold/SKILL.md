---
name: soia-dev-project-scaffold
description: 为任意新 Git 项目生成最小 AI 协作基线：可编辑的 AGENTS.md 和 docs 导航目录；在写入前确认目标路径。
version: 1.0.0
created_at: 2026-07-20 11:52:54
updated_at: 2026-07-20 11:52:54
created_by: gpt-5.6-luna
updated_by: gpt-5.6-terra
---

# soia-dev-project-scaffold

## 客户可读说明

### 这个技能可以做什么

为一个新建或空白的 Git 项目创建一套最小、可编辑的 AI 协作基线：`AGENTS.md`、文档导航、项目概览、变更记录和 AI 工作记录目录。它不生成应用框架、云服务模块或组织内部治理结构。

### 客户如何使用

提供目标项目的绝对路径，并明确允许创建文件。先运行帮助或检查目录；目标已有同名文件时，先展示差异并取得覆盖确认。

```bash
bash skills/soia-dev-project-scaffold/shells/init-project-baseline.sh <project-path>
```

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-project-scaffold -y
```

依赖 POSIX shell、`mkdir` 和 `git`（仅用于检查，不初始化仓库）。不需要私有配置；项目特定规则应由客户在生成后的 `AGENTS.md` 中补充。

### 日志与完成回执

```markdown
完成：<已创建或预览的基线>。

日志摘要：
- target: <绝对路径>
- created/updated: <文件列表>
- skipped/failed: <原因或无>

验证：<git status、文件清单和读取检查>
问题与下一步：<需要填充的项目规则或无>
```

## 适用与边界

适用于“新建 Git 项目”“补 AGENTS.md”“建立 docs/ 导航”等请求。不用于已有项目的大规模重构、语言/框架脚手架，或需要组织专属目录模板的项目。

## 最小流程

1. 确认绝对目标路径和写入授权。
2. 检查是否已存在 `AGENTS.md` 或将生成的 docs 文件；存在时先停下并询问是否覆盖。
3. 运行脚本，或按同一文件清单手动创建。
4. 用 `git -C <project-path> status --short` 和 `find`/`sed` 复核生成结果。
5. 回执列出创建项、验证证据及仍需客户填写的项目规则。

## 输出

脚本生成：

- `AGENTS.md`
- `docs/navigation.md`
- `docs/project-overview.md`
- `docs/product/README.md`
- `docs/changelog/README.md`
- `docs/ai-workspace/README.md`
- `docs/templates/README.md`

## 验证

```bash
bash skills/soia-dev-project-scaffold/shells/init-project-baseline.sh --help
bash -n skills/soia-dev-project-scaffold/shells/init-project-baseline.sh
```
