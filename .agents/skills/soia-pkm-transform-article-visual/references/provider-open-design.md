# Open Design Provider

适用：高质量长图、信息图、海报、封面、插画与带动效的视觉解释。

`provider=open-design` 的执行依赖 `soia-dev-open-design-ops` 原子层；它不是 `local` 或 `codex-image` 路径的依赖。未安装或原子层检查失败时，停止 Open Design 路径，返回安装/修复建议，不把本地结果称为 Open Design 交付。

环境、daemon 端口、启动命令、状态文件和 Open Design 上游版本等事实只在 `soia-dev-open-design-ops/SKILL.md` 维护；本文件只规定 visual 对它的调用与交付链。

## 使用模式

回执必须写明采用的模式：

1. **Open Design handoff**：将已落盘的 brief、信息架构和素材交给 Open Design agent / App，由其生成或继续编辑视觉项目。
2. **Template-guided local render**：查询 Open Design 的 template 规则后，由当前 agent 在本地生成 HTML/CSS 并以 Chromium 渲染验证。这是模板指导的本地生成，不得声称 Open Design agent 已生成。

两种模式都先保留 source coverage、信息架构、模板映射和 prompt；不能把长文压成低信息量装饰图。

## MCP dry-run 纪律

MCP 安装会改写用户的 agent 配置，必须先 dry-run：

```bash
od mcp install codex --print
od mcp install claude --print
od mcp install gemini --print
od mcp install opencode --print
```

仅在用户确认后才去掉 `--print`。公共 skill 不自动改写多 agent 配置。

## 可用性检查：调用 ops 原子层

从已安装 skill 调用（任意工作目录）：

```bash
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/check_env.py
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/daemon_ctl.py status
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/daemon_ctl.py health
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/list_skills.py
```

在 `soia-open-skills` 仓库根目录开发时，可用对应相对路径：

```bash
python3 skills/soia-dev-open-design-ops/scripts/check_env.py
python3 skills/soia-dev-open-design-ops/scripts/daemon_ctl.py status
python3 skills/soia-dev-open-design-ops/scripts/daemon_ctl.py health
python3 skills/soia-dev-open-design-ops/scripts/list_skills.py
```

`check_env.py` 必须返回 `status=ok`；`health` 以 `/api/skills` 返回数组为证据，不能仅以进程或 `/api/health` 存活替代。`list_skills.py` 查询的是 functional skills，不代表 rendering templates；模板通过 Open Design App 的 “Start from” 或 `GET /api/design-templates` 查询。环境缺口、daemon 启动、端口覆盖和安全边界均回到 ops 的 SKILL.md，不在这里复制。

## 视觉产物主链

输入完成结构化后，主链为：

```text
信息架构与视觉 brief → image / HTML canvas 项目 → 渲染验收 → 导出交付
```

| 主链步骤 | Open Design handoff | Template-guided local render |
|---|---|---|
| 信息架构与 brief | 本地：形成主题判断、8–15 个信息块、source coverage、画幅和负向约束 | 本地：同左 |
| image / HTML canvas | handoff：Open Design agent / App 以选定模板和设计系统生成或编辑 canonical visual 项目 | 本地：读取 template 规则后生成 HTML/CSS visual，并以 Chromium 预览验证 |
| 静态交付 | 从实际项目预览或导出物检查文字、裁切、乱码、尺寸和文件格式 | 截图为 PNG，检查同左 |
| 动效交付（需要时） | 使用 HyperFrames HTML renderer 生成 MP4，并按 ops SKILL.md 等待任务、检查文件与可播放性 | 不伪造 Open Design MP4；改用本地能力时明确是本地路径 |

HTML/canvas 项目是视觉真相源。HTML、PDF、PPTX、MP4 的可用导出入口、格式语义和验收步骤以 ops SKILL.md 为准；尤其不要把截图式或位图导出说成可编辑交付。

## 验收与回执

- 记录输入类型、信息架构、模板/设计系统、prompt 路径与 handoff/local 边界。
- 验收静态图存在、尺寸正确、文字无明显重叠/截断/乱码，且抽查目标尺寸下可读。
- 若使用 HyperFrames，验证 MP4 存在、MIME、时长与可播放性。
- 若 Open Design handoff 未获可验证产物，报告失败/待修，不降级声称完成。
- 继续已有设计时由 Open Design daemon 的 native resume 处理；检查实际 conversation/run 与 touched files，不能把重建会话称为 resume。
