<div align="center">

# soia-open-skills

> *「不是把 X 存进硬盘，是让 X 上的每一句话能在你需要的时候被引出来。」*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)

<br>

**面向 Obsidian 重度用户的 Agent skill 集合 · 把日常知识管理工作流封装成 skill**

<br>

我们日常都在用 AI 整理信息。早上手机刷 X 看到一篇好 thread，转发到 Telegram「我的收藏」；电脑前打开 Claude Code 让它存进 Obsidian——但这一步特别繁琐：要先打开链接、要把 thread 拼起来、要补元数据。

本仓库把这类「**重复但有价值**」的工作流封装成 skill：装上 skill 后，一句话就能跑完。

```bash
npx skills add soia-team/soia-open-skills
```

跨 agent 通用——Claude Code、Cursor、Codex、Hermes、OpenClaw 都能装。

[Skills 清单](#skills-清单) · [安装](#安装) · [设计哲学](#设计哲学) · [Roadmap](#roadmap)

</div>

---

## Skills 清单

### 🐦 [x-to-obsidian](./skills/x-to-obsidian/)

把 X (Twitter) 推文 / thread / Article 长文一键归档到 Obsidian vault，附带 Telegram「我的收藏」批量同步。

**核心特性**：

- 基于 [fxtwitter](https://github.com/FixTweet/FixTweet) 公开 API — 无需 X API key、无需登录、零成本
- thread 自动沿 `replying_to_status` 回溯到根
- X Article 长文取 `content.blocks` 全量
- 元数据齐全（作者、views/likes/bookmarks、媒体直链、created_at）
- 自动 URL 去重（按 frontmatter `url:` 字段扫 vault）
- 多语言识别（zh / en / ja / ko，先检假名再判中文，日韩中分得清）
- Telegram 我的收藏两条同步路径：
  - **JSON 导出**（推荐）— Telegram Desktop 官方导出，零依赖、零风险、ToS 合规
  - **MTProto API**（高阶）— Telethon 实时同步，需 `api_id/hash` 和住宅 IP

**触发词**（说人话用，agent 自动识别）：

```
"归档这条 X：URL"          → archive_x.py <URL>
"归档并翻译：URL"          → 同上 + AI 自动翻译
"整理一下这条 thread：URL" → 同上 + 强制 thread 回溯
"同步我的电报收藏"          → sync_telegram_export.py <json_path>
```

---

## 安装

### 方式 A：npx skills add（推荐）

```bash
npx skills add soia-team/soia-open-skills
```

会自动把 `skills/` 下所有 skill 装到你 agent 的 skill 目录。

### 方式 B：手动 clone + 复制

```bash
# 1. clone 仓库
git clone https://github.com/soia-team/soia-open-skills.git
cd soia-open-skills

# 2. 复制到你 agent 的 skills 目录
cp -R skills/x-to-obsidian ~/.claude/skills/         # Claude Code
cp -R skills/x-to-obsidian ~/.codex/skills/          # Codex
cp -R skills/x-to-obsidian ~/.agents/skills/         # 通用 agent
```

### 配置 Obsidian vault 路径

每个 skill 都通过环境变量找 vault：

```bash
# ~/.zshrc 或 ~/.bashrc
export OBSIDIAN_VAULT=~/Documents/MyVault           # 必须
export OBSIDIAN_ARTICLES="Articles"                 # 可选，归档子目录，默认 "Articles"
```

或者每次调脚本时用 `--vault` 参数覆盖。

---

## Telegram 我的收藏同步指南

本仓库特别为重度用户提供「**手机收藏 → 电脑同步**」的完整工作流。

### 为什么需要这个

很多人的习惯：

```
早上 / 通勤
  手机刷 X → 看到好内容 → 长按转发 → Telegram「我的收藏」

晚上 / 工作时
  打开电脑 → 想把那些链接整理进 vault → ??
```

如果一条条手动复制粘贴归档，每次 30 条 X 至少 30 分钟。本 skill 把这一步压缩到一行命令。

### 推荐路径：JSON 导出（5 分钟完成 0-200 篇归档）

1. **Telegram Desktop 导出**：
   ```
   左上角汉堡 ☰ → Settings → Advanced → Export Telegram data
   勾「私聊」(Personal chats) ← 必勾
   格式选 ⊙ Machine-readable JSON
   时间范围按需，点导出
   ```

2. 几秒到 1 分钟后得到一个目录：
   ```
   ~/Downloads/Telegram Desktop/ChatExport_2026-06-30/
   ├── result.json   ← 主数据
   ├── chats/        ← 媒体（脚本不用这个）
   └── lists/
   ```

3. **跑同步**（默认从最新开始）：
   ```bash
   # 看看会归档什么（不实际跑）
   python3 ~/.claude/skills/x-to-obsidian/scripts/sync_telegram_export.py \
     "$HOME/Downloads/Telegram Desktop/ChatExport_2026-06-30/result.json" \
     --dry-run

   # 实际归档（自动 URL 去重，已存在的跳过）
   python3 ~/.claude/skills/x-to-obsidian/scripts/sync_telegram_export.py \
     "$HOME/Downloads/Telegram Desktop/ChatExport_2026-06-30/result.json"

   # 只处理某日期之后的
   python3 ~/.claude/skills/x-to-obsidian/scripts/sync_telegram_export.py \
     "<path>" --since 2026-06-01

   # 限量
   python3 ~/.claude/skills/x-to-obsidian/scripts/sync_telegram_export.py \
     "<path>" --limit 30
   ```

4. **以后每月**重新导出一次（30 秒）+ 跑命令 → **自动跳过已归档的，只处理新增**。

**这条路径不需要任何 Telegram API 凭证**，Telegram 官方支持，ToS 合规，0 风控风险。

### 高阶路径：MTProto API

如果你想「不导出就能拉」，可以走 MTProto API。但**国内大陆用户不推荐**：

- 要去 [my.telegram.org](https://my.telegram.org/auth) 申请 api_id + api_hash
- 申请 app 时 Telegram 对**机房 IP** 和**手机号-IP 跨区**有强风控
- 大陆 +86 号 + 国内 IP / 机场节点 / 美国 VPN 几乎必触发 ERROR
- 反复尝试会**锁号 24-72 小时**

如果你确实有住宅 IP（香港 PCCW / 日本 HKT / 等），按 [skills/x-to-obsidian/SKILL.md](skills/x-to-obsidian/SKILL.md) 的「MTProto」段操作。

---

## 设计哲学

### 1. Vault 不分子目录，靠多维度索引

Obsidian 的核心价值是 **frontmatter + tag + wikilink 的多维度索引网络**。文件夹是单维度、强约束的；多维度索引才是 Obsidian 的正解。

本套 skill 严格遵守：

- 文章按年扁平存放，不按主题分子目录
- 主题聚合靠 frontmatter `topics: [[xxx]]` + `_MOC/<主题>.md`
- 跨域关联靠 wikilink `[[]]`
- 复杂查询靠 [Obsidian Bases](https://help.obsidian.md/bases)（1.7.0+ 核心功能）

### 2. 机器层 + AI 层双轨

- **机器层**（脚本）：拉数据、去重、规范化、写入合同字符串段
- **AI 层**（LLM）：补摘要、判主题、关联人物、提炼笔记

两层用**段标题合同字符串**通信（如 `## Summary`），互不干扰。脚本写"机器段"，AI 写"用户段"，用户在"思考段"。

### 3. 用户内容永不覆盖

所有写入都遵守：

- 用户写的 `## My Thoughts` `## Related` 等段**绝不被脚本动**
- 机器段标记明确（带「来自 fxtwitter · 自动同步」字样），用户在里面写字会被下次同步覆盖（这个行为是合同里写明的）
- 已存在文件的 `topics` / `people` / `Summary` 字段在 `--force` 重抓时会被覆盖（明确警告）

### 4. 跨 agent 通用

不绑定特定 agent。`SKILL.md` + 一组 Python 脚本（纯 stdlib，可选第三方）就是 skill 的全部。Claude Code / Codex / Cursor / Hermes 都能装。

---

## 仓库结构

```
soia-open-skills/
├── README.md              ← 你正在看
├── LICENSE                ← MIT
├── .gitignore
└── skills/                ← npx skills 扫描这个目录
    └── x-to-obsidian/     ← 第一个 skill
        ├── SKILL.md       ← skill 入口（必须）
        └── scripts/
            ├── archive_x.py
            ├── sync_telegram_export.py
            ├── sync_telegram_saved.py
            └── generate_telegram_session.py
```

未来添加新 skill：

```
skills/
├── x-to-obsidian/
├── readwise-to-obsidian/    ← 未来
├── notion-to-obsidian/      ← 未来
└── ...
```

每个 skill 一个文件夹，独立的 `SKILL.md` + 自己的脚本。

---

## Roadmap

### 已完成

- ✅ **x-to-obsidian** — X 推文 / thread / Article 归档 + Telegram 我的收藏同步

### 计划中

- ⏳ **readwise-to-obsidian** — Readwise 高亮一键导入 vault
- ⏳ **notion-to-obsidian** — Notion 页面批量迁移（保留 toggle、callout、引用）
- ⏳ **webclip-to-obsidian** — 用 Obsidian Web Clipper 抓的 Inbox 文件自动归类
- ⏳ **podcast-to-obsidian** — 播客文稿（小宇宙 / Spotify）归档
- ⏳ **rss-to-obsidian** — RSS 阅读器（如 Feedly）的 starred items 归档

欢迎 issue 提需求或 PR 提交新 skill。

---

## 致谢与相关项目

本仓库 **不包括** 但 **强烈推荐配合使用** 的 skill：

- [**alchaincyf/huashu-weread**](https://github.com/alchaincyf/huashu-weread) — 微信读书高阶顾问 skill（4 个 workflow：advisor / path / alchemy / review）。在 weread 官方 skill 之上做工作流编排。花叔写的，本仓库借鉴了它的 README 风格。
- [**WeRead 官方 skill**](https://weread.qq.com/r/weread-skills) — 微信读书原子 API skill，作为 huashu-weread-advisor 的底层。

---

## 贡献

欢迎 PR、issue。如果你也在搭建类似的 Obsidian + AI 知识管理系统，特别欢迎：

- 新 skill（如 Notion / Logseq / Roam Research 迁移）
- 现有 skill 的 bug 修复 / 体验改进
- 文档完善

加 skill 时请遵守：

1. 放在 `skills/<skill-name>/` 下
2. 必须有 `SKILL.md`，frontmatter 含 `name` 和 `description`
3. `description` 控制在 200 字符内（渐进式披露原则）
4. 任何路径、key、个人数据**严禁**硬编码，全部用环境变量
5. 给出至少 1 个端到端用例

---

## License

[MIT](LICENSE) — 自由 fork、改造、商用。请保留 attribution。

---

## 维护者

**soia-team** · [GitHub](https://github.com/soia-team)
