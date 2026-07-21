---
name: soia-pkm-maintain
description: Obsidian vault 维护技能（支撑类）——三个工作流：①周维护（lint 四类体检 + 周简报）②全库地图重生成 ③AI 会话日志接入（Claude Code / Codex 双平台）。底层机械脚本纯 Python stdlib / bash，参数化支持任意 vault 路径，不硬编码具体库。Triggers：「vault 周维护」「跑周维护」「重建全库地图」「更新知识库地图」「接入会话日志」「配置会话日志」
dependencies:
  optional: [soia-pkm-organize-article-moc]
version: 1.0.1
created_at: 2026-07-07 13:32:04
updated_at: 2026-07-20 19:05:00
created_by: claude opus 4.6
updated_by: claude fable 5
---

# soia-pkm-maintain

PKM 闭环的**维护·支撑环节**：不产出新知识内容，只保证 vault 这套基础设施本身是干净、可信、有留痕的——链接不断、标签不漂、地图不过时、AI 改了什么有迹可循。

## 客户可读说明

### 这个技能可以做什么

Obsidian vault 维护技能（支撑类）——三个工作流：①周维护（lint 四类体检 + 周简报）②全库地图重生成 ③AI 会话日志接入（Claude Code / Codex 双平台）。底层机械脚本纯 Python stdlib / bash，参数化支持任意 vault 路径，不硬编码具体库

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-maintain -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-maintain/config.yml
SOIA_PKM_MAINTAIN_CONFIG_FILE=<custom-config-path>
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

vault 用久了会积累三类"基础设施债"：

1. **内容腐化**：死链、重复文件名、标签漂移、过期未复核的时效性文章——不影响单篇笔记能不能读，但会拖累检索和 MOC 聚合的可信度。
2. **地图过时**：全库结构变了，`OB知识库地图.md` 这类总览快照却停留在旧状态。
3. **AI 改动无留痕**：多个 AI（Claude Code / Codex）都在改 vault，但改了什么、什么时候改的，没有统一记录。

本 skill 用三个工作流分别对应：①体检 + 周简报，②重生成地图，③接会话日志。全部是**机械层脚本 + AI 判断**的组合——脚本负责确定性扫描/生成，AI 负责读报告、写简报、和用户对齐配置改动。

## 前置依赖

- Obsidian vault（任意目录结构，脚本不假设固定的分区命名）
- Python 3，纯 stdlib（`lint_vault.py` / `gen_vault_map.py` 无第三方依赖）
- bash（`session_end_log.sh` / `codex_notify_wrapper.sh`）
- `--vault <path>`，或私有 `config.yml` 里的 `env.OBSIDIAN_VAULT`（二选一，`--vault` 优先）
- 软依赖 `soia-pkm-organize-article-moc`：MOC 重建、主题归类是它的职责，本 skill **只引用，不重复实现**——lint 报告里的"重复文件名"如果是需要合并 MOC 的场景，转给 `soia-pkm-organize-article-moc` 处理

## 触发词

| 用户说 | 调用 |
|--------|------|
| 「vault 周维护」「跑周维护」 | 工作流①：lint 四类体检 + 周简报 |
| 「重建全库地图」「更新知识库地图」 | 工作流②：重生成 `OB知识库地图.md` |
| 「接入会话日志」「配置会话日志」 | 工作流③：Claude Code / Codex 会话日志接入 |

## 工作流① 周维护（lint + 周简报）

1. 跑体检脚本：
   ```bash
   python3 scripts/lint_vault.py --vault <path>
   ```
   拿到四类发现：死链 wikilink / 重复文件名 / 主标签漂移 / 过期文章。
2. AI 汇总写周简报，落地路径：
   ```
   <vault>/<周报目录>/<YYYY>-W<ISO周数>-vault周报.md
   ```
   例：`2026-W28-vault周报.md`（ISO 周数取当天 `date.isocalendar()` 的周数，两位数补零）。

   frontmatter：
   ```yaml
   ---
   tags: [周报]
   created: <YYYY-MM-DD>
   ---
   ```

   正文骨架（四个小节都要写，没有发现的一律写"无"，不要整节省略）：
   - **近 7 天新进文章统计**（AI 用 `git log` 或按文件名日期扫一遍新增的 `.md`）
   - **lint 四类发现**（死链 / 重复文件名 / 主标签漂移 / 过期文章，为空写"无"）
   - **已执行的安全修复**（本轮 AI 已经直接改掉的，见第 4 步）
   - **建议人工处理清单**（拿不准、需要用户判断的项）

3. **MOC 归并声明依赖 `soia-pkm-organize-article-moc`**：如果发现的重复文件名/标签漂移背后是"需要重新归类/合并 MOC"，本 skill 不做这个判断，只在简报里标注并建议衔接 `soia-pkm-organize-article-moc`，不越界重复实现它的主题归类逻辑。
4. 只有**能确定是安全修复**的项才直接改（比如死链明显是打错了大小写/多了个空格、能一一对应到唯一同名文件）；只要有歧义（比如同名文件不止一个候选、标签漂移可能是故意的新分类）就只写进简报，不擅自动内容。

