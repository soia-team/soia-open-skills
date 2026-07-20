---
name: soia-dev-open-design-ops
description: Open Design 原子操作层：环境/安装/daemon 健康管理，DESIGN.md/三件套与项目接入，skills/templates 查询，HTML/PDF/PPTX/MP4 导出及会话 resume；供上层设计流程调用。Triggers：「检查 Open Design」「接入 DESIGN.md」「查询设计目录」「导出设计产物」「恢复设计会话」
version: 1.0.0
created_at: 2026-07-20 14:16:00
updated_at: 2026-07-20 14:16:00
created_by: gpt-5.6-sol
updated_by: gpt-5.6-sol
---

# soia-dev-open-design-ops — Open Design 原子操作层

只执行可验证的 Open Design 原子操作，不替客户做视觉方向、叙事或模板取舍。上层设计流程可把本技能作为 daemon、目录、设计系统与导出能力的底座。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 检查或启动 Open Design | 检查 Node、pnpm、checkout，控制本地 daemon 并探测 `/api/skills` | JSON 状态、缺失项、日志位置与修复命令 |
| 接入设计系统 | 区分正式三件套与 `DESIGN.md`-only 兼容路径，再用上游 CLI/App 接入 | 设计系统 id、来源、验证结果 |
| 查询能力目录 | 分开查询 functional skills 与 rendering templates | 名称、说明、`od.mode`/category 清单 |
| 渲染和导出 | 按上游稳定入口驱动 App/CLI，导出 HTML、PDF、PPTX 或 MP4 | 产物路径、格式语义、可打开性检查 |
| 继续已有设计会话 | 复用 daemon 保存的原生 session handle | 同一会话的 follow-up 结果或明确降级原因 |

### 客户如何使用

1. 说明目标：环境检查、daemon、设计系统、目录查询、渲染/导出或继续会话。
2. 提供 Open Design checkout 路径；设计系统接入时再提供项目路径或 `DESIGN.md`。
3. 导出时提供 project id、项目内源文件、目标格式与输出路径；PPTX 还要说明“像素保真”还是“可编辑”。
4. Agent 先运行只读检查，再执行最小原子命令；覆盖文件、删除系统或写远端前必须单独确认。
5. 执行后检查真实 API 响应或产物，不以命令退出码代替验收。

### 依赖与安装

安装本技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-open-design-ops -y
```

Open Design 本地开发 checkout 的上游前置为 Node.js 24.x、pnpm 10.33.x 与 Corepack。按 upstream `QUICKSTART.md`：

```bash
git clone https://github.com/nexu-io/open-design.git <open-design-root>
cd <open-design-root>
corepack enable
corepack pnpm --version   # upstream 当前 pin 10.33.2
pnpm install
```

本技能不安装或内嵌 Open Design，也不把 Open Design 当作另一个 agent skill。Node/pnpm/checkout 任一缺失时，停止需要 daemon 的 workflow，并返回补齐命令。

### 私有配置

复制 `config.example.yml` 到：

```text
~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-open-design-ops/config.yml
SOIA_DEV_OPEN_DESIGN_OPS_CONFIG_FILE=<custom-config-path>
```

至少配置 `OPEN_DESIGN_HOME`。daemon 默认绑定 loopback，端口默认 `7456`；可用 `OPEN_DESIGN_DAEMON_PORT`、`OPEN_DESIGN_WEB_PORT`、`OPEN_DESIGN_DAEMON_URL` 覆盖。项目自己的 `DESIGN.md` 路径可放 `OPEN_DESIGN_PROJECT_DESIGN_MD`。本机 checkout 与项目路径只进私有 config 或进程环境，不写进公开正文、仓库或日志。

### 日志与完成回执

daemon 后台日志与 PID 状态写入用户 state 目录；可用 `OPEN_DESIGN_STATE_DIR` 改位置。不得打印 config 内容或 env 值。最低回执：

```markdown
完成：<本次原子操作及结果>。

日志摘要：
- environment/daemon: <ok、missing 或 unreachable>
- processed: <系统/技能/模板/产物数量>
- created/updated: <产物或状态类别>
- skipped/failed: <数量与原因>

