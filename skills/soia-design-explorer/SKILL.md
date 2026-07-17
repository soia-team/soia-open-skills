---
name: soia-design-explorer
description: 调用外部 huashu-design 能力制作高保真 HTML 原型、设计变体、幻灯片、动画或设计评审；要求显式上游路径、用户自带品牌规范、五分类输出落点与可复现验证。
dependencies:
  external:
    - name: huashu-design
      required: true
      install: "npx skills add alchaincyf/huashu-design -g -y"
version: 1.1.0
created_at: 2026-07-07 14:44:10
updated_at: 2026-07-17 09:33:04
created_by: claude opus 4.6
updated_by: gpt-5.6-sol
---

# soia-design-explorer

这是一个公共设计产物工作流包装层。它把外部 `huashu-design` 的能力收敛为明确输入、显式依赖路径、可控输出和可复现验证；它不替代产品规格或生产实现。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 高保真 prototype / deck / animation | 收集目标、画幅、内容和资产，调用上游工作流逐步生成 | 产物路径、预览、缺口与验证证据 |
| style exploration | 生成 2–4 个可比较方向，不让用户只凭文字盲选 | 方向差异、真实视觉和推荐理由 |
| design review | 对已有页面或截图分级评审 | 结论、严重度、优先修复动作 |

不用于常规前端实现、CSS bug 修复、低保真线框或 PRD 编写。

### 客户如何使用

提供：

1. 交付类型：`prototype` / `deck` / `animation` / `style-exploration` / `review`；
2. 平台与画幅；
3. 受众、用途和成功标准；
4. 真实内容与资产；
5. 用户自带的品牌规范（文件、URL 或明确说明“无”）；
6. 输出类别与路径；
7. `huashu-design` 的显式安装根路径。

需求模糊时先给 2–3 个互斥形态选项。品牌信息不足时使用中性探索方向并标注 placeholder，不从记忆猜品牌色。

### 依赖与安装

安装本技能和外部依赖：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-design-explorer -y
npx skills add alchaincyf/huashu-design -g -y
```

`huashu-design` 是第三方 external dependency，不由本仓库维护或复制。上游公开仓库为 `https://github.com/alchaincyf/huashu-design`；其 README 与 LICENSE 当前声明自 2026-05-14 起采用 MIT，可个人或商业使用。升级前仍应复核上游版本和许可证。

本技能不扫描 `$HOME` 猜测 upstream。每次必须通过本次输入、环境变量或配置给出路径：

```text
~/.config/soia-skills/soia-open-skills/soia-design/soia-design-explorer/config.yml
SOIA_DESIGN_EXPLORER_CONFIG_FILE=<custom-config-path>
HUASHU_DESIGN_ROOT=<huashu-design-root>
```

建议配置：

```yaml
schema_version: 1
env:
  HUASHU_DESIGN_ROOT: "<huashu-design-root>"
  DESIGN_EXPLORER_TEMP_ROOT: "<optional-temp-root>"
  DESIGN_EXPLORER_STATE_ROOT: "<optional-state-root>"
```

品牌规范不是 skill 依赖。客户可提供 brand guideline、logo、色板、字体、截图和文案规则；未提供时明确记录缺口。

### 日志与完成回执

```markdown
完成：<产物或评审结果>。

日志摘要：
- type/platform: <类型与画幅>
- upstream: <显式路径与读取的参考，不输出秘密>
- inputs: <品牌/内容/素材完整度>
- created/updated: <产物路径>
- skipped/failed: <数量和原因>

验证：<浏览器、截图、导出打开或交互检查>
问题与下一步：<placeholder、缺素材或无>
```

## 触发条件

- 做高保真 HTML 原型或 interactive demo；
- 做 HTML slides、动画、演示视频素材或设计变体；
- 对已有视觉稿做方向推荐、评审或改版建议；
- 用户明确提到 `soia-design-explorer`、`huashu-design`、`prototype` 或“视觉方向”。

## 边界