## 工作流② 全库地图重生成

```bash
python3 scripts/gen_vault_map.py --vault <path>                    # 覆盖 <vault>/20_资料库/OB知识库地图.md
python3 scripts/gen_vault_map.py --vault <path> --output /tmp/x.md # 干跑预览，不碰 vault
```

遍历全 vault 目录树，`.md` 渲染成可点击的 wikilink，非 `.md` 只列文件名；超过 40 个文件的目录压缩显示（前 2 + 末 1 + 计数）。头部"文件数/目录数/GB"统计和日期都是运行时动态算的，不是写死的历史快照。

## 工作流③ AI 会话日志接入

按 **[references/session-log-setup.md](references/session-log-setup.md)** 执行完整步骤（Claude Code 的 `hooks.SessionEnd` 片段示例、Codex 的 `notify` + wrapper 接入步骤、两平台差异、卸载方法都在里面）。

> ⚠️ **显著提醒**：写入 Claude Code 的 `.claude/settings.json`（hooks）或修改 Codex 的
> `config.toml`（notify）之前，**必须先向用户说明要改什么、为什么改，并获得明确同意，
> 绝不能静默改配置**。已有 hooks 时是"合并追加"，不是整体覆盖。

底层脚本：`scripts/session_end_log.sh`（两平台共用，靠 `--agent` 区分子目录和节流状态文件）+ `scripts/codex_notify_wrapper.sh`（Codex 专用包装层，因为 `notify` 只能挂一条命令）。

## 命令行参考

```bash
# 工作流① lint 体检
python3 scripts/lint_vault.py --vault <path>
python3 scripts/lint_vault.py --vault <path> --json
python3 scripts/lint_vault.py --vault <path> --exclude "20_资料库/OB知识库地图.md,某目录/某文件.md"
python3 scripts/lint_vault.py --vault <path> --tags "书库,童书,日记,调研,文章摘抄,阅读记录,阅读计划,重读,周报"

# 工作流② 地图重生成
python3 scripts/gen_vault_map.py --vault <path>
python3 scripts/gen_vault_map.py --vault <path> --output /tmp/preview.md

# 工作流③ 会话日志（一般由 hooks/notify 自动调用，不需要手动跑）
bash scripts/session_end_log.sh --vault <path> --agent Claude-Code
bash scripts/session_end_log.sh --vault <path> --agent Codex
```

所有脚本共享同一套参数化约定：`--vault <path>` 或私有 `config.yml` 的 `env.OBSIDIAN_VAULT`（二选一，`--vault` 优先），不硬编码任何具体 vault 路径。会话日志目录可用 `--log-dir <vault内相对目录>` 或私有配置的 `SOIA_SESSION_LOG_DIR` 覆盖；默认是 `30_日志与思考/20_Agent工作日志`。私有配置优先级：`$SOIA_PKM_MAINTAIN_CONFIG_FILE`（或兼容别名 `$SOIA_PKM_MAINTAIN_ENV_FILE`）> `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-maintain/config.yml`。

## 边界与异常

| 场景 | 处理 |
|------|------|
| 未指定 `--vault` 且私有 `config.yml` 中无 `OBSIDIAN_VAULT` | 报错退出（`exit 1`），提示二选一 |
| lint 四类发现都为空 | 周简报里写"无"，不是省略该小节 |
| lint 报告里的重复文件名/标签漂移涉及主题归类判断 | 转交 `soia-pkm-organize-article-moc`，本 skill 不做归类决策 |
| 微信读书同步需求 | 转交 `soia-pkm-library-weread-sync`；本 skill 不碰书库数据线 |
| 书库补建记录 / 总览生成需求 | 转交 `soia-pkm-library-book-catalog`；本 skill 不碰书库数据线 |
| 会话日志接入需要改 `settings.json` / `config.toml` | 必须先征询用户、拿到同意才写，绝不静默改配置；已有配置要合并不要覆盖 |
| Codex `notify` 已经接了别的用途（如 computer-use 客户端） | 用 `codex_notify_wrapper.sh` 包装，不覆盖原命令，见 references 文档 |
| `lint_vault.py` 遇到附件类 wikilink（图片/PDF/office 文档等） | 视为附件引用，跳过死链检查（脚本只维护 `.md` 索引） |
| 想干跑预览地图，不覆盖 vault 原文件 | `gen_vault_map.py` 支持 `--output <临时路径>` |

## 完成后回执

执行完**必须**向用户输出（不要默默做完）：

1. **做了什么** — 一句话总结完成的工作。
2. **文件变更** — 列出新建 / 修改 / 移动的文件（完整路径）；未改动文件则说明"未改动文件"。
3. **下一步** — 可选的后续建议（如衔接 `soia-pkm-organize-article-moc` 处理 MOC 归并）。
