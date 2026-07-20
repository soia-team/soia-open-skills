---
name: soia-dev-design-explorer
description: 基于 Open Design（经 soia-dev-open-design-ops）做高保真 HTML 原型、设计变体、幻灯片、动画探索与设计评审；要求用户品牌输入、五分类输出落点与可复现验证。
dependencies:
  hard: [soia-dev-open-design-ops]
version: 1.3.0
created_at: 2026-07-07 14:44:10
updated_at: 2026-07-20 14:54:56
created_by: claude opus 4.6
updated_by: gpt-5.6-terra
---

# soia-dev-design-explorer

这是一个公共设计产物工作流包装层。它以 `soia-dev-open-design-ops` 提供的 Open Design 原子操作为底座，将高保真设计探索收敛为明确输入、受控输出和可复现验证；它不替代产品规格或生产实现。

## 客户可读说明

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 高保真 prototype / deck / animation | 收集目标、画幅、内容和资产，借助 Open Design 逐步生成 | 产物路径、预览、缺口与验证证据 |
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
7. Open Design checkout 路径；设计系统接入时再提供项目路径或 `DESIGN.md`。

需求模糊时先给 2–3 个互斥形态选项。品牌信息不足时使用中性探索方向并标注 placeholder，不从记忆猜品牌色。

### 依赖与安装

安装本技能及其硬依赖：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-design-explorer -y
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-dev-open-design-ops -y
```

Open Design 的 checkout、Node/pnpm 前置、私有配置、daemon 端口及安全边界全部由 `soia-dev-open-design-ops` 维护。本技能不内嵌或安装 Open Design；原子层不可用时停止设计生成路径，返回其安装或修复建议，不把本地替代品称为 Open Design 交付。

设计系统优先使用正式三件套：`manifest.json`、`DESIGN.md`、`tokens.css`。现有用户项目可走 `DESIGN.md`-only 兼容接入；须由原子层的 CLI/App `import-local` 注册，不能复制或猜测用户项目路径。

品牌规范不是 skill 依赖。客户可提供 brand guideline、logo、色板、字体、截图和文案规则；未提供时明确记录缺口。

### 日志与完成回执

```markdown
完成：<产物或评审结果>。

日志摘要：
- type/platform: <类型与画幅>
- open-design: <环境/daemon/设计系统或目录检查结果，不输出秘密>
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
- 用户明确提到 `soia-dev-design-explorer`、Open Design、`prototype` 或“视觉方向”。

## 边界

- 输出是设计探索物或评审，不自动成为生产代码、业务合同或产品规格。
- 修改现有文件、覆盖导出、发布或写远端前必须预览并取得确认。
- 不加载或假定任何组织内部 workspace、治理目录、品牌 skill 或落盘规则。
- 不修改 Open Design checkout 的上游源码；只通过原子层脚本或上游 CLI/App 做受控操作。

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

### Step 3. 调用 Open Design 原子层

先使用 `soia-dev-open-design-ops` 检查环境和 daemon；不得以进程存活替代目录可用性检查：

```bash
# 从已安装 skill 调用（任意工作目录）
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/check_env.py
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/daemon_ctl.py status
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/daemon_ctl.py health

# 在 soia-open-skills 仓库根目录开发时
python3 skills/soia-dev-open-design-ops/scripts/check_env.py
python3 skills/soia-dev-open-design-ops/scripts/daemon_ctl.py status
python3 skills/soia-dev-open-design-ops/scripts/daemon_ctl.py health
```

`check_env.py` 必须返回 `status=ok`；`health` 必须以 `/api/skills` 返回数组为证据。缺失 checkout、Node/pnpm 或 daemon 不可用时停止，并按原子层给出的建议修复。

接入设计规则时，先检查用户提供的项目是否有正式三件套；没有时将用户项目的 `DESIGN.md` 作为兼容输入，并由原子层的 `design-systems import-local` 接入。查询 functional skills 用 `list_skills.py`；查询 rendering templates 用 Open Design App 的 “Start from” 或 `GET /api/design-templates`。两种目录不得混为一谈。

### Step 4. 按五分类选择输出落点

先分类，再写文件：

| 类别 | 本技能中的例子 | 落点 |
|---|---|---|
| A 临时 | 一次性预览、中间截图、临时 render | 用户指定 `DESIGN_EXPLORER_TEMP_ROOT`；否则 `${TMPDIR}/soia-dev-design-explorer/<slug>/`，`TMPDIR` 未设置则先询问 |
| B 审计 | 发布、覆盖、远端写入等高影响动作记录 | 用户指定 `DESIGN_EXPLORER_STATE_ROOT` 或 `${XDG_STATE_HOME}/soia-dev-design-explorer/`；未配置则先询问 |
| C 交付物 | HTML、PPTX、PDF、MP4、GIF、最终截图 | 用户明确指定的交付目录；不得默认写 cwd 或 Downloads |
| D 产品功能即日志 | 目标产品明确规定的设计记录 | 只服从目标项目公开/本地规则，不由本技能创建约定 |
| E 纯 stdout | 无需留档的简短 review | 不写磁盘 |

写入 C/D 类或覆盖已有文件前展示绝对目标、现状和预计文件列表。A 类不能冒充最终交付物。

### Step 5. 生成与迭代

- 先做最小可见版本，再扩展；
- style exploration 先产出 2–4 个实质不同方向；
- prototype 先保证关键路径可点击，再打磨视觉；
- review 先给结论和问题分级，再给修复建议；
- 所有品牌选择以用户资产或可引用的公开品牌资料为证据；
- 通过 Open Design App/CLI 生成、继续会话或导出时，遵从原子层的稳定入口；不构造未文档化的 API payload。

### Step 6. 验证

至少执行与交付类型相称的一项验证：

- 浏览器打开并检查关键 viewport；
- Playwright/Open Design 验证脚本截图；
- 导出文件可打开、页数/时长符合预期；
- prototype 的关键交互可点击；
- review 覆盖优点、严重度排序问题和最高优先级 3 个动作。

只声称实际运行的检查。预览通过不等于生产实现验收。

## 参考文件

- 执行清单：`references/execution-checklist.md`
