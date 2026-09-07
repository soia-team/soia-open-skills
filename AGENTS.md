# AGENTS.md - soia-open-skills

Rules for all AI agents editing this repository.

## 规则适用与任务完成

- 宿主实际加载的全局规则、父目录规则与本文件共同适用；本文件补充本仓事实和边界，不把共享贡献手册的旧示例当作新的授权。遇到无法按层级消解的实质冲突，指出具体条款，仅暂停受影响动作。
- 解释、诊断或审阅只读取相关规则与证据，不自动授权修复、安装或发布；明确要求实施且范围已清楚时，完成修改、适度验证和结果交付，不只返回计划。
- 已批准范围内的常规补丁、相关只读检查和验证连续推进；只在缺少会实质改变结果的信息、重叠改动无法安全保留，或下一步超出授权时询问。已确认且目标与影响未变的计划不重复确认。
- 未提交改动属于原作者；不清理、不混入提交、不覆盖。无关脏文件不阻断可隔离工作，真实重叠只暂停冲突部分。
- 不因仓名或“完整交付”默认启动多模型、子 Agent、全生态扫描、全量安装或产品治理流程；仅在用户要求、适用项目角色规则或任务风险明确需要时采用对应流程。
- 提交、远端写入、合并、部署、发布、发送消息、权限变更、凭据操作及重要数据删除仍遵守各自授权门；本地修改完成不代表这些后续动作已获授权。
- 交付说明实际改动、验证结果、未验证项及阻塞。要求实施的任务应做到授权边界内可验证的完成；区分本次已请求但待批的剩余步骤与未请求的后续动作；未请求的发布/安装不属于本次未完成工作。

## Repository Purpose

`soia-open-skills` is the public SOIA Skills ecosystem portal and specification
source of truth. It retains the `soia-meta-*` ecosystem skills (the generated catalog is the count source), the
shared authoring/storage specifications and template, the canonical audit and
catalog tooling, and the public cross-repository routing manifest. Domain skills
are published from focused spoke repositories. Every committed artifact must be
safe for users who do not share the maintainer's machine, vault layout, accounts,
private data, or SOIA internal workspace.

## Safety Rules

- No real API keys, tokens, cookies, session strings, passwords, account ids,
  private `config.yml`, or `.env` files.
- No maintainer-specific absolute paths such as `/Users/<name>/...`.
- No private family, home, health, finance, or learner profile context.
- Put user-specific behavior behind CLI args, env vars, or skill-specific
  user-owned config files outside this repo:
  `~/.config/soia-skills/<skill-name>/config.yml`. The former
  `<repo>/<skill-type>/<skill-name>/` namespace is only a read-compatible v1
  migration source; all new writes use the v2 skill-name directory.
- Public examples must use placeholders such as `<path>`, `<repo>`, and
  `<YOUR_KEY>`.

## Validation

日常验证按影响面选择：纯指令/文档修订先检查 diff、链接与条款一致性；脚本或技能行为变化运行受影响测试。涉及技能行为、脚本、依赖或公共工具的提交前执行以下完整门禁；纯指令/说明文档提交不机械套用全仓测试，但 CI/正式发布明确要求的检查不得省略：

```bash
# 仅缺依赖且环境安装已获授权时执行；已有依赖不重复安装
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/generate_skill_catalog.py --check
python3 scripts/audit_skills.py
git diff --check
```

修改技能时可补充运行兼容的 quick validator；仅其不支持本仓必需的版本、时间、作者等 frontmatter 时，记录不兼容并以本仓 audit 判定，不删除字段迁就工具。其他真实校验错误仍须处理。纯 AGENTS.md 修订不触发技能行为测试。辅助命令：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

只有本次明确包含安装验收时才执行安装；最终验收使用已发布的远端来源，不把本地调试副本冒充正式版。先确认 project/global、Agent 和 skill/domain/all，再按已确认计划执行。以下先列只读发现命令；全局全量命令仅供客户明确选择该范围后的安装，不是默认检查步骤：

```bash
npx skills add soia-team/soia-open-skills -l --full-depth
# 仅在全局 + 全量技能 + 全部 Agent 范围已明确批准后使用
npx skills add soia-team/soia-open-skills -g --all
```

## Git Workflow（本仓特有：默认分支是 main）

- 本仓同样以 `dev` 为集成分支，但**默认分支保持 `main`**——本仓既是插件市场
  又是插件（`soia-meta` 的 marketplace `source` 为 `"./"`，无 sha pin），
  客户端克隆市场时取的是**默认分支**。把默认分支指向 `dev` 会让 `-SNAPSHOT`
  直达所有客户端，且发布门禁拦不住（没有 pin 提交可检查）。
- 因此：提 PR 必须**显式 `--base dev`**，不要依赖默认分支。
- **新分支从 `main` 开**（最新正式版），PR 目标仍是 `dev`：实际核对 `main` → `dev` 的祖先关系和合并冲突，不把祖先关系当作无冲突的保证。确实要基于 dev 上尚未发布的
  工作时才从 `dev` 开，并在 PR 正文说明。
- `main` 不接收任何 PR：它只在正式发版时由 `dev` 快进推进。
- `dev` 上 plugin.json 版本带 `-SNAPSHOT` 声明下个目标，feature PR 不改版本号。

## 正式发版需用户逐次授权（硬门禁）

**正式发版是对外动作，必须用户当次点头才能执行，不得顺手做、不得推断授权。**

- 需本次发布授权：`formal_release.py`（或等效的手工步骤）、定稿 PR、`dev` → `main` 快进、tag、`gh release create` 与市场 pin 刷新。一个已批准的完整发布计划内按顺序执行，不逐命令重复确认；发现将夹带未批准改动时停下确认。
- 本地验证、`--dry-run` 与只读体检不需要发布授权。feature/fix PR 进入 `dev` 不属于正式发布，但远端写入和合并仍须在当前已授权工作流范围内，不能由“修 bug”推断。
- 「用户让我修某个 bug」**不等于**「用户让我发版」。按本次约定交付到本地修改、PR 或 `dev`；仅当发布尚未授权时在发布边界停止并报告。若发布已明确授权，继续完成已批准的 tag、Release、pin 与版本列车收口，不在合入 `dev` 后提前结束。
- 多 AI 并行时尤其重要：另一个 agent 可能正在改同一批仓，未经协调的发版会把
  它未完成的工作一起送出去。2026-08-03 实际发生过一次未授权发版。

## Open Items (current state)

- **Formal release plan P3/P4** (see the 2026-08-01 release plan, owned at the v7 workspace level): SkillHub onboarding (env / media-content / pkm-vault first), WorkBuddy sharecode trial, Red Skill uploads, first Xiaohongshu notes — blocked on the user's market report; decisions D5-D8 still open.
- **Unattended marketplace refresh** is undecided (needs a PAT secret or a ruleset change that weakens classic branch protection) — awaiting user decision. Until then, refresh pins via the skill-release flow.
- Version discipline is live: `dev` is the integration branch, `main` is always the latest formal release, plugin.json uses `-SNAPSHOT` during development, and the marketplace generator rejects manifests containing `-SNAPSHOT`. Do not revert this.

## 维护本仓技能

技能契约、调试安装、新增/改名/拆分/删除的完整流程，以及插件市场发布步骤，统一见
元仓的 [CONTRIBUTING.md](https://github.com/soia-team/soia-open-skills/blob/main/CONTRIBUTING.md)。
本文件只保留本仓特有的用途、边界与验证命令。
