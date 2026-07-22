# Examples

## 1. 可编辑课件

```text
把 <article.md> 做成给小白讲的 16 页 PPTX，后面还要修改。
```

路由：`local_editable`。先做内容合同和 slide plan，再生成 2-3 张无字视觉素材，最后用宿主演示文稿能力生成可编辑 PPTX、全量预览和 montage。

## 2. NotebookLM 视觉版

```text
用 NotebookLM 把 <article.md> 做成中文课件。
```

路由：`notebooklm`。认证健康检查后生成；按本次 artifact id 下载 PPTX；全量渲染；来源页不得出现 notebook/source/artifact id 和下载路径；回执说明编辑性。

## 3. 两版对比

```text
这篇文章本地做一版，NotebookLM 再做一版，我要比较哪个好。
```

路由：`hybrid`。本地可编辑版是正式母版，NotebookLM 是视觉对照版。两版共用同一个 `main_verdict` 和 source coverage，但 prompt 分开。分别生成 preview/montage 和验证结果。

比较时至少说明：

- 内容覆盖与事实可靠性。
- 视觉焦点和叙事节奏。
- 中文可读性。
- 编辑性和后续维护成本。
- 生成时间与 provider 依赖。

## 4. PPT 加重点简图

```text
把 <article.md> 做成 PPT，同时做一张 1080x1600 的重点简图。
```

路由：`local_editable` + infographic。PPT 保留完整内容，简图只承担一个 `map` 或 `flow` 任务。imagegen 先做无字主视觉，HTML/CSS 再排中文。

## 5. 旧 `.ppt` 兼容

```text
公司电脑只能打开旧版 .ppt，请同时给 PPTX 和 PPT。
```

先生成并验收 `.pptx`，再用可用的 PowerPoint/LibreOffice 转为 `.ppt`。重新打开和渲染 `.ppt` 检查字体、图片和版式漂移。没有转换器时只交 PPTX 并说明缺口，不重命名扩展名。

## 6. 不合格模式

- 6 页以内泛泛摘要，每页一个标题加三条 bullet。
- 为了“好看”生成多张无用途插画，却没有完整术语和 source 地图。
- NotebookLM 来源页出现 `[ARTIFACT_ID_PLACEHOLDER]` 或内部下载路径。
- `.pptx` 每页只有一张图，却声称内容可编辑。
- 信息图方向与文章逻辑相反，或中文由图片模型直接生成而出现错字。
- 文件生成后没有渲染预览，只检查文件存在。

