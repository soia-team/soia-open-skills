# ProcessOn 下载归档工作流

## 宿主无关浏览器主路线

正式批量必须调用 `scripts/processon_browser_runner.py`，不得在客户正在使用的 Chrome 中用 browser/computer-use/扩展逐份开标签。runner 使用技能专用持久化 profile：首次 `login` 打开独立窗口让客户手动登录，后续 `status`、`snapshot`、`run` 默认 headless。任何 AI host 只需运行 Python 命令，不需要自己的浏览器工具。

已有归档计划时，优先使用 `scripts/processon_archive_batch.py`：一个专用 persistent context 固定复用 worker 页，不为每份 artifact 新建并遗留标签；浏览器下载可受控并发，最终归档与进度仍只有一个 writer。Playwright 直接 `download.save_as(<managed-root>/<run-id>/<artifact_id>/<原文件名>)`，不与其他同名文件共享 staging，也不经过个人 Downloads；结构/语义校验后在同一文件系统 no-copy move 到交付目录。`--workers 1` 不需要 proof；`--workers 2` 或 `3` 必须分别提供当前计划下真实样本生成的语义并发 proof。

```bash
python3 scripts/processon_browser_runner.py login --url '<team-url>'
python3 scripts/processon_browser_runner.py status --url '<team-url>'
python3 scripts/processon_browser_runner.py snapshot --url '<folder-url>'
```

`status`、`snapshot` 和 `run` 默认在初始导航后等待 2000ms，让 ProcessOn SPA 完成首屏渲染；慢网络可在子命令前传 `--settle-ms <0..30000>`。若快照的 `visible_text` 与 `interactive` 同时为空，先增加 settle 或改用独立 headed 诊断，禁止从空快照生成盲点动作。

默认 profile 位于用户私有 config 根的 `soia-skills/soia-open-skills/cwork/soia-cwork-processon-diagrams/browser-profile/`。可用 `--profile-dir` 或 `SOIA_CWORK_PROCESSON_BROWSER_PROFILE_DIR` 覆盖，但 runner 会拒绝系统默认 Chrome/Chromium profile、符号链接和非空无技能标记目录。profile 由浏览器保存登录态；技能不读取其 Cookie、Storage、密码或凭据文件。

`run` 接收 schema 1 JSON。只允许 `goto`、有名称的语义 `click`/`hover`、`scroll`、`wait_text`、非激活型 `press`、`back`、`snapshot`、固定只读 `inspect_text`、ProcessOn 专用 `row_menu`、`download` 和嵌套 `popup`；URL 仅限 HTTPS ProcessOn。任意 CSS、无名称控件、调用方 JavaScript、删除/编辑/移动/分享/发布等远端变更标签会被拒绝；没有 `fill`、Cookie/Storage 或网络拦截动作。`inspect_text` 只接收标题文字与 `nth`，用技能内固定代码返回最多六层祖先和直接子节点摘要。`row_menu` 只接收可见文件标题，在已验证的同行容器内打开“更多”；文本动作默认先过滤隐藏重复节点：

```json
{
  "schema_version": 1,
  "start_url": "https://www.processon.com/org/teams/<team-id>",
  "steps": [
    {"action": "snapshot"},
    {"action": "click", "text": "<diagram-title>", "button": "right"},
    {"action": "hover", "text": "下载"},
    {"action": "download", "text": "VISIO文件"}
  ]
}
```

页面结构不同时，先 `snapshot`，再根据实际可见 role/name/text 生成不超过 10 个 artifact 的小批次 action；不要把示例文案当固定选择器。流程图和思维导图格式仍由归档计划决定。

标签生命周期是硬门禁：专用 context 启动时只保留一个父页面；确需新页面时必须用嵌套 `popup`，子步骤完成、失败或超时后都在 `finally` 中关闭；整次命令退出时关闭所有专用页面和 context。成功 JSON 与错误 JSON 都必须带 `receipt`；`scoped_pages_opened` 与 `scoped_pages_closed` 必须相等，且 `pages_closed_at_exit >= 1`。异常也必须返回关闭回执；缺少回执时停止下一份并按“清理未验证”处理。ProcessOn 同一标题可能对应多个 DOM 节点，`wait_text` 用 `nth` 明确选择（默认 `0`），不要把 strict mode 重复节点误判为文件缺失。中断后先核对回执和下载目录，再恢复队列。

## 配置优先级

按以下顺序解析，先命中的值生效：

1. CLI：`--temp-dir`、`--output-dir`、`--manifest-dir`、`--retention-days`
2. 当前进程环境变量
3. `SOIA_CWORK_PROCESSON_DIAGRAMS_CONFIG_FILE` 指向的私有 YAML
4. 技能默认私有配置路径
5. 跨平台安全默认值

默认私有配置：

```text
~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-processon-diagrams/config.yml
```

