---
name: soia-cwork-processon-diagrams
description: 通过宿主无关的专用浏览器 profile 和可恢复队列，递归盘点 ProcessOn 个人/团队空间到叶子文件；按授权对流程图默认导出 Visio VSDX、对思维导图默认导出 XMind，将未知类型列入待确认清单，并完成下载校验与归档；适用于“读取 ProcessOn 文件”“导出架构图”“盘点全部子目录”“批量下载但不要影响我的 Chrome”“从 POS/VSDX/XMind 提取结构”等请求。
version: 1.8.1
created_at: 2026-07-20 18:57:53
updated_at: 2026-07-22 14:07:21
created_by: gpt-5.6-sol
updated_by: gpt-5.6-sol
dependencies:
  optional: [soia-dev-drawio-visio-diagrams]
---

# ProcessOn 图表浏览与导出

通过技能自有的 ProcessOn 浏览器 profile 读取团队空间、文件夹、图表标题与可见内容；在用户指定范围内导出图表，把下载安全归档到交付目录，并对本地 POS、图片、SVG、PDF、XMind 文件生成可核验清单。默认只读，不修改、分享、移动或删除远端文件；正式批量任务不得接管客户正在使用的 Chrome。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 盘点团队空间 | 从指定节点递归到每个子目录和叶子文件，按小批次保存并审计恢复状态 | Markdown/JSON 树、进度快照、遗漏差集、权限缺口与完成回执 |
| 看图里有什么 | 进入“浏览”视图读取可访问文字，并用截图核对视觉布局 | 内容摘要、关键文字与截图 |
| 导出图表 | 按客户授权选择 VSDX、POS、PNG、SVG、PDF、XMind 或 Office 格式 | 下载文件、格式/大小/SHA-256 验收 |
| 归档浏览器下载 | 解析 CLI、环境变量和私有 YAML 中的路径，把下载文件校验后复制/移动到交付目录 | 最终路径、碰撞策略、SHA-256 和审计 manifest |
| 批量续跑归档 | 从归档计划初始化下载队列，逐项领取、记录成功/失败/阻断并重放审计 | `download-progress.json`、下一批列表和机械验收结果 |
| 不干扰地控制浏览器 | 从任意 AI/终端调用本地 Playwright runner，在技能专用 profile 中 headless 执行 | 独立登录态、页面关闭计数、下载回执；客户主 Chrome 不被接管 |
| 解析已有导出 | 读取本地 POS/XMind/SVG/图片；VSDX 可交给可选 draw.io/Visio 技能 | 标题、图表类型、节点文字、尺寸与校验值 |

### 客户如何使用

客户提供以下信息中的最少必要部分：

1. ProcessOn 团队、文件夹或图表 URL；也可以给出空间名和文件名。
2. 目标动作：初始化盘点、增量盘点、下载归档，或解析/转换已有导出文件。
3. 导出时指定文件范围、格式和交付目录；未指定格式时，流程图默认选择当前菜单可用的 Visio `.vsdx`，思维导图默认选择 `.xmind`。两类都建议同时保留 POS 作为 ProcessOn 原生结构备份。无法从图标、浏览视图或菜单确认类型时，只写入“待人工确认”清单，不猜测格式、不自动下载。视觉复用优先 SVG/高清 PNG，审阅交付优先 PDF。
4. 第一次使用时，客户只在 runner 弹出的**独立 ProcessOn 窗口**手动输入用户名、密码、短信码或验证码；成功后窗口自动关闭，后续批量默认 headless。技能不读取、记录或输出 Cookie、Local Storage、密码文件或凭据。
5. 可选复制 [路径配置模板](assets/config.example.yml) 到私有配置目录，固定临时下载、最终交付、审计清单和保留天数。

示例：

