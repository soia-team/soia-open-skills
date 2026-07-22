# Media Bundle Contract

本技能把输出组织成一个媒体包。路径可由用户覆盖；默认使用 source 文件名作为 `<stem>`。

```text
<output-dir>/
├── <stem>-editable.pptx
├── <stem>-notebooklm.pptx          # provider=notebooklm/hybrid 时
├── <stem>-infographic.png          # 请求信息图时
├── assets/
│   └── imagegen/
├── prompts/
│   ├── ppt-local.txt
│   ├── image-01.txt
│   └── ppt-notebooklm.txt          # 使用 NotebookLM 时
├── previews/
│   ├── editable/slide-*.png
│   └── notebooklm/slide-*.png      # 使用 NotebookLM 时
├── qa/
│   ├── editable-montage.png
│   └── notebooklm-montage.png      # 使用 NotebookLM 时
├── media-manifest.json
└── media-validation.json
```

`media-manifest.json` 是该媒体包的单一清单，至少包含：

- source 路径、标题、作者、URL、发布时间、章节和概念。
- `main_verdict`、受众、provider、页数和图片数量。
- 每个预期产物的路径、是否必需、编辑性语义。
- 规划时间。时间由运行环境实际读取，不手写未来时间。

manifest 不存账号、cookie、token、NotebookLM 下载 URL、用户邮箱或模型身份。Notebook/source/artifact id 仅在确有调试需要时写入用户私有运行日志，不进入幻灯片。

## 命名语义

- `editable`：以可编辑文本、形状、表格和连接线为主。插画可以是位图。
- `notebooklm`：NotebookLM 原生视觉结果。默认按 flattened/image-only 理解，除非检查证实可编辑。
- `infographic`：完成中文排版后的最终图，不是 imagegen 原始素材。
- `assets/imagegen`：无密集文字的视觉部件，不能直接冒充完整信息图。

## Prompt 落盘

每个真正调用的生成路径都要保存 prompt。未调用的 provider 不创建空 prompt。prompt 中不得放登录凭据；包含敏感 source 时由用户决定输出目录是否进入版本控制。

