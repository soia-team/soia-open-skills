# WorkBuddy 安装指南

WorkBuddy 是桌面客户端，接 SOIA 技能有两条路线，**推荐走专家路线**。

| | 专家路线（推荐） | 软链路线 |
|---|---|---|
| 装什么 | 一个角色化专家，自带该域全部技能 | 单个技能软链到 `~/.workbuddy/skills` |
| 按需能力 | 有——不召唤就不在场 | 无，装了就常驻索引 |
| 附带 | 人设、推荐提示词、头像 | 只有技能本身 |
| 适合 | 日常使用 | 只想要某一个技能 |

## 路线 A：安装 SOIA 专家（推荐）

SOIA 提供三个面向桌面办公的专家，各自携带对应域的全部技能：

| 专家 | 花名 | 携带技能 |
|---|---|---|
| 知识库管家 | 阿藏 | 知识库全域 26 个：网页/公众号/X/小红书/云盘归档、整理、解读、转 PPT 与长图 |
| 新媒体运营 | 阿墨 | 内容域 6 个：成文、配图、公众号/小红书/X 改写与存草稿 |
| 办公资料助手 | 阿档 | 协作域 3 个：飞书只读调研、知识库同步、ProcessOn 图表归档 |

在克隆好的元仓里先看计划：

```bash
python3 scripts/generate_workbuddy_experts.py --dry-run
```

确认后执行：

```bash
python3 scripts/generate_workbuddy_experts.py
```

生成器把技能从各域仓拷进专家包，再调用 WorkBuddy 官方 `expert-manager` 完成校验与注册。
重启 WorkBuddy，在【专家中心 - 我的专家】即可召唤。

专家定义与新增方法见 [`experts/README.md`](../../experts/README.md)。

### 验证

```bash
ls ~/.workbuddy/plugins/marketplaces/my-experts/plugins
```

三个 `soia-*` 目录都在，且同级 `.codebuddy-plugin/marketplace.json` 里有对应条目，即为成功。

### 更新

域仓技能更新后重跑生成器即可——专家包整目录重建，不会残留上一轮的技能。

### 卸载

删掉对应的专家目录，并从 `.codebuddy-plugin/marketplace.json` 里移除该条目。

## 路线 B：软链单个技能

只想要某一个技能时用同步工具。先装 `soia-meta` 插件拿到同步脚本：

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

```bash
claude plugin install soia-meta@soia
```

预览要同步什么（`<版本>` 取 `ls ~/.claude/plugins/cache/soia/soia-meta` 里最新的一个）：

```bash
python3 ~/.claude/plugins/cache/soia/soia-meta/<版本>/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --targets workbuddy --skills <技能名> --dry-run
```

确认预览后移除 `--dry-run` 执行。

### 验证

```bash
readlink ~/.workbuddy/skills/<技能名>
```

### 卸载

用同步工具的 `--exclude-skills` 排除该技能后重跑，或直接删掉软链。

## 特有说明

- WorkBuddy 也支持 SkillHub 与 zip 导入；zip 的包根目录必须包含 `SKILL.md`。
- 专家的技能是**包内实体**，与 `~/.workbuddy/skills` 里的软链互不影响。两条路线装了同一个技能时，
  索引里会出现两份且各自漂移——和插件与 npx 并存是同一类问题，建议二选一。

[← 返回安装指南](README.md)
