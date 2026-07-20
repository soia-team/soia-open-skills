# 知识库 / Wiki 工作流

本文件只处理飞书知识库、知识空间、Wiki 节点和 Wiki 文档。云盘目录、个人文件夹和 Drive 文件请改读 [`drive-workflow.md`](drive-workflow.md)。

## 1. 先选择身份

| 身份 | 凭证 | 开放平台页签 | 可见范围 | 适用场景 |
|---|---|---|---|---|
| 应用身份 | `tenant_access_token` | 应用身份权限 | 应用拥有、被授权或租户策略允许访问的知识空间 | 企业知识库 Bot 盘点，默认模式 |
| 用户身份 | `user_access_token` | 用户身份权限 | 当前登录用户本人可访问的知识空间和节点 | 个人知识库、`my_library`、Bot 不可见的私有库 |

同一个 Wiki API 如果要同时支持两种身份，需要在两个页签分别申请对应的只读权限。开通用户身份权限不会让 Bot 获得用户资源，反之亦然。

## 2. 最小只读权限

在开放平台“权限管理”中按实际身份选择以下权限：

- `wiki:wiki:readonly`：读取知识库相关资源。
- `wiki:space:read`：读取知识空间。
- `wiki:space:retrieve`：获取知识空间详情。
- `wiki:node:read`：读取知识库节点。
- `wiki:node:retrieve`：获取节点详情。
- `docs:doc:readonly`：读取旧版文档。
- `docx:document:readonly`：读取新版文档。
- `docs:document.content:read`：读取文档正文内容。

如果只需要列知识空间和树形节点，可以先申请前五项；只有需要读取正文时再补文档只读权限。具体缺失 scope 以 CLI 返回的 `missing_scopes` 为准。

## 3. Bot 模式

前置条件：

1. 在“应用身份权限”页签开通最小 scope。
2. 需审核权限创建版本、提交线上发布并等待企业管理员审核。
3. 知识库管理员把应用加入目标知识空间或节点的可访问成员/管理员范围。

验证命令：

```bash
lark-cli wiki +space-list --as bot --page-all --format json
lark-cli wiki +node-list --as bot --space-id '<SPACE_ID>' --page-all --format json
lark-cli docs +fetch --as bot --doc '<WIKI_URL_OR_TOKEN>' --scope outline --doc-format markdown --format json
```

`space-list` 返回的只是 Bot 可见空间，不代表企业中所有知识库。空结果不能证明用户没有知识库。

## 4. 用户 OAuth 模式

仅在用户明确要求访问个人知识库或 Bot 不可见的私有知识库时使用。前置条件：

1. 在“用户身份权限”页签开通目标 scope。
2. 若权限处于“审核中”，先完成应用版本发布和企业管理员审核。
3. 由用户在 OAuth 页面登录自己的飞书账号并同意授权。

推荐使用最小 scope 的 split-flow：

```bash
mkdir -p "${TMPDIR:-/tmp}/soia-cwork-feishu-cli"
lark-cli auth login --scope "<minimal-user-scopes>" --no-wait --json
lark-cli auth qrcode '<verification_url>' --output "${TMPDIR:-/tmp}/soia-cwork-feishu-cli/feishu-user-oauth.png"
```

用户确认授权完成后，由 agent 执行 `lark-cli auth login --device-code <device_code>`，然后验证：

```bash
lark-cli auth status --json --verify
lark-cli wiki +space-list --as user --page-all --format json
lark-cli wiki +node-list --as user --space-id '<SPACE_ID>' --page-all --format json
```

不要读取浏览器 Cookie、密码或浏览器 profile；不要把 `device_code`、access token 或 refresh token 写入日志、聊天或仓库。

注意：`accounts.feishu.cn/oauth/v1/device/verify` 是 CLI device flow 的验证入口，不是 Bot 登录入口；但如果它跳转到 `open.feishu.cn/page/scope-authorization` 并显示“已提交申请，正在审核中”，说明应用的用户身份权限或应用版本还没有生效，不能把这次流程记为 OAuth 成功。`login-state-management/get` 对应的是登录后的 `user_info` API，不负责发起登录。

## 5. 资源边界和失败分类

- 缺少 scope：按 CLI 错误中的 `console_url` 在正确的身份页签申请，并发布应用版本。
- Bot 看不到目标知识库：检查知识库设置中的成员/管理员授权，不能只补 scope。
- User 看不到目标知识库：检查当前用户在飞书页面中的成员权限；OAuth 不会提升用户自身权限。
- `my_library` 或个人知识库：只能用 user 身份验证，不能用 Bot 空结果推断不存在。
