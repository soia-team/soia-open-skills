# 飞书应用权限开通清单

本清单服务于 `soia-cwork-feishu-cli` 的应用凭证（bot）模式。按客户目标选择最小权限，不因为客户已有一份很大的权限列表就默认申请全部权限。

## 1. 安装、创建应用、配置凭证

完整链路是：安装 Feishu CLI → 在飞书开放平台创建自建应用 → 添加机器人能力 → 获取 App ID / App Secret → 开通 tenant 权限 → 发布应用版本 → 用 `lark-cli` 验证。

参考入口：

- [Feishu CLI 安装与配置指南](https://feishu-cli.com/zh/feishu-cli-installation-guide.html)
- [lark-cli 官方 README：认证](https://github.com/larksuite/cli/blob/main/README.zh.md#认证)
- [飞书开放平台](https://open.feishu.cn/app)
- [自建应用开发流程](https://open.feishu.cn/document/home/introduction-to-custom-app-development/self-built-application-development-process)
- [创建应用并添加机器人能力](https://open.feishu.cn/document/home/develop-a-bot-in-5-minutes/create-an-app)

应用权限页按当前 App ID 拼接，不要把客户的真实 App ID 写进公共 skill：

```text
https://open.feishu.cn/app/<APP_ID>/auth
```

`<APP_ID>` 来自私有配置中的 `LARK_APP_ID`。配置脚本会在成功后输出对应入口。

## 2. tenant 与 user 权限边界

本技能默认使用应用凭证，以 bot 身份执行命令，因此主要申请 **tenant 权限**。客户权限清单中出现的 `user` scope 属于 OAuth 用户身份；本技能默认不调用 `lark-cli auth login`，不要把 user scope 当成 bot 权限。

应用凭证开通 scope 后，还必须在开放平台保存权限配置，并在“版本管理与发布”中发布应用版本。只保存权限草稿不视为权限已经生效。

## 3. 按客户目标选择最小权限

### A. 知识库 / Wiki 只读盘点（默认推荐）

用于列知识空间、列节点、读取 Wiki 文档并做迁移评估：

```text
wiki:wiki:readonly
wiki:space:read
wiki:space:retrieve
wiki:node:read
wiki:node:retrieve
docs:doc:readonly
docx:document:readonly
docs:document.content:read
```

如果控制台只显示其中一部分，按当前开放平台提供的等价只读项申请；如果 CLI 返回明确的 `missing_scopes`，以错误中的 scope 为准。

### B. 云盘搜索、文件和文档元数据

用于 Drive Search、文件类型盘点和文档 URL 类型识别：

```text
drive:drive.search:readonly
drive:drive:readonly
```

不同版本的 CLI / OpenAPI 可能会把元数据检查报告为以下名称。只有当 CLI 的授权错误明确返回它们时才补充：

```text
drive:drive
drive:drive.metadata:readonly
```

不要因为 `drive +inspect` 缺少元数据 scope，就顺手申请 Drive 上传、移动或删除权限。

### C. 评论和权限元数据只读

只有客户要求查看评论、成员或访问设置时才申请：

```text
docs:document.comment:read
docs:permission.member:readonly
docs:permission.member:retrieve
docs:permission.setting:read
docs:permission.setting:readonly
```

权限查询属于敏感元数据。回执只展示必要字段，不输出 token、Secret 或完整个人信息。

### D. 附件、导出和下载（按需）

只有客户明确要求读取图片、下载附件或导出文件时才申请：

```text
docs:document.media:download
drive:file:download
drive:export:readonly
```

下载和导出属于敏感数据动作；即使权限已开通，也要确认具体对象和输出位置。

### E. 表格和多维表只读（按需）

客户要求盘点或读取 Sheets / Base 时再申请对应只读权限：

```text
sheets:spreadsheet:readonly
sheets:spreadsheet.meta:read
base:record:read
base:record:retrieve
```

不要为了 Wiki / 云盘调研申请 Base、Sheets 的创建、更新或删除权限。

### F. 实时事件和订阅（不属于默认调研）

只有客户明确要求持续监听文档变化、删除或打开事件时，才单独评估：

```text
docs:event.document_deleted:read
docs:event.document_edited:read
docs:event.document_opened:read
docs:event:subscribe
```

这类权限还需要事件订阅、回调地址和应用发布配置，不能因为一次性调研而默认开启。

## 4. 不要默认申请的高风险权限

以下权限会扩大远端修改、分享或数据变更能力。只读调研不申请；如果客户提出写入需求，必须单独展示影响范围并重新确认：

```text
docs:doc
docs:document.comment:create
docs:document.comment:update
docs:document.comment:delete
docs:document.comment:write_only
docs:document.media:upload
docs:document:copy
docs:document:import
docx:document:create
docx:document:write_only
drive:file:upload
wiki:node:create
wiki:node:update
wiki:node:move
wiki:node:copy
wiki:setting:write_only
wiki:space:write_only
space:document:move
space:document:delete
base:record:create
base:record:update
base:record:delete
sheets:spreadsheet:create
sheets:spreadsheet:write_only
```

`docs:document:export`、`docs:document.media:download`、`drive:file:download` 虽然不一定修改远端，也可能导出或带走敏感数据，应按敏感数据权限处理。

## 5. 开通、发布、验证闭环

当 CLI 报告缺少 scope 时，按下面顺序操作：

1. 从私有配置读取 `LARK_APP_ID`，打开 `https://open.feishu.cn/app/<APP_ID>/auth`。
2. 在权限管理中搜索 CLI 错误里的精确 scope；优先选择上面对应分类中的只读 scope。
3. 保存权限配置；若飞书要求管理员审批，等待审批完成。
4. 在版本管理中创建或更新版本并发布应用。只保存权限草稿不能视为已生效。
5. 重新执行应用凭证配置，确保 CLI 使用目标 profile：

   ```bash
   python3 <skill-path>/scripts/setup_app_credentials.py --use
   lark-cli doctor
   lark-cli auth status --json --verify
   lark-cli whoami
   ```

6. 重新执行一个与客户目标对应的代表性只读命令：Wiki 用 `wiki +space-list`，云盘用 `drive +search`，具体文档用 `docs +fetch`，权限元数据用 `drive +list-comments` 或对应只读命令。
7. 如果仍失败，把 `missing_scopes`、`console_url`、identity 和目标命令写入回执；不要静默切换到 user OAuth，也不要追加写权限。

## 6. 给客户的提醒格式

技能执行前或遇到权限错误时，按下面格式分类提醒：

```markdown
权限状态：需要在飞书开放平台开通并发布应用后才能继续。

入口：https://open.feishu.cn/app/<APP_ID>/auth

必需（本次目标）：
- <scope>：<对应的 Wiki / Drive / 文档能力>

可选（客户明确需要时）：
- <scope>：<评论 / 下载 / Sheets / Base / 事件能力>

不要默认开通：
- <写入、删除、移动、上传、成员管理权限>

开通后：保存权限 → 发布应用版本 → 重新运行 auth status → 重试代表性只读命令。
```

## 7. 重要边界

- bot 只能读取应用拥有、被授予应用访问权或租户策略允许访问的资源；开通 scope 不会自动让 bot 看到用户个人云盘或 `my_library`。
- 客户提供的一份权限蓝图可以作为能力覆盖参考，但其中的 `*_write_only`、创建、更新、删除、上传、成员管理权限不属于本技能默认范围。
- 具体 scope 名称和授权错误以当前飞书开放平台、当前 `lark-cli` 版本和错误中的官方 `console_url` 为准。
