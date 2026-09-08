# SOIA 技能安装指南

[English](README.en.md) · [按使用场景选择安装组合](../install-profiles.md) · [先搞懂它怎么运转](../learning-guide.md)

SOIA 当前由 7 个公开域仓分发，设计能力已并入 dev。安装范围的唯一规范见[根 README 安装节](../../README.md#安装)：默认项目、明确宿主、单技能；下文的全局或整域命令仅供明确选择该范围时使用。

## 两条安装路线

| | 路线 A：npx 安装 | 路线 B：插件市场 |
|---|---|---|
| **适用宿主** | 所有宿主（60+） | Claude Code、Codex、Qwen Code、qodercli |
| **安装粒度** | 单个技能 | 整个领域（一个仓库 = 一个插件） |
| **落盘位置** | 默认 `<project>/.agents/skills`；选择 `-g` 才使用 `~/.agents/skills`，宿主按能力复用 | 各宿主独立的插件缓存 |
| **开关能力** | 无（安装即常驻） | 有（`enable` / `disable` 域级开关） |
| **适合** | 精确控制安装哪几个技能 | 按领域整体启停、控制常驻上下文 |

### 机制说明（重要）

**路线 A 默认项目级，`-g` 才是用户全局。** `-a` 选择宿主，`-s` 选择技能；`--copy` 调整宿主目标使用副本还是链接，不替代范围选择。安装后核对实际落点与当前项目的宿主目录。

**路线 B 的插件安装在各宿主独立的缓存目录**，不进入 `~/.agents/skills`。其中：

- **Claude Code**：插件与 npx 安装的技能是两条独立通道，互不影响。
- **Codex**：插件是**叠加**在共享真源之上的。安装插件不会减少 Codex 从 `~/.agents/skills` 读到的技能数量；若要减少 Codex 的常驻索引，需要缩减共享真源本身。

## 快速开始

### 路线 A：安装单个技能

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -a codex -s soia-pkm-clip-web
```

在目标项目中执行。参数：不带 `-g` 为项目级，`-g` 用户级 · `-a` 目标 AI（如 `claude-code`、`codex`）· `-s` 技能名 · `-y` 跳过确认。全局、多个宿主、`'*'` 或 `--all` 仅在明确选择后使用，不是默认值。

其他常用命令：

```bash
npx skills ls -a claude-code
```

```bash
npx skills remove -a codex -s <技能名>
```

```bash
npx skills update <技能名> --project
```

```bash
npx skills find <关键词>
```

### 路线 B：安装整个领域插件

以下是明确选择整域后的命令，不能将宿主用户级插件安装冒充项目级单技能。

Claude Code：

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

```bash
claude plugin install soia-pkm-vault@soia
```

Codex：

```bash
codex plugin marketplace add soia-team/soia-open-skills
```

```bash
codex plugin add soia-pkm-vault@soia
```

## 7 个领域插件

| 插件名 | 来源仓库 | 内容 |
|---|---|---|
| `soia-dev` | soia-open-dev-skills | 工程与 UI：功能规格、架构、实现审查、UI 设计验收、Open Design、图表和 Office 工具 |
| `soia-pkm-vault` | soia-open-pkm-vault-skills | 知识库：剪藏（网页/公众号/X/抖音/小红书/GitHub）、网盘、整理、提炼、转换、书库 |
| `soia-media-content` | soia-open-media-content-skills | 新媒体：文章成文、文章图片、公众号/X/小红书发布 |
| `soia-cwork-office` | soia-open-cwork-office-skills | 办公协作：飞书知识库与云盘、ProcessOn 图表 |
| `soia-edu-course` | soia-open-edu-course-skills | 教育课程：课程大纲设计、教案编写 |
| `soia-env` | soia-open-env-skills | 环境：AI CLI 与运行时安装、网络诊断、系统维护 |
| `soia-meta` | soia-open-skills | 生态管理：技能检索、多 AI 同步、发布收尾、提示词起草 |

## 按 AI 工具查看

| 工具 | 支持插件 | 安装指南 |
|---|---|---|
| Claude Code | 支持 | [claude-code.md](claude-code.md) |
| Codex | 支持 | [codex.md](codex.md) |
| Qwen Code | 支持 | [qwen-code.md](qwen-code.md) |
| qodercli | 支持 | [qodercli.md](qodercli.md) |
| Cursor | — | [cursor.md](cursor.md) |
| Windsurf | — | [windsurf.md](windsurf.md) |
| GitHub Copilot CLI | — | [copilot-cli.md](copilot-cli.md) |
| Zed | — | [zed.md](zed.md) |
| Gemini CLI | — | [gemini-cli.md](gemini-cli.md) |
| Antigravity（agy） | — | [antigravity-agy.md](antigravity-agy.md) |
| Kimi CLI | — | [kimi-cli.md](kimi-cli.md) |
| OpenCode | — | [opencode.md](opencode.md) |
| DeepCode | — | [deepcode.md](deepcode.md) |
| WorkBuddy | — | [workbuddy.md](workbuddy.md) |
| Trae | — | [trae.md](trae.md) |

## 宿主读取机制速查

| 读取方式 | 宿主 | 含义 |
|---|---|---|
| 直读共享真源 `~/.agents/skills` | Codex、Zed、Cursor、GitHub Copilot、Gemini CLI、DeepCode | npx 安装完即生效，无需额外步骤 |
| 读自己的目录 | Claude Code（`~/.claude/skills`） | npx 会自动建立链接 |
| 需要同步软链接 | Windsurf、Trae、WorkBuddy、Kimi、OpenCode、qodercli | 用下方 sync 工具分发 |

## 多 AI 同步工具

以下为已明确选择用户全局和多个宿主时的示例，不是项目默认安装；先由 `soia-meta-sync-skills` 生成计划并确认具体 source/target/skill，再执行。WorkBuddy 走[专家安装](workbuddy.md)，不通过 npx 或普通技能软链代装。

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --source-dir ~/.agents/skills --targets claude --skills <技能名> --dry-run
```

排除指定技能并持久化（之后的全量同步不会再链回来）：

```bash
python3 ~/.agents/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --source-dir ~/.agents/skills --targets claude --exclude-skills <技能名A>,<技能名B> --save-excludes
```

## 常见问题

**安装后没有生效？** 先在目标项目核对实际宿主技能目录、版本与链接，再用新会话输入真实请求。默认查项目 `.agents/skills` 与对应宿主目录；只有全局安装才查 `~/.agents/skills`。目录存在不等于自然命中或执行成功。

**插件和 npx 可以同时使用吗？** 可以，但同一宿主的同一技能会产生两份索引。建议同一宿主二选一。

**如何减少常驻上下文？** ① 路线 A 只用 `-s` 安装需要的技能；② 路线 B 装插件后用 `disable` 关闭暂时不用的领域；③ 长尾技能通过 `soia-meta-find-skill` 按需检索后再安装。

**如何安装非公开仓库的技能？** 命令形式与公开仓完全相同，把仓名换成你有权限的那个即可；前提是 `gh auth status` 已登录且你在该仓的授权名单里。没有权限时命令会直接失败，不会泄露仓内容。

**如何更新？** npx 路线：`npx skills update`；插件路线：`claude plugin update <插件名>` 或 `claude plugin marketplace update soia`。

## 保持更新

SOIA 市场清单在每次技能发布时刷新（由 `soia-meta-skill-release` 技能提交 PR 更新 sha pin），指向各域仓当时的最新提交。你只需让本地拉取这份清单：

| 宿主 | 手动更新 | 自动更新 |
|---|---|---|
| Claude Code | 界面 Sync + 齿轮更新；或 `claude plugin marketplace update soia` 后 `claude plugin update <插件>@soia` | 在 `~/.claude/settings.json` 为 soia 市场设 `autoUpdate: true`（[配置方法](claude-code.md#保持更新)） |
| Codex | `codex plugin marketplace add soia-team/soia-open-skills` 后 `codex plugin add <插件>@soia` | 不支持，需手动 |
| npx 路线 | 默认项目 `npx skills update <技能名> --project`；已选全局才用 `-g` | 按当前 CLI 能力与明确范围执行 |

团队场景可在项目 `.claude/settings.json` 中统一声明市场与插件并提交版本库，成员无需各自配置，详见 [Claude Code 指南](claude-code.md#团队统一配置)。