文件变化：<产物路径或“未改动项目文件”>
验证：<API、文件存在、页数/时长/打开检查>
问题与下一步：<缺依赖、需客户确认或“无”>
```

## 定位与边界

- 只做安装引导、daemon、目录、设计系统接入、渲染/导出和 resume 等原子操作。
- 不决定设计方向、版式、品牌语言、deck 叙事或视觉评审；这些属于 slides、visual、`soia-dev-design-explorer` 等上层流程。
- functional skill 是 agent 工作中的能力；design template 是渲染形态。不得把两类目录合并成一个列表。
- 不臆造 headless API。上游没有稳定脚本入口时，明确写“由 agent 按文档驱动 upstream App/CLI”。
- 凭据、provider 登录态和本机路径只进 provider 自有存储、私有 config 或进程环境。

## 环境与 daemon

### 1. 检测环境

从本 skill 目录运行：

```bash
python3 scripts/check_env.py
```

脚本离线检查 `node`、`pnpm`、`OPEN_DESIGN_HOME` 与关键仓库文件，输出 `status`、`missing`、`checks` 和 `suggestions` JSON。Node 不是 24.x、pnpm 不是 10.33.x 时返回不兼容状态，不自动升级。

### 2. 启停与健康检查

```bash
python3 scripts/daemon_ctl.py start
python3 scripts/daemon_ctl.py status
python3 scripts/daemon_ctl.py health
python3 scripts/daemon_ctl.py stop
```

`start` 使用 upstream Quickstart 的 `pnpm tools-dev run web` 控制面，显式传 `--daemon-port`，并以 detached/nohup-style 后台进程记录 PID 与日志。不要使用已移除的 `pnpm dev`、`pnpm daemon` 或 `pnpm start` aliases。健康检查以 `GET /api/skills` 返回 `skills` 数组为准；`/api/health` 只说明进程级存活，不证明技能目录可用。

默认 URL 是 `http://127.0.0.1:7456`。只允许 loopback URL；需要远端部署、反向代理或 `0.0.0.0` 时，本技能停止并要求客户按 upstream 安全配置处理，不替客户公开本机 daemon。

## 设计系统管理与项目接入

### Design System Project 三件套

新建或维护正式 Open Design Design System Project 时，以 upstream `_schema` 为源，最低契约为：

```text
<design-system-slug>/
├── manifest.json
├── DESIGN.md
└── tokens.css
```

- `manifest.json` 使用 `od-design-system-project/v1`，folder slug 与 manifest id 一致。
- `DESIGN.md` 是给 agent 的 canonical design prose；`tokens.css` 是 canonical compiled semantic tokens。
- 新系统不得把 `DESIGN.md`-only 当 authoring target。rich package 的可选文件与 token 约束以 upstream `docs/design-systems.md`、`design-systems/_schema/AGENTS.md` 和 TypeScript schema 为准。

### 用户项目的 `DESIGN.md`-only 兼容接入

现有项目可先把设计规则放在 `<user-project>/DESIGN.md`。daemon 对已注册的 legacy/user-installed 目录保留 `DESIGN.md`-only discovery，但这是兼容 fallback。项目接入优先走 CLI/App 的 local import，让 daemon 扫描并建立可编辑设计系统：

```bash
node <open-design-root>/apps/daemon/dist/cli.js design-systems import-local <user-project> --name "<project-name>" --json
node <open-design-root>/apps/daemon/dist/cli.js design-systems list --json
```

首次实例可把某个真实产品项目的 `<product-project>/DESIGN.md` 配到私有 `OPEN_DESIGN_PROJECT_DESIGN_MD`，再以 `<product-project>` 执行 `import-local`；不要复制或写死维护者路径。若 `dist/cli.js` 不存在，先在 checkout 中运行 `pnpm --filter @open-design/daemon build`。

常用管理命令以 `od design-systems help` 的实际输出为准；v0.13.0 已有 list/show/rename/download/import-local/import-github/import-shadcn。rename、delete、覆盖导入或 token rebuild 影响持久状态，先展示目标与现状再确认。

## 目录查询

### Functional skills

```bash
python3 scripts/list_skills.py
python3 scripts/list_skills.py --category slides
```

脚本调用 daemon `GET /api/skills`，输出 `name`、`description`、`od.mode` 与 category；`--category` 是对 API 返回结果做本地精确过滤，因为该路由本身没有 server-side category query。

### Rendering templates

渲染模板由 `GET /api/design-templates` 与 checkout 的 `design-templates/` 提供，不属于 `/api/skills`。需要模板时用 App 的 New Project “Start from” rail 或直接查询该 API；不要用 `list_skills.py` 假装覆盖模板目录。

Deck 先在三类入口中选一类，再交给上层流程做设计决定：

- `simple-deck`：design-system 驱动、单文件、约束明确的水平 deck；
- `guizang-ppt`：电子杂志/WebGL 系，包含 Monocle、WIRED、Kinfolk、Domus、Lab 五个方向；
- `html-ppt`：HTML PPT Studio 系，提供 full-deck、theme、layout、animation 与 presenter runtime 目录。

## 渲染与导出

### 提交渲染任务

