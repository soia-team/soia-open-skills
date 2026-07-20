# ProcessOn 能力与格式

> 核对日期：2026-07-20。ProcessOn 迭代较快，执行时以当前官方帮助页和账号实际菜单为准。

## 官方能力结论

### 普通账号与团队空间

- 团队空间用于按部门/业务/项目归集文件；成员只能看到自己被加入空间中的内容。
- 文件列表的右键或三点菜单提供“浏览”和“下载”。
- 公开分享链接会改变文件的可见范围，不属于默认只读流程。

官方说明：

- [团队空间](https://www.processon.com/support/question/63736b71b07e9b189e3319f6)
- [文件预览](https://www.processon.com/support/file-view)
- [如何导出文件](https://www.processon.com/support/question/5229b3240cf204f505bc6a01)

### 导出格式

| 图表类型 | 官方列出的格式 | 备注 |
|---|---|---|
| 流程图 | PNG、高清 PNG、JPG、SVG、高清 PDF、POS | 部分高清格式需要会员；产品页还会展示 Visio 能力，以实际菜单为准 |
| 思维导图 | Word、PPT、Excel、PNG、高清 PNG、JPG、SVG、高清 PDF、POS、FreeMind、XMind | 部分格式需要会员 |

官方说明：

- [流程图下载](https://www.processon.com/support/flow-2-5)
- [思维导图下载](https://www.processon.com/support/mind-2-5)
- [文件导入](https://www.processon.com/support/file-import)

### POS 格式

ProcessOn 将 POS 描述为开放格式，可下载到本地并重新导入编辑。实际导出的 POS 是 JSON：

- `meta.diagramInfo` 常见字段：标题、category、创建/修改时间。
- 流程图通常在 `diagram.elements.elements` 中保存图形和 `textBlock`。
- 思维导图通常在 `diagram.elements` 中保存根标题和递归 `children`。

不要依赖未公开的内部下载 URL。通过官方 UI 获取 POS，再用本技能脚本只读解析。

## API 边界

ProcessOn 官方 [API 服务平台](https://www.processon.com/toolservice) 面向企业嵌入与格式转换，提供 JS-SDK、在线编辑/预览和转换能力，需要注册认证、体验凭证与正式权益。当前官方公开页面没有提供普通账号“列出个人/团队文件并批量下载”的公共 REST API 文档。

因此：

1. 普通账号默认使用浏览器登录态和官方 UI。
2. 企业已经购买 API 服务时，客户需提供官方开发文档、允许调用的环境和凭证变量名；凭据仍放客户自己的秘密存储。
3. 不使用逆向 Cookie、内部接口或猜测 URL 代替官方能力。

## 浏览器执行提示

1. 优先复用客户已经登录的浏览器。
2. 先读最新 DOM/可访问性快照，再根据真实标签定位：
   - `团队空间`
   - `搜索文件/文件夹/团队空间`
   - 文件卡片标题
   - 右键菜单中的 `浏览`、`下载`
3. ProcessOn 可能显示滑块安全验证。停止并请客户手动完成；不要绕过。
4. 目录盘点可以读取卡片缩略图 URL，但缩略图只用于预览，不等价于高清导出。
5. 下载必须等待浏览器真实 download 事件并检查本地文件。

## 格式选择建议

| 目标 | 首选 | 备选 |
|---|---|---|
| 长期可编辑备份 | POS | XMind（仅思维导图） |
| AI 提取文字/结构 | POS | XMind、SVG |
| 简历/PPT 插图 | SVG、高清 PNG | PDF |
| 审阅与打印 | 高清 PDF | PNG |
| Office 二次加工 | PPT/Word/Excel（思维导图） | SVG/PNG |
