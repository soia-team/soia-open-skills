---
name: soia-cwork-processon-diagrams
description: 递归浏览和盘点 ProcessOn 个人/团队空间到叶子文件，预览流程图与思维导图，按授权对流程图默认导出 Visio VSDX、对思维导图默认导出 XMind，将未知类型列入待确认清单，并通过可配置的临时/交付/审计目录完成下载校验与归档；适用于“读取 ProcessOn 文件”“导出架构图”“盘点全部子目录”“从 POS/VSDX/XMind 提取结构”“整理浏览器下载”等请求。
version: 1.5.0
created_at: 2026-07-20 18:57:53
updated_at: 2026-07-21 18:32:37
created_by: gpt-5.6-sol
updated_by: gpt-5.6-sol
dependencies:
  optional: [soia-dev-drawio-visio-diagrams]
---

# ProcessOn 图表浏览与导出

通过用户已经授权的 ProcessOn 账号和浏览器登录态，读取团队空间、文件夹、图表标题与可见内容；在用户指定范围内导出图表，把浏览器下载安全归档到交付目录，并对本地 POS、图片、SVG、PDF、XMind 文件生成可核验清单。默认只读，不修改、分享、移动或删除远端文件。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 盘点团队空间 | 从指定节点递归到每个子目录和叶子文件，按小批次保存并审计恢复状态 | Markdown/JSON 树、进度快照、遗漏差集、权限缺口与完成回执 |
| 看图里有什么 | 进入“浏览”视图读取可访问文字，并用截图核对视觉布局 | 内容摘要、关键文字与截图 |
| 导出图表 | 按客户授权选择 VSDX、POS、PNG、SVG、PDF、XMind 或 Office 格式 | 下载文件、格式/大小/SHA-256 验收 |
| 归档浏览器下载 | 解析 CLI、环境变量和私有 YAML 中的路径，把下载文件校验后复制/移动到交付目录 | 最终路径、碰撞策略、SHA-256 和审计 manifest |
| 解析已有导出 | 读取本地 POS/XMind/SVG/图片；VSDX 可交给可选 draw.io/Visio 技能 | 标题、图表类型、节点文字、尺寸与校验值 |

### 客户如何使用

客户提供以下信息中的最少必要部分：

1. ProcessOn 团队、文件夹或图表 URL；也可以给出空间名和文件名。
2. 目标动作：盘点、预览、导出或解析本地导出文件。
3. 导出时指定文件范围、格式和交付目录；未指定格式时，流程图默认选择当前菜单可用的 Visio `.vsdx`，思维导图默认选择 `.xmind`。两类都建议同时保留 POS 作为 ProcessOn 原生结构备份。无法从图标、浏览视图或菜单确认类型时，只写入“待人工确认”清单，不猜测格式、不自动下载。视觉复用优先 SVG/高清 PNG，审阅交付优先 PDF。
4. 客户在可控制的浏览器中手动输入用户名、密码、短信码或验证码；登录完成后告诉 Agent 继续。技能不读取、记录或保存 Cookie、Local Storage、密码文件、凭据或浏览器配置。
5. 可选复制 [路径配置模板](assets/config.example.yml) 到私有配置目录，固定临时下载、最终交付、审计清单和保留天数。

示例：

```text
盘点这个 ProcessOn 团队空间，只读，不下载：<team-url>
打开“系统架构”文件夹，读取其中架构图的标题和主要内容
把这 3 张流程图默认导出为 Visio，放到 <output-dir>
把浏览器刚下载的 <downloaded-file> 校验后归档到配置的交付目录
解析 <export-dir> 里的 POS，整理成 Markdown 目录
```

### 依赖与安装

| 依赖 | 类型 | 安装 / 配置 | 缺失时怎么处理 |
|---|---|---|---|
| ProcessOn 账号与目标资源权限 | 强依赖 | 客户在 ProcessOn 官方页面登录，并确保自己可见目标空间 | 停止远端读取，列出缺失权限 |
| 可复用登录态的浏览器控制能力 | 远端操作强依赖 | 使用当前 Agent 已安装的浏览器/Chrome 控制能力 | 改为客户手动导出后解析本地文件 |
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

### 日志与完成回执

每次运行至少报告：

