---
name: soia-pkm-alipan-curator
description: 阿里云盘资源顾问，在 soia-pkm-alipan 原子操作上提供 inventory/organize/catalog/plan 四类工作流：盘点云盘、整理资源、生成 Obsidian 馆藏、分区缓存式增量 Excel 总索引与家庭课程导航、基于本次用户提供的学情生成学习计划。Triggers：「整理云盘」「云盘盘点」「更新云盘索引」「更新Excel总索引」「生成家庭导航Excel」「给云盘建图书馆」「用网盘资源做学习计划」
dependencies:
  hard: [soia-pkm-alipan]
---

# soia-pkm-alipan-curator — 云盘资源顾问

## 客户可读说明

### 这个技能可以做什么

阿里云盘资源顾问，在 soia-pkm-alipan 原子操作上提供 inventory/organize/catalog/plan 四类工作流：盘点云盘、整理资源、生成 Obsidian 馆藏、增量 Excel 总索引与家庭课程导航、基于本次用户提供的学情生成学习计划

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-pkm-alipan-curator -y
```

配置约定：

```text
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-alipan-curator/config.yml
SOIA_PKM_ALIPAN_CURATOR_CONFIG_FILE=<custom-config-path>
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

## 定位与依赖

本 skill 的分层设计可类比 `huashu-weread-advisor` / `weread-skills` 的“顾问层 / 原子层”关系，但**不依赖也不调用**这两个第三方 skill。实际底层命令全部走 [[soia-pkm-alipan]]，本 skill 只管**方法论和产出**。
学习计划的排期方法论继承 soia-pkm-reading-plan：**书按字数排期 → 视频按 集数×单集时长 排期**，不拍脑袋。

依赖关系必须按下面口径说明：

| 依赖/参考 | 对 `soia-pkm-alipan-curator` 的关系 |
|---|---|
| `soia-pkm-alipan` | **强依赖**：所有云盘读写、登录、扫描、移动、重命名都走这个原子层 |
| `soia-pkm-reading-plan` | 方法复用：学习计划排期方法沿用其“按真实体量排期”原则；不要求运行它 |
| `huashu-weread-advisor` | 非依赖：只作为“顾问层/原子层”分工类比，不读取或调用该第三方 skill |
| `weread-skills` | 非依赖：本 skill 处理阿里云盘资源，不调用微信读书 API |
| `book-to-skill` / `find-skills` | 非依赖 |

## 数据源（三件套，plan 前必读）

1. **资源地图**：用户通过 `--out <vault>/<catalog-relative-path>` 指定的馆藏总览（由 `gen_catalog.py` 产出）——只推**云盘里已有**的资源，别让用户去找新资源
2. **学习者信息**：只使用用户本次明确提供的成绩单/截图/学情描述；不要读取或引用私有记忆、长期个人档案或任何可识别个人的信息
3. **计划格式**：参照 `references/plan-template.md`（仿用户阅读计划格式：frontmatter + 映射总表 + 排期 + 待确认转正）

## 子命令路由

### inventory — 盘点
递归扫描到资源根或叶级终态；只有用户显式给出深度、敏感目录或聚合阈值时才提前停止。把核对清单写到用户显式指定的 `<vault>/<inventory-relative-path>`：每支记「内容 · 类型 · 建议动作」，用户拍板后交 organize。没有输出参数时先询问，不猜 vault 目录。

### organize — 整理
执行规范（每步终态验证，安全守则见 soia-pkm-alipan）：

**硬约定（先记录后动手）**：AI 生成并将执行的移动/删除清单——即本 skill `scripts/gen_catalog.py` 的 `--moves` / `--deletes` / `--roots` 输入文件——标准落盘位置为 `${XDG_STATE_HOME:-$HOME/.local/state}/soia-pkm-alipan-curator/moves/<date>-<batch>.jsonl`。执行云盘 `mv`/`rmdir` 前必须先把该清单落盘到此路径，不允许先动手再补记录；事后可凭这份清单追溯操作。

