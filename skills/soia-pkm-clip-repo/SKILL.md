---
name: soia-pkm-clip-repo
description: 把 GitHub 开源项目仓库一键归档到 Obsidian vault 的「开源项目图书馆」——clone 上游代码（不进 vault）+ 生成/更新项目卡（分类/语言/访问链接/最近提交自动填，用途/状态/stars/我的笔记留人工）+ 起调研笔记骨架 + 双向链接；也支持批量重跑刷新全部项目卡的自动字段。当用户说「归档这个项目 URL」「归档下这个仓库」「clip 这个 repo」「重新生成开源项目卡」时触发。
---

# soia-pkm-clip-repo

把散落各处的开源代码仓库调研，沉淀成 Obsidian vault 里可筛选、可点击跳转的「开源项目图书馆」索引层。

## 客户可读说明

### 这个技能可以做什么

把 GitHub 开源项目仓库一键归档到 Obsidian vault 的「开源项目图书馆」——clone 上游代码（不进 vault）+ 生成/更新项目卡（分类/语言/访问链接/最近提交自动填，用途/状态/stars/我的笔记留人工）+ 起调研笔记骨架 + 双向链接；也支持批量重跑刷新全部项目卡的自动字段。当用户说「归档这个项目 URL」「归档下这个仓库」...

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 完成本技能覆盖的工作 | 读取用户请求、必要上下文和本技能正文流程，执行最小可靠步骤 | 客户会看到 Obsidian/vault 文件变更、终端日志、生成产物路径和最终回执。 |
| 缺少依赖、权限、配置或 key | 停止需要外部状态的动作，明确指出缺什么 | 安装命令、申请地址、配置路径或需要客户确认的问题 |
| 执行完成 | 汇总成功、跳过、失败、文件变更和验证结果 | 一段可复制进工单/日志的完成回执 |

### 客户如何使用

1. 用自然语言说明目标，并提供必要输入：文件、URL、repo、workspace、proposal、vault 或平台账号状态。
2. Agent 先判断是否命中本技能，再检查依赖、配置、权限和风险动作。
3. 能 dry-run 或预览的动作先给预览；涉及删除、覆盖、发送、发布、写远端状态时先征求客户确认。
4. 执行后验证真实输出，不用“看起来成功”代替证据。
5. 最终回复必须给客户可见总结：做了什么、日志摘要、文件变化、问题和下一步。

### 依赖与安装

安装本技能（单个技能）：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-clip-repo -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-repo/config.yml
SOIA_PKM_CLIP_REPO_CONFIG_FILE=<custom-config-path>
```

- 如果本技能不需要私有配置，可以不创建 `config.yml`。
- 如果需要 API key、cookie、session、provider home 或本机路径，只能放进私有 `config.yml`、进程环境或 provider 自己的登录态里，不能写进仓库、vault 正文或日志。
- 强依赖、可选依赖和第三方 skill 关系必须以本 `SKILL.md` 后续的“依赖 / 前置 / 资源 / 边界”说明为准；没有写清楚时，先补说明或询问客户，不要猜。
- 第三方 skill 只能声明依赖和安装方式，不直接修改第三方 skill 文件。

### 日志与完成回执

每次执行都要让客户看见过程和结果。最低回执格式：

```markdown
完成：<一句话说明本次完成了什么>。

日志摘要：
- started: <检查到的输入/配置/依赖，不打印秘密值>
- processed: <数量或范围>
- created/updated: <数量或路径>
- skipped/failed: <数量和原因>

文件变化：
- <绝对路径或“未改动文件”>

验证：
- <运行过的检查、命令或人工核对点>

问题与下一步：
- <缺 key / 缺依赖 / 需要客户确认 / 建议下一条命令；没有则写“无”>
```

## 定位

代码本体留在本机一个 `git clone` 的 upstream 目录（**不进 vault**）；vault 只存索引——
一仓一张项目卡 + 一篇调研笔记骨架。结构与设计哲学同云盘馆藏 / 个人书库：外部资源留在
原地，vault 只装可点击、可筛选的索引层。

## 前置依赖

- Obsidian vault，含（或将新建）两个子目录：`60_开源项目/00_图书馆/项目卡/` 与
  `60_开源项目/10_调研笔记/`
- 本机一个存放 git clone 仓库的 upstream 目录（任意路径，多个仓库各占一个子目录）
- Python 3，纯 stdlib，无第三方依赖
- vault 定位优先级：命令行 `--vault` > 环境变量 `OBSIDIAN_VAULT`
- upstream 定位优先级：命令行 `--upstream` > 私有配置的 `SOIA_REPO_UPSTREAM_DIR`
- 私有 `config.yml`（可选，**不要放在 vault 或开源 skill 仓库**）：

  优先级：`$SOIA_PKM_CLIP_REPO_CONFIG_FILE`（或兼容别名 `$SOIA_PKM_CLIP_REPO_ENV_FILE`）> `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-repo/config.yml`。

  支持变量名：`OBSIDIAN_VAULT`、`SOIA_REPO_UPSTREAM_DIR`。真实路径只写在私有 `config.yml`
  文件里，不写入本文件或脚本源码（脚本本身不写死任何个人绝对路径）。

## 触发词

| 用户说 | 调用 |
|--------|------|
| 「归档这个项目 \<url\>」/「归档下这个仓库」/「clip 这个 repo」 | 单仓归档模式：`gen_repo_catalog.py --add <url>` |
| 「重新生成开源项目卡」/「批量刷新项目卡」/「新 clone 了几个仓库，补下卡」 | 批量模式：`gen_repo_catalog.py --upstream <dir> --vault <path>` |

## 工作流：归档开源项目 `<URL>`

1. 解析 URL 得到 `owner/repo`
2. upstream 目录下没有该仓 → `git clone` 进去；已存在则跳过 clone，直接建卡
3. clone 失败（私有仓库/无权限/网络问题）→ 跳过 clone，只用 URL 生成最小卡并提示用户
4. 调生成器单仓模式，给这一个仓建/更新项目卡（`60_开源项目/00_图书馆/项目卡/<仓名>.md`）
5. 在 `60_开源项目/10_调研笔记/` 起一篇 `YYYY-MM-DD-调研-<仓名>.md` 骨架笔记（若该仓已有
   调研笔记则跳过新建），frontmatter 带 `关联仓库` 双链回项目卡；正文骨架：
   `## 是什么` / `## 架构与代码` / `## 对我的价值` / `## 运行验证` / `## 我的结论`
