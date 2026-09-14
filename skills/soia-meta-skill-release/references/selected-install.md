# 定向安装与客户端更新

仅在客户明确请求安装、更新或 dev 试装时读取对应部分；默认只发布，不读本机安装目录。先核对当前宿主版本与官方帮助，以下历史命令不是无条件执行清单。

## 本机收口入口

正式远端发版使用SKILL.md 的 `formal_release.py`；下列 `release_skills.py` 只负责发布后的本机收口选择。先提供仓库、技能名单和可选旧名：

```bash
python3 skills/soia-meta-skill-release/scripts/release_skills.py \
  --repo <owner/name> \
  --skills <skill-a,skill-b> \
  --removed <legacy-skill> \
  --dry-run
```

复核 dry-run 后，移除 `--dry-run` 执行。默认 `remote-only`，不选择任何 Agent；要安装时必须明确 scope、Agent、skill/domain/all 与目标。版本核对按以下顺序解析本地 checkout：

1. `--repo-dir <repo-path>` 显式路径；
2. 当前进程的 `SOIA_SKILL_REPOS_ROOT/<repo-name>`；
3. 私有 YAML：`--config` → `SOIA_META_SKILL_RELEASE_CONFIG_FILE` → `~/.config/soia-skills/soia-meta-skill-release/config.yml` 中的 `env.SOIA_SKILL_REPOS_ROOT`；
4. v1 私有配置目录只读回退（会向 stderr 输出建议的 `mv` 迁移命令）；
5. 旧版维护者本地目录约定，仅作弃用中的向后兼容回退。

仓库内部仍须采用 `skills/<skill-name>/SKILL.md` 布局。对未来新增仓库，只要 `--repo` 提供对应的任意 `<owner>/<repo-name>`，无需修改脚本。

## 工作流

`--install-mode` 默认 `remote-only`。**默认不修改任何本机技能目录**；项目/全局、单/多 Agent、skill/domain/all 都保留，但必须由客户明确选择。

### `remote-only` 模式（默认）

读取仓库版本并输出发布/市场/客户端更新指引；不安装、不删除旧名、不清理缓存，也不广播任何 Agent。客户只说“发布”时走这条。

### `ask` 模式（`--install-mode ask`，交互式选择）

需要交互终端，只确认“发布后是否继续安装”。若选安装，调用 Agent 必须已收齐 `--install-scope`、`--agents`、`--target-kind`、项目或全局目标与 `--source-dir`；缺项即停止并列出缺口，不代选。仅收齐选择字段不等于写入批准；只有已展示影响并获客户明确批准、且包含 source、具体 target、action 以及删除/替换影响的完整计划，才可传给 sync owner 而不重复询问。计划字段变化时重新确认。非交互环境改用 `remote-only` 或参数齐全的 `selected-install`。

### `selected-install` 模式（显式 opt-in）

本模式把明确选择转交 `soia-meta-sync-skills`，自身不维护第二套目录映射。先 dry-run；`all` 或全部宿主的实际写入还需 `--confirm-all-targets`。`plugin`/`npx` 只作为旧调用的兼容别名，分别映射到 `remote-only`/`selected-install`。

```bash
python3 skills/soia-meta-skill-release/scripts/release_skills.py \
  --repo <owner/name> --skills <skill> --install-mode selected-install \
  --install-scope project --project-dir <project> --agents <agent> \
  --target-kind skill --source-dir <shared-skill-dir> --dry-run
```


## 试装 dev（本地验证快照版）

触发词：**「试装 dev」**、**「本地装 dev 版」**。dev 快照只做本地验证，绝不常驻安装。

- **Claude Code（推荐，会话级）**：`claude --plugin-dir <域仓本地路径>` 启动会话，
  当前检出（dev 时即 SNAPSHOT 版）被加载为插件，退出即卸、不污染安装态；可叠加
  多个 `--plugin-dir`。只验证不开会话时用
  `claude --plugin-dir <路径> plugin details <插件名>`（`--plugin-dir` 必须在
  `plugin` 子命令之前）。
- **WorkBuddy**：试装会替换实际专家，先批准目标、正式来源备份/恢复计划；临时验证后恢复，不得留作常驻 SNAPSHOT。本地 checkout 切到 dev 后运行
  `install_workbuddy_experts.py <插件名>`——脚本复制本地 checkout，装出的专家即
  SNAPSHOT 版，界面版本号可直接分辨。
- **Codex**：无会话级机制，**禁止**把 dev/SNAPSHOT 常驻安装——SNAPSHOT 会进入
  客户端版本比较路径，这正是发布门禁在市场侧拦截的场景。

### 5. 指导客户端更新

Claude Code：**先记录安装清单**，收尾要对账——`plugin update` 对未安装的插件会直接失败，卸载重装类操作也容易漏装：

```bash
claude plugin list | grep soia > /tmp/claude-soia-before.txt && cat /tmp/claude-soia-before.txt
```