**大型整理固定执行链**：统一按 `merge map → assign numbers (optional) → build reclass → build structure → preflight → audit → dry-run → execute → fresh terminal scan` 顺序推进；任何一步失败都停在该步，不得跳过门禁直接写云盘。多 agent 只可并行做只读盘点、内容审核、计划生成和独立验证；`mkdir` / `mv` / `rename` / 回收站删除 / 上传等云盘写入始终由一个写入者执行，批量入口显式使用 `--max-parallel 1`。计划和结构合同合并后，写入者还必须按 file_id 做迁移后终态扫描，确认空壳确实存在且子项为 0，再按已批准清单送回收站。

阶段入口按本 skill 的脚本职责对应：`merge_classification_map.py` → `assign_resource_numbers.py`（仅编号已确认时）→ `build_reclass_plan.py` → `build_structure_plan.py` → `preflight_reclass.py` → 非 `--final` 的 `audit_run_bundle.py` → `apply_reclass.py`/`apply_reclass_bulk.py` 的 dry-run → 同一写入者加 `--execute`。`audit_structure.py --final` 和 `audit_run_bundle.py --final` 属于 fresh terminal scan 后的收官审计，不得用前置 audit 代替。

**大型整理正式脚本表**：以下是可复用的正式入口；不要在运行包、临时目录或会话里另写同职能 builder。

| 阶段 | 正式脚本 | 职责与边界 |
|---|---|---|
| 合并分类结论 | `scripts/merge_classification_map.py` | 将审核过的分类、分类目标、可选覆写与 inventory 合并成待审 TSV map；按资源 ID 对齐并拒绝缺失或未知覆写。 |
| 编号（可选） | `scripts/assign_resource_numbers.py` | 仅在编号规则已获确认时，为 map 中的资源目录分配稳定前缀；保留既有编号并更新 map，不改云盘。 |
| 生成重分类计划 | `scripts/build_reclass_plan.py` | 从审核过的 TSV map 生成确定性的 JSONL `mkdir`/`move`/`rename` 计划；只写本地计划，不调用云盘。 |
| 生成结构计划 | `scripts/build_structure_plan.py` | 从结构合同和已登记批次生成有序的 `mkdir` JSONL 计划；结构批次须登记到运行包后再进入后续阶段。 |
| 执行前预检 | `scripts/preflight_reclass.py` | 对已登记的计划做新鲜只读云端核对，检查来源、目标、ID 和父级顺序，并输出预检报告及 `run.json`、各已登记计划的 SHA-256。 |

运行 `preflight_reclass.py` 前，先在 `run.json.files.preflight_report` 登记一个尚不存在的、相对运行包的报告路径；脚本拒绝覆盖既有报告，也拒绝把 `--report` 写到未登记或运行包外的位置。非 final 的 `audit_run_bundle.py` 会调用 `scripts/preflight_gate.py` 对账；执行器的 `--execute` 分支必须显式传 `--run-dir`，并在首个云盘写入前即时调用 `verify_preflight_gate(Path(args.run_dir), plan_path=Path(args.plan))`，确认报告已登记且 `passed`、报告属于该运行包、当前执行计划已登记，并且 `run.json` 与所有登记计划的 SHA-256 未变化。纯 dry-run 可不传 `--run-dir`，但如提供则同样执行门禁。计划或 manifest 有任何变动，保留旧证据，登记新报告路径并重新预检；不得仅靠此前 audit 的结果执行。

预检支持断点运行包：逐批读取 `result` ledger 中同一 operation key（`action_id/op/from/to/file_id`）的最新记录，只把最新状态为 `verified` / `completed` 且当前云端能以同一 `file_id` 证明计划终态的连续链前缀计为 `already_verified`。`mv → rename` 等链先验证最终落点，再按全局计划逆序回卷后重放；账本单方面声称成功、错误 ID、未登记 operation key 或中间断链都必须产生 violation。若已 verified 的空 `mkdir` 后续经用户批准送入回收站，只能通过 `run.files.empty_cleanup_evidence` 登记的 JSONL 证据转为 `superseded`；证据必须与缺失目标精确匹配、`files=0`、状态以 `removed_to_recycle_bin` 开头且子目录先于父目录。报告 `checked` 分开输出 `ready_actions`、`already_verified_actions` 与 `superseded_actions`；gate 的 SHA-256 绑定覆盖当前 `run.json`、全部登记计划和已登记 cleanup evidence。