从 `assets/config.example.yml` 复制模板，只填写本地路径。不要加入 ProcessOn 用户名、密码、Cookie、Token 或浏览器 profile。

正式批量若要求 no-copy 归档，`TEMP_DIR` 与 `OUTPUT_DIR` 必须位于同一文件系统；推荐把 TEMP 指向交付根下专用 `_staging` 目录。脚本会用受管标记约束清理范围，且拒绝把 output/manifest 放进 temp 内部。

## 配置键与默认值

| 环境变量 | 用途 | 安全默认值 |
|---|---|---|
| `SOIA_CWORK_PROCESSON_DIAGRAMS_TEMP_DIR` | 浏览器下载的受管临时目录 | 操作系统临时根目录下的 `soia-cwork-processon-diagrams/` |
| `SOIA_CWORK_PROCESSON_DIAGRAMS_OUTPUT_DIR` | 客户交付物目录 | 用户 Downloads 下的 `soia-cwork-processon-diagrams/` |
| `SOIA_CWORK_PROCESSON_DIAGRAMS_MANIFEST_DIR` | 归档与清理审计清单 | 用户 state 根目录下的 `soia-cwork-processon-diagrams/manifests/` |
| `SOIA_CWORK_PROCESSON_DIAGRAMS_RETENTION_DAYS` | 临时文件保留天数 | `7` |

Windows 使用系统 `TEMP`、`APPDATA`、`LOCALAPPDATA`；macOS/Linux 使用 Python 的系统临时目录、`XDG_CONFIG_HOME`、`XDG_STATE_HOME` 或用户目录安全回退。脚本不硬编码 `/tmp` 或维护者路径。

## 登录交接

1. Agent 运行 runner `login --url '<team-url>'`，打开技能专用 ProcessOn 窗口。
2. 客户只在该独立窗口里手动输入用户名、密码、短信码和验证码。
3. Agent 不读取输入值，不接收聊天中的密码，不访问 Cookie、Local Storage、密码文件或浏览器 profile。
4. runner 检测目标页可访问后自动关闭独立窗口；Agent 用 headless `status`/`snapshot` 继续盘点或下载。

账号密码只用于 ProcessOn 官方浏览器会话，不进入技能配置和 manifest。

### CDP 与浏览器扩展的边界

- CDP（Chrome DevTools Protocol）是浏览器控制通道，不是凭据存储。不要通过 CDP 命令、环境变量或脚本参数传递用户名和密码。
- 首次登录后，由 runner 的专用持久化 profile 保存登录会话；后续 Agent 复用登录态但不接触 Cookie 或密码。
- 不附着客户主 Chrome 的 CDP，也不复制默认 profile。普通目录盘点、浏览和官方下载不需要另开发 Chrome 扩展。只有 ProcessOn 官方 UI 无法提供、且客户明确批准的新能力，才单独评估扩展或企业 API；扩展也不得读取或外传凭据。

## 初始化路径

```bash
python3 scripts/finalize_processon_download.py paths
python3 scripts/finalize_processon_download.py paths --ensure
```

第一条只显示解析结果；第二条创建目录并在临时目录写入技能安全标记。非空且没有标记的目录不会被认领，避免误把共享 Downloads 当成可清理目录。

## 归档一个下载文件

浏览器必须先返回真实落地路径：

```bash
python3 scripts/finalize_processon_download.py finalize <browser-downloaded-file> --dry-run
python3 scripts/finalize_processon_download.py finalize <browser-downloaded-file>
```

默认行为：

- 复制源文件，保留浏览器原文件。
- 先检查文件非空、类型和结构，再原子写入交付目录。
- 同名文件自动变成 `name (1).ext`，不覆盖原文件。
- 写入包含源路径、交付路径、大小、格式、SHA-256 和配置来源的 JSON manifest。

文件位于带标记的技能临时目录时，可以显式移动：

```bash
python3 scripts/finalize_processon_download.py finalize <managed-temp-file> --move
```

只有交付文件校验和 manifest 写入成功后才删除源文件。move 使用同文件系统 hard-link + atomic replace，不复制 payload；跨文件系统直接失败，不静默回退复制。

## 正式批量下载队列

目录盘点和归档计划完成后，先初始化可恢复的 artifact 状态，再领取小批次：

```bash
python3 scripts/processon_archive_state.py init \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json
python3 scripts/processon_archive_state.py next \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json \
  --limit 10
```

浏览器下载、`finalize` 和本地结构校验完成后，用 `record` 绑定 artifact_id、浏览器落地文件、最终交付文件与 finalizer manifest。失败或阻断分别用 `mark` 记录原因；已有截图、Markdown 或错误响应等诊断文件时，重复传入 `--evidence-file`，脚本会把它们复制到 `<run-dir>/artifacts/evidence/`、记录大小与 SHA-256，并由 `audit` 重放。未知类型仍在人工确认队列，不得用 `mark` 冒充已确认类型。

