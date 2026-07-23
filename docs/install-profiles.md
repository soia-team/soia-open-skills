# 分域安装配置

[完整安装指南](install-guide.md) · [English installation guide](install-guide.en.md)

按机器的主要用途安装必要仓库，减少所有宿主启动时需要索引的技能描述。以下命令均从远端仓库安装到用户级；`-a '*'` 表示写入所有受支持的 agent 目标，`-y` 跳过交互确认。

## 安装矩阵

| 场景 | 安装范围 | 适合任务 |
|---|---|---|
| 写作机 | PKM 剪藏 + PKM vault + media | 收集素材、整理知识库、写作与发布 |
| 编码机 | meta + dev coding + dev design | 编码闭环、终端操作与设计资产 |
| 教育机 | edu + PKM vault 精选子集 | 课程大纲、教案、阅读计划与教学资料整理 |
| 最小 | 3 个 meta 技能 | 提示词澄清、技能同步与发布收尾 |

### 写作机

```bash
npx skills add soia-team/soia-open-pkm-clip-skills -g -a '*' -y
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -y
npx skills add soia-team/soia-open-media-content-skills -g -a '*' -y
```

### 编码机

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -y
npx skills add soia-team/soia-open-dev-coding-skills -g -a '*' -y
npx skills add soia-team/soia-open-dev-design-skills -g -a '*' -y
```

### 教育机

教育技能全装；PKM vault 只装初始化、文章分析整理和阅读计划所需子集：

```bash
npx skills add soia-team/soia-open-edu-course-skills -g -a '*' -y
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' \
  -s soia-pkm-bootstrap-vault-base \
  -s soia-pkm-bootstrap-vault-obsidian \
  -s soia-pkm-interpret-article-analysis \
  -s soia-pkm-organize-article-moc \
  -s soia-pkm-reading-plan -y
```

### 最小配置

显式列出 3 个 meta 技能，避免本仓以后新增技能时被意外带入：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' \
  -s soia-meta-prompt-clarity \
  -s soia-meta-sync-skills \
  -s soia-meta-skill-release -y
```

## 各宿主的按需机制

- **Claude Code：双层目录。** 用户级 `~/.claude/skills/` 对所有项目生效，项目级 `.claude/skills/` 只服务当前仓库；两层都会先把技能名和 `description` 作为路由索引提供给模型，完整正文仅在命中时加载。因此全局层只放高频通用技能，项目专用技能放项目层，并保持 description 短而有区分度。详见 [Claude Code Skills 官方文档](https://code.claude.com/docs/en/slash-commands)。
- **Kimi Code CLI：启动时选目录。** 默认自动发现用户级和项目级技能；需要一次性限定技能集合时，重复传入 `--skills-dir <path>`。该参数会替换本次启动的自动发现目录，而不是叠加；需要持久叠加目录时使用配置项 `extra_skill_dirs`。详见 [Kimi Agent Skills 官方文档](https://moonshotai.github.io/kimi-cli/en/customization/skills.html)。
- **Codex：目录自动发现。** Codex 自动扫描从当前目录到仓库根目录各层的 `.agents/skills/`，并扫描用户级 `~/.agents/skills/`；技能目录可使用软链接。Codex先索引名称、描述和路径，命中后再加载正文。详见 [Codex Skills 官方文档](https://developers.openai.com/codex/skills/)。

安装后若某个宿主没有发现技能，先确认该宿主实际扫描的目录，再用 `soia-meta-sync-skills` 预览并同步到明确选择的目标；不要手工复制技能目录。

## 路由器模式：覆盖低频长尾

不想预装全部领域技能时，只安装通用发现器：

```bash
npx skills add vercel-labs/skills -g -a '*' -s find-skills -y
```

日常先让 `find-skills` 搜索公开 Agent Skills；SOIA 生态内的低频需求再查本仓生成的 [`routing/routing-manifest.json`](../routing/routing-manifest.json)，按条目的 `repo` 与 `skillPath` 精确安装。这个组合把高频能力留在本机索引里，把未预装的长尾能力交给路由清单兜底。