- **去营销尾巴**：目录名里的「公众号：XXX」「【xx.xGB】」「持续更新」等广告字样批量 rename 掉
- **去套娃**：目录内只有一个子目录时，先判定是否为 HTML/播放列表/字幕/脚本/配置引用的技术包或源码依赖；技术包、源码及其依赖目录必须整体保留，不拆文件、不编号、不因“只剩一个子目录”删壳。只有普通业务容器才可内容上提一层、再删空壳
- **删广告**：「↑↑订阅↑↑」目录、`800T资源.txt`、`福利码.txt` 等先进入候选删除清单；获得用户对规则与范围的明确授权后再删
- **按查找目的选主轴**：先从主题、用途、受众、阶段、状态、媒介等维度中选择本层主轴；不混用维度，不照抄历史目录，也不按可识别个人身份命名
- **命名统一**：同级目录使用同一命名策略；用户选择编号排序时，再统一编号格式与步长
- **先写分区边界句**：相邻分区必须能用一句互斥规则判断去向。例如用户同时维护“课程区”和“书库”时，独立书籍/独立书集归书库，视频、讲义和素材共同构成的课程包整包留在课程区；不能一部分书按主题留在课程区、另一部分书按媒介进入书库
- **不确定项可隔离复核**：只有用户显式指定待确认/存档目标后，才把 `unclear` 项移入该目标；按来源或不确定原因分组并保留源路径记录。独立文件逐文件处理，课程/技术包整包处理，不为归档而拆散依赖树；公共 skill 不写死目录名或编号

**全区深度重组（盘点→方案→裁定→分批→索引→消费端联动 六步全流程）→ 必读 [references/deep-reorg-playbook.md](references/deep-reorg-playbook.md)**（多分区实战提炼：SHA1 删除证据、同名不同哈希隔离不删、消费端 file_id 红线、多 AI 协作边界、完成定义）。

覆盖完整一级分区、多个二级分区或用户一次指出多个漏整理目录时，还必须读 **[references/run-bundle.md](references/run-bundle.md)**。先在 `${XDG_STATE_HOME:-$HOME/.local/state}/soia-pkm-alipan-curator/runs/<run-id>/` 建立与 AI workspace 无关的运行包，再动云盘。用户点名链接、`未分类/合集/视频/其他` 等弱语义大桶和 inventory 发现的高风险根全部写入 `focus_targets`；每个焦点都要有 `content-audit.jsonl` 真读/抽样证据。收官时先跑 `audit_structure.py --final`，再跑 `audit_run_bundle.py --final`；机械合同与 AI 二次复核都通过才可称“特大模块完成”。

遇到 `LIST_FAIL`、空目录、覆盖上传、旧 file_id、重复目录、技术依赖树、局部索引拼接或多 agent 并发时，先读 **[references/operations-troubleshooting.md](references/operations-troubleshooting.md)**。核心红线：`LIST_FAIL` 不等于空目录；每条命令显式 `--driveId`；删除/覆盖必须有授权；同一索引文件只能有一个写入者。

