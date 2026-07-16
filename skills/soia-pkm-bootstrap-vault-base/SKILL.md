---
name: soia-pkm-bootstrap-vault-base
description: 初始化知识库通用结构：创建 PARA 目录、AGENTS 规则、Markdown 模板和多 AI 入口，并接入 soia-pkm-* 闭环技能。知识库中立，适用于任意本地 Markdown 知识库；Obsidian 或腾讯 ima 特化配置请使用对应 skill。Triggers：「初始化知识库」「从零建 Markdown 知识库」「搭通用 vault 骨架」「新建 PKM 库」
dependencies:
  external:
    - name: weread-skills
      required: false
      install: "npx skills add Tencent/WeChatReading -g -y"
    - name: huashu-weread-advisor
      required: false
      install: "npx skills add alchaincyf/huashu-weread -g -y"
version: 2.0.0
created_at: 2026-07-02 16:45:19
updated_at: 2026-07-16 16:00:31
created_by: claude opus 4.6
updated_by: codex 5
---

# soia-pkm-bootstrap-vault-base

用一套知识库中立的 Markdown 骨架初始化 AI-native 知识库：PARA 目录、AGENTS 路由、模板、多 AI 入口和 PKM 闭环技能。Obsidian、腾讯 ima 等平台只消费本地 Markdown；平台特化配置由对应 skill 负责。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 从零开始建本地 Markdown 知识库 | 按配置创建 PARA 骨架、各区规则、模板和使用手册 | 目录、规则文件、模板及终端摘要 |
| 让多个 AI 共用一套规则 | 创建多 AI adapter，并让 `AGENTS.md` 保持唯一真源 | 各入口文件和规则路由 |
| 接入 PKM 闭环 | 安装或检查 SOIA 的 clip、organize、distill、compose、publish 等技能 | 安装结果、缺失依赖和后续命令 |

本 skill 不负责安装或配置 Obsidian，也不负责把内容上传到 ima。需要这些能力时，继续使用 `soia-pkm-bootstrap-vault-obsidian` 或 `soia-pkm-bootstrap-vault-ima`。

### 客户如何使用

1. 提供目标 vault 路径，并说明是否使用默认 JSON 配置或自己的 JSON/YAML 配置。
2. 对通用 Markdown 知识库运行初始化脚本时使用 `--no-obsidian`，跳过默认配置中的 `.obsidian/**` 产物。
3. 检查生成的目录、规则和模板，再接入需要的 AI 与 PKM 技能。
4. 需要 Obsidian 时，让 `soia-pkm-bootstrap-vault-obsidian` 在 base 完成后处理平台配置；需要 ima 时，让 `soia-pkm-bootstrap-vault-ima` 处理云端消费端接入。
5. 执行后核对真实文件和闭环示例，不以命令退出码单独宣称完成。

### 依赖与安装