1. 在 App 选择 runtime、design template 与 design system，提交 prompt；filesystem-capable runtime 写 canonical project files，text-only/BYOK runtime 返回完整 `<artifact>`。
2. 从 App 打开项目并验证预览；或让 daemon-spawned agent 使用注入的 `OD_BIN`、`OD_DAEMON_URL`、`OD_PROJECT_ID`、`OD_PROJECT_DIR`。
3. 不直接 POST 未文档化的 chat/run payload。自动化优先使用已构建的 `od` CLI；App-only 交互由 agent 按 upstream 文档驱动。

### HTML

HTML 是 project 中的 canonical artifact。用 App Download → HTML，或读取/复制项目内源文件。v0.13.0 的 `od export` 没有 `--format html`，不得伪造该格式；项目文件 API/route 仅在确有 project id 与路径时使用。

### PDF 与 PPTX

构建 daemon CLI 后，可用 upstream v0.13.0 的稳定命令：

```bash
node <open-design-root>/apps/daemon/dist/cli.js export <project-file.html> \
  --project <project-id> --format pdf --out <output.pdf>
node <open-design-root>/apps/daemon/dist/cli.js export <deck.html> \
  --project <project-id> --format pptx --out <output.pptx>
```

内置 PPTX 是一页一张截图，适合像素保真交付，不是可编辑 shape/text deck。可编辑 PPTX 推荐链：

1. 以 HTML deck 为视觉真相源；
2. 调 functional skill `pptx-generator` 生成可编辑 `.pptx`；
3. 调 `pptx-html-fidelity-audit` 比较 HTML/PPTX，修 footer overflow、裁切、字体/italic 与节奏漂移；
4. 打开最终 PPTX，核对页数、画幅、关键文本与无越界。

### MP4

MP4 使用 HyperFrames HTML 渲染器，不冒充通用视频导出：

```bash
node <open-design-root>/apps/daemon/dist/cli.js media generate \
  --surface video --model hyperframes-html \
  --project <project-id> --composition-dir <project-relative-composition-dir> \
  --output <output.mp4>
```

composition 目录必须包含 upstream 要求的 `hyperframes.json`/`meta.json`/`index.html`。daemon 实际驱动 `npx hyperframes render`；任务排队后按 CLI 返回的 task id 使用 `od media wait`，最后验证文件存在、MIME、时长与可播放性。

## 会话 resume（v0.13.0）

Native resume 由 daemon 自动完成，不是用户手工 `od resume`：

1. 重新打开原 project 与原 conversation，不新建会话；
2. 发送 follow-up turn；
3. daemon 对支持的 runtime 复用已捕获的 native session id，使 Codex、OpenCode、Pi 与 Open Design Cloud 等 v0.13.0 支持项跨 turn 延续；
4. 检查 run 结果与 touched files，确认不是 cold start。

如果 session handle 过期、runtime 不支持或 CLI 拒绝 resume，明确报告是“resume unavailable/expired”，再由客户决定是否以历史消息重建上下文；不得把重建冒充原生 resume。daemon 重启后仍以实际 conversation/run metadata 为证据。

## 私有配置命令包装器

需要显式加载 config 执行受控 upstream 命令时：

```bash
python3 scripts/run_with_env.py -- pnpm tools-dev status
python3 scripts/run_with_env.py -- pnpm --filter @open-design/daemon build
```

包装器只允许 Corepack/pnpm 的已知 Open Design 生命周期与 build/install/version 形态；拒绝 shell、`env`、`printenv`、任意 executable 和 pnpm exec/dlx。不得用 `set -x`，不得打印 env 值。

## 安全守则

1. daemon 是本机特权服务，默认只绑定 `127.0.0.1`；不得为了方便暴露公网端口。
2. 不打印 config、env、provider 凭据或 daemon 注入的 token；日志只说明存在/缺失。
3. stop 只处理本技能记录的 PID；PID 不匹配或状态不明时停止并报告，不猜进程。
4. import、rename、delete、download overwrite、export overwrite 前查看目标现状；删除和覆盖必须获得当前请求的明确授权。
5. 不修改 `OPEN_DESIGN_HOME` 里的 upstream 源码来“接通”项目；本技能只读查询或按官方 CLI/App 操作。

## 验收

- 环境：`check_env.py` 返回 `status=ok`，无 missing。
- daemon：`daemon_ctl.py health` 验证 `/api/skills` 返回数组。
- 目录：skills 与 templates 分开取数；category 过滤结果全部匹配。
- 设计系统：三件套齐全，或明确标为 `DESIGN.md`-only compatibility；import 后能 list/show。
- 导出：目标文件存在、非空、格式可打开；PDF/PPTX 核页数，MP4 核时长和可播放。
- resume：同一 project/conversation 的 follow-up 有 native resume 证据；无证据时不得声称成功。