```text
初始化盘点这个 ProcessOn 团队空间，只读，不下载：<team-url>
对上次盘点和今天重新审计后的快照做增量盘点，不猜测删除项
按已审计计划下载已确认流程图为 VSDX、思维导图为 XMind，归档到 <output-dir>
解析 <export-dir> 里的 POS，或把 VSDX 转成 draw.io 真源后升级
```

### 依赖与安装

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| ProcessOn 账号与目标资源权限 | 强依赖 | 客户在 ProcessOn 官方页面登录，并确保自己可见目标空间 | 停止远端读取，列出缺失权限 |
| Playwright + Chrome/Chromium | 远端操作强依赖 | `pip install playwright && python -m playwright install chromium` | 改为客户手动导出后解析本地文件 |
| Agent 自带 browser/computer-use | 可选诊断能力 | 只允许客户明确同意的一次性排障；禁止作为正式批量主路线 | 直接使用宿主无关 runner，不影响功能 |
| Python 3.10+ | 本地解析与归档依赖 | 系统 Python 即可 | 只完成浏览器侧盘点/导出 |
| PyYAML | 私有配置可选依赖 | 使用 `config.yml` 时安装：`python3 -m pip install pyyaml` | 改用 CLI 参数、环境变量或安全默认值 |
| `soia-dev-drawio-visio-diagrams` | VSDX 理解/升级可选依赖 | 从同一 SOIA skills 仓安装 | 仍可下载和归档 VSDX，但不做 draw.io 转换与元素级升级 |
| ProcessOn API 服务 | 可选商业能力 | 企业按官方流程申请 JS-SDK/格式转换凭证 | 不影响普通账号的浏览器工作流 |

私有配置默认位置：

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-processon-diagrams/config.yml
SOIA_CWORK_PROCESSON_DIAGRAMS_CONFIG_FILE=<custom-config-path>
```

配置优先级为 CLI 参数 → 进程环境变量 → 私有 `config.yml` → 跨平台安全默认值。配置键、默认路径和命令见 [下载归档工作流](references/download-workflow.md)。私有配置只保存路径和保留策略，不保存用户名、密码、Cookie、Token 或浏览器 profile。

正式远端操作先执行宿主无关 runner；任何 Claude Code、Codex、Gemini CLI、OpenCode 或普通终端都可调用：

```bash
python3 scripts/processon_browser_runner.py login --url '<team-url>'
python3 scripts/processon_browser_runner.py status --url '<team-url>'
python3 scripts/processon_browser_runner.py snapshot --url '<folder-url>'
python3 scripts/processon_browser_runner.py run \
  --actions <actions.json> --download-dir <managed-temp-dir>