ProcessOn 导出任务可能晚于菜单点击数秒才真正落盘；如果同一页面在前一份完成前切换列表选中项，下载文件名可能使用后来选中的标题，而文件内容仍属于前一项。同一 worker 因此必须严格串行：记录 artifact 独占 staging，发起一份导出，等下载事件和落盘完成，再做结构/页面文字校验，最后才切换下一项。不得把不同条目平铺到 `~/Downloads` 并用浏览器生成的 `(1)`、`(2)` 推断来源。多 worker 只在 proof 证明独立页面没有交叉串件后启用；每份仍需核对弹页标题、source URL、建议文件名和 VSDX/XMind 内部标题信号。出现相同 SHA、意外后缀或语义冲突时，本 wave 保持 pending 并降级为串行；不能立即重试或写 `record`。

VSDX 的语义校验先尝试完整标题信号。中文复合标题可能只在图内分散出现，例如标题含“柜面状态”而图中分别写“柜面视频身份核验标识”和“任务状态”；此时必须已经核对稳定 `remote_id/source_url`，并至少命中两个互不重叠的中文二字片段，记录 `semantic_match_method: chinese_bigram_pair`。只命中一个“状态”“系统”等泛词仍然失败并保持 pending。

VSDX 页面文字在语义校验前先运行明文凭据门禁。当前保守识别中文“密码”以及英文 `password/passwd/pwd` 后的赋值形式；命中后错误和批次 receipt 只记录模式类型与数量，不包含匹配值。文件不得进入 Git 交付目录，应移到同盘持久敏感隔离区、只用脱敏索引作为 `mark --outcome blocked` 的证据，等待凭据轮换或脱敏副本。

推荐批次入口：

```bash
python3 scripts/processon_archive_batch.py \
  --plan <run-dir>/artifacts/archive-plan.json \
  --progress <run-dir>/artifacts/download-progress.json \
  --team-url '<team-url>' --config <private-config.yml> \
  --manifest-dir <run-dir>/artifacts/finalizer-manifests \
  --source-links <archive-root>/_manifests/source-links.yml \
  --progress-mirror <archive-root>/_manifests/archive-progress.yml \
  --workers 1 --limit 12 --dry-run
```

`--output-root`、`--download-dir` 和 `--manifest-dir` 仍可逐项覆盖 config；`--download-dir` 表示受管 staging 前缀，batch 会自动追加从 progress 路径推导的 `<run-id>`。

历史状态中只要 `download_source` 直接位于个人 `~/Downloads` 根目录，无论文件名有没有 `(n)`，都不能证明来源与 artifact_id 唯一绑定。先生成换行分隔的 artifact id 清单，再用 `reopen` 将已有交付文件和 `metadata.yml` 原子移入同盘持久隔离区（推荐 `<archive-root>/_quarantine/<run-id>/legacy-flat`）；状态提交失败会回滚文件。隔离区不能放在按保留期自动清理的 `_staging` 下。重开项计入 `revalidation_pending` 和 `remaining_known`，会被 `next` 重新领取，新的 `record` 成功后自动清除复验状态。

并发前先用两份可信 VSDX/XMind 做串行基线和两路真实下载，解析文件内文字确认没有交叉串件，再保存运行包私有 `concurrency-proof.json` 并改为 `--workers 2 --concurrency-proof <proof>`。三路需要独立三路 proof，不能拿两路结果外推。批处理持有全局 lock；第二个 orchestrator 必须立即失败，不能重复领取。

ProcessOn 列表是虚拟化渲染：目标不在当前视口时必须先滚动并重新读取快照。思维导图列表页原生格式无产物时进入官方编辑器重试 XMind、POS、POSM；只有 Markdown 能下载时将其作为阻断证据，不作为 artifact 交付物。同目录同名的 collision-risk 项无论 `--workers` 为多少都从自动队列排除；只有取得行级稳定 ID/URL 或人工逐项确认后，才允许进入专用下载流程，交付目录附加 artifact_id 前 8 位。

每一小批结束运行 `audit`。它重新检查计划 SHA-256、成功记录计数、交付文件大小与 SHA-256、VSDX/XMind 包结构、阻断诊断证据及 finalizer manifest。进度文件使用原子写入和独占锁；会话中断后再次执行 `init` 与 `next` 即可继续。

覆盖属于高影响动作，必须由客户在当前请求中明确授权并同时传入：

```bash
--collision overwrite --allow-overwrite
```

## 清理临时文件

```bash
python3 scripts/finalize_processon_download.py cleanup --dry-run
python3 scripts/finalize_processon_download.py cleanup
```

清理只遍历带正确技能标记的临时目录，跳过符号链接和安全标记，按保留天数删除过期普通文件，并为实际删除生成审计 manifest。交付目录或审计目录位于临时目录内部时直接拒绝执行。
