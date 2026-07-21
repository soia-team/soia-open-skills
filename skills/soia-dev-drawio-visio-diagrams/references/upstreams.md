# 上游能力与边界

> 核对日期：2026-07-21。上游会更新，执行前以本机 `drawio --help` 与最新官方文档为准。

## 采用结论

| 上游 | 协议 | 可借鉴/调用 | 本技能不做的假设 |
|---|---|---|---|
| [jgraph/drawio-desktop](https://github.com/jgraph/drawio-desktop) | Apache-2.0 | 官方本地 CLI；当前 help 明确支持 VSDX 输入以及 XML/PNG/SVG/PDF/JPG 输出 | 不假设当前版本能导出 VSDX |
| [jgraph/drawio](https://github.com/jgraph/drawio) | Apache-2.0 | VSDX 导入与 changelog 真源 | 26.1.0 已移除 VSDX export；不锁定旧版本规避限制 |
| [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) | MIT | `.drawio` XML 生成、CLI 渲染、自检闭环的方法参考 | 不复制其代码、shape 索引或完整 skill；它不解决 VSDX 真源治理 |
| [lgazo/drawio-mcp-server](https://github.com/lgazo/drawio-mcp-server) | MIT | 可选的元素/页面/图层级读写和内置编辑器 | draw.io Desktop 集成仍受 CSP 限制；不把实验能力写成已稳定 |

## 为什么不直接把 VSDX 当长期编辑格式

draw.io 官方 changelog 显示 26.1.0 移除了 VSDX 导出。当前 draw.io 30.x CLI 仍可把 VSDX 作为输入，并导出 draw.io XML 或视觉格式。因此稳定闭环是：

```text
VSDX 原件（只读） → .drawio 可编辑真源 → PNG/SVG/PDF/JPG
```

如客户必须交付新的 VSDX，需要在独立兼容性项目中评估 Microsoft Visio、固定旧版 draw.io 或其他转换器，并用原生 Visio 验收；不属于本技能默认承诺。

## GitHub 调研方法

1. 用 `gh repo view ... --json licenseInfo,defaultBranchRef,url` 核对仓库与协议。
2. 用 GitHub API 读取上游 `SKILL.md`、README、TOOLS、DESKTOP 和 changelog，不从搜索摘要推断能力。
3. 只借鉴工作流和能力边界；未复制第三方代码。
4. 本技能的脚本为独立实现，第三方登记见仓库根 `THIRD_PARTY_NOTICES.md`。
