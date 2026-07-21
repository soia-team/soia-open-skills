# Draw.io 升级计划格式

`edit_drawio.py` 接收一个 JSON 文件。只操作未压缩 `.drawio` XML，输出必须是新路径。

```json
{
  "schema_version": 1,
  "rename_pages": [
    {"from": "Page-1", "to": "生产架构"}
  ],
  "replace_text": [
    {"from": "Legacy Gateway", "to": "API Gateway", "match": "exact"},
    {"from": "旧域名", "to": "新域名", "match": "substring"}
  ],
  "set_style": [
    {"cell_id": "node-1", "properties": {"fillColor": "#dae8fc", "strokeColor": "#6c8ebf"}}
  ],
  "set_geometry": [
    {"cell_id": "node-1", "x": 120, "y": 80, "width": 160, "height": 60}
  ]
}
```

## 规则

- `schema_version` 目前只能是 `1`。
- `rename_pages` 与 `replace_text` 默认要求每条至少匹配一次；零匹配会失败，避免假升级。
- `match=exact` 只替换完整 `mxCell@value`；`substring` 替换其中的字符串。
- `set_style.properties` 的值为字符串；值为 `null` 时删除该 style 键。
- `set_geometry` 只接受 `x`、`y`、`width`、`height` 数字字段。
- 同一输出路径已存在时拒绝写入。
- 脚本不会新增或删除组件/边。复杂语义重构用 draw.io Desktop 或可选 MCP，并单独做结构和视觉验收。
- 几何修改必须控制在明确的节点范围内；扩大节点宽高或移动位置后，要重新导出 PNG/SVG，检查相邻节点、文字、连线是否重叠或被裁切。
- 结构检查通过不代表视觉通过。交付前至少核对：文字完整、节点无重叠、连线无断裂、箭头方向正确、没有新增的无意义交叉线。