```

runner 的 action 文件只允许导航、有名称的语义点击/悬停、滚动、等待、受控 popup 和下载；不接受任意 CSS/无名称控件，并机械拒绝删除、编辑、移动、分享、发布等远端变更入口；不提供填表、执行脚本、读取 Cookie/Storage 或注入凭据。动作格式和标签生命周期见 [下载归档工作流](references/download-workflow.md)。

### 日志与完成回执

每次运行至少报告：

- 读取的空间/文件夹范围，以及发现的文件夹数、图表数和受限项数。
- 预览时实际看到的是 DOM 文字、缩略图、浏览视图还是导出的 POS；不要把缩略图 OCR 当作结构化原文。
- 导出时逐类报告请求格式、实际格式、成功/失败数、文件大小与校验结果。
- 归档时报告浏览器实际下载路径、最终交付路径、复制/移动模式、同名处理、manifest 路径和 SHA-256。
- 清理时先报告 dry-run 候选数；实际清理只处理带技能标记的临时目录，并生成删除审计 manifest。
- 安全验证、会员格式限制、权限不足或页面结构变化必须单列，不得伪装成成功。
- 每批报告浏览器模式、专用 profile、`pages_seen_at_start`、`stale_pages_closed`、`scoped_pages_opened/closed` 和 `pages_closed_at_exit`；关闭数异常时本批不得宣称完成。
- `status`、`snapshot` 和 `run` 在初始导航后必须等待有上限的 SPA settle（默认 2000ms）；空快照只能报告“页面未渲染/待复核”，不得据此生成点击动作。
- 全量盘点必须报告“父目录声明的子目录集合 − 实际访问集合”；差集非空时只能写“部分完成”。
- 完成回执必须来自 `audit` 重放全部不可变批次后的机械结果；不能仅凭 checkpoint 统计或浏览器页面宣称完成。
- 目录盘点和源文件归档必须分阶段报告：`inventory_completed_asset_archive_pending` 不是“知识库归档完成”。
- 资产归档前必须从最终 checkpoint 生成归档计划；`ready_for_known_artifacts` 控制已确认类型的下载，`ready_for_archive` 只有在未知类型也清零后才为 `true`。
- 正式下载必须先初始化 `download-progress.json`，每份 artifact 完成或受阻后立即 `record`/`mark`；不得只在对话、浏览器下载列表或知识库 Markdown 中维护唯一进度。
- 增量盘点必须报告两份完整快照的 SHA-256、added、changed、removed candidates；它不是 ProcessOn 事件/API 增量。没有稳定 `remote_id/id` 时不得声称文件“移动”，只报告新增/移除候选。
- 最终回复给出交付目录、验证方式和未完成项；不输出账号、Cookie、Token 或浏览器内部状态。

## 运行边界

- 默认只读。浏览、搜索、截图和下载属于允许动作；编辑、重命名、复制、移动、删除、锁定、邀请协作、公开分享必须由客户在当前请求中明确授权。
- 正式批量只能使用技能专用 profile；禁止附着客户默认 Chrome profile，禁止用 Codex/Claude 的 browser、computer-use 或扩展在客户主 Chrome 中循环开关标签。专用 runner 默认 headless；只有首次登录、真实可见验证码或客户明确要求观察时才使用 headed。
- 专用 context 启动时只保留一个父页面；临时 popup 最多一个并必须在嵌套动作 `finally` 中关闭；成功、失败、超时、Ctrl-C 与 SIGTERM 都必须关闭全部专用页面和 context。软中断后先核对关闭回执再续跑。
- 下载前确认目标文件、格式和交付位置。客户已经在当前请求中明确要求导出时，无需重复确认相同范围。
- 只处理客户有权访问的文件。不要通过猜测 URL、内部接口、Cookie 或未公开端点扩大可见范围。
- 优先使用 ProcessOn 官方 UI 和官方文档。普通账号没有公开的团队文件 REST API 时，不得把逆向接口包装成稳定 API。
- 只有验证码/滑块控件真实出现在当前视口并遮挡或阻断目标操作时才停止自动交互，保留页面供客户接管；DOM 中存在 `display:none`、零尺寸或移到视口外的预加载 iframe 不是“验证码已弹出”。不得模拟拖动、调用验证码接口或绕过验证。
- 不要求客户把密码发到对话中；不把用户名、密码、Cookie、Token、登录态或浏览器 profile 写入配置、命令参数、日志或 manifest。
- 下载归档默认复制并在同名时自动改名。`--move` 只允许处理带技能标记的临时目录；覆盖必须同时使用 `--collision overwrite --allow-overwrite`，且客户在当前请求中明确授权。
- 临时清理必须显式执行 `cleanup`；无技能标记、交付目录位于临时目录内部或符号链接文件时一律拒绝。

## 私密信息与中间数据

- ProcessOn 图表、目录名、作者和导出文件均可能包含企业内部信息；盘点默认只在 stdout/客户指定报告中出现，不写入公共技能仓库。
- 用户名、密码、短信码、Cookie、Token、Local Storage 和浏览器 profile 交给浏览器/提供商自身保存，本技能不读取、不复制、不记录。
- 技能专用 profile 默认位于用户私有 config 根下；它是 ProcessOn/浏览器持有的本地登录态，不进入公共仓库、运行包或知识库。runner 拒绝默认 Chrome/Chromium profile 及非空无技能标记的目录。
- 临时下载使用操作系统临时目录下的技能受管子目录；交付物放客户指定目录，审计 manifest 放用户 state 目录。保留期和路径解析见 [下载归档工作流](references/download-workflow.md)。
- 浏览器长任务按系统/一级目录分批，默认在 `${XDG_STATE_HOME:-~/.local/state}/soia-cwork-processon-diagrams/runs/<run-id>/` 建立运行包；每批立即持久化原始批次和检查点。会话中断后从 `pending_paths` 续跑，不依赖易失内存保存唯一盘点结果。
- 资产归档进度固定写入运行包的 `artifacts/download-progress.json`；状态脚本用独占锁保证单写入者，记录已完成、失败、阻断和待确认队列，并从同一计划指纹恢复。
- 运行包是中间控制面，不是知识库正文；知识库只接收冻结清单、最终 artifact manifest 和已校验交付文件。

## 本次执行固化的失败门禁

执行复杂团队空间前先读取 [失败模式参考](references/known-failure-modes.md)。以下规则是硬门禁：

1. “全量”必须递归到叶子目录；一级页面、旧浏览会话或模型记忆不能代替 checkpoint。
2. 多 Agent 只并行做页面只读分析；同一运行包的 `record`、`audit` 和状态文件只能由一个写入者串行执行。
3. 只有当前视口真实可见并阻断操作的验证码才暂停；隐藏/零尺寸/视口外 iframe 不算弹窗，不得绕过验证。
4. 用户手动登录，Agent 不接收密码、不读 Cookie/Token/profile，也不通过 CDP 或扩展注入凭据。
5. 图表类型无法被卡片、浏览视图或菜单证实时保留 `unknown`，进入人工确认队列。
6. 目录审计通过只代表 `inventory` 阶段完成；下载、格式校验、SHA-256、manifest、draw.io 转换和预览属于独立的 `artifact_archive` 阶段。
7. 宿主浏览器能力不是主执行器；批量任务必须从专用 runner 启动。每个 popup 和整个 context 都要有关闭回执，缺少回执视为中断待恢复。

## 工作流（严格按三个阶段）

### 1. `inventory`：初始化盘点或增量盘点

#### 1.1 访问与初始化盘点（`inventory.init`）

1. 先查找 ProcessOn 官方连接器、公开 API 或 CLI；没有满足当前任务的专用能力时，使用 `processon_browser_runner.py` 和技能专用 profile。首次登录只在 runner 的独立窗口由客户手动完成；不读取输入值、Cookie、Token 或 profile，也不需要 Chrome 扩展。宿主 browser/computer-use 只能在客户明确授权后做一次性诊断，不能承担批量主流程。
2. 用 runner `status`/`snapshot` 打开客户 URL（未提供时从“我的文件/团队空间”进入），确认目标空间可见。若登录或当前视口真实可见的安全验证阻断，用独立 headed 会话等待客户接管；隐藏 iframe 不算弹窗。读取 [ProcessOn 能力与格式](references/processon-capabilities.md) 后再操作。
3. `init` 必须先创建一个新的运行包；用 BFS/DFS 从指定根递归到叶子。每访问 3—6 个目录，将**完整目录快照**落为不可变批次再 `record`；不要把唯一清单只放在浏览器会话。格式、恢复和审计见 [递归盘点中间状态](references/inventory-checkpoint.md)。
4. 每层记录逻辑完整路径、子目录、图表标题、类型、作者、更新时间、可见缩略图/访问限制。文件夹单击进入；深层面包屑折叠时仍以逻辑路径为准。虚拟列表连续两次滚动无新增条目才停止。
5. 运行 `audit` 重放批次。只有 `discovered_paths - visited_paths - blocked_paths = 0` 且 `blocked=0` 才得到可用的完整快照和 `receipt.md`；否则只能报告部分盘点。

```bash
python3 scripts/processon_inventory_state.py init \
  --run-id '<run-id>' --root-path '<logical-root>' --source-url '<team-url>'