- 读取的空间/文件夹范围，以及发现的文件夹数、图表数和受限项数。
- 预览时实际看到的是 DOM 文字、缩略图、浏览视图还是导出的 POS；不要把缩略图 OCR 当作结构化原文。
- 导出时逐类报告请求格式、实际格式、成功/失败数、文件大小与校验结果。
- 归档时报告浏览器实际下载路径、最终交付路径、复制/移动模式、同名处理、manifest 路径和 SHA-256。
- 清理时先报告 dry-run 候选数；实际清理只处理带技能标记的临时目录，并生成删除审计 manifest。
- 安全验证、会员格式限制、权限不足或页面结构变化必须单列，不得伪装成成功。
- 全量盘点必须报告“父目录声明的子目录集合 − 实际访问集合”；差集非空时只能写“部分完成”。
- 完成回执必须来自 `audit` 重放全部不可变批次后的机械结果；不能仅凭 checkpoint 统计或浏览器页面宣称完成。
- 目录盘点和源文件归档必须分阶段报告：`inventory_completed_asset_archive_pending` 不是“知识库归档完成”。
- 资产归档前必须从最终 checkpoint 生成归档计划；`ready_for_known_artifacts` 控制已确认类型的下载，`ready_for_archive` 只有在未知类型也清零后才为 `true`。
- 最终回复给出交付目录、验证方式和未完成项；不输出账号、Cookie、Token 或浏览器内部状态。

## 运行边界

- 默认只读。浏览、搜索、截图和下载属于允许动作；编辑、重命名、复制、移动、删除、锁定、邀请协作、公开分享必须由客户在当前请求中明确授权。
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
- 临时下载使用操作系统临时目录下的技能受管子目录；交付物放客户指定目录，审计 manifest 放用户 state 目录。保留期和路径解析见 [下载归档工作流](references/download-workflow.md)。
- 浏览器长任务按系统/一级目录分批，默认在 `${XDG_STATE_HOME:-~/.local/state}/soia-cwork-processon-diagrams/runs/<run-id>/` 建立运行包；每批立即持久化原始批次和检查点。会话中断后从 `pending_paths` 续跑，不依赖易失内存保存唯一盘点结果。
- 运行包是中间控制面，不是知识库正文；知识库只接收冻结清单、最终 artifact manifest 和已校验交付文件。

## 本次执行固化的失败门禁

执行复杂团队空间前先读取 [失败模式参考](references/known-failure-modes.md)。以下规则是硬门禁：

1. “全量”必须递归到叶子目录；一级页面、旧浏览会话或模型记忆不能代替 checkpoint。
2. 多 Agent 只并行做页面只读分析；同一运行包的 `record`、`audit` 和状态文件只能由一个写入者串行执行。
3. 只有当前视口真实可见并阻断操作的验证码才暂停；隐藏/零尺寸/视口外 iframe 不算弹窗，不得绕过验证。
4. 用户手动登录，Agent 不接收密码、不读 Cookie/Token/profile，也不通过 CDP 或扩展注入凭据。
5. 图表类型无法被卡片、浏览视图或菜单证实时保留 `unknown`，进入人工确认队列。
6. 目录审计通过只代表 `inventory` 阶段完成；下载、格式校验、SHA-256、manifest、draw.io 转换和预览属于独立的 `artifact_archive` 阶段。

## 工作流

### 1. 选择访问方式

1. 先查找是否存在 ProcessOn 官方连接器、公开 API 或 CLI。
2. 若没有满足当前任务的专用能力，使用已安装的浏览器控制能力，并优先复用客户现有登录态。
3. 打开客户给出的 URL；未给 URL 时，从 ProcessOn 官方“我的文件/团队空间”进入。
4. 若跳到登录页，停在登录表单并让客户在该浏览器手动输入用户名、密码和安全验证；不要读取输入值。客户确认登录完成后重新读取页面快照。
5. 验证页面显示目标账号可见的空间或文件。
6. 读取 [ProcessOn 能力与格式](references/processon-capabilities.md)，再决定浏览、预览或导出路线。

CDP/浏览器控制只负责导航、点击、读取页面和下载，不充当密码库。首次登录由客户手动完成，后续由浏览器自身的持久化 profile 复用登录态；普通盘点和导出不需要额外 Chrome 扩展。详细边界见 [下载归档工作流](references/download-workflow.md)。

