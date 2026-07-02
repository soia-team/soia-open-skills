<div align="center">

# soia-open-skills

> *把「收藏」变成「作品」——AI 时代的个人知识管理技能体系。*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

<br>

**面向 Obsidian 的 `soia-pkm-*` 技能集 · 覆盖「收 → 整理 → 点 → 写 → 发」完整 PKM 闭环**

```bash
npx skills add soia-team/soia-open-skills
```

跨 agent 通用——Claude Code、Cursor、Codex、Gemini、Kimi 都能装。

[闭环框架](#pkm-闭环一篇内容的一生) · [Skills 清单](#skills-清单10) · [安装](#安装) · [Telegram 同步](#telegram-我的收藏同步clip-x) · [设计哲学](#设计哲学)

</div>

---

## PKM 闭环：一篇内容的一生

```
                     soia-pkm 个人知识管理闭环

   收 ────────→ 整理 ───────→ 点 ────────→ 写 ────────→ 发
 ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
 │ clip-x  │  │         │  │         │  │         │  │         │
 │ clip-   │  │organize │  │ distill │  │ compose │  │ publish │
 │  wechat │─→│ 分类/MOC│─→│收藏→观点 │─→│ 观点→文 │─→│ 公众号  │
 │ clip-web│  │ /归位/  │  │(你的看法)│  │ (草稿)  │  │/X/小红书│
 │ clip-   │  │ 补双链  │  │         │  │         │  │         │
 │  drive  │  │         │  │         │  │         │  │         │
 └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
   多源输入                                                  │
      ↑                                                      ▼
      └─────────  飞轮：发布 → 心得喂回 vault → 更好的输入  ──┘

  支撑：soia-pkm-bootstrap（一句话从零搭 vault + 接入多 AI）
        soia-pkm-reading-plan（读书线：把书单排成可执行阅读计划）
```

**核心理念**：收藏 ≠ 吸收。大多数人的知识库是"信息坟场"——囤了一大堆，从不回看。`soia-pkm` 把「收藏 → 观点 → 成文 → 发布」这条**从消费到创造**的链路，拆成职责单一、可组合的 skill，让 AI 帮你把囤积的信息真正变成**你自己的**作品。

---

## Skills 清单（10）

### 📥 收集 · clip 家族

| skill | 说明 |
|-------|------|
| [`soia-pkm-clip-x`](./skills/soia-pkm-clip-x/) | X 推文 / thread / Article 长文 → vault（fxtwitter API + Telegram 批量同步）|
| [`soia-pkm-clip-wechat`](./skills/soia-pkm-clip-wechat/) | 微信公众号文章 → vault（静态 HTML 抓取）|
| [`soia-pkm-clip-web`](./skills/soia-pkm-clip-web/) | 通用网页 / 博客 → vault（正文抽取）|
| [`soia-pkm-clip-drive`](./skills/soia-pkm-clip-drive/) | 云盘 PDF / Word / 文档 → vault |

### 🗂️ 整理

| skill | 说明 |
|-------|------|
| [`soia-pkm-organize`](./skills/soia-pkm-organize/) | 分类 / 补 frontmatter / 建两级 MOC / 按月归位 / 补双链 |

### ✍️ 提炼 → 成文 → 发布

| skill | 说明 |
|-------|------|
| [`soia-pkm-distill`](./skills/soia-pkm-distill/) | **收藏 → 观点**：读原文 → 苏格拉底式一次一问 → 你答 → 整理成「我的看法」（内容是你的，AI 只落字、不替写）|
| [`soia-pkm-compose`](./skills/soia-pkm-compose/) | **观点 → 文章草稿**（以你的观点为骨、摘抄为料）|
| [`soia-pkm-publish`](./skills/soia-pkm-publish/) | **一稿 → 多平台**：公众号（三级强调排版 + 推草稿箱）/ X thread / 小红书。只建草稿、不自动群发 |

### 🧰 支撑

| skill | 说明 |
|-------|------|
| [`soia-pkm-bootstrap`](./skills/soia-pkm-bootstrap/) | 从零初始化 AI-native vault（PARA 骨架 + AGENTS + 模板 + Bases + CSS + 多 AI 接入）|
| [`soia-pkm-reading-plan`](./skills/soia-pkm-reading-plan/) | 场景化阅读计划生成器（书单 / 主题 → 按真实字数排期的计划）|

---

## 安装

```bash
npx skills add soia-team/soia-open-skills
```

会把 `skills/` 下所有 skill 装到你 agent 的目录，**跨 agent 通用**（Claude Code / Codex / Cursor / Gemini / Kimi …）。装后直接说：

| 你说 | 触发 |
|------|------|
| `归档这条 X：<URL>` | clip-x |
| `整理文章库` / `重建 MOC` | organize |
| `给这篇补我的看法` | distill |
| `把这些观点写成一篇` | compose |
| `把这篇发成公众号` | publish |
| `从零搭个知识库` | bootstrap |

### 配置 vault 路径

```bash
# ~/.zshrc 或 ~/.bashrc
export OBSIDIAN_VAULT=~/Documents/MyVault           # 必须
export OBSIDIAN_ARTICLES="40_阅读与摘抄/10_文章摘抄"  # 可选，归档子目录
```

或每次调脚本时用 `--vault` 覆盖。

---

## Telegram 我的收藏同步（clip-x）

`clip-x` 的杀手锏：把手机随手转发到 Telegram「我的收藏」的 X 链接，一行命令批量归档。

**推荐路径：JSON 导出**（合规、零风控、不需 API 凭证）

1. Telegram Desktop → Settings → Advanced → Export Telegram data → 勾「私聊」+ 选 **Machine-readable JSON** → 导出。
2. 得到 `result.json`。
3. 跑同步（自动 URL 去重，已归档的跳过）：

```bash
python3 ~/.claude/skills/soia-pkm-clip-x/scripts/sync_telegram_export.py \
  "$HOME/Downloads/Telegram Desktop/ChatExport_XXXX/result.json" --dry-run   # 预览
python3 ~/.claude/skills/soia-pkm-clip-x/scripts/sync_telegram_export.py \
  "<path>"                                                                     # 实跑
```

高阶的 MTProto API 路径（国内不推荐，有风控）见 [clip-x 的 SKILL.md](./skills/soia-pkm-clip-x/SKILL.md)。

---

## 设计哲学

1. **收藏 ≠ 吸收**：闭环的命脉是 `distill`——把别人的文章变成**你自己的**判断。收藏一万条不如吸收一条。
2. **观点是你的，AI 只落字**：`distill` / `compose` 绝不替你编造观点，缺料就问。产出的是你的作品，不是 AI 的总结。
3. **Vault 不分子目录，靠多维索引**：文章按年扁平存放，主题聚合靠 frontmatter `topics:[[]]` + `_MOC/` + [Bases](https://help.obsidian.md/bases)，不靠文件夹。
4. **机器层 + AI 层双轨**：脚本管拉取 / 去重 / 规范化（机器段），LLM 管摘要 / 判主题 / 提炼（用户段），用段标题合同字符串通信，互不覆盖。
5. **职责单一、可组合**：每个 skill 只做一件事，串成闭环；扩展靠新建 skill + 依赖声明，**不改第三方 skill**（`npx skills check` 会覆盖）。
6. **跨 agent**：一次写 `SKILL.md`，所有支持 skills 标准的 AI 都能用。

---

## 命名规范

`soia-pkm-<环节>-<对象>`，全小写 kebab-case。`soia-pkm-*` 是 SOIA 技能体系的第四个域（与 `soia-design-*` / `soia-dev-*` / `soia-gov-*` 平级），专管个人知识管理。

## 仓库结构

```
soia-open-skills/
├── README.md
├── LICENSE · CONTRIBUTING.md
└── skills/                    ← npx skills 扫描此目录
    ├── soia-pkm-clip-x/       ├── soia-pkm-distill/
    ├── soia-pkm-clip-wechat/  ├── soia-pkm-compose/
    ├── soia-pkm-clip-web/     ├── soia-pkm-publish/
    ├── soia-pkm-clip-drive/   ├── soia-pkm-bootstrap/
    ├── soia-pkm-organize/     └── soia-pkm-reading-plan/
```

每个 skill 一个文件夹，独立 `SKILL.md`（frontmatter 含 `name` + `description`）+ 自己的 `scripts/`。

---

## 致谢与相关项目

配合使用的第三方 skill（本仓库借鉴其方法论，但不修改其文件）：

- [**alchaincyf/huashu-weread**](https://github.com/alchaincyf/huashu-weread) — 微信读书高阶顾问。`distill` 借鉴了它的 alchemy 提炼方法论，`reading-plan` 与它协同。README 风格亦受其启发。
- [**Tencent/WeChatReading**](https://github.com/Tencent/WeChatReading) — 微信读书原子 API skill，读书线的底层。

## 贡献

欢迎 PR / issue。加 skill 请：① 放 `skills/<name>/` ② 有 `SKILL.md`（`name` + `description`，description ≤200 字）③ 路径 / key / 个人数据全用环境变量，严禁硬编码 ④ 至少 1 个端到端用例。详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## License

[MIT](./LICENSE) — 自由 fork、改造、商用，请保留 attribution。

## 维护者

**soia-team** · [GitHub](https://github.com/soia-team)