深度分类（大规模重构时用）：先读 **[references/classification-methods.md](references/classification-methods.md)** 选择分类主轴并按领域示例校正，再读 `references/library-method.md` 设计图书馆产出。
- **真实内容审计**：全量列资源根；文档读目录与代表章节，音视频读清单、字幕/讲义与元数据，必要时下载最小样本；逐项记录证据、置信度与建议去向
- **一层一轴**：主题、用途、受众、阶段、状态、媒介只能选择一个作为本层主轴；其余维度放到下层或索引字段
- **编号可配置且必须闭环**：只有用户选择编号排序时才给业务分类层加 `NN_`；业务层不按目录深度判断，课程内供用户选择的“正课/练习/答疑/其他”同样属于导航层，章节文件和技术依赖树则不编号。步长、格式、待确认区含义和适用层级由本次方案声明，不设公共固定值。执行后必须逐个扫描已声明层级，漏号数为 0，不能靠索引折叠掩盖实体目录漏号
- **长系列分组可配置且必须闭环**：课程、播客、视频或卷册超过用户确认的单夹上限时，按原序号或内容阶段建立分组；阈值、分组命名和适用系列写进本次 `chunk_layers` 合同，公共 skill 不写死“20 集”或具体目录。组数超过 9 时，编号前缀必须统一扩宽（如 `010/020/.../100`），避免名称排序把 `100` 放到 `10` 前；同一父目录内不得混用两位和三位前缀。主媒体附带字幕、封面、XML 等侧车时，用 `count_pattern` 只计算主媒体，但所有侧车仍要跟随主媒体进入同组。拆分后根目录不留散文件、每组主媒体不超上限；同级技术目录必须在 `exclude` 中显式声明，其他未匹配目录视为漏整理；源资料缺号只记录不补造。终态还要用 `flat_series_discovery` 对本次范围做第二遍扫描，发现未写进 `chunk_layers` 的超限平铺目录；自然月份等稳定语义桶只能通过本次合同的 `exclude_path_patterns` 显式豁免
- **学习导航必须闭环**：用户选择“先看这里”模式时，方案必须声明导览名称和覆盖层级；每个在架学习分类都要有导览目录及已验证的导航文件。分区根本身需要入口时，单独写入 `required_guides`，不能只审计根下子分类而漏过根级导览；两种导览规则都必须提供非空 `file_pattern`，文件默认至少 1 字节，也可用 `min_bytes` 提高门槛，不接受任意杂项文件、空壳或零字节占位。先上传导览，再做终态扫描和索引；缺任意一个都不算完成
- **云端产物与资源地图必须可复核**：关键 Excel/说明上传后写入 `required_artifacts`，用终态扫描按完整路径、字节数、SHA1 和可选 file_id 精确对账；不能把上传回显当作成功。OB 资源地图写入 `resource_maps`，逐个声明必须出现的最终 file_id 和显式 `url_prefix`；只有真实 Markdown 云盘链接才算通过，正文声称“可直达”或粘贴裸 URL 都不算完成
- **杂包必拆**：含糊命名的合集目录逐项盘点→可独立使用的高价值资源提升到合适业务类→剩余按同一主轴分类→删壳前对账总数吻合
- **SHA1 级查重**：同名/疑似重复资源先做文件级哈希比对再决定删哪份，不凭文件名/大小相似猜
- **广告清理特征清单**：几千T资源/扫码进群/十万度V信/XH1080 尾巴/超低价网盘会员/可疑 exe——文字类见即删，可疑 exe 先列清单等确认

### catalog — 索引落 OB
**调用本 skill 的 `scripts/gen_catalog.py`** 从全盘扫描数据生成 `00_馆藏总览`（浏览）+ `_全文检索/`（检索），不手写、不把脚本写进 vault。整理/移动后**必须**重跑刷新（尤其跨盘导致 file_id 全换时），否则索引腐烂。

只重扫一个根分区时，加 `--merge-existing <现有00_馆藏总览.md>`：生成器会只替换该分区正文与统计行，并按差额更新全盘目录/文件总数；其他分区保持不变。增量扫描必须配 `--roots` 补入本次根分区的 `file_id`，并继续用 `--search-dir` 刷新同名分区全文检索文件。

### Excel 产出选择