### 2. 盘点团队空间

1. 先读取当前页面快照，定位团队空间、文件夹、搜索框和文件卡片。
2. 建立 BFS/DFS 队列：起点目录入队，`visited_paths` 为空；每访问一层就立刻保存当前面包屑、目录项和叶子文件，不把完整清单只留在浏览器会话内存。
3. 记录当前层级的：
   - 空间/文件夹名称；
   - 图表标题、类型、作者、更新时间；
   - 可见缩略图和明确的访问限制。
4. 只在客户指定范围内递归。客户说“盘点团队/文件夹”且未明确限制深度时，默认递归到叶子文件；不得把一级目录统计当作全量盘点。
5. 每发现一个子目录就把规范化面包屑加入队列；只有实际读取其文件列表后才加入 `visited_paths`。同名目录用完整面包屑区分。
6. ProcessOn 文件夹用单击进入；不要双击，因为第一次单击已经完成导航，第二次点击可能落在新页面的无关位置并造成误判。
7. 深层目录的可见面包屑会折叠成省略号。始终在清单中维护逻辑完整路径；页面侧只校验当前活动目录标题，不用可见面包屑长度推断深度。
8. 页面采用无限滚动或虚拟列表时，用“滚动前后唯一条目数”验证是否还有新项目；连续两次不增长才停止。返回父目录后空列表时，重新从团队根按逻辑路径逐级单击进入，不猜测内部 URL。
9. 第一次开始前用 `processon_inventory_state.py init` 创建中间状态；浏览器每完成 3—6 个目录，就把完整目录快照写入批次 JSON，并用 `record` 原子合并。批次必须先落盘再继续下一批，不把唯一结果留在浏览器或模型会话内存中。格式见 [递归盘点中间状态](references/inventory-checkpoint.md)。
10. 完成前计算 `discovered_folder_paths - visited_paths`。差集必须为 0；否则逐项列出未访问、权限不足或页面故障。
11. 运行 `processon_inventory_state.py audit --run-dir <run-dir>`，用不可变批次重建 checkpoint 并核对哈希、索引和统计。只有审计通过且 `pending=0、blocked=0` 时才生成 `handoff/receipt.md` 并标记完成。
12. 输出清单时保留层级和来源 URL，但不要生成公开分享链接。

### 2.1 生成资产归档计划

目录审计通过后，先把最终 checkpoint 转成可恢复的资产计划，再开始任何下载：

```bash
python3 scripts/build_processon_archive_plan.py build \
  --checkpoint <run-dir>/inventory/checkpoint.json \
  --output <run-dir>/artifacts/archive-plan.json
```

脚本为每个条目生成稳定 `artifact_id`、完整逻辑目录、类型证据、默认格式、回退格式、同名风险和状态；流程图默认 `vsdx`，思维导图默认 `xmind`，`unknown` 只进入 `pending_confirmation`。`ready_for_known_artifacts=true` 且 `archive_status=known_ready_pending_confirmation` 时可以下载已确认类型，但不得宣称全量资产归档完成；`ready_for_archive=true` 才代表全部条目均可进入归档。盘点继续变化或恢复后，先重新生成计划，禁止沿用旧计划。

下载过程中可用以下命令检查计划是否仍对应当前 checkpoint：

```bash
python3 scripts/build_processon_archive_plan.py verify \
  --plan <run-dir>/artifacts/archive-plan.json \
  --checkpoint <run-dir>/inventory/checkpoint.json
```

校验失败时停止下载，先重新生成计划；不要把陈旧计划中的成功数合并到新一轮报告。

### 3. 预览和读取内容

1. 在文件卡片的可见菜单中选择“浏览”；不要进入编辑模式。
2. 能从浏览视图读取文字时，记录标题、正文/节点文字与结构层级。
3. DOM 不暴露画布文字时：
   - 截图用于理解布局和人工复核；
   - POS 用于结构化提取；
   - SVG/高清 PNG/PDF 用于视觉复核。
4. 只看到缩略图时，明确标注“缩略图级证据”；不要声称已读完整图表。
5. 对架构图、流程图或脑图给出内容摘要时，区分“图中明确写出”和“根据布局推断”。