python3 scripts/processon_inventory_state.py audit --run-dir <run-dir>
```

#### 1.2 增量盘点（`inventory.incremental`）

1. ProcessOn 普通团队空间没有可依赖的公开文件事件 API；“增量”是**两次完整、已审计快照的本地差分**，不是只扫一级目录、更不是猜测远端变更。
2. 先重新执行一次 `inventory.init` 范围相同的完整盘点并通过 `audit`，然后比较前后 checkpoint：

```bash
python3 scripts/diff_processon_inventory.py \
  --previous <previous-run>/inventory/checkpoint.json \
  --current <current-run>/inventory/checkpoint.json \
  --output <current-run>/analysis/inventory-delta.json
```

3. 差分脚本拒绝 pending 或 blocked 的快照、跨根/跨 URL 比较、符号链接和重复的稳定 ID；输出 `added`、`changed`、`removed_candidates` 及两份 checkpoint SHA-256。只有具有稳定 `remote_id/id` 的条目才可报告 `moved`/`renamed`；无 ID 条目不会伪造移动关系。重复的无 ID 身份会隔离进 `ambiguous_entries`，不参与任何变更结论。`removed_candidates` 是待复核候选，不会自动删除本地归档。

### 2. `archive`：下载并归档已确认源文件

仅在阶段 1 产生**最新、完整且审计通过**的 checkpoint 后开始。先生成和验证可恢复的资产计划：

```bash
python3 scripts/build_processon_archive_plan.py build \
  --checkpoint <run-dir>/inventory/checkpoint.json \
  --output <run-dir>/artifacts/archive-plan.json
