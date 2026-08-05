# soia-dev-open-design-ops

> 提供供上层设计流程调用的 Open Design 原子操作与运行保障

所属：[`soia-dev-design`](https://github.com/soia-team/soia-open-dev-design-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-design-skills/tree/main/skills/soia-dev-open-design-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「检查 Open Design」「接入 DESIGN.md」「恢复设计会话」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 检查或启动 Open Design | 检查 Node、pnpm、checkout，控制本地 daemon 并探测 `/api/skills` | JSON 状态、缺失项、日志位置与修复命令 |
| 接入设计系统 | 区分正式三件套与 `DESIGN.md`-only 兼容路径，再用上游 CLI/App 接入 | 设计系统 id、来源、验证结果 |
| 查询能力目录 | 分开查询 functional skills 与 rendering templates | 名称、说明、`od.mode`/category 清单 |
| 渲染和导出 | 按上游稳定入口驱动 App/CLI，导出 HTML、PDF、PPTX 或 MP4 | 产物路径、格式语义、可打开性检查 |
| 继续已有设计会话 | 复用 daemon 保存的原生 session handle | 同一会话的 follow-up 结果或明确降级原因 |

### 客户如何使用

其他可识别说法包括「查询设计目录」「导出设计产物」；要求设计探索或评审时由上层 `soia-dev-design-explorer` 编排，本技能只执行原子操作。

1. 说明目标：环境检查、daemon、设计系统、目录查询、渲染/导出或继续会话。
2. 提供 Open Design checkout 路径；设计系统接入时再提供项目路径或 `DESIGN.md`。
3. 导出时提供 project id、项目内源文件、目标格式与输出路径；PPTX 还要说明“像素保真”还是“可编辑”。
4. Agent 先运行只读检查，再执行最小原子命令；覆盖文件、删除系统或写远端前必须单独确认。
5. 执行后检查真实 API 响应或产物，不以命令退出码代替验收。

## 安装

本技能随 `soia-dev-design` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev-design@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev-design@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-dev-design-skills -g -a '*' -s soia-dev-open-design-ops -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