6. 双向链接：卡片「## 关联调研」自动列出该笔记；笔记 `关联仓库` 字段指向该卡

「归档」只是快速建卡 + 笔记骨架 + 双链；深度调研（把笔记正文填完整）是后续单独一步，
不在本 skill 的自动化范围内。

## 批量模式（新 clone 了多个仓库，或想刷新全部自动字段）

```bash
python3 scripts/gen_repo_catalog.py --upstream <upstream目录> --vault <vault路径>
```

扫 upstream 下每个子目录，逐仓生成/更新项目卡。幂等：只刷新自动字段，不覆盖人工字段。

## 项目卡 frontmatter

```yaml
---
tags: [开源项目]
仓名: "<仓名>"
github: owner/repo             # 自动：git remote get-url origin 转 owner/repo
分类: <11 类之一>                # 自动：仓名→分类映射表 REPO_CATEGORY_MAP；未列出的按
                                # README/名字启发式归类，兜底「工具其他」
语言: Rust / Go / JS/TS / Python / Java / Swift / 未知   # 自动：启发式扫构建文件
用途: ""                        # 人工：这个仓库对你的具体用途
状态: 研究中                     # 人工：研究中 / 已借鉴 / 已弃 等
本地路径: "<upstream 下绝对路径>"  # 自动
访问链接: "https://github.com/<owner>/<repo>"  # 自动：github 字段拼出的完整 URL
最近提交: "YYYY-MM-DD"           # 自动：git log -1 --format=%cs，非 git 目录留空
stars:                          # 人工
---
```

**自动字段 vs 人工字段**——这是本 skill 的核心约定：
- **自动字段**（`github` / `分类` / `语言` / `本地路径` / `访问链接` / `最近提交` /
  正文简介 / 正文「## 关联调研」）：每次重跑都刷新，不要手工维护；「## 关联调研」
  按仓名匹配 `10_调研笔记/` 文件名（或其 frontmatter `关联仓库`）自动回填 wikilink
- **人工字段**（`用途` / `状态` / `stars` / 正文「## 我的笔记」）：生成器**不覆盖**，
  随便写，重跑安全

正文简介取 README 里第一句叙述性句子（跳过标题/徽章/HTML 装饰行/纯命令行/导航条），
抓不到时留 `(待补描述)`。

## 命令参考

```bash
# 单仓归档（clone + 建卡 + 起调研笔记骨架 + 双链）
python3 scripts/gen_repo_catalog.py --add https://github.com/<owner>/<repo> \
  --upstream <upstream目录> --vault <vault路径>

# 批量重跑（刷新全部仓库的自动字段）
python3 scripts/gen_repo_catalog.py --upstream <upstream目录> --vault <vault路径>

# 覆盖调研笔记目录（默认 60_开源项目/10_调研笔记）
python3 scripts/gen_repo_catalog.py --upstream <dir> --vault <path> --notes-dir <相对路径>
```

## 边界与异常

| 场景 | 处理 |
|------|------|
| clone 失败（私有仓库/无权限/网络问题） | 跳过 clone，只用 URL 生成最小卡，提示用户手动处理 |
| 非 git 目录（手动拷贝、没跑过 `git clone` 的项目） | `github`/`最近提交` 留空，不报错 |
| 仓库不在写死的 `REPO_CATEGORY_MAP` 里 | 走 README/仓名关键词启发式；都测不出归「工具其他」 |
| 项目卡已存在 | 幂等更新：只刷新自动字段，人工字段与「## 我的笔记」原样保留 |
| upstream 之外单独研究、不打算 clone 的项目 | 不适用本 skill，用 vault 内 `_模板/项目卡模板.md` 手工建卡 |
| 未指定 `--vault`/`--upstream` 且私有配置也没设 | 报错并提示环境变量名，不静默用某个人写死的默认路径 |

---

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结（单仓归档 / 批量刷新，涉及几个仓库）。
2. **文件变更** — 列出新建 / 更新的项目卡、新建的调研笔记（完整路径）。
3. **下一步** — 提醒用户：读完代码/做完调研后回填项目卡的 `用途`、`状态`、
   「## 我的笔记」。
