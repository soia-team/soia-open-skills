# ProcessOn 下载归档工作流

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

1. Agent 打开 ProcessOn 官方登录页。
2. 客户在受控浏览器里手动输入用户名、密码、短信码和验证码。
3. Agent 不读取输入值，不接收聊天中的密码，不访问 Cookie、Local Storage、密码文件或浏览器 profile。
4. 客户确认登录完成后，Agent重新读取页面快照并继续盘点或下载。

账号密码只用于 ProcessOn 官方浏览器会话，不进入技能配置和 manifest。

### CDP 与浏览器扩展的边界

- CDP（Chrome DevTools Protocol）是浏览器控制通道，不是凭据存储。不要通过 CDP 命令、环境变量或脚本参数传递用户名和密码。
- 首次登录后，由浏览器自己的持久化 profile 保存登录会话；后续 Agent 复用已登录页面，不接触 Cookie 或密码。
- 普通目录盘点、浏览和官方下载不需要另开发 Chrome 扩展。只有 ProcessOn 官方 UI 无法提供、且客户明确批准的新能力，才单独评估扩展或企业 API；扩展也不得读取或外传凭据。

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
