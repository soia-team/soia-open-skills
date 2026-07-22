---
name: soia-dev-officecli-ops
description: OfficeCLI 原子操作层：检查环境，读取、查询、复制后修改并验证 DOCX/XLSX/PPTX，提供稳定元素路径、原子 batch、HTML/截图预览和 MCP/CLI 使用边界。适用于「检查 Office 文件」「修改 Word/Excel/PPT」「批量修复 Office」「验证 OpenXML」「OfficeCLI」「officecli ops」。
version: 1.0.0
created_at: 2026-07-22 18:02:28
updated_at: 2026-07-22 18:02:28
created_by: gpt-5.6-luna
updated_by: gpt-5.6-luna
---

# soia-dev-officecli-ops

把 OfficeCLI 封装成可供上层技能复用的 Office 文件原子操作层。它负责环境检查、结构读取、稳定定位、复制后修改、OpenXML 校验和预览证据；不替上层流程决定内容、叙事、品牌或视觉方向。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 检查 Word、Excel 或 PPT | 提取结构、文本、统计与 issues，必要时渲染 HTML/截图 | 问题清单、元素路径、预览和修复建议 |
| 精确修改现有 Office 文件 | 优先用稳定 ID/名称定位，在副本上执行 `set/add/remove/move/swap` | 新文件、修改回执、校验结果 |
| 一次执行多项修改 | 把 3 项及以上操作组织成原子 `batch` | 成功/失败步骤；失败时不交付半成品 |
| 创建基础 Office 文件 | 创建 DOCX/XLSX/PPTX 结构并逐步添加内容 | 可继续编辑的 Office 文件 |
| 给其他技能提供 Office 底座 | 根据宿主能力和任务类型选择 OfficeCLI、Open Design 或宿主原生工具 | 清晰的执行路线和降级说明 |

### 客户如何使用

1. 提供 `.docx`、`.xlsx` 或 `.pptx` 路径，并说明要检查、创建还是修改。
2. 修改已有文件时同时说明输出路径；默认生成副本，不原地覆盖源文件。
3. Agent 先运行环境检查和只读查询，再展示修改目标；删除、覆盖、raw XML、安装、MCP 注册必须单独确认。
4. 三项及以上修改优先使用原子 batch。完成后依次做 schema、issues 和视觉检查。
5. 最终回执说明使用的执行层、修改数量、输出文件、验证证据和剩余限制。

示例：

```text
检查 <report.docx> 的格式和结构问题，先不要修改
把 <deck.pptx> 第 3 页标题改掉，输出为 <deck-fixed.pptx>
审计 <workbook.xlsx>，确认后批量修复公式和格式
用 OfficeCLI 复验刚生成的 PPTX，并给出逐页截图
```

### 依赖与安装

安装本技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-officecli-ops -y
```

核心 workflow 需要官方 `officecli` 可执行文件。先只读检查：

```bash
python3 scripts/check_env.py
```

缺失时只报告官方安装选项，不自动执行远程安装脚本。可按 [OfficeCLI 官方仓库](https://github.com/iOfficeAI/OfficeCLI) 的当前说明安装，再用 `officecli --version` 验证。使用自定义二进制时设置：

```text
OFFICECLI_BIN=<path-to-officecli>
```

本技能不需要凭据或私有配置。OfficeCLI 的 `install`、`mcp`、插件安装和 agent skill 安装会修改用户环境，只有客户明确要求并确认目标后才执行。

与其他能力的关系：

- `soia-dev-open-design-ops`：设计系统、模板、HTML 视觉真相源和高保真导出；不是 OfficeCLI 的替代品。
- 宿主 presentations/documents/spreadsheets：负责宿主规定的创作路线；本技能不得绕过宿主硬约束。
- OfficeCLI：负责跨宿主的 OOXML 读取、精确编辑、批处理、校验与预览。

完整选择表见 [references/tool-routing.md](references/tool-routing.md)。

### 日志与完成回执

```markdown
完成：<检查、创建或副本修改结果>。

- execution_layer: officecli
- source: <输入路径；新建时省略>
- output: <输出路径；只读时省略>
- operations: <读取/修改/批处理数量>
- schema: clean | failed | skipped
- issues: <数量与类别>
- visual_review: passed | failed | skipped