| 用户要的产物 | 正式入口 | 说明 |
|---|---|---|
| 全盘/多分区馆藏总索引 | `scripts/gen_catalog_xlsx.py` | 轻量总入口 + 每分区明细；按 Markdown SHA-256 增量刷新 |
| 单个学习分区的家长说明与课程导航 | `scripts/gen_family_nav_xlsx.mjs` | `01_先看这里` + `02_资源导航`；课程名称可点击直达 |
| 已批准重分类方案的可恢复执行 | `scripts/apply_reclass.py` | 读取带 `action_id` 的 JSONL 计划；`mv`/`rename` 必须携带 `file_id`，写前、终态与 resume 都按 `name → file_id` 回读核验；限定 `--root` 与可选 `--archive-root`、默认 dry-run、失败即停并写 verified 账本 |
| 大批同源同目标移动的可恢复执行 | `scripts/apply_reclass_bulk.py` | 沿用相同计划/边界/身份/账本合同；最多 20 项合并一次 `mv`，批前批后各读源与目标并逐 action 以 `file_id` 记终态；云盘写入始终单写者，`--max-parallel` 只能是 `1`；默认 dry-run |
| 超长系列的可审核分组计划 | `scripts/plan_series_chunks.py` | 从逐文件扫描和本次规则 JSON 生成稳定的 `mkdir`/`mv` 计划与异常报告；自然排序、同课主媒体和侧车跟组，未匹配文件默认阻断；只生成计划，不写云盘 |
| 编号、导览、云端关键产物、资源地图直达链接、长系列分组与待确认项闭环审计 | `scripts/audit_structure.py` | 从终态 scan JSONL 和本次合同检查实体结构、精确 SHA1/字节及消费端直达链接；失败时返回非零退出码 |
| 特大模块运行包、焦点目录逐项覆盖、批次账本与 AI 复核闭环 | `scripts/audit_run_bundle.py` | 检查运行包路径安全、初末扫描、用户点名目标内容证据、动作计划/结果、结构审计和 AI 复核；失败时返回非零退出码 |

`preflight_reclass.py` 和两条重分类执行器的每个 `aliyunpan` 调用都经同仓 `soia-pkm-alipan/scripts/run_with_env.py` 启动，以加载该原子 skill 的私有登录态。默认从当前脚本所在的 `skills/` 相对定位；只在调用方显式设置 `SOIA_ALIPAN_RUNNER` 时覆盖 runner。runner 缺失或无法启动会明确失败，绝不回退为裸 `aliyunpan` 或输出私有配置细节。

不要在 vault、临时目录或会话产物目录另写一次性 builder。全盘索引的参数、依赖、数据口径、云端覆盖与验收见 [references/catalog-excel.md](references/catalog-excel.md)；家庭导航的 JSON 字段、运行命令、上传顺序与验收见 [references/family-navigation-excel.md](references/family-navigation-excel.md)。核心约定：

- 全盘输出为轻量 `00_阿里云盘馆藏总索引.xlsx` + 相邻的每分区明细工作簿；分区数由 `_全文检索/*.md` 动态决定。
- 默认按每份 `_全文检索/*.md` 的 SHA-256 增量刷新；哪个分区变化只重建哪个，未变化分区不改写。总览或任一分区变化时只额外重建轻量总入口。
- 首次生成或生成规则整体升级才使用 `--force`；日常刷新禁止无理由全量重建。
- 解析缓存只进 `${XDG_CACHE_HOME:-$HOME/.cache}/soia-pkm-alipan-curator/catalog-xlsx/`，不进 vault/仓库。
- Excel 作者层必须使用宿主提供的 `@oai/artifact-tool`；缺失时停止并说明，不临时换库。交付验收时加 `--verify`，有 `soffice` 时传入以预计算链接显示值。
- 分区需要面向家长的简明说明、筛选表和课程直达链接时，家庭导航输入必须来自终态扫描；传 `--soffice` 预计算 `HYPERLINK` 显示值，避免在线预览只显示公式。
- 家庭导航先上传并复核，再做终态扫描与总索引；否则索引会少算刚上传的文件。
- 深度整理完成前运行 `audit_structure.py --scan <scan.jsonl> --contract <contract.json> [--scan-errors <scan.errors>] [--unclear <unclear.jsonl>] --final`。必须先确认终态扫描进程已退出且退出码为 0，不能审计仍在增长的 JSONL。`contract.json` 只声明本次用户选择的编号层、根级/分类导览、关键云端产物、资源地图链接、已知长系列分组、未声明长系列发现范围和可选待确认根；所有阈值、路径、file_id、URL 前缀、哈希与语义桶例外由调用方从本次终态证据传入，脚本不内置任何个人目录、真实云盘 ID 或固定集数。发现范围必须使用逐文件、无聚合、无 `no-descend` 的终态扫描；聚合行、非空或缺失的错误 sidecar、关键产物不匹配、资源地图缺少真实链接都会使审计失败，分类导览或发现规则零匹配也默认失败。只有已通过其他证据确认确实为空时才设置规则级 `allow_empty=true`；只有独立验证扫描完整性后才可使用 CLI 的 `--allow-missing-scan-errors`。
- 同参数第二次运行全盘生成器必须返回 `status=unchanged`、`rebuilt=[]`；若已上传，远端 SHA1/bytes 必须与本地一致。