安装本技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-bootstrap-vault-base -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-bootstrap-vault-base/config.yml
SOIA_PKM_BOOTSTRAP_VAULT_BASE_CONFIG_FILE=<custom-config-path>
```

- 本 skill 没有 SOIA-managed hard dependency；两个平台特化 skill 将它声明为 hard dependency。
- `weread-skills` 与 `huashu-weread-advisor` 只在用户需要读书同步或增强时安装，不是通用初始化的阻断依赖。
- 私有路径、API key、cookie、session 和登录态只能放在用户自己的配置或 provider 登录态中。

### 日志与完成回执

每次执行都要报告：使用的 vault/config（不打印秘密）、创建或跳过的目录和文件类别、技能安装结果、验证命令、失败原因和下一步。涉及本地资源时只报告用户已提供的目标位置，不泄露其他本机路径或私有数据。

## 初始化流程（Step 2–5 + Step 6 可选）

### Step 2 — 建知识库骨架

```bash
python3 scripts/init_vault.py <目标 vault 路径> --no-obsidian
python3 scripts/init_vault.py <目标 vault 路径> --config <你的配置.json> --no-obsidian
```

脚本幂等地创建目录骨架、各区 `AGENTS.md`、Markdown 模板、使用手册、多 AI 入口文件。已存在的文件默认不覆盖。`--no-obsidian` 只跳过配置中 `.obsidian/**` 的目录和文件；不带该参数时保持原有默认行为，便于既有 Obsidian 用户兼容升级。

目录和种子文件来自 `scripts/default_config.json`，不要把个人需求写死进脚本。需要自定义时：

```bash
python3 scripts/init_vault.py --print-default-config > my-vault-config.json
python3 scripts/init_vault.py <目标 vault 路径> --config my-vault-config.json --no-obsidian
```

配置支持 JSON（零依赖）和 YAML（需本机装 PyYAML）。`scripts/example_custom_config.json` 演示如何增删目录、替换种子文件。

### Step 3 — 接入多 AI

`AGENTS.md` 是唯一规则源；其他入口只做适配，不另立一套规范。

| AI | 入口 | 说明 |
|---|---|---|
| Codex | `AGENTS.md` | 原生读取根规则与子目录规则 |
| Claude Code | `CLAUDE.md` | 回读 `AGENTS.md`，可加载 `~/.claude/skills/` |
| Gemini CLI | `GEMINI.md` | 回读 `AGENTS.md`，可使用共享 `~/.agents/skills/` |
| Antigravity CLI | `AGENTS.md` / `GEMINI.md` | 保留现有规则文件 |
| opencode | `OPENCODE.md` | 回读 `AGENTS.md` |
| workbuddy | `WORKBUDDY.md` / `.workbuddy/memory/` | 记忆只存长期事实，不替代 vault 正文 |

AI 直接读写 vault 的 `.md` 文件，不以任何平台插件作为通用层前置条件。技能安装约定：Claude Code 使用 `~/.claude/skills/`，Codex 使用 `~/.codex/skills/`，其他 agent 优先共用 `~/.agents/skills/`。

### Step 4 — 装 PKM 闭环技能

```bash
npx skills add soia-team/soia-open-skills
npx skills add Tencent/WeChatReading  # 仅在需要读书线时
```

bootstrap 自身只负责初始化本地骨架和安装自建 SOIA skill，不修改第三方 skill 文件。

闭环：`clip-*(收) → organize(整理) → distill(点) → compose(写) → publish(发)`。支撑：`soia-pkm-maintain`（周维护 lint + 简报；会话日志自动接入见 Step 6）。

### Step 5 — 验证

对 AI 说 `归档这条 X：<URL>`，确认文章落到配置中的文章摘抄目录；再说 `给这篇补我的看法` 跑一次提炼。若用户未安装对应 clip 或 distill skill，记录缺失项，不把未执行的闭环写成已完成。

初始化脚本的 fixture / forward test 至少覆盖两种运行：在临时目录执行一次带 `--no-obsidian` 的初始化，确认通用目录和模板存在且 `.obsidian/` 不存在；再在另一个临时目录执行不带该参数的初始化，确认默认 `.obsidian/snippets/wide-page.css` 存在。重复执行一次，确认已有种子文件被跳过而不是无提示覆盖。

### Step 6 — 接入会话日志（可选）

装完 PKM 技能后，先征得用户同意，再把每次会话的改动快照追加进配置的日志目录：

- Claude Code：在 `.claude/settings.json` 加 `SessionEnd` hook。
- Codex：改 `config.toml` 的 notify wrapper。
- 具体步骤见 `soia-pkm-maintain` 的 `references/session-log-setup.md`。

不得静默修改 agent 配置或读取私有会话内容。

## 从零到发布的工作流

初始化完成后，完整路径是：

```
clip-*(收集) → organize(清洗/归类/MOC) → distill(用户观点) → compose(草稿) → publish(平台适配/发布留底) → vault 周维护
```

提示词要让用户提供 vault 路径、目录命名偏好、研究领域、输出平台、可用 AI，以及是否使用默认配置；要求保留原文和来源，观点只写用户自己的；最终汇报已完成、未完成、需手动完成的事和下一步。

## 产物

一个可用的本地 Markdown 知识库骨架、已接入的多 AI 入口和 PKM 闭环技能。Obsidian 与 ima 只作为消费端，分别由对应特化 skill 接入。

## 完成后回执

执行完必须输出：

1. 做了什么：一句话总结。
2. 文件变更：新建、修改、移动的文件类别和位置。
3. 验证：实际运行过的命令或人工核对点。
4. 下一步：平台特化、缺失依赖或客户手动操作；没有则写“无”。
