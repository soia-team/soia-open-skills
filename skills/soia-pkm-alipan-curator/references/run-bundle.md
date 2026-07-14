# 大型整理运行包与交接规范

> 当一次任务覆盖完整一级分区、多个二级分区或大量云盘实体时使用。目标是让中间证据脱离具体 AI 工作空间，任何后继 AI 都能从同一个运行包恢复、核对和继续。

## 目录

- [存放位置](#存放位置)
- [目录结构](#目录结构)
- [文件职责](#文件职责)
- [runjson 合同](#runjson-合同)
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
    "final_scan": "verification/final.scan.jsonl",
    "final_errors": "verification/final.scan.jsonl.errors",
    "structure_audit": "verification/structure-audit.json",
    "ai_review": "verification/ai-review.json",
    "receipt": "handoff/receipt.md"
  },
  "batches": [
    {"name": "rename-and-regroup", "plan": "actions/10-rename.plan.jsonl", "result": "actions/10-rename.result.jsonl"}
  ]
}
```

用户点名的每个链接、inventory 发现的高风险大桶、含“未分类/合集/视频/其他”等弱语义目录，都要进入 `focus_targets`。没有进入焦点合同，就不能靠一句“全区已扫”宣布完成。

## 内容审计合同

`analysis/content-audit.jsonl` 每个焦点至少一行：

```json
{"target_id":"<id>","path":"/<path>","status":"reviewed","evidence":[{"method":"listing","source":"<relative-source>","finding":"<fact>"},{"method":"document-sample","source":"<file-or-page>","finding":"<fact>"},{"method":"media-metadata","source":"<file-or-timepoint>","finding":"<fact>"}],"recommendation":"<keep-rename-move-split-archive>","confidence":"high"}
```

证据项必须含 `method/source/finding`。目录与文件名只算 `listing` 证据；文档至少补目录/代表页，媒体至少补清单、字幕/讲义或元数据。确实判不了时写 `status=unclear`；收官前必须写 `disposition=archived` 和最终 `target`，不能留在业务区伪装成已分类。

## 执行账本合同

计划和结果用稳定 `action_id` 一一对应：

```json
{"action_id":"B10-001","op":"move","from":"/<old>","to":"/<new>","reason":"<approved-rule>"}
{"action_id":"B10-001","status":"verified","evidence":"independent terminal listing","final_path":"/<new>"}
```

计划文件中的 `action_id` 必须唯一。结果账本是追加式证据：断点恢复时允许同一 `action_id` 先出现 `failed/skipped`、后追加 `verified`，审计以该 action 的最后一条结果为终态；不得覆盖或删除早期失败证据。最终每个计划 action 只接受最新状态为 `verified`，或最新状态为带明确原因的 `skipped`；最新状态仍为 `failed` 或缺结果会阻断收官。旧的 `${STATE}/moves/` 单文件账本继续可读，但新大型任务应使用运行包，避免不同 AI 把同一轮证据散在多个目录。

执行已批准方案时优先使用 skill 内的恢复型执行器；默认 dry-run，先审预览再加 `--execute`。跨到归档区时必须同时显式给出业务边界和归档边界，不能把允许范围放宽到云盘根目录：

```bash
python3 '<skill-dir>/scripts/apply_reclass.py' \
  --plan '<run-dir>/actions/10-reclass.plan.jsonl' \
  --ledger '<run-dir>/actions/10-reclass.result.jsonl' \
  --driveId '<drive-id>' --root '/<business-partition>' \
  --archive-root '/<archive-partition>' --execute --resume
```

同一源目录中的大量实体要按多个目标组迁移时，可把计划按“同一源父目录 + 同一目标目录”连续排列，再使用批量入口。它最多把 20 个兼容动作合并为一次 CLI `mv`，但仍为每个 `action_id` 追加独立结果；任一前置缺失、目标冲突或终态不一致都会整批停止，不会用命令返回码冒充成功：

```bash
python3 '<skill-dir>/scripts/apply_reclass_bulk.py' \
  --plan '<run-dir>/actions/40-long-series.plan.jsonl' \
  --ledger '<run-dir>/actions/40-long-series.result.jsonl' \
  --driveId '<drive-id>' --root '/<business-partition>' \
  --batch-size 20 --execute --resume
```

若写命令后登录态/网络在终态回读时中断，账本会留下 `failed` 而不会假装成功。恢复登录后用 `--resume`：执行器先检查源与目标；源已消失且目标同名实体已存在时追加 `verified + idempotent-resume`，否则才重试或保留 `skipped`，避免制造 `(1)` 重复目录。

## AI 复核与机械验收

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
5. 导航上传后做最终扫描、结构审计、AI 复核和运行包审计。
6. OB 只保存资源地图、冻结审计和短回执；运行时 JSONL 留在 state，不复制进 vault。
7. 交接时只需给出 `<run-dir>`；接手 AI 先运行 `audit_run_bundle.py`，再读 `run.json` 指向的证据。
