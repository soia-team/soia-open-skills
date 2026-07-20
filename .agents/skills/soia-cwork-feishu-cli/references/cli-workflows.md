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

### 首次初始化与 profile 刷新

应用凭证从技能专属私有配置读取，Secret 通过 stdin 交给 CLI。首次初始化：

```bash
python3 <skill-path>/scripts/setup_app_credentials.py --use
```

已有 profile 需要更换 App ID、App Secret 或 brand 时，只有在用户明确要求刷新时才执行：

```bash
python3 <skill-path>/scripts/setup_app_credentials.py --replace --use
```

由于 lark-cli 不允许同一个 App ID 同时存在于两个 profile，脚本会先删除旧 profile，再写入新 profile；因此只在私有配置确认无误、且用户明确要求时执行。若写入失败，检查私有配置后重新运行初始化。刷新后验证：

```bash
lark-cli profile list
lark-cli auth status --json --verify
lark-cli whoami
lark-cli doctor
```

遇到错误码 `20140` / `invalid_client` / `The auth method is not supported.` 时，先按 [`errors.yml`](errors.yml) 处理凭证和 profile，不要执行 `auth login`，也不要先申请更多 scope。

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

## 知识库 / Wiki 盘点

知识库和云盘是两条独立工作流。知识库树形结构、空间和节点使用 `lark-wiki`；云盘文件夹和文件使用下一节的 `lark-drive`。

### Bot（应用身份）

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

### User（用户 OAuth）

只有用户明确要求个人知识库或 Bot 不可见的私有知识库时才使用。先在“用户身份权限”页签申请最小 Wiki/文档只读 scope，再通过 `lark-cli auth login` 完成 OAuth。用户授权完成后使用：

```bash
lark-cli wiki +space-list --as user --page-all --format json
lark-cli wiki +node-list \
  --as user \
  --space-id '<SPACE_ID>' \
  --page-all \
  --format json
```

如果 device flow 页面跳转到 `open.feishu.cn/page/scope-authorization` 并显示“审核中”，说明应用权限/版本审核尚未完成；此时 `auth status` 仍会显示 `user: missing`，不能当作 OAuth 成功。

## 云盘 / Drive 搜索

### Bot（应用身份）

按类型、关键词或空间搜索：

```bash
lark-cli drive +search \
  --as bot \
  --query '' \
  --doc-types doc,docx,sheet,bitable,file,folder,wiki,slides \
  --format json
```

Bot 只能看到应用拥有、被授权或租户策略允许访问的文件夹和文档；它不能自动看到用户个人云盘。

### User（用户 OAuth）

个人云盘需要在“用户身份权限”页签申请：

```text
drive:drive.search:readonly
drive:drive:readonly
drive:drive.metadata:readonly
```

OAuth 完成后，将相同的只读命令切换为 `--as user`：

```bash
lark-cli drive +search \
  --as user \
  --query '' \
  --doc-types doc,docx,sheet,bitable,file,folder,wiki,slides \
  --format json
```

`lark-cli auth login` 是 CLI 的用户 OAuth/device flow；官方 `login-state-management/get` 文档对应的是拿到 `user_access_token` 后查询当前用户信息的 API，不是另一条 CLI 登录命令。

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

`drive +inspect` 必须与前面选择的身份保持一致；Wiki URL 解包后，正文读取再路由到 `lark-doc`。

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
