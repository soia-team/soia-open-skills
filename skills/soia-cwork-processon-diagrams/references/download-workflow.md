# ProcessOn 下载归档工作流

## 宿主无关浏览器主路线

正式批量必须调用 `scripts/processon_browser_runner.py`，不得在客户正在使用的 Chrome 中用 browser/computer-use/扩展逐份开标签。runner 使用技能专用持久化 profile：首次 `login` 打开独立窗口让客户手动登录，后续 `status`、`snapshot`、`run` 默认 headless。任何 AI host 只需运行 Python 命令，不需要自己的浏览器工具。

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

只有交付文件校验和 manifest 写入成功后才删除源文件。

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

ProcessOn 导出任务可能晚于菜单点击数秒才真正落盘；如果在前一份完成前切换列表选中项，下载文件名可能使用后来选中的标题，而文件内容仍属于前一项。正式队列因此必须严格串行：记录下载目录基线，发起一份导出，轮询到新增文件完成且大小连续稳定，再做结构/页面文字校验和 `record`，最后才领取下一项。浏览器下载事件短时超时后继续核对真实文件，不能立即重试或切换选中项。出现同名不同 SHA、意外 `(n)` 后缀或标题与页面文字冲突时，使用 `soia-dev-drawio-visio-diagrams` 只读提取 VSDX 文字；无法唯一映射的文件保留为诊断材料，对应 artifact 继续 pending。

ProcessOn 列表是虚拟化渲染：目标不在当前视口时必须先滚动并重新读取快照。思维导图列表页原生格式无产物时进入官方编辑器重试 XMind、POS、POSM；只有 Markdown 能下载时将其作为阻断证据，不作为 artifact 交付物。同目录同名且缺少远端 ID 时，交付目录附加 artifact_id 前 8 位，避免浏览器 `(1)` 后缀失去来源定位。

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
