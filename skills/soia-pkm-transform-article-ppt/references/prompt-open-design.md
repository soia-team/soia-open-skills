# Open Design Prompt

先读取 [provider-open-design.md](provider-open-design.md)，再把内容合同和 slide plan 交给 Open Design。

```text
请基于以下 source coverage 和 slide plan 生成 16:9 中文 PPT。

模式：{handoff | template_guided_local_render}
受众：{audience}
用途：{job_to_be_done}
主判断：{main_verdict}
页数：{slide_count}
模板/设计系统：{template_or_design_system}

要求：
1. 正式母版以可编辑 PPTX 为目标；若只能截图式导出，标记 flattened。
2. 保留每页 source anchor 和页面任务，不能把内容改写成低密度摘要卡。
3. 视觉素材沿用 asset plan；中文、数字、表格和来源保持可编辑。
4. 至少四种页面轮廓，页面主判断和阅读顺序清楚。
5. 来源页不出现模型名、运行 id、下载路径和占位符。
6. 导出后运行 HTML/PPTX fidelity audit，并渲染全部页面复核。
```

