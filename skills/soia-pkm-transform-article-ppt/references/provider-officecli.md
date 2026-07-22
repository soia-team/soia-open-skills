# OfficeCLI Execution Layer

OfficeCLI 是生成后的 Office 文件操作与复验层，不是 deck 视觉设计 provider。

## 适用场景

- 已有 PPTX，需要读取页、shape、文本、备注、动画或资源关系。
- 需要用 `@id`/`@name` 稳定定位，做小范围精确修改。
- 有 3 项以上变更，希望用原子 batch 防止半完成文件。
- 需要 OpenXML schema、静态 issues、HTML 或截图证据。
- Open Design 或宿主 presentations 已生成 PPTX，需要第二条实现路径复验。

## 不适用场景

- 从文章直接决定整套叙事和视觉方向。
- 用大量低级 shape 命令替代宿主 presentations 或 Open Design 的设计能力。
- 只因 OfficeCLI 能创建 PPTX，就绕过当前宿主明确要求的 runtime。

## 调用顺序

1. 先由 `local_editable` 或 `open_design` 生成母版。
2. 调 `soia-dev-officecli-ops` 做只读 `outline/stats/issues/get/query/validate`。
3. 需要修复时先展示目标路径和修改计划，在副本上执行。
4. 三项以上修改使用原子 batch。
5. 重新跑本技能的 `media_bundle.py validate`，并全量渲染、人工逐页复核。

## 编辑性边界

OfficeCLI 能修改 OOXML 不代表上游 deck 本身可编辑。Open Design 的像素保真 PPTX 或 NotebookLM PPTX 仍可能是一页一张图；必须抽查 shape/text 结构并在回执中如实说明。
