---
name: soia-dev-drawio-visio-diagrams
description: 读取和盘点 Microsoft Visio VSDX，使用 draw.io Desktop 将 VSDX 转为可编辑的 .drawio 真源，理解页面、图形、文字与连接关系，按受控计划更新标签、样式、几何与页面名，并导出 PNG、SVG、PDF 或 JPG；适用于“读懂 ProcessOn 导出的 Visio”“把 VSDX 转成 draw.io”“升级现有架构图/流程图”“批量校验图表”等请求。
version: 1.0.0
created_at: 2026-07-21 10:01:24
updated_at: 2026-07-21 10:01:24
created_by: gpt-5.6-sol
updated_by: gpt-5.6-sol
---

# Draw.io / Visio 图表工程

把外部 `.vsdx` 当作只读原件，先做安全结构盘点，再用本机 draw.io Desktop 转成可编辑 `.drawio`，最后在新文件上理解、修改、渲染和复核。当前 draw.io 可以导入 VSDX，但 26.1.0 起移除了 VSDX 导出；默认交付真源是 `.drawio`，不要承诺无损回写 VSDX。

## 客户可读说明

### 这个技能可以做什么

| 客户目标 | 技能动作 | 可核验证据 |
|---|---|---|
| 读懂 VSDX | 只读解析 OOXML 包中的页面、形状、文字、连接和媒体 | JSON/Markdown 盘点、SHA-256、页数/形状数/连接数 |
| 转成 draw.io | 调用本机 draw.io Desktop CLI，把 VSDX 导入并导出为未压缩 `.drawio` XML | 原件未变、目标文件、CLI 版本、XML 验收 |
| 操作与升级 | 在副本上按 JSON 计划修改页面名、文字、样式和几何，或交给可选 draw.io MCP 做元素级编辑 | 变更计数、未匹配项、前后结构对比 |
| 生成预览/交付 | 从 `.drawio` 或 `.vsdx` 导出 PNG、SVG、PDF、JPG | 文件签名、大小、SHA-256、视觉复核 |
| 批量治理 | 递归检查目录并生成清单；修改仍逐文件显式执行 | 成功/失败/跳过清单，不覆盖原文件 |

### 客户如何使用

提供输入文件或目录、目标动作和交付路径。没有明确授权时只读，不覆盖原件。

```bash
python3 scripts/inspect_vsdx.py <diagram.vsdx> --format markdown
python3 scripts/drawio_cli.py doctor
python3 scripts/drawio_cli.py convert <diagram.vsdx> --output <diagram.drawio>
python3 scripts/inspect_drawio.py <diagram.drawio> --format markdown
python3 scripts/edit_drawio.py <diagram.drawio> --plan <upgrade-plan.json> --output <diagram-upgraded.drawio>
python3 scripts/drawio_cli.py export <diagram-upgraded.drawio> --format png --output <preview.png>
```

典型请求：

```text
读懂这个 ProcessOn 导出的 VSDX，列出页面、组件和关键链路
把这个 VSDX 转成可编辑 draw.io，原件不要动
把架构图里的旧系统名批量换成新名称，统一主色并导出 PNG
审查升级前后的 draw.io，确认页数、组件和关键文字没有丢
```

### 依赖与安装

| 依赖 | 类型 | 安装/用途 | 缺失时 |
|---|---|---|---|
| Python 3.10+ | 必需 | VSDX/draw.io 结构盘点与受控编辑 | 无法运行本地脚本 |
| draw.io Desktop | 转换/渲染必需 | macOS `brew install --cask drawio`；其他平台使用官方桌面版 | 仍可解析 VSDX，但不能转换和渲染 |
| `drawio-mcp-server` | 可选 | 需要实时元素级交互时使用其内置编辑器 | 使用本技能 XML 计划或 draw.io Desktop 手工编辑 |

本技能会依次查找 `DRAWIO_BIN`、`drawio`、`draw.io` 和各平台常见官方安装路径。不要为了使用 MCP 强行安装浏览器扩展：`lgazo/drawio-mcp-server --editor` 自带编辑器；其 draw.io Desktop 直连仍是实验能力。

### 私密信息与中间数据

- VSDX、`.drawio`、预览图和分析结果可能包含企业架构、账号名或业务数据，均按客户私有文件处理。
- 只读盘点默认仅输出到 stdout；交付物必须写到客户明确指定的 `--output`。
- 转换和编辑不把文件上传到第三方；draw.io Desktop 在本地运行。
- 不把客户文件复制进技能仓库、fixture、缓存或公开日志；临时验证使用操作系统临时目录并在结束后删除。
- 不在配置、命令或报告中保存密码、Cookie、Token、浏览器 profile 或 ProcessOn 登录态。