```bash
claude plugin marketplace update soia
```

```bash
claude plugin update <域插件名>@soia
```

收尾对账；发现缺失先报告原因，只有恢复目标仍在已批准安装范围内时才补回：

```bash
claude plugin list | grep soia | diff /tmp/claude-soia-before.txt -
```

更新后需重启 Claude Code 生效。已开启 `autoUpdate` 的用户会在下次启动时自动完成这两步。

> `claude plugin details <名>` 对私有市场的插件要带市场后缀（`<名>@<市场>`），不带会报「not installed」，容易误判成插件丢失。核对安装状态用 `plugin list` 更可靠。

Codex：**先记录当前安装清单**——下面要删缓存，删错粒度会连带卸掉同市场的其他插件：

```bash
codex plugin list | grep '@soia' > /tmp/soia-installed-before.txt && cat /tmp/soia-installed-before.txt
```

历史版本曾复用旧市场暂存。仅当前安装内容确实过期、官方更新未奏效时诊断缓存；列明精确暂存目标并取得清理授权后再处理，不把删缓存当作更新前置。

必要的插件缓存清理同样须先列目标并获授权；只处理已选择插件，`soia` 是市场名不是插件名，不能删整个市场下的其它插件。

```bash
codex plugin marketplace add soia-team/soia-open-skills
```

```bash
codex plugin add <域插件名>@soia
```

**收尾比对安装清单**，确认没有连带损失；有缺失就逐个 `plugin add` 补回：

```bash
codex plugin list | grep '@soia' | diff /tmp/soia-installed-before.txt -
```

以下是历史版本现象，不能替代当前 CLI 帮助或作为强制删除依据：跳过暂存诊断曾出现「命令报成功、内容还是旧的」——2026-07-27 实际踩过：corp 市场的暂存停在没有 `assets/icon.svg` 的旧版本，`composerIcon` 指向不存在的文件，界面回退成通用图标，排查时误判为路径写错。

### 6. WorkBuddy 专家（客户在用 WorkBuddy 时才做）

WorkBuddy 是 Electron 桌面端，**没有 CLI**——不存在 `workbuddy plugin install`，
也没有能指向我们 GitHub 的市场通道。所以这一步由脚本代劳，不要去找对等命令：

```bash
python3 skills/soia-meta-skill-release/scripts/install_workbuddy_experts.py --dry-run
```

确认目标与替换影响后，仅执行选择的插件；省略参数会装全部，不作为默认：

```bash
python3 skills/soia-meta-skill-release/scripts/install_workbuddy_experts.py <目标插件>
```

脚本把域仓 checkout 复制进 `my-experts/plugins/<插件名>`，再调 WorkBuddy 官方
`register_expert.py` 注册。三条实测约束决定了只能这么做：

| 约束 | 实测结论 |
|---|---|
| 目录 | 自建专家只认硬编码的 `my-experts`，应用内出现 38 处；别处放了不显示 |
| 软链 | 不行。官方 `validate_expert.py` 对路径 `resolve()`，穿透后判定「不在专家目录下」 |
| 远端 | 市场条目 `source` 只能是路径字符串，没有 sha pin 层；`expert/install` 深链要 `sharecode`，走官方云 |

装完**必须让客户重启 WorkBuddy**，否则新专家不出现在【专家·技能·连接器 → 我的专家】。

验证：召唤该专家后问「你有多少个可用技能」，该域技能应全部在场；不召唤时不在场。

### 7. 回收旧版本缓存（另有清理授权才做）

两家客户端在 `plugin update` 后都只新增版本目录，**不回收旧的**；Claude 的 `.in_use` 标记也不可靠（实测同一插件新旧两个版本都带这个文件）。不清理会线性堆积，并干扰排查——用 `find` 找资源会匹配到多个版本目录，`ls` 统计技能数会得出离谱结果。

```bash
python3 skills/soia-meta-skill-release/scripts/prune_plugin_cache.py
```

预演确认无误后执行：

```bash
python3 skills/soia-meta-skill-release/scripts/prune_plugin_cache.py --apply
```

按语义化版本取最高值保留，其余删除；非语义化版本目录（如官方插件的 `latest`）一律跳过。可重新下载不免除删除确认；语义版本最高也不必然是本次批准版本，须先核对实际安装来源。

### 8. 验证

```bash
claude plugin list
```

```bash
codex plugin list
```

确认目标插件版本已变化、状态为 enabled，并核对正式来源与实际加载内容；一次真实输入验证技能效果，列表或 details 不替代加载成功。

### 域仓与插件对照

| 域仓 | 插件名 |
|---|---|
| soia-open-dev-skills | soia-dev |
| soia-open-pkm-vault-skills | soia-pkm-vault |
| soia-open-media-content-skills | soia-media-content |
| soia-open-cwork-office-skills | soia-cwork-office |
| soia-open-edu-course-skills | soia-edu-course |
| soia-open-env-skills | soia-env |
| soia-open-skills | soia-meta |
