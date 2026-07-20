# Open Design Provider

适用：高质量 PPT / HTML deck、数据叙事、课程模块、技术分享与视觉探索。

`provider=open-design` 的执行依赖 `soia-dev-open-design-ops` 原子层；它不是 `local` 或 `notebooklm` 路径的依赖。未安装或原子层检查失败时，停止 Open Design 路径，返回安装/修复建议，不把本地结果称为 Open Design 交付。

环境、daemon 端口、启动命令、状态文件和 Open Design 上游版本等事实只在 `soia-dev-open-design-ops/SKILL.md` 维护；本文件只规定 slides 对它的调用与交付链。

## 使用模式

回执必须写明采用的模式：

1. **Open Design handoff**：将已落盘的 brief、内容提纲和素材交给 Open Design agent / App，由其按选定 deck 模板生成或继续编辑设计产物。
2. **Template-guided local render**：查询 Open Design 的 template 规则后，由当前 agent 在本地生成 HTML/CSS/PPTX，并用 Playwright managed Chromium 验证。这是模板指导的本地生成，不得声称 Open Design agent 已生成。

两种模式都先保留 source coverage、叙事结构、模板映射和 prompt；不能只输出低信息量 bullet deck。

## MCP dry-run 纪律

MCP 安装会改写用户的 agent 配置，必须先 dry-run：

```bash
od mcp install codex --print
od mcp install claude --print
od mcp install antigravity --print
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
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/list_skills.py --category slides
```

在 `soia-open-skills` 仓库根目录开发时，可用对应相对路径：

```bash
python3 skills/soia-dev-open-design-ops/scripts/check_env.py
python3 skills/soia-dev-open-design-ops/scripts/daemon_ctl.py status
python3 skills/soia-dev-open-design-ops/scripts/daemon_ctl.py health
python3 skills/soia-dev-open-design-ops/scripts/list_skills.py --category slides
```

`check_env.py` 必须返回 `status=ok`；`health` 以 `/api/skills` 返回数组为证据，不能仅以进程或 `/api/health` 存活替代。`list_skills.py` 查询的是 functional skills，不代表 rendering templates；模板通过 Open Design App 的 “Start from” 或 `GET /api/design-templates` 查询。环境缺口、daemon 启动、端口覆盖和安全边界均回到 ops 的 SKILL.md，不在这里复制。

## PPT 主链

输入完成结构化后，主链固定为：

```text
大纲 → deck 模板选型 → pptx-generator → pptx-html-fidelity-audit → PPTX 交付
```

模板选型先在三个风格系中择一，并将理由写入 prompt：

| 风格系 | 适用叙事 |
|---|---|
| `deck-guizang-editorial` | 观点、媒体感长文、文化或高情绪张力主题 |
| `deck-open-slide-canvas` | 关系图、流程、系统结构与自由编排内容 |
| `deck-swiss-international` | 数据、研究、技术与克制的信息层级 |

| 主链步骤 | Open Design handoff | Template-guided local render |
|---|---|---|
| 大纲 | 本地：按输入类型形成可确认的叙事、source coverage 与逐页要点 | 本地：同左 |
| deck 模板选型与 HTML deck | handoff：Open Design agent / App 以选定风格系生成或编辑 canonical HTML deck | 本地：读取 template 规则后生成 HTML/CSS deck，并以 Chromium 预览验证 |
| `pptx-generator` | handoff：由 Open Design agent 调该 functional skill，生成可编辑 `.pptx` | 本地：调用该 functional skill，从 HTML 视觉真相源生成可编辑 `.pptx` |
| `pptx-html-fidelity-audit` | handoff：由 Open Design agent 调审计 skill，修正 footer overflow、裁切、字体/italic 与节奏漂移 | 本地：调用该审计 skill并修正 HTML/PPTX 差异 |
| PPTX 交付 | 本地：打开最终文件，核页数、画幅、关键文本与无越界，再交付 | 本地：同左 |

HTML deck 是视觉真相源。若目标是像素保真而不是可编辑 PPTX，可按 ops SKILL.md 的 Open Design 导出流程导出截图式 `.pptx`，并在回执明确其不可编辑语义；不得把它混同于 `pptx-generator` 产物。

## 验收与回执

- 记录输入类型、内容结构化结果、模式、模板风格系、prompt 路径与 handoff/local 边界。
- 验收最终 PPTX 可打开、页数和画幅正确、无空白页、关键文本无越界，并保存 fidelity audit 结果。
- 若 Open Design handoff 未获可验证产物或 audit 未通过，报告失败/待修，不降级声称完成。
- 继续已有设计时由 Open Design daemon 的 native resume 处理；检查实际 conversation/run 与 touched files，不能把重建会话称为 resume。