验证：<实际运行的命令与人工检查范围>
限制：<缺少渲染器、未做 Office App 实机检查或其他残余风险>
```

## 定位与硬边界

1. **原子层不做设计决策。** 内容结构、讲述顺序、品牌方向和模板选择由上层技能或客户决定。
2. **默认 copy-on-write。** 修改已有文件必须输出到不同路径；`scripts/officecli_safe.py` 拒绝原地修改。
3. **覆盖必须显式确认。** 输出已存在时先展示目标，客户确认后才使用 `--overwrite`。
4. **L1 → L2 → L3。** 先 `view/get/query`，再 DOM `set/add/...`，最后才用 `raw/raw-set`；不得因不熟悉 schema 直接改 XML。
5. **路径必须来自读取结果。** 优先稳定 `@id`、`@name`、`@paraId`，不要猜测易漂移的位置索引。
6. **文件存在不等于完成。** `validate` 只证明 OpenXML schema；可读性、公式、版式和视觉仍需对应质量门。
7. **第三方边界。** 本技能依赖 Apache-2.0 的 OfficeCLI，但不复制、修改或冒充其内置 skills。

## 标准工作流

### 1. 环境检查

```bash
python3 scripts/check_env.py
python3 scripts/check_env.py --json
```

最低推荐 OfficeCLI `1.0.137`，因为该版本起 batch 默认原子执行。版本更低时停止写操作；只读检查可在明确标注兼容性未验证后继续。

### 2. 只读盘点

先确认格式和目标，再逐层收窄：

```bash
officecli view <file> outline
officecli view <file> stats --json
officecli view <file> issues --json
officecli get <file> / --depth 2 --json
officecli query <file> '<selector>' --json
officecli validate <file> --json
```

属性名、值格式或命令语法不确定时先运行 `officecli help <format> <element> --json`，不凭记忆猜。

### 3. 建立修改计划

每项修改记录：目标路径、修改前读回、动作、期望读回和风险。三项及以上修改写成 batch JSON，先检查所有 selector 和 stable path，再执行一次。

删除、替换、raw XML、接受/拒绝修订、公式重写和覆盖输出属于高风险动作。执行前向客户展示范围与输出路径。

### 4. 在副本上执行

单项或少量 DOM 修改通过安全包装器执行：

```bash
python3 scripts/officecli_safe.py \
  --input <source.pptx> \
  --output <result.pptx> \
  --dry-run \
  -- set '/slide[1]/shape[@id=42]' --prop text='New title'
```

客户确认后去掉 `--dry-run`。若输出已存在且客户明确同意覆盖，再加 `--overwrite`。

新建文件：

```bash
python3 scripts/officecli_safe.py --output <result.docx> --dry-run -- create
python3 scripts/officecli_safe.py --output <result.docx> -- create
```

包装器只允许文档修改 verbs，不允许 `install`、`mcp`、`plugins`、`watch` 或任意 shell；使用 `subprocess` argv 调用，不经过 shell。详细 recipe 见 [references/command-recipes.md](references/command-recipes.md)。

### 5. 读回与质量门

执行后至少检查：

1. 目标路径读回与期望一致。
2. `officecli validate <output> --json` 无 schema error。
3. `officecli view <output> issues --json` 的关键问题已处理或解释。
4. 版式敏感任务生成 HTML/截图并人工查看全部相关页。
5. 在交给非 OfficeCLI 程序或客户前运行 `close`，确保 resident 内容已落盘。

各格式完整门槛见 [references/quality-gates.md](references/quality-gates.md)。

## MCP 与 resident

- 多轮修改可先 `officecli open <file>`，结束时 `officecli close <file>`；跨工具读取前必须 flush/close。
- MCP 和 CLI 共用同一命令语义。MCP 的工具参数是单一 `command` 字符串或 argv，不要臆造结构化 format/type 参数。
- 注册或卸载 MCP 会修改其他应用配置，先读取当前状态并获得明确确认。
- `watch` 是本机预览服务，默认只用 loopback；不要公开到网络接口。

## 资源

- 工具选择与 Open Design 边界：[references/tool-routing.md](references/tool-routing.md)
- 常用命令与批处理模式：[references/command-recipes.md](references/command-recipes.md)
- DOCX/XLSX/PPTX 验收：[references/quality-gates.md](references/quality-gates.md)

## 验收

- 静态：`check_env.py` 能准确报告缺失、版本过低和可用状态。
- 安全：包装器拒绝原地修改、未知 verb、无确认覆盖和非 Office 扩展名。
- 前向：用真实 OfficeCLI 创建并修改 DOCX/XLSX/PPTX fixture，三种文件均通过 schema 校验。
- 视觉：涉及版式时，渲染全部受影响页面并人工检查，不以 `validate` 代替视觉验收。