```

脚本为每个条目生成稳定 `artifact_id`、完整逻辑目录、类型证据、默认格式、回退格式、同名风险和状态；流程图默认 `vsdx`，思维导图默认 `xmind`，`unknown` 只进入 `pending_confirmation`。`ready_for_known_artifacts=true` 且 `archive_status=known_ready_pending_confirmation` 时可以下载已确认类型，但不得宣称全量资产归档完成；`ready_for_archive=true` 才代表全部条目均可进入归档。盘点继续变化或恢复后，先重新生成计划，禁止沿用旧计划。

下载过程中用以下命令检查计划仍对应当前 checkpoint：

```bash
python3 scripts/build_processon_archive_plan.py verify \
  --plan <run-dir>/artifacts/archive-plan.json \
  --checkpoint <run-dir>/inventory/checkpoint.json
```

校验失败时停止下载，先重新生成计划；不要把陈旧计划中的成功数合并到新一轮报告。然后按计划逐项执行：

先初始化或恢复正式下载队列，并按计划顺序领取下一小批：

```bash
python3 scripts/processon_archive_state.py init \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json
python3 scripts/processon_archive_state.py next \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json \
  --limit 10
```

`init` 在进度文件已存在时只接受相同计划 SHA-256，保留既有成功/失败/阻断证据并机械刷新计数；计划变更时 fail closed。`next` 默认跳过已完成、失败和阻断项，显式重试时才使用 `--include-failed` 或 `--include-blocked`。

1. 先用 runner `snapshot` 取得当前目录可见文字和语义控件，再生成小批次 action JSON；根据快照定位目标的“下载/导出”，不依赖固定坐标或私有 CSS。ProcessOn 文件列表可能虚拟化；目标条目未进入当前视口时先用 `scroll` 并重新快照，不能把定位超时写成文件不存在。按已确认类型选择：
   - 流程图默认选当前账号菜单中的 `VISIO文件`/`.vsdx`；多画布优先 `导出全部画布 (.vsdx)`；
   - 思维导图默认选 `Xmind文件`/`.xmind`；
   - 无法确认类型的文件加入“待人工确认”清单，不自动打开下载菜单。
   默认格式不可用、会员/权限阻断或下载失败时回退 POS，并明确记录“原请求格式、实际格式、降级原因”，不得静默替换。列表页点击无文件时进入官方编辑器重试 XMind/POS/POSM；若这些原生格式均无文件、但 Markdown 能下载，只能把 Markdown 作为诊断证据并将 artifact 标为 `blocked`，不能把 Markdown 冒充 XMind/POS 完成。格式选择见 [ProcessOn 能力与格式](references/processon-capabilities.md)。
2. 首次需要受管临时目录时运行 `paths --ensure`；由 runner `download` 动作捕获真实下载事件并保存到受管目录，不凭 Toast 判断成功。ProcessOn 导出是异步任务：一次只发起一个 artifact，必须等该文件真实落地、大小稳定并完成结构/语义校验后，才能切换选中项或发起下一份；固定 `sleep`、点击成功和短时下载事件超时都不能替代落盘信号。临时源页面必须在下载完成/失败后的 `finally` 中关闭。先 dry-run，再归档。受管临时目录可显式 `--move`；否则默认复制并保留浏览器原文件：

```bash
python3 scripts/finalize_processon_download.py paths --ensure
python3 scripts/finalize_processon_download.py finalize <browser-downloaded-file> --dry-run
python3 scripts/finalize_processon_download.py finalize <browser-downloaded-file>
```

3. 核对文件非空、扩展名与内容类型一致；VSDX 必须是有效 ZIP/OOXML 且包含 `visio/document.xml`，图像核对尺寸，POS/XMind 核对标题和可提取文字，所有文件记录 SHA-256。文件名只能作为候选证据：若异步队列产生 `(1)` 后缀、标题漂移或同名不同 SHA，调用 `soia-dev-drawio-visio-diagrams` 提取 VSDX 页面文字反证来源；无法唯一对应 artifact 时保持 pending，不移动、不改名、不调用 `record`。批量下载只能逐个执行；官网未明确支持时不声称存在批量 API。清理临时目录必须先 `cleanup --dry-run`，再由客户确认。

4. `finalize` 成功后立即把 artifact、实际交付文件和 finalizer manifest 绑定到进度；下载事件未被浏览器观察到但真实文件已校验时，使用 `not_observed_verified_file`，不能误写成浏览器事件成功：

```bash
python3 scripts/processon_archive_state.py record \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json \
  --artifact-id <artifact-id> \
  --download-source <browser-downloaded-file> \
  --destination <archived-file> \
  --manifest <finalizer-manifest.json> \
  --actual-format vsdx \
  --download-event not_observed_verified_file