- 输出是设计探索物或评审，不自动成为生产代码、业务合同或产品规格。
- 修改现有文件、覆盖导出、发布或写远端前必须预览并取得确认。
- 不加载或假定任何组织内部 workspace、治理目录、品牌 skill 或落盘规则。
- 上游是独立第三方项目；只读取显式根路径内与当前任务相关的文件，不修改第三方 skill。

## 最小工作流

### Step 1. 锁定任务形态

一次只选择一种主形态：

- `prototype`：可点击页面或 flow；
- `deck`：HTML 幻灯片或导出演示稿；
- `animation`：时间轴动画及可选 MP4/GIF；
- `style-exploration`：2–4 个可比较视觉方向；
- `review`：结构化设计评审。

### Step 2. 检查输入完整度

在生成前列出 `available / missing / placeholder`：

- 真实文案与数据；
- logo、产品图、截图、字体；
- 用户提供的品牌规范；
- 目标平台、画幅和无障碍要求；
- 输出用途、受众和成功标准。

资产缺失会显著影响结果时先询问。允许 placeholder 时必须在产物和回执中标明。

### Step 3. 解析并验证 upstream

从显式输入、`HUASHU_DESIGN_ROOT` 或配置读取根路径。路径缺失时停止并给出安装/配置命令，不递归扫描用户家目录猜测安装位置。

```sh
HUASHU_DESIGN_ROOT="${HUASHU_DESIGN_ROOT:?set explicit huashu-design root}"
test -f "$HUASHU_DESIGN_ROOT/SKILL.md"
```

先读取上游 `SKILL.md`，再按任务读取其直接参考：

- 通用流程与验证：`references/workflow.md`、`references/verification.md`；
- 评审：`references/critique-guide.md`；
- 幻灯片：`references/slide-decks.md`、`references/editable-pptx.md`；
- 动画：`references/animations.md`、`references/video-export.md`；
- 风格探索：`references/design-styles.md`、`references/scene-templates.md`。

上游版本的文件名可能变化；文件不存在时报告实际缺口，不臆造内容。

### Step 4. 按五分类选择输出落点

先分类，再写文件：

| 类别 | 本技能中的例子 | 落点 |
|---|---|---|
| A 临时 | 一次性预览、中间截图、临时 render | 用户指定 `DESIGN_EXPLORER_TEMP_ROOT`；否则 `${TMPDIR}/soia-design-explorer/<slug>/`，`TMPDIR` 未设置则先询问 |
| B 审计 | 发布、覆盖、远端写入等高影响动作记录 | 用户指定 `DESIGN_EXPLORER_STATE_ROOT` 或 `${XDG_STATE_HOME}/soia-design-explorer/`；未配置则先询问 |
| C 交付物 | HTML、PPTX、PDF、MP4、GIF、最终截图 | 用户明确指定的交付目录；不得默认写 cwd 或 Downloads |
| D 产品功能即日志 | 目标产品明确规定的设计记录 | 只服从目标项目公开/本地规则，不由本技能创建约定 |
| E 纯 stdout | 无需留档的简短 review | 不写磁盘 |

写入 C/D 类或覆盖已有文件前展示绝对目标、现状和预计文件列表。A 类不能冒充最终交付物。

### Step 5. 生成与迭代

- 先做最小可见版本，再扩展；
- style exploration 先产出 2–4 个实质不同方向；
- prototype 先保证关键路径可点击，再打磨视觉；
- review 先给结论和问题分级，再给修复建议；
- 所有品牌选择以用户资产或可引用的公开品牌资料为证据。

### Step 6. 验证

至少执行与交付类型相称的一项验证：

- 浏览器打开并检查关键 viewport；
- Playwright/上游验证脚本截图；
- 导出文件可打开、页数/时长符合预期；
- prototype 的关键交互可点击；
- review 覆盖优点、严重度排序问题和最高优先级 3 个动作。

只声称实际运行的检查。预览通过不等于生产实现验收。

## 参考文件

- 执行清单：`references/execution-checklist.md`
