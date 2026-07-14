# 飞书 CLI 工作流

本参考只记录本技能的“读取和调研”路径。命令、scope、参数和权限错误以当前安装的 CLI 内嵌技能为准；开始前运行 `lark-cli skills read <skill-name>`，不要凭记忆猜 API 参数。

## 安装与健康检查

```bash
npx @larksuite/cli@latest install
npx skills add larksuite/cli -g -y
lark-cli doctor
lark-cli profile list
lark-cli auth status --json --verify
lark-cli whoami
```

应用凭证模式使用 `profile add`，不使用用户 OAuth：

```bash
printf '%s' '<YOUR_APP_SECRET>' | lark-cli profile add \
  --name <profile-name> \
  --app-id '<YOUR_APP_ID>' \
  --app-secret-stdin \
  --brand feishu
```

如果使用本技能配置脚本，凭证从私有 `config.yml` 读取并通过 stdin 传给 CLI；不要把 Secret 放在 argv。

## 读取官方操作说明

```bash
lark-cli skills read lark-shared
lark-cli skills read lark-drive
lark-cli skills read lark-wiki
lark-cli skills read lark-doc
```

正文读取前再读匹配的参考文件：

```bash
lark-cli skills read lark-doc references/lark-doc-fetch.md
```

## 知识库盘点

先列出 bot 可见的知识空间：

```bash
lark-cli wiki +space-list \
  --as bot \
  --page-all \
  --format json
```

再按返回的真实 `space_id` 列根节点：

```bash
lark-cli wiki +node-list \
  --as bot \
  --space-id '<SPACE_ID>' \
  --page-all \
  --format json
```

深入某个节点时使用返回的 `node_token`：

```bash
lark-cli wiki +node-list \
  --as bot \
  --space-id '<SPACE_ID>' \
  --parent-node-token '<NODE_TOKEN>' \
  --page-all \
  --format json
```

`my_library` 是用户个人文档库别名，只能用 user 身份；应用凭证 bot 不可见属于正常权限边界，不要静默切换身份。

## 云盘和文档搜索

按类型、关键词或空间搜索：

```bash
lark-cli drive +search \
  --as bot \
  --query '' \
  --doc-types doc,docx,sheet,bitable,file,folder,wiki,slides \
  --format json
```

按标题搜索并限制类型：

```bash
lark-cli drive +search \
  --as bot \
  --query '<关键词>' \
  --only-title \
  --doc-types docx,wiki,sheet \
  --format json
```

搜索是分页 API。只把 `has_more=false` 的完整分页结果当作全量；若为了控制规模设置了 `--page-size` 或没有继续传 `page_token`，必须标记为抽样。

## 解析 URL、读取正文和元数据

不要把 Wiki token 直接当文档 token：

```bash
lark-cli drive +inspect \
  --as bot \
  --url '<FEISHU_URL>' \
  --format json
```

读取文档大纲：

```bash
lark-cli docs +fetch \
  --as bot \
  --doc '<FEISHU_URL_OR_TOKEN>' \
  --scope outline \
  --doc-format markdown \
  --format json
```

读取全文：

```bash
lark-cli docs +fetch \
  --as bot \
  --doc '<FEISHU_URL_OR_TOKEN>' \
  --scope full \
  --doc-format markdown \
  --format json
```

大文档优先读 `outline`，再按章节或关键词读取；不要一次把全量知识库正文加载进上下文。

## 权限和评论：只读检查

权限、评论和访问记录属于敏感元数据。用户要求调研时只读取，不修改：

```bash
lark-cli drive +list-comments --as bot --url '<FEISHU_URL>' --format json
lark-cli drive permission.public get --as bot --params '{"token":"<TOKEN>","type":"docx"}' --format json
```

调用原生 API 前，必须先看 schema：

```bash
lark-cli schema drive.permission.public.get --format json
```

如果命令的参数或权限仍有歧义，停下来读取对应官方 skill 或错误中的官方控制台链接，不要试错写入。

## 应用身份的关键限制

- bot 不能自动读取用户的个人日历、私信、个人云盘、个人文档库。
- bot 只能看到应用自己拥有、被授予应用访问权、或租户策略允许应用访问的资源。
- 需要调研用户个人资源时，应由用户把应用加入对应知识空间/文档，或明确授权用户 OAuth；本技能默认不切换到 OAuth。
- 研究报告必须单列“已读取范围”和“不可见范围”，避免把 bot 视角误报成用户全量使用情况。
