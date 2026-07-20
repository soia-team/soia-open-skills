# 飞书应用权限开通指南

本文件是给客户和执行者看的申请流程；具体 scope、场景、风险、验证命令和禁止默认申请的权限，以同目录的 [`permissions.yml`](permissions.yml) 为准；认证和 API 常见错误，以 [`errors.yml`](errors.yml) 为准。

## 1. 先区分资源和身份

本技能把资源分成两类，也把调用身份分成两类：

| 资源场景 | 应用身份 / Bot | 用户身份 / OAuth |
|---|---|---|
| 知识库 / Wiki | 盘点应用可见的知识空间和节点；需要知识库管理员授权应用 | 读取当前用户可见的知识库、个人知识库或 `my_library` |
| 云盘 / Drive | 盘点应用拥有或被授权的共享资源；不能自动访问个人云盘 | 读取当前用户的“我的文件夹”、个人文件和共享资源 |

两种身份对应不同的 access token 和权限页签：

- **应用身份权限** → `tenant_access_token` → 运行时 `bot`。
- **用户身份权限** → `user_access_token` → 运行时 `user`，还必须由用户 OAuth 登录。

如果要同时支持“Bot 读企业知识库 + 用户 OAuth 读个人云盘”，同一能力需要在两个页签分别申请；只使用一种身份时不要重复申请。开通 scope 不等于资源自动可见，Bot 仍可能需要知识库管理员、文档所有者或租户管理员授权应用。

## 2. 创建应用和打开权限页

完整链路是：安装 Feishu CLI → 创建企业自建应用 → 添加机器人能力 → 获取 App ID / App Secret → 按目标场景开通最小权限 → 配置应用数据权限 → 发布应用版本 → 用 CLI 验证。

参考入口：

- [Feishu CLI 安装与配置指南](https://feishu-cli.com/zh/feishu-cli-installation-guide.html)
- [lark-cli 官方 README：认证](https://github.com/larksuite/cli/blob/main/README.zh.md#认证)
- [飞书开放平台](https://open.feishu.cn/app)
- [自建应用开发流程](https://open.feishu.cn/document/home/introduction-to-custom-app-development/self-built-application-development-process)
- [创建应用并添加机器人能力](https://open.feishu.cn/document/home/develop-a-bot-in-5-minutes/create-an-app)
- [申请 API 权限](https://open.feishu.cn/document/server-docs/application-scope/introduction?lang=zh-CN)
- [API 权限列表](https://open.feishu.cn/document/server-docs/application-scope/scope-list)
- [获取授权码（网页 OAuth）](https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code?lang=zh-CN)
- [获取用户信息（需要已有 user_access_token）](https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/get)
- [配置应用数据权限](https://open.feishu.cn/document/home/introduction-to-scope-and-authorization/configure-app-data-permissions)
- [云文档权限概述](https://open.feishu.cn/document/server-docs/docs/permission/overview?lang=zh-CN)

权限页按当前 App ID 拼接：

```text
https://open.feishu.cn/app/<APP_ID>/auth
```

`<APP_ID>` 只能从用户自己的私有配置或 CLI profile 中读取，不要写进公共技能。

注意：开放平台的“获取用户信息”文档对应的是登录后的 `user_info` API，不是登录入口。网页 OAuth 的授权入口是授权码接口；lark-cli 则通过 `auth login` 的 device flow 完成用户授权。

## 3. 按资源场景选择最小权限

先读取 [`permissions.yml`](permissions.yml)，根据 `scenarios.knowledge_base_readonly` 或 `scenarios.drive_readonly`，再根据 `identity_modes.application` 或 `identity_modes.user_oauth` 选择权限。不要把 Wiki 和 Drive 的权限清单混在一起。

### 知识库 / Wiki

详细规则见 [`wiki-workflow.md`](wiki-workflow.md)。

- Bot：在“应用身份权限”申请 Wiki、空间、节点和正文只读 scope；再授权目标知识空间。
- User OAuth：在“用户身份权限”申请同一组最小只读 scope；再由用户登录授权。

### 云盘 / Drive

详细规则见 [`drive-workflow.md`](drive-workflow.md)。

- Bot：在“应用身份权限”申请搜索和文件只读 scope；资源所有者还需授权应用。
- User OAuth：在“用户身份权限”申请搜索、文件和元数据只读 scope；用户 OAuth 后才可读个人云盘。

### 其他能力

| 场景 | 默认策略 | 典型验证 |
|---|---|---|
| 评论和权限信息 | 客户明确要求时才申请 | `drive +list-comments` 或对应只读命令 |
| 附件、导出和下载 | 客户明确要求并确认敏感数据范围 | 下载或导出命令 |
| Sheets / Base | 不属于 Wiki 或 Drive 默认范围 | 对应表格或多维表只读命令 |
| 实时事件 | 另行评估事件、回调和发布配置 | 事件订阅验证 |

不要为了读取而申请创建、更新、删除、移动、上传、评论写入、成员管理等权限。高风险权限清单见 YAML 的 `policy.never_default_scopes`。

## 4. 保存、发布和验证

企业自建应用按以下闭环处理：

1. 进入“开发配置 → 权限管理”，先选择资源场景，再选择“应用身份权限”或“用户身份权限”页签。
2. 按目标 API 的权限要求开通最小 scope；同一个 scope 如果需要两种身份，分别开通。
3. 如果使用 `tenant_access_token`，检查并配置应用数据权限和资源可见范围；用户身份通常跟随用户本人权限范围。
4. 保存权限配置；需审核权限还要创建或更新应用版本并提交发布。
5. 等企业管理员审核通过。页面显示“审核中”不等于权限已经正式生效。
6. 重新运行：

   ```bash
   python3 <skill-path>/scripts/setup_app_credentials.py --use
   lark-cli doctor
   lark-cli auth status --json --verify
   lark-cli whoami
   ```

7. 使用对应身份运行目标场景的代表性只读命令，确认不再返回 `missing_scopes`。

测试版本的权限不自动等于正式版本权限；正式发布前要重新核对正式版本的权限和可用范围。

## 5. 遇到权限错误时如何提醒客户

```markdown
权限状态：需要在飞书开放平台的正确身份页签开通并发布应用后才能继续。

入口：https://open.feishu.cn/app/<APP_ID>/auth

调用身份：<bot / user>
资源场景：<知识库 / 云盘>

必需（本次目标）：
- <scope>：<对应的 Wiki / Drive / 文档能力>
- 申请页签：<应用身份权限 / 用户身份权限>

可选（客户明确需要时）：
- <scope>：<评论 / 下载 / Sheets / Base / 事件能力>

不要默认开通：
- <写入、删除、移动、上传、成员管理权限>

开通后：保存权限 → 发布应用版本 → 如为 user 则完成 OAuth → 重新运行 auth status → 用同一身份重试代表性只读命令。
```

如果 OAuth 验证链接跳转到 `open.feishu.cn/page/scope-authorization` 并显示“已提交申请，正在审核中”，应记录为“应用权限审核阻塞”，不能记录为“用户已登录”。

## 6. 重要边界

- 具体 scope 名称和授权错误，以当前飞书开放平台、当前 `lark-cli` 版本和错误中的官方 `console_url` 为准。
- 客户现有权限蓝图只能作为能力覆盖参考，其中的写入、创建、更新、删除、上传和成员管理权限不属于本技能默认范围。
- bot 只能读取应用拥有、被授予应用访问权或租户策略允许访问的资源；一次搜索为空不能证明用户云盘为空。