### 日志与完成回执

每次至少报告：输入/输出路径、输入 SHA-256、draw.io 版本、页数/形状数/连接数、实际修改数、未匹配项、导出格式/大小/SHA-256、是否做过视觉复核以及仍未验证的兼容性。不得把“命令退出码为 0”写成“图形语义无损”。

## 能力边界

1. `.vsdx` 是 ZIP/OOXML 包，先用 `inspect_vsdx.py` 做大小、路径穿越、解压总量和 XML 结构检查。
2. VSDX 是输入格式，不是本工作流的编辑真源。转换后保留原件，以 `.drawio` 继续修改。
3. draw.io 30.x CLI 明确支持 VSDX 输入和 XML/PNG/SVG/PDF/JPG 输出；不支持 VSDX 输出。历史 26.0.16 的 VSDX 导出不作为默认依赖。
4. VSDX → draw.io 可能损失字体、主题、复杂母版、图片裁切、超链接或特殊连接语义。结构计数通过后仍需渲染预览做视觉复核。
5. `edit_drawio.py` 只操作未压缩 `.drawio` XML，且只支持计划中明确列出的页面名、文字、style 键和几何字段；复杂重画交给 draw.io Desktop 或可选 MCP。
6. 远端上传、公开分享、覆盖、删除、另存回企业空间都属于外部状态变更，必须由客户明确授权。

## 标准工作流

### 1. 盘点原件

1. 检查扩展名、文件签名、大小和 SHA-256。
2. 运行 `inspect_vsdx.py`，记录页面名、形状/连接数、非空文字和嵌入媒体。
3. 发现宏格式、加密/非 ZIP、路径穿越、XML 过大或解压总量超限时停止，不尝试修复或执行内容。

### 2. 转为可编辑真源

1. 运行 `drawio_cli.py doctor`，记录实际二进制和版本。
2. 为输出指定新的 `.drawio` 路径；目标已存在时停止，不静默覆盖。
3. `convert` 调用官方 CLI 的 VSDX 输入与 XML 输出，随后验证 `<mxfile>`、页面和非空文件。
4. 用 `inspect_drawio.py` 重新统计页面、顶点、边和文字；与 VSDX 盘点做数量和关键文字对照。

### 3. 理解与提出升级

1. 从页面、形状文字、连接关系和视觉预览分别获取证据。
2. 把“图中明确写出”“从拓扑推断”“业务上建议补充”分开写。
3. 在修改前生成升级清单：现状问题、目标、具体操作、验收信号和回滚文件。
4. 会改变系统边界、数据流、职责或安全含义的语义修改，先让客户确认；纯文字纠错、颜色统一和布局清理可按当前请求直接执行。

### 4. 受控编辑

小范围机械改动使用 [升级计划格式](references/upgrade-plan.md) 和 `edit_drawio.py`。复杂新增/删除节点、跨页重构和图形库操作优先使用 draw.io Desktop；已安装 `drawio-mcp-server` 时可在其内置编辑器中逐元素修改，但先读 [上游能力与边界](references/upstreams.md)。任何路线都只改副本。

### 5. 验收

1. 对升级后的 `.drawio` 再运行结构盘点。
2. 导出 PNG 或 SVG；多页图另导出 PDF `--all-pages`。
3. 视觉检查裁切、重叠、乱码、断线、箭头方向、层级和关键文字。
4. 对照升级清单逐项给证据，并明确 VSDX 回写未执行。

## 本地脚本

- `inspect_vsdx.py`：安全读取 VSDX OOXML，输出页面、文字、形状、连接、媒体与校验值。
- `drawio_cli.py`：发现本机 draw.io，执行 doctor、VSDX→draw.io 转换和 PNG/SVG/PDF/JPG 导出，拒绝覆盖。
- `inspect_drawio.py`：读取压缩或未压缩 `.drawio`，输出页面、节点、边、文字和校验值。
- `edit_drawio.py`：按 JSON 计划修改未压缩 `.drawio` 副本，并输出结构化回执。

## 验证

```bash
python3 -m py_compile skills/soia-dev-drawio-visio-diagrams/scripts/*.py
python3 -m unittest tests.test_drawio_visio_diagrams -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/soia-dev-drawio-visio-diagrams
python3 scripts/audit_skills.py --strict
git diff --check
```

真实前向测试至少使用一份客户授权或公开的 VSDX，跑通“inspect → convert → inspect → export”，核对关键文字和预览。公开样本仅用于验证工具链，不提交到仓库。
