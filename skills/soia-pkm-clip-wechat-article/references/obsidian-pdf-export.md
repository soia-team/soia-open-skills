# Obsidian 原生 PDF 导出

当用户说「归档并转 PDF」「归档并导出 PDF」「archive and export PDF」时，先完成 clip 归档和元数据补全，再执行本流程。

## 何时使用

- 目标 Markdown 已落在 Obsidian vault 内（能从当前目录向上找到 `.obsidian` 或 `AGENTS.md`，或用户/脚本已明确传入 `--vault`）。
- 本机安装了 Obsidian，或 Obsidian 已在运行。
- 用户要的是 Obsidian 笔记视图的 PDF，而不是另做一份排版稿。

## 优先路径

1. 打开最终 Markdown 笔记，而不是临时文件。若可以用 URI，优先打开：
   `obsidian://open?vault=<vault-name>&file=<vault-relative-urlencoded-path>`。
   `vault-name` 通常是 vault 目录名；不确定时，激活当前已打开的 Obsidian vault 后用快速切换或文件树打开该笔记。
2. 调用 Obsidian 自带导出：菜单 `File` / `文件` → `导出 PDF`。自动化时可用系统 UI（macOS `osascript` / System Events）点击这个菜单项；不要优先调用 pandoc、wkhtmltopdf、Chromium 手写 HTML 导出。
3. 输出位置优先选最终 Markdown 同目录，文件名同 stem、扩展名 `.pdf`。如果 Obsidian 默认先写到 Desktop/Downloads，把生成的 PDF 移回 Markdown 同目录。
4. 保持 Markdown 原样。不要为了 PDF 临时删除「我的看法」「关联」等模板段；若 vault 已有 print CSS（如隐藏来源信息/占位块），交给 Obsidian 当前配置处理。

## 验收

- `pdfinfo <pdf>`：页数大于 0，文件非空；Obsidian 导出的 PDF 通常显示 `Creator: Chromium` 或 `Producer: Skia/PDF`。
- `pdftoppm -png -f 1 -l 1 <pdf> <prefix>`，必要时再渲染最后一页；必须目视确认中文正常、没有乱码/方块、图片可见、没有明显空白尾页或重叠。
- `pdftotext` 只作辅助检查。PDF 文本层可能把中英文断行拆开，不能代替视觉验收。

## 降级

只有在 Obsidian 不可用、UI 自动化被阻止、或用户明确接受非 Obsidian 导出时，才使用 pandoc/wkhtmltopdf/其他 PDF 引擎。降级时在回执中明确说明「未走 Obsidian 原生导出」以及原因。
