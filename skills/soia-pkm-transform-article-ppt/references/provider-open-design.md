# Open Design Provider

`provider=open_design` 适用于已有 Open Design 环境、模板或设计系统的 PPT。该路径硬依赖 `soia-dev-open-design-ops`；环境、daemon、模板查询和导出命令以其 `SKILL.md` 为单一真源。

## 模式

1. `handoff`：把内容合同、slide plan、素材和 prompt 交给 Open Design agent/App。
2. `template_guided_local_render`：读取模板规则后，由当前 agent 本地生成 HTML/PPTX。

回执必须写明实际模式。只参考模板不等于 Open Design 已生成。

## 调用前检查

```bash
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/check_env.py
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/daemon_ctl.py health
python3 ~/.agents/skills/soia-dev-open-design-ops/scripts/list_skills.py --category slides
```

真实 MCP 配置修改和 provider 安装遵守 ops skill 的确认门。环境检查失败时停止该路径，不静默冒充 Open Design。

## PPT 主链

```text
内容合同 -> slide plan -> 模板选择 -> canonical HTML/deck -> PPTX -> fidelity audit -> 全量渲染
```

如果导出结果是截图式 PPTX，明确标记 `flattened`；只有经过 `pptx-generator` 或等价可编辑导出的结果才能作为正式可编辑母版。

## 验收

- 记录模板、模式、项目/会话和最终产物。
- fidelity audit 与最终 PPTX 对应，不能拿旧报告充数。
- 最终文件仍需通过本技能的机械门和人工门。

