# Office Quality Gates

## 通用门槛

1. 输出存在、非空，扩展名与输入格式一致。
2. 修改目标读回与计划一致；未命中的 find/selector 视为失败，不算“无变化成功”。
3. `officecli validate <file> --json` 无 schema error。
4. `officecli view <file> issues --json` 的 error 已清零，warning 已处理或解释。
5. 版式敏感任务必须渲染全部受影响页面并人工查看。
6. 交给 OfficeCLI 之外的程序前执行 `close`，避免 resident 中的未落盘内容造成假阴性。

## DOCX

- 核对标题层级、分页、页眉页脚、表格宽度、列表编号、脚注/尾注和修订状态。
- 检查字体回退、孤行、表格跨页、图片裁切和空白页。
- 涉及 tracked changes 时，分别确认修订仍保留还是已接受/拒绝，不能只看最终文本。

## XLSX

- 核对公式文本、引用范围、命名区域、数据类型、日期/金额格式和错误值。
- schema 通过不代表计算正确；关键总计必须独立重算或与源数据抽样比对。
- 图表、透视表、条件格式和冻结窗格需要打开或渲染检查。

## PPTX

- 核对页数、画幅、标题、主要文本、备注、动画/转场和资源关系。
- 全量渲染，检查空白页、越界、重叠、乱码、低清图片、裁切和页码。
- Open Design 的截图型 PPTX 要明确标注不可编辑性；可编辑 deck 要抽查文本和关键 shape 能否独立选中修改。

## 交付措辞

- 只跑 `validate`：写“schema 校验通过”。
- 同时跑 issues：写“结构与静态问题检查通过”。
- 渲染并人工逐页查看：才写“视觉 QA 通过”。
- 在 Microsoft Office/PowerPoint/Excel/Word 中实际打开：才写“Office 实机兼容性已检查”。