### 4. 导出

1. 根据最新页面快照定位目标文件的“下载/导出”操作，不依赖固定坐标或私有 CSS。
2. 按客户指定格式导出。未指定时按已确认类型选择：
   - 流程图默认选当前账号菜单中的 `VISIO文件`/`.vsdx`；多画布优先 `导出全部画布 (.vsdx)`；
   - 思维导图默认选 `Xmind文件`/`.xmind`；
   - 无法确认类型的文件加入“待人工确认”清单，不自动打开下载菜单。
   默认格式不可用、会员/权限阻断或下载失败时回退 POS，并明确记录“原请求格式、实际格式、降级原因”，不得静默替换。格式选择见 [ProcessOn 能力与格式](references/processon-capabilities.md)。
3. 首次需要受管临时目录时运行 `paths --ensure`。浏览器能力支持指定下载目录时使用解析出的临时目录；否则保留下载事件返回的真实文件路径。
4. 使用浏览器的下载事件或下载列表确认真实文件落地；不要只凭菜单关闭或 Toast 判断成功。
5. 先 dry-run，再把真实下载文件归档。文件位于受管临时目录时可以显式 `--move`；否则默认复制并保留浏览器原文件：

```bash
python3 scripts/finalize_processon_download.py paths --ensure
python3 scripts/finalize_processon_download.py finalize <browser-downloaded-file> --dry-run
python3 scripts/finalize_processon_download.py finalize <browser-downloaded-file>
```

6. 核对文件非空、扩展名与内容类型一致；VSDX 必须是有效 ZIP/OOXML 且包含 `visio/document.xml`，图像核对尺寸，POS/XMind 核对标题和可提取文字，所有文件记录 SHA-256。
7. 批量导出默认逐个文件执行并汇总结果。官网未明确支持批量下载时，不声称存在批量 API。
8. 需要清理技能临时目录时先运行 `cleanup --dry-run`；只有客户确认候选范围后才运行实际 `cleanup`。

### 5. 本地解析兜底

浏览器不可用、账号未登录或真实可见的安全验证未完成时，让客户手动导出 VSDX/POS/PNG/PDF/XMind，再运行本技能脚本。POS 是 ProcessOn 官方开放格式；VSDX 可交给 `soia-dev-drawio-visio-diagrams` 转为 `.drawio` 真源并升级。

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

## 验证

- 静态：`python3 -m py_compile scripts/inspect_processon_export.py scripts/finalize_processon_download.py scripts/processon_inventory_state.py scripts/build_processon_archive_plan.py`
- 单测：`python3 -m unittest tests.test_processon_downloads tests.test_processon_inventory_state -v`，覆盖配置优先级、安全默认路径、原子复制、同名改名、受管移动、保留期清理，以及中间状态的原子落盘、幂等合并、断点续跑、篡改检测和完成门禁。
- POS：用一份流程图和一份思维导图 POS 运行 `--format json`，确认标题、category、节点文字和元素数。
- 图片：用 PNG/JPEG 运行脚本，确认宽高与 SHA-256。
- 归档：用真实导出文件依次运行 `finalize --dry-run` 和 `finalize`，核对交付文件 SHA-256 与 manifest；不要把 fixture 路径写入公共文档。
- 远端：至少验证一次“打开团队空间 → 读取文件列表 → 右键看到浏览/下载”；若安全验证阻断导出，结论必须写成“远端读取已验证，完整导出待人工验证后继续”。
- 递归：用至少三级目录验证 discovered/visited 差集为 0；模拟会话中断后从持久化恢复点继续。
- 计划：用真实 checkpoint 运行 `build` 和 `verify`；人为修改 checkpoint 或计划条目后，`verify` 必须失败；含 `unknown` 时计划必须标记待确认，允许已确认类型分阶段下载但不可宣称全量归档就绪。
- VSDX：真实下载或公开样本通过 ZIP/OOXML 检查；装有可选 draw.io 技能时再跑一次 VSDX → `.drawio` → PNG 前向验证。
- 结构：运行仓库 `scripts/audit_skills.py --strict`、支持本仓库版本字段的 skill validator 和 `git diff --check`。