**图书馆建法（浏览/检索/策展 + 分类方案）**（精选资源沉淀为可查询馆藏时用，模板与字段详见 `references/library-method.md`）：
1. **馆藏总览**：全盘索引 MOC。用 `scripts/gen_catalog.py --scan-dir <scan-dir> --out <catalog-output> --url-prefix <drive-url-prefix> [--moves f --deletes f --roots f --heading-pattern REGEX --section-icons JSON --max-heading-depth N]` 生成。`--url-prefix` 必须显式提供或由 `SOIA_ALIPAN_URL_PREFIX` 注入；可选 `--catalog-link/--cards-link/--classification-link` 由用户传入 vault-relative wikilink 目标。默认保守展示全部目录；需要折叠内部素材树时，用 `--heading-pattern` 声明业务目录规则，例如编号体系传 `^\d{2}[_.]`。公共默认只用中性文件夹图标，分区图标通过 `--section-icons` 可选注入。总览不铺单个文件；需要单文件检索时加 `--search-dir <search-output-dir> --junk <ignored-prefixes>`。
2. **馆藏卡**：一卡对应云盘一个资源目录；最低字段为 `type/tags(馆藏)/drive_link`，其余字段和卡片分组路径由本次主分类轴与常用查询推导，不强制 `topic/medium/subject/stage/status`；实际体量字段若启用必须实测
3. **Bases 数据库**（`.base`）：`filter: file.hasTag("馆藏")`；视图从用户确认的主分类轴和常用查找问题推导，例如全部馆藏/按主题/按受众/按媒介/卡片墙，不写死固定视图
4. **分区深度分类方案文档**：每分区一份，含现状/N类结构/归类规则（供未来新增资源判断落位）/变更史/待办

### plan — 学习计划（高频主场景）
输入：成绩截图/学情描述（如「这是某个学习者的期末情况，出个假期方案」）。流程：
1. **诊断**：从成绩单提取 分数/排名/失分点/目标（截图里有就直接用，没有就问 1-2 个关键问题）
2. **资源映射**：弱项 → 云盘索引里的对应资源，标注「为什么这个资源治这个失分点」
3. **排期**：视频资源查实**集数与单集时长**，按用户给出的可用时间、目标优先级和负担上限倒排周计划；若这些约束缺失，先询问，不在公共 skill 中预设主线条数或年龄负担标准
4. **落盘**：写到 OB 的学习计划目录，文件名用 `YYYY-MM-DD-<学习者代号>-<主题>.md` 这类匿名代号，状态「待确认」，用户拍板后转正

## 组织流程（大规模重构的四步闭环，详见 references/library-method.md）

