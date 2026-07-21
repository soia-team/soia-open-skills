# 递归盘点中间状态

ProcessOn 深层目录可能包含数百个目录页。任何“全量盘点”都必须使用本地 JSON 检查点，不能把队列和结果只放在浏览器控制会话或模型上下文里。

## 1. 初始化运行包

默认沿用 SOIA 长任务的 XDG state 运行包模式：

```text
${XDG_STATE_HOME:-~/.local/state}/soia-cwork-processon-diagrams/
└── runs/<run-id>/
    ├── run.json
    ├── inventory/
    │   ├── checkpoint.json
    │   └── batches/
    ├── analysis/
    ├── artifacts/
    ├── handoff/
    │   ├── progress.md
    │   └── receipt.md
    └── verification/
        └── inventory-audit-<attempt>.json
```

`run.json` 是控制面，`inventory/checkpoint.json` 是可恢复队列，每个 `inventory/batches/*.json` 是不可变的浏览器批次证据。`progress.md` 是自动刷新的当前快照；`receipt.md` 只在最终机械审计通过后产生。运行期状态不放知识库或公共技能仓库。

```bash
python3 scripts/processon_inventory_state.py init \
  --run-id '2026-07-21-backend-processon-inventory' \
  --root-path '解决方案后端组' \
  --source-url 'https://www.processon.com/org/teams/<team-id>'
```

也可以用 `--run-dir <absolute-run-dir>` 显式指定运行包。`--state <inventory-state.json>` 仅保留为轻量兼容模式，不保存不可变批次和 `run.json`。初始化后根目录位于 `pending_paths`；目录权限为 `0700`，JSON 文件权限为 `0600`，更新通过同目录临时文件原子替换。

## 2. 每个浏览器小批次落盘

每批只处理 3—6 个目录。浏览器读取完目录列表后，先生成批次 JSON：

```json
{
  "directories": [
    {
      "path": "解决方案后端组/01_系统架构",
      "status": "visited",
      "captured_at": "2026-07-21T10:00:00+08:00",
      "folders": [
        {"name": "规范", "path": "解决方案后端组/01_系统架构/规范"}
      ],
      "files": [
        {
          "title": "系统架构图",
          "type": "flowchart",
          "owner": "周鹏",
          "remote_updated_at": "8月前"
        }
      ]
    }
  ],
  "blocked": []
}
```

`files` 必须是该目录当前读取到的完整快照，而不是相对上一次的增量。类型只使用 `flowchart`、`mindmap` 或 `unknown`；无法确认时写 `unknown`，不要猜。

原子合并：

```bash
python3 scripts/processon_inventory_state.py record \
  --run-dir <run-dir> \
  --input <browser-batch.json>
```

`record` 先按内容 SHA-256 把原始批次归档到 `inventory/batches/`，同时记录批次语义哈希和落盘文件哈希，再幂等更新 checkpoint、`run.json` 与 `handoff/progress.md`；重复提交同一批不会重复累计。只有 `record` 成功并返回最新统计后，才能开始下一批浏览器操作。权限受限、真实可见验证码阻断或页面故障写入 `blocked`，同时记录明确原因。

同一个运行包始终只有一个写入者；可以并行做只读页面分析，但批次归档和 checkpoint 合并必须串行，避免两个进程竞争批次序号或覆盖控制面。

## 3. 中断后恢复

```bash
python3 scripts/processon_inventory_state.py status \
  --run-dir <run-dir>
```

恢复时只读取 `pending_paths`，即：

```text
discovered_paths - visited_paths - blocked_paths
```

最终验收要求 `pending_count = 0`；`blocked_count > 0` 时仍不能写成“全量读取成功”，必须逐项交接。`status` 只读取恢复队列，不代替完整性审计。

## 4. 机械审计与完成门禁

任务进行中可以随时审计，确认已有批次仍能可靠恢复：

```bash
python3 scripts/processon_inventory_state.py audit --run-dir <run-dir>
```

每次审计生成新的 `verification/inventory-audit-<attempt>.json`，不覆盖旧审计。审计依次验证：

1. `run.json`、checkpoint 和批次路径均在运行包内；
2. 批次语义 SHA-256 与落盘文件 SHA-256 未变化；
3. 按登记顺序重放全部批次能精确重建 checkpoint；
4. `run.json.batches` 与 checkpoint 批次索引一致；
5. `run.json.counts` 与 checkpoint 实时统计一致。

完整性通过但仍有待访问目录时，运行状态继续保持 `inventory_running`。只有审计通过且 `pending_count=0、blocked_count=0` 时，状态才变为 `completed` 并生成 `handoff/receipt.md`。任何哈希、重放或索引不一致都 fail closed 为 `inventory_audit_failed`，不得发布完成结论。

## 5. 与知识库归档的关系

- XDG state 运行包是控制面：持续更新，可以续跑，并保留原始批次证据。
- Markdown 盘点报告是阶段性快照：从状态文件生成或核对，不反向充当唯一队列。
- VSDX/XMind/POS 和预览文件是内容归档：只在目录盘点和类型确认后下载。
- 状态 JSON、批次 JSON 和企业图表都可能敏感；公开发布前单独做权限与脱敏审查。
