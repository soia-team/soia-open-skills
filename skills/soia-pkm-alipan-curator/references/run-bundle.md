# 大型整理运行包与交接规范

> 当一次任务覆盖完整一级分区、多个二级分区或大量云盘实体时使用。目标是让中间证据脱离具体 AI 工作空间，任何后继 AI 都能从同一个运行包恢复、核对和继续。

## 目录

- [存放位置](#存放位置)
- [目录结构](#目录结构)
- [文件职责](#文件职责)
- [runjson 合同](#runjson-合同)
- [执行链与正式脚本](#执行链与正式脚本)
- [内容审计合同](#内容审计合同)
- [执行账本合同](#执行账本合同)
- [AI 复核与机械验收](#ai-复核与机械验收)
- [生命周期](#生命周期)

## 存放位置

统一使用宿主状态目录，不依赖 Claude、Codex 或其他 AI 的 workspace：

```text
${XDG_STATE_HOME:-$HOME/.local/state}/soia-pkm-alipan-curator/runs/<run-id>/
```

`run-id` 使用 `YYYY-MM-DD-<partition-slug>-<purpose>`；同日重复执行时追加短序号。名称只描述范围与目的，不包含用户名、孩子姓名、账号或云盘 ID。

扫描、计划、账本和验收证据都放运行包；临时下载、OCR 图片、媒体片段和 Excel QA 预览放 `${XDG_CACHE_HOME:-$HOME/.cache}/soia-pkm-alipan-curator/<run-id>/`，不进入 vault、skill 仓库或运行包。

## 目录结构

```text
<run-id>/
├── run.json
├── inventory/
│   ├── initial.scan.jsonl
│   └── initial.scan.jsonl.errors
├── analysis/
│   ├── content-audit.jsonl
│   └── decisions.jsonl
├── plans/
│   └── structure-contract.json
├── actions/
│   ├── 10-<batch>.plan.jsonl
│   └── 10-<batch>.result.jsonl
├── verification/
│   ├── final.scan.jsonl
│   ├── final.scan.jsonl.errors
│   ├── preflight-reclass-<attempt>.json
│   ├── structure-audit.json
│   └── ai-review.json
└── handoff/
    └── receipt.md
```

新增批次时使用 `20-`、`30-`，不覆盖旧账本。脚本自动产生的 `.progress` 与扫描文件同目录保留到任务结束，完成后可删除；`.errors` 必须保留且终态为空。

## 文件职责

| 文件 | 作用 | 何时写 |
|---|---|---|
| `run.json` | 本轮范围、焦点目录和所有证据文件的唯一索引 | 盘点前创建，阶段变化时更新 |
| `initial.scan.jsonl` | 动手前逐文件基线 | 任何写操作前 |
| `content-audit.jsonl` | AI 真读/抽样证据、结论与置信度 | 方案前持续追加 |
| `decisions.jsonl` | 用户裁定、边界句与豁免理由 | 每次裁定后追加 |
| `structure-contract.json` | 编号、导览、分组、产物与地图的机械合同 | 执行前草拟，终态 ID 出现后补齐 |
| `*.plan.jsonl` | 本批次准备执行的动作 | 云盘写操作前 |
| `*.result.jsonl` | 每条动作的独立复核结果 | 每条动作后立即写 |
| `empty-cleanup-evidence.jsonl` | 已 verified 空目录经用户批准送回收站的逐项证据 | 清理后追加；可选，但用于 supersede 时必须登记并受 hash gate 绑定 |
| `preflight-reclass-<attempt>.json` | 对已登记计划的新鲜只读预检结果，以及 manifest/计划/cleanup evidence SHA-256 | dry-run 前；先在 `run.json` 登记路径，再生成 |
| `final.scan.jsonl` | 无聚合、无 `no-descend` 的终态扫描 | 所有导航上传后 |
| `structure-audit.json` | `audit_structure.py --final` 的完整 JSON 输出 | 终态扫描后 |
| `ai-review.json` | AI 对名实、分类轴、重点目录、统计与消费端的第二遍审核 | 机械审计后 |
| `receipt.md` | 给用户和下一个 AI 的短回执 | 全部通过后 |

## `run.json` 合同

路径全部相对运行包，禁止绝对路径和 `..`：

```json
{
  "schema_version": 1,
  "run_id": "YYYY-MM-DD-partition-purpose",
  "status": "in_progress",
  "partition": {"path": "/<partition>", "id": "<optional-id>"},
  "focus_targets": [
    {
      "id": "<cloud-file-id>",
      "path": "/<partition>/<target>",
      "reason": "user_reported_or_inventory_risk",
      "min_evidence": 3
    }
  ],
  "files": {
    "initial_scan": "inventory/initial.scan.jsonl",
    "initial_errors": "inventory/initial.scan.jsonl.errors",
    "content_audit": "analysis/content-audit.jsonl",
    "structure_contract": "plans/structure-contract.json",
    "preflight_report": "verification/preflight-reclass-01.json",
    "empty_cleanup_evidence": "verification/empty-cleanup-evidence.jsonl",
    "final_scan": "verification/final.scan.jsonl",
    "final_errors": "verification/final.scan.jsonl.errors",
    "migration_conservation": "verification/migration-conservation.json",
    "structure_audit": "verification/structure-audit.json",
    "ai_review": "verification/ai-review.json",
    "receipt": "handoff/receipt.md"
  },
  "execution_chain": [
    "merge-map: merge_classification_map.py",
    "assign-numbers-optional: assign_resource_numbers.py",
    "build-reclass: build_reclass_plan.py",
    "build-structure: build_structure_plan.py",
    "preflight: preflight_reclass.py",
    "audit",
    "dry-run",
    "execute",
    "fresh-terminal-scan"
  ],
  "batches": [
    {"name": "rename-and-regroup", "plan": "actions/10-rename.plan.jsonl", "result": "actions/10-rename.result.jsonl"}
  ]
}
```

用户点名的每个链接、inventory 发现的高风险大桶、含“未分类/合集/视频/其他”等弱语义目录，都要进入 `focus_targets`。没有进入焦点合同，就不能靠一句“全区已扫”宣布完成。

## 执行链与正式脚本

大型整理必须沿用以下正式入口；前五步的输出属于运行包证据或已登记计划，不能用会话临时脚本替代。

| 执行链阶段 | 正式脚本 | 运行包内的结果 |
|---|---|---|
| merge map | `scripts/merge_classification_map.py` | 已审核分类、目标、覆写和 inventory 合并后的 TSV map。 |
| assign numbers（可选） | `scripts/assign_resource_numbers.py` | 已确认编号规则后的 map；只改本地 map，不写云盘。 |
| build reclass | `scripts/build_reclass_plan.py` | 可审核的重分类 JSONL；登记为 `run.json.batches` 的语义动作批次。 |
| build structure | `scripts/build_structure_plan.py` | 由结构合同和已登记批次推导的有序 `mkdir` JSONL；登记为 `kind: "structure"` 的批次。 |
| preflight | `scripts/preflight_reclass.py` | 新鲜只读预检报告，检查已登记计划的实际云端前提，并保存 manifest 与每个已登记计划的 SHA-256。 |

预检报告路径必须在调用 `preflight_reclass.py` **之前**登记到 `run.json.files.preflight_report`，且指向尚不存在的运行包内相对路径；脚本会拒绝未登记、越界或与 `--report` 不一致的目标。报告中的 `hashes["run.json"]` 必须对上包含该登记的 manifest，`hashes` 的其余键必须精确覆盖 `run.json.batches` 当前登记的全部计划。任一计划、批次登记或报告路径变化都会使旧报告失效：保留旧证据，登记新的报告路径，再运行一次预检。

`scripts/preflight_gate.py` 提供两层稳定接口：`validate_preflight_gate(...)` 是不读写文件的纯策略函数；`verify_preflight_gate(run_dir, plan_path=<executor-plan>)` 是执行器适配器，读取当前 manifest、报告和计划并返回 `{status, checked, violations}`。非 final 的 `audit_run_bundle.py` 默认执行该门禁；但 audit 与 execute 之间仍可能发生文件变化，因此每个恢复型执行器都必须在 `--execute` 分支、首个云盘写命令之前再次调用适配器，且 `status != "passed"` 时 fail closed。具体接入位置：单项执行器在 `load_plan` 完成、进入 `execute(...)` 前；批量执行器在取得单写者 `execution_slot` 后、进入 `execute(...)` 前。`--execute` 必须显式提供 `--run-dir`；纯 dry-run 可省略，但一旦提供也执行同一门禁。两者都把 `--plan` 作为 `Path` 传给 `plan_path`，从而阻止拿已通过的运行包报告执行未登记计划。

对部分执行后的运行包，preflight 会读取每批 `result` ledger：同一 `(action_id, op, from, to, file_id)` 只认最新记录，且 `verified` / `completed` 只是待核候选，不是事实。候选必须构成该 `file_id` 的连续计划前缀，并由当前 listings 证明最终路径上的实体仍是同一 ID；随后按全局计划逆序回卷已完成动作，再顺序 replay。证明通过的动作状态为 `already_verified`，剩余安全动作仍为 `ready`；伪账本、错 ID、未登记 key、链中间缺口或逆序回卷冲突均使报告失败。

已 verified 的 `mkdir` 若后来经用户批准确认空目录并送入回收站，可由 `run.files.empty_cleanup_evidence` 登记的 JSONL 撤销，不要求 preflight 重建。每行至少包含 `path/file_id/files/dirs/decision/status`，例如 `{"path":"/<removed-dir>","file_id":"<deleted-id>","files":0,"dirs":0,"decision":"user_approved_empty_cleanup","status":"removed_to_recycle_bin_verified"}`。preflight 仅在 ledger 最新状态仍为 `verified` / `completed`、当前目标确实缺失、证据 path 精确命中该 mkdir、`file_id` 非空且唯一、`files` 严格为 0、decision 非空、status 以前述前缀开头时计为 `superseded`。JSONL 使用物理行顺序表达删除顺序：子孙必须早于祖先；父记录若声明 `dirs>0`，此前必须有同数量的直属子目录 removed 证据。`checked.ready_actions + checked.already_verified_actions + checked.superseded_actions` 在无 violation 时应等于 `checked.registered_actions`。

cleanup evidence 是 preflight 输入，不是旁路说明；其相对路径必须属于运行包，SHA-256 与 `run.json`、所有登记计划一起写入报告 `hashes`。证据被修改、替换、移出运行包或从 manifest 注销后，`verify_preflight_gate` 必须失败并要求生成新的 preflight 报告。

## 多 agent 与云盘写入门禁

多 agent 只可并行执行只读盘点、内容审核、计划生成和独立验证；不得并行执行 `mkdir`、`mv`、`rename`、回收站删除、上传或任何其他云盘写入。`merge map` 以及 OB/Excel/云盘索引/`01_先看这里` 的写入也由主控或指定单一写入者负责，避免局部证据互相覆盖。

云盘写入始终是单写者：批量执行器显式传 `--max-parallel 1`，不因分区互不相交而开启第二路。`max_parallel=1` 是本 skill 的固定安全边界；失败恢复沿用原计划和原账本串行 `--resume`，不得复制脚本、改锁目录或提高并行度绕过。

## 内容审计合同

`analysis/content-audit.jsonl` 每个焦点至少一行：

```json
{"target_id":"<id>","path":"/<path>","status":"reviewed","evidence":[{"method":"listing","source":"<relative-source>","finding":"<fact>"},{"method":"document-sample","source":"<file-or-page>","finding":"<fact>"},{"method":"media-metadata","source":"<file-or-timepoint>","finding":"<fact>"}],"recommendation":"<keep-rename-move-split-archive>","confidence":"high"}
```

证据项必须含 `method/source/finding`。目录与文件名只算 `listing` 证据；文档至少补目录/代表页，媒体至少补清单、字幕/讲义或元数据。确实判不了时写 `status=unclear`；收官前必须写 `disposition=archived` 和最终 `target`，不能留在业务区伪装成已分类。

## 执行账本合同

计划和结果用稳定 `action_id` 一一对应：

```json
{"action_id":"B10-001","op":"mv","from":"/<old>","to":"/<new>","file_id":"<source-file-id>","reason":"<approved-rule>"}
{"action_id":"B10-001","status":"verified","evidence":"independent terminal listing","final_path":"/<new>"}
```

计划文件中的 `action_id` 必须在本次运行包的**所有 `run.json.batches` 登记计划之间全局唯一**，同批重复和跨批重复都阻断执行；空值或缺失值也阻断。每个批次应在 `run.json` 登记后再审计，`actions/` 下历史遗留但未登记的 obsolete plan 不属于本轮范围，不纳入这道检查。结果账本是追加式证据：断点恢复时允许同一 `action_id` 先出现 `failed/skipped`、后追加 `verified`，审计以该 action 的最后一条结果为终态；不得覆盖或删除早期失败证据。最终每个计划 action 只接受最新状态为 `verified`，或最新状态为带明确原因的 `skipped`；最新状态仍为 `failed` 或缺结果会阻断收官。旧的 `${STATE}/moves/` 单文件账本继续可读，但新大型任务应使用运行包，避免不同 AI 把同一轮证据散在多个目录。

### 执行前门禁

所有批次计划写入并登记到 `run.json` 后、第一次云盘写操作前，先运行非 `--final` 的运行包审计：

```bash
python3 '<skill-dir>/scripts/audit_run_bundle.py' \
  --run-dir '<run-dir>'
```

审计失败时不得执行任何云盘写操作。重复报告会给出 `batch`、登记的 `plan` 相对路径和 JSONL 物理 `line`，并指出该 `action_id` 的首次出现位置；审计只读取 `run.json.batches` 指向的计划，不会因为 `actions/` 目录中存在未登记的历史计划而阻断本轮。

执行已批准方案时优先使用 skill 内的恢复型执行器；默认 dry-run，先审预览再加 `--execute`。跨到归档区时必须同时显式给出业务边界和归档边界，不能把允许范围放宽到云盘根目录：

严格按以下链条执行，不能把 `dry-run`、`audit` 或 `fresh terminal scan` 合并成“看起来成功”的一步：

```text
merge map → assign numbers (optional) → build reclass → build structure
→ preflight → audit → dry-run → execute → fresh terminal scan
```

```bash
python3 '<skill-dir>/scripts/apply_reclass.py' \
  --run-dir '<run-dir>' \
  --plan '<run-dir>/actions/10-reclass.plan.jsonl' \
  --ledger '<run-dir>/actions/10-reclass.result.jsonl' \
  --driveId '<drive-id>' --root '/<business-partition>' \
  --archive-root '/<archive-partition>' --execute --resume
```

同一源目录中的大量实体要按多个目标组迁移时，可把计划按“同一源父目录 + 同一目标目录”连续排列，再使用批量入口。它最多把 20 个兼容动作合并为一次 CLI `mv`，但仍为每个 `action_id` 追加独立结果；任一前置缺失、目标冲突或终态不一致都会整批停止，不会用命令返回码冒充成功：

```bash
python3 '<skill-dir>/scripts/apply_reclass_bulk.py' \
  --run-dir '<run-dir>' \
  --plan '<run-dir>/actions/40-long-series.plan.jsonl' \
  --ledger '<run-dir>/actions/40-long-series.result.jsonl' \
  --driveId '<drive-id>' --root '/<business-partition>' \
  --batch-size 20 --max-parallel 1 --execute --resume
```

`mv`/`rename` 计划必须携带来源 `file_id`。执行器把每次 `ll` 解析为 `name → file_id`：写前拒绝同名但 ID 不同的来源或目标，写后只在目标同名实体仍是计划 ID 时记为 verified；resume key 也包含该 ID，旧账本不能跳过同路径的新实体。

预检和执行器不能依赖外层 `eval` 注入登录态：`preflight_reclass.py` 的只读 `ll` 与执行器的每个 `aliyunpan` 调用都通过相邻原子 skill 的 `soia-pkm-alipan/scripts/run_with_env.py` 运行。默认 runner 路径由当前脚本相对 `skills/` 动态推导；调用方如需替换，只能显式设置 `SOIA_ALIPAN_RUNNER`。runner 不存在或不能启动时立即返回脱敏失败，绝不改用裸 `aliyunpan`。

批量执行器在同一 drive 上始终只允许 1 个写入进程，并在 XDG state 中使用跨 workspace 的进程锁。`--max-parallel` 只能传 `1`；不得传 `2`，也不得为了提速复制脚本或改变状态目录绕过限制。若历史执行曾留下 `failed`，先用 `ll` 对账“已移动项在目标、未移动项仍在源”，再沿用原计划和原账本串行 `--resume`，让最新终态覆盖历史失败结论。

执行迁移后，必须以最终 `file_id` 为主键重新扫描来源父目录和候选空壳目录：只有独立读取确认目录仍存在且子项数为 0，才可把该 file_id 纳入已批准的回收站清理；路径消失、file_id 不一致或扫描异常都保留并报告，不能按旧路径顺手删除。技术包、源码目录和相对路径依赖树始终作为整体资源保留，不得拆散后把残留目录误判为空壳。

超长系列不要在会话临时脚本里手拼计划。先把本次阈值、主媒体、集号和侧车规则写成运行包内的 JSON，再由公共规划器生成可审阅计划；无法匹配的直属文件默认使规划失败，只有明确决定原地保留时才设置 `direct_file_policy=leave`：

```bash
python3 '<skill-dir>/scripts/plan_series_chunks.py' \
  --scan '<run-dir>/inventory/current.scan.jsonl' \
  --rules '<run-dir>/plans/series-rules.json' \
  --out-plan '<run-dir>/actions/40-long-series.plan.jsonl' \
  --out-report '<run-dir>/analysis/series-plan-report.json'
```

规划器只写本地计划和报告，不调用云盘。主控必须先审核报告中的 `errors/unresolved/protected/planned_protected`、抽查首尾分组及同课配套文件，再把计划交给恢复型执行器；已有输出默认拒绝覆盖，重算时保留旧证据或显式使用新的批次文件名。

规划报告审核通过后，把每个系列 `groups[].name` 的实际预期组逐项写入 `structure-contract.json` 的 `chunk_layers[].required_children`，不要只抄一个能匹配任意编号目录的宽 `child_pattern`：

```json
{
  "parent": "/<series-parent>",
  "child_pattern": "^\\d{2}_\\d{3}(?:-\\d{3})?$",
  "required_children": ["10_001-020", "20_021-035"],
  "count_pattern": "(?i)\\.mp4$",
  "max_items": 20,
  "exclude": ["assets", "配套资料"]
}
```

`child_pattern` 只验证组名格式；`required_children` 才定义本轮终态的精确组集合。缺少任一预期组会报告 `missing_required_chunk`，出现匹配格式但不在清单中的组会报告 `unexpected_chunk`。`exclude` 只豁免明确保留的非分组兄弟目录，不能当作必需组，也不会自动加入 `required_children`。未生成分组且允许保持平铺的系列不要填写空数组，直接省略 `required_children` 以保留兼容行为。

`protect` 只表示“命中保护规则”。缺省不提供 `protected_dir` 时，命中文件继续原地保留，只出现在 `protected` 报告中，不生成移动动作。只有在语义明确、确实属于该系列的配套资料（例如该课的字幕、讲义或说明）时，才显式提供 `protected_dir`；它必须是单个安全相对目录名。此时规划器会生成 `<parent>/<protected_dir>` 的 `mkdir` 和逐文件 `mv`，并在 `planned_protected` 中列出对应动作。无法确认归属的文件不要用这个字段“顺手收纳”，应继续报告为 `unresolved`，或按用户明确指定的边界留在 `90_存档`（或等价存档区）。

启用 `protected_dir` 后，若该目录或生成的 group 目标已在扫描中存在，或其名称与本次生成的 group 名相同，规划器必须报错并且不写计划；不要依赖执行器覆盖已有实体。

若写命令后登录态/网络在终态回读时中断，账本会留下 `failed` 而不会假装成功。恢复登录后用 `--resume`：执行器先检查源与目标；源已消失且目标同名实体已存在时追加 `verified + idempotent-resume`，否则才重试或保留 `skipped`，避免制造 `(1)` 重复目录。

## AI 复核与机械验收

### 跨根迁移守恒审计

所有 `--final` 收官审计都必须在 `run.json.files` 登记 `migration_conservation` 报告并使其通过：`audit_run_bundle.py --final` 无条件检查该报告，跨业务根、归档根或多个候选终态根迁移的场景尤其关键。因此结构审计之外还必须运行 `audit_migration_conservation.py`。它只读取运行包中的 JSON/JSONL，不调用云盘；以初始扫描的 `file_id` 为基线，将一个或多个终态扫描合并后核验：初始实体仍存在、文件 `size`/`SHA1` 未变、已验证的 `mv`/`rename` 计划 ID 落在计划终态路径、没有重复物理行或聚合行。目录整包移动不要求目录路径不变，但其所有初始后代文件仍必须按 `file_id`、字节数和 SHA1 守恒。

在 `run.json.files` 中保留既有单扫描 `final_scan`，或改用非空的 `final_scans` 数组登记多个互不重叠的终态逐文件扫描；后者优先。计划和账本始终只读取已登记的 `run.json.batches[].plan/result`，不会接受 `actions/` 目录内未登记的文件：

```json
{
  "files": {
    "initial_scan": "inventory/initial.scan.jsonl",
    "final_scans": [
      "verification/final-business.scan.jsonl",
      "verification/final-archive.scan.jsonl"
    ],
    "migration_conservation": "verification/migration-conservation.json"
  }
}
```

常规迁移不得丢失任何初始实体。若经用户明确批准需要移除某个空壳或其他实体，计划必须使用 `op: "delete" | "remove" | "trash"`、同一 `file_id`、非空 `reason` 和 `allow_missing: true`，且该 action 在账本中的最新状态必须是 `verified`；这才是唯一被视为已授权缺失的情况。不能用 `skipped`、旧路径消失或未登记账本来推定授权。

```bash
python3 '<skill-dir>/scripts/audit_migration_conservation.py' \
  --run-dir '<run-dir>' --final \
  > '<run-dir>/verification/migration-conservation.json'
```

未加 `--final` 时脚本仍输出完整报告，便于执行前发现扫描/计划问题；`--final` 下任一违规都返回非零，不能收官。终态扫描必须逐文件、无聚合，并且多个扫描不得重叠同一 `file_id`。

先运行结构合同，再由另一次 AI 审核原始证据，而不是复述执行者结论：

```bash
python3 '<skill-dir>/scripts/audit_structure.py' \
  --scan '<run-dir>/verification/final.scan.jsonl' \
  --scan-errors '<run-dir>/verification/final.scan.jsonl.errors' \
  --contract '<run-dir>/plans/structure-contract.json' \
  --final > '<run-dir>/verification/structure-audit.json'

python3 '<skill-dir>/scripts/audit_run_bundle.py' \
  --run-dir '<run-dir>' --final
```

`ai-review.json` 必须使用下列稳定检查名，至少覆盖：焦点目录逐项、分类主轴互斥性、名不符实、超限平铺、编号/导览、跨区消费端、计数守恒。稳定名称让后继 AI 和机械脚本能判断复核是否真的做过，而不是只看到一个笼统的 `passed`：

```json
{"status":"passed","checks":[
  {"name":"focus-target-coverage","status":"passed","evidence":"all declared targets independently reviewed"},
  {"name":"classification-axis","status":"passed","evidence":"each audited layer uses one declared axis"},
  {"name":"semantic-name-match","status":"passed","evidence":"sampled content agrees with final names and stages"},
  {"name":"long-series","status":"passed","evidence":"declared and discovered long series were checked"},
  {"name":"numbering-guides","status":"passed","evidence":"numbering and required guides agree with the contract"},
  {"name":"consumer-links","status":"passed","evidence":"resource maps contain verified direct cloud links"},
  {"name":"count-conservation","status":"passed","evidence":"initial, moved, archived and final counts reconcile"}
],"unresolved":[]}
```

机械脚本验证“证据是否齐全且相互闭合”，AI 验证“分类判断是否合理”。两者都通过才允许把 `run.json.status` 改为 `completed`。

## 生命周期

1. 盘点前建运行包和 `run.json`，先写用户点名目标。
2. 初始扫描退出码为 0、`.errors` 为空后，才开始 AI 内容审计。
3. 方案与用户裁定写入运行包，所有写操作先写计划账本。
4. 每批结果独立复核；失败不覆盖，追加新批次。
5. 严格按 `merge map → assign numbers (optional) → build reclass → build structure → preflight → audit → dry-run → execute → fresh terminal scan` 收敛；迁移后按 file_id 扫描空壳，获授权后才回收站清理。
6. 导航上传后做最终扫描、结构审计、AI 复核和运行包审计；随后必须更新 OB、Excel、云盘索引和 `01_先看这里`，并验证这些消费端引用最终 file_id。
7. OB 只保存资源地图、冻结审计和短回执；运行时 JSONL 留在 state，不复制进 vault。
8. 交接时只需给出 `<run-dir>`；接手 AI 先运行 `audit_run_bundle.py`，再读 `run.json` 指向的证据。