1. **方案先行**：分类方案文档先写完整（现状/N类结构/归类规则/待裁定区），frontmatter `status: 待拍板`，不擅自开始移动
2. **用户裁定**：疑难项（受众模糊/去向二选一/查重后留哪份）列清单给用户，逐项拍板
3. **分批执行**：按"风险从低到高、跨库/跨盘操作放后面"分批，每批做完立即复核（重新 ls 对照终态），操作记一份移动日志（jsonl：原路径/新路径/操作类型/时间戳）
4. **结构闭环 + 地图/总览刷新 + 文档回填**：终态扫描后先跑编号/导览/关键云端产物/长系列分组/待确认项审计，违规数为 0；再重建受影响地图（尤其跨盘导致 file_id 全换时），把最终 file_id 写入 `resource_maps` 合同并验证真实 Markdown 直达链接。收官必须依次更新 OB 资源地图、Excel、云盘索引和 `01_先看这里`，并回填方案文档变更史；任何一个消费端未更新都不算完成

特大模块在上述四步外增加运行包门禁：`run.json` 中的所有 `focus_targets` 必须同时出现在初始扫描、内容审计和终态扫描；所有批次 action 均有 verified/带原因 skipped 结果；`structure-audit.json` 与 `ai-review.json` 均通过；最后执行 `scripts/audit_run_bundle.py --run-dir <run-dir> --final`。运行时证据留在 XDG state，OB 只保存资源地图、冻结审计与短回执。

## 执行编排经验

- **决策与执行分层**：主控只做审核决策（批方案/拍板疑难项/复核终态），执行代理只在已批准范围内运行 `ls`/`mv`/`rename`，不自行改变分类规则
- **并行范围固定**：多 agent 仅可并行盘点、内容审核、计划和验证；merge map、云盘写入、索引/OB/Excel/导航产物写入均由主控或指定单写者串行完成。云盘写入不因分区互不相交而开第二路，`max_parallel` 永远为 1
- **并行须给进度看板**：多代理并发跑不同分区时，给主控方一份一眼看完的进度看板，不要让用户去追多个会话各自输出
- **写操作双层验证**：任何 `mv`/`rm`/`rename` 完成后立即用独立通道（换一次 ls / 用 Read 而非 Bash）核对结果，不要只信命令返回的成功提示——曾出现过"回显污染"（显示成功但实际未执行），靠双层验证纠正

## 检查点（必须过用户确认）

- inventory 后：核对清单先给用户过目，**不擅自动结构**
- organize 深度分类前：主分类轴、全量内容审计表和模糊项先给用户看；用户裁定后才生成移动清单
- plan 落盘前：资源映射表先展示，用户说「换掉 X」就重排
- 涉及删除：永远列清单等确认

## 场景 few-shot

- 「给你个截图，这是某个学习者的期末，给我出假期学习方案」→ plan（诊断→映射→排期→落 OB）
- 「某学习者要做幼小衔接，语言还没启蒙」→ plan（按现有启蒙资源排学习序列）
- 「云盘又乱了，整理下」→ inventory → 用户确认 → organize → catalog
- 「这个目录既有书也有视频，原分类不合适」→ organize（真读抽样→选择主题/用途等主轴→评估是否改分区边界→全量审计表→用户裁定）
- 「编程课程、源码和课件混在一起怎么分」→ organize（按能力领域识别课程根，课程内部媒介不拆；多方向合集逐套盘点）
- 「云盘里有什么数学资源」→ 直接查 00_馆藏总览回答，不用扫盘
- 「给云盘建个图书馆，方便找孩子的学习资源」→ catalog（图书馆建法（浏览/检索/策展 + 分类方案）：馆藏总览+馆藏卡+Bases+分类方案）
- 「把云盘 Markdown 做成可筛选 Excel / 更新 Excel 总索引」→ catalog（`gen_catalog_xlsx.py` 增量生成总入口 + 分区明细；普通刷新不加 `--force`）
- 「给这个课程区做一份家长能看懂、能点进课程的 Excel」→ catalog（`gen_family_nav_xlsx.mjs`；先按 `family-navigation-excel.md` 准备终态 JSON）
- 「这堆资源哪些是学习者用、哪些是照护者或教师用」→ organize（本次确有多受众混装时，选择受众为主轴：审计表逐项标注→模糊项待裁定→裁定后迁移）