```

会员限制、真实可见验证码、权限或格式失败用 `mark --outcome blocked|failed --reason <reason>` 落盘；不得混入未开始项。已有诊断文件时用可重复的 `--evidence-file` 归档到运行包，状态脚本会复制、哈希并在 `audit` 时重放，避免 `Downloads` 清理后证据消失：

```bash
python3 scripts/processon_archive_state.py mark \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json \
  --artifact-id <artifact-id> \
  --outcome blocked \
  --reason "XMind/POS/POSM 无文件落盘；Markdown 仅用于证明下载通道可用" \
  --evidence-file <diagnostic-export.md>
```

同目录同名条目没有稳定远端 ID 时，交付目录必须附加稳定 `artifact_id`（建议前 8 位），例如 `未命名文件--8ba9f60f/`；不能只依赖浏览器自动生成的 `(1)` 文件名。每批结束运行 `audit`，重新检查计划指纹、计数、交付文件、阻断证据、SHA-256 和 finalizer manifest：

```bash
python3 scripts/processon_archive_state.py audit \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json
```

### 3. `analyze`：询问后才解析、转换或升级

阶段 2 完成某个 artifact 后，先询问用户要“只归档、提取结构、转换、还是升级图”。未经指令不自动解析、改图或打开编辑器。

| 用户目标 / 文件 | 调用路线 | 输出与边界 |
|---|---|---|
| POS、XMind、SVG、图片、PDF 的内容盘点 | 本技能 `inspect_processon_export.py` | 只读标题、节点文字、尺寸、校验值；缩略图级证据不能冒充结构化原文 |
| VSDX 的读取、转 draw.io、可编辑升级 | `soia-dev-drawio-visio-diagrams` | 先前向验证 VSDX，再转 `.drawio` 真源；任何图形升级须有用户具体目标 |
| 仅需看图 | ProcessOn “浏览”视图或导出预览 | 记录 DOM 文字、视觉截图或缩略图证据，并区分明确文字与布局推断 |

浏览器不可用、账号未登录或真实可见安全验证未完成时，让客户手动导出 VSDX/POS/PNG/PDF/XMind，再从阶段 2 的本地归档入口继续。

## 本地检查脚本

`scripts/inspect_processon_export.py`：

- 支持单文件或目录（可递归）。
- 解析 POS 的元数据、流程图元素或思维导图节点文字。
- 解析 XMind 的 `content.json` / `content.xml` 主题文字。
- 读取 PNG/JPEG/GIF/WebP 尺寸、SVG 文字与 `viewBox`。
- 对 PDF 和其他文件至少记录大小、扩展名与 SHA-256。
- 默认只读，不修改源文件。

`scripts/finalize_processon_download.py`：

- 解析 CLI、环境变量、私有 YAML 和跨平台默认路径。
- 初始化带安全标记的临时目录，拒绝认领非空共享目录。
- 先检查再原子复制；默认同名改名，覆盖需要双重显式开关。
- 仅对受管临时目录开放 `--move` 和清理，成功后生成 JSON manifest。
- 交付目录和审计目录不得放在临时目录内部。

`scripts/processon_inventory_state.py`：

- 初始化独立 JSON 检查点，原子保存 `discovered_paths`、`visited_paths`、`blocked_paths` 和逐目录文件清单。
- 每个浏览器小批次通过 `record` 幂等合并；同一完整目录快照重复记录不会重复累计文件。
- `record` 自动刷新 `handoff/progress.md`；原始批次同时记录语义哈希和落盘文件哈希。
- `status` 直接计算可恢复的 `pending = discovered - visited - blocked`，会话中断后从 `pending_paths` 继续。
- `audit` 逐批校验 SHA-256、重新构造 checkpoint、核对 `run.json`；只有差集和受阻项均为 0 才生成完成回执。
- 拒绝相对路径穿越、符号链接状态文件和无效 schema；状态文件权限为 `0600`。

`scripts/build_processon_archive_plan.py`：

- 从已持久化 checkpoint 生成资产归档计划，不访问 ProcessOn、不读取凭据，也不下载文件。
- 输出每个条目的稳定 `artifact_id`、默认导出格式、POS 回退策略、unknown 确认队列和同名风险，并区分 `ready_for_known_artifacts` 与全量 `ready_for_archive`。
- 在归档前验证 checkpoint SHA-256、条目内容和阶段标志，防止目录盘点更新或计划被改写后继续使用旧计划。

`scripts/processon_archive_state.py`：

- 从已验证的归档计划初始化或恢复单写入者下载队列，计划 SHA-256 不一致时拒绝合并旧进度。
- `next` 给出下一批可执行 artifact；`record` 将实际文件、finalizer manifest、大小和 SHA-256 绑定到稳定 artifact_id；`mark` 单列失败和阻断。
- `audit` 重放已完成证据并重新计算计数；进度文件原子写入、权限为 `0600`，未知类型只进入人工确认队列。

`scripts/processon_browser_runner.py`：

- 从任何 AI host/普通终端启动技能专用 Playwright profile，不依赖 Codex/Claude 浏览器工具，也不附着客户主 Chrome。
- `login` 只负责独立窗口中的人工登录；`status`、`snapshot`、`run` 默认 headless。
- action 合同只允许 ProcessOn HTTPS 导航、有名称的语义 click/hover、scroll、wait、受控 popup 和下载；拒绝任意 CSS、无名称控件和远端变更标签，没有填表、脚本执行、Cookie/Storage 或凭据接口。
- 启动时关闭专用 profile 的陈旧多余页面；每个 popup 在 `finally` 中关闭，整次 context 在所有正常/异常退出路径关闭并输出计数回执。

`scripts/diff_processon_inventory.py`：

- 对两个完整 checkpoint 做 fail-closed 的本地快照差分，不访问 ProcessOn、不读取凭据，也不宣称事件/API 增量。
- 仅在稳定 `remote_id/id` 存在时标记移动或重命名；无 ID 文件按安全回退身份比较，无法确认移动时保留新增/移除候选。
- 拒绝 incomplete、blocked、跨范围和重复的稳定 ID；重复无 ID 身份隔离为 `ambiguous_entries`，移除只保留 `removed_candidates`，从不驱动远端或本地删除。

## 验证

- 静态：`python3 -m py_compile scripts/inspect_processon_export.py scripts/finalize_processon_download.py scripts/processon_inventory_state.py scripts/build_processon_archive_plan.py scripts/processon_archive_state.py scripts/diff_processon_inventory.py scripts/processon_browser_runner.py`
- 单测：`python3 -m unittest tests.test_processon_downloads tests.test_processon_inventory_state tests.test_processon_archive_plan tests.test_processon_archive_state tests.test_processon_inventory_delta tests.test_processon_browser_runner -v`，覆盖配置优先级、安全默认路径、原子复制、同名改名、受管移动、目录与资产中间状态、计划漂移拒绝、失败/阻断续跑、完整快照增量门禁，以及主 Chrome profile 拒绝、敏感 action 拒绝和正常/异常页面关闭。
- POS：用一份流程图和一份思维导图 POS 运行 `--format json`，确认标题、category、节点文字和元素数。
- 图片：用 PNG/JPEG 运行脚本，确认宽高与 SHA-256。
- 归档：用真实导出文件依次运行 `finalize --dry-run` 和 `finalize`，核对交付文件 SHA-256 与 manifest；不要把 fixture 路径写入公共文档。
- 远端：至少验证一次“打开团队空间 → 读取文件列表 → 右键看到浏览/下载”；若安全验证阻断导出，结论必须写成“远端读取已验证，完整导出待人工验证后继续”。
- 非干扰浏览器：用临时专用 profile 跑 `status`/`snapshot` smoke；验证客户默认 Chrome 不在进程参数中、启动陈旧页被清理、异常 action 后 context 全关。真实账号 E2E 必须由客户在独立窗口先完成一次登录，不得复制主 Chrome profile。
- 递归：用至少三级目录验证 discovered/visited 差集为 0；模拟会话中断后从持久化恢复点继续。
- 计划：用真实 checkpoint 运行 `build` 和 `verify`；人为修改 checkpoint 或计划条目后，`verify` 必须失败；含 `unknown` 时计划必须标记待确认，允许已确认类型分阶段下载但不可宣称全量归档就绪。
- 下载队列：对真实计划运行 `init` 和 `next`；记录一份真实归档文件后运行 `record` 与 `audit`，确认重启后不会重复领取、计数可重算、修改文件或计划后审计失败。
- 增量：用两份完整审计 checkpoint 运行差分；修改、移动、重命名、添加和移除候选必须可复现。将其中一份变为 pending/blocked 或注入重复稳定 ID 后，命令必须失败；重复无 ID 身份必须隔离，不能产出伪变更。
- VSDX：真实下载或公开样本通过 ZIP/OOXML 检查；装有可选 draw.io 技能时再跑一次 VSDX → `.drawio` → PNG 前向验证。
- 结构：运行仓库 `scripts/audit_skills.py --strict`、支持本仓库版本字段的 skill validator 和 `git diff --check`。
