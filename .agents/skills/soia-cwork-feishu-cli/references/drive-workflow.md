# 云盘 / Drive 工作流

本文件只处理飞书云盘、个人文件夹、共享文件夹、Drive 文件和文件元数据。知识空间和 Wiki 节点请改读 [`wiki-workflow.md`](wiki-workflow.md)。

## 1. 先选择身份

| 身份 | 凭证 | 开放平台页签 | 可见范围 | 适用场景 |
|---|---|---|---|---|
| 应用身份 | `tenant_access_token` | 应用身份权限 | 应用拥有或被授权的共享资源 | Bot 盘点共享文件夹和应用可见文档，默认模式 |
| 用户身份 | `user_access_token` | 用户身份权限 | 当前登录用户本人可访问的个人和共享资源 | “我的云盘”“我的文件夹”、个人文档 |

应用身份和用户身份是两条独立链路。Bot 的 Drive 搜索为空，不等于用户个人云盘为空。

## 2. 最小只读权限

### 云盘清单、搜索和元数据

按身份在对应页签申请：

- `drive:drive.search:readonly`：搜索当前身份可见的云盘资源。
- `drive:drive:readonly`：读取当前身份可见的云盘资源。
- `drive:drive.metadata:readonly`：读取根目录、文件夹和文件的名称、类型、Token、所有者等元数据。

对于 Bot，`drive:drive.metadata:readonly` 可先作为条件权限，只有 CLI 明确返回 `missing_scopes` 时再补。对于用户 OAuth 读取个人云盘根目录，建议直接申请该元数据只读权限。

### 按需追加

- `drive:file:download`：明确需要下载普通文件时申请。
- `drive:export:readonly`：明确需要导出在线文档时申请。
- `docs:document.media:download`：明确需要下载文档图片或附件时申请。

不要默认申请 `drive:drive`、上传、移动、删除、成员管理或权限修改权限。若 CLI 明确返回全量 `drive:drive` 缺失，先确认具体命令和风险，再按错误要求处理。

## 3. Bot 模式

前置条件：

1. 在“应用身份权限”页签申请最小 Drive scope。
2. 需审核权限创建版本、提交线上发布并等待企业管理员审核。
3. 文件夹或文档所有者把应用加入目标资源；应用数据权限和资源可见范围也要满足要求。

验证命令：

```bash
lark-cli drive +search \
  --as bot \
  --query '' \
  --doc-types doc,docx,sheet,bitable,file,folder,wiki,slides \
  --format json

lark-cli drive +inspect --as bot --url '<FEISHU_URL>' --format json
```

Bot 不能自动代表用户访问“我的文件夹”。不要因为搜索结果为 0 就创建文件夹或修改权限。

## 4. 用户 OAuth 模式

用户明确要求个人云盘时，在“用户身份权限”页签申请：

```text
drive:drive.search:readonly
drive:drive:readonly
drive:drive.metadata:readonly
```

然后通过 OAuth 登录当前用户：

```bash
mkdir -p "${TMPDIR:-/tmp}/soia-cwork-feishu-cli"
lark-cli auth login \
  --scope "drive:drive.search:readonly drive:drive:readonly drive:drive.metadata:readonly" \
  --no-wait --json
lark-cli auth qrcode '<verification_url>' --output "${TMPDIR:-/tmp}/soia-cwork-feishu-cli/feishu-user-oauth.png"
```

用户确认完成后，由 agent 执行 `--device-code` 完成绑定，并检查 `auth status` 的 `user` 身份：

```bash
lark-cli auth status --json --verify
lark-cli drive +search \
  --as user \
  --query '' \
  --doc-types doc,docx,sheet,bitable,file,folder,wiki,slides \
  --format json

lark-cli drive +inspect --as user --url '<FEISHU_URL>' --format json
```

如果授权页显示“已提交申请，正在审核中”，说明应用的用户身份权限或应用版本还没有正式生效；这不是用户已经完成 OAuth 的证明。

`accounts.feishu.cn/oauth/v1/device/verify` 是 lark-cli 的 device flow 验证入口。若它跳转到 `open.feishu.cn/page/scope-authorization`，应先处理应用用户身份权限和版本审核，再重新发起 OAuth；不要把该页面当作个人云盘登录成功。官方“获取用户信息”接口是 OAuth 完成后的后置 API，需要 `user_access_token`，不能代替登录。

## 5. 内容类型分流

- 文件夹、文件列表和元数据：`lark-drive`。
- 文档正文：在身份确定后切换到 `lark-doc`，保持相同的 `--as bot|user`。
- 表格单元格：切换到 `lark-sheets`。
- 多维表记录：切换到 `lark-base`。
- Wiki URL：先用 `drive +inspect` 解包，再按底层类型处理；Wiki 树形结构本身走 `lark-wiki`。

## 6. 安全边界

- 个人云盘内容属于用户数据；读取、下载和导出前要明确目标范围。
- 不读取浏览器 Cookie、密码、浏览器 profile 或 keychain 原始内容。
- 不把授权链接、device code、access token 或 refresh token 写入仓库、日志或文档。
