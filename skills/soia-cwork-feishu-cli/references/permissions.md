# 飞书应用权限开通指南

本文件是给客户和执行者看的申请流程；具体 scope、场景、风险、验证命令和禁止默认申请的权限，以同目录的 [`permissions.yml`](permissions.yml) 为准。

## 1. 先判断身份模式

本技能默认使用应用凭证，以 `tenant_access_token` 和 bot 身份执行命令：

- 申请的是 **tenant / 应用身份权限**。
- 不要把 `user_access_token` 的 user scope 当成 bot 权限。
- 开通 scope 不等于 bot 自动看见用户的个人云盘、个人知识库或所有文档。
- 资源本身可能还需要知识库管理员、文档所有者或租户管理员授权应用。

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
- [配置应用数据权限](https://open.feishu.cn/document/home/introduction-to-scope-and-authorization/configure-app-data-permissions)
- [云文档权限概述](https://open.feishu.cn/document/server-docs/docs/permission/overview?lang=zh-CN)

权限页按当前 App ID 拼接：

```text
https://open.feishu.cn/app/<APP_ID>/auth
```

`<APP_ID>` 只能从用户自己的私有配置或 CLI profile 中读取，不要写进公共技能。

## 3. 按目标选择最小权限

先读取 [`permissions.yml`](permissions.yml)，根据场景选择权限：

| 场景 | 默认策略 | 典型验证 |
|---|---|---|
| Wiki / 知识库只读 | 申请 Wiki、文档只读权限 | `wiki +space-list`、`wiki +node-list`、`docs +fetch` |
| 云盘搜索和元数据 | 先申请云盘搜索/只读；元数据 scope 以 CLI 错误为准 | `drive +search`、`drive +inspect` |
| 评论和权限信息 | 客户明确要求时才申请 | `drive +list-comments` 或对应只读命令 |
| 附件、导出和下载 | 客户明确要求并确认敏感数据范围 | 下载或导出命令 |
| Sheets / Base | 不属于 Wiki 默认范围 | 对应表格或多维表只读命令 |
| 实时事件 | 另行评估事件、回调和发布配置 | 事件订阅验证 |

不要为了读取而申请创建、更新、删除、移动、上传、评论写入、成员管理等权限。高风险权限清单见 YAML 的 `policy.never_default_scopes`。

## 4. 保存、发布和验证

企业自建应用按以下闭环处理：

1. 进入“开发配置 → 权限管理”，按目标 API 的权限要求开通 scope。
2. 如果使用 `tenant_access_token`，检查并配置应用数据权限和资源可见范围。
3. 保存权限配置；需审核权限还要创建或更新应用版本并提交发布。
4. 等企业管理员审核通过。页面显示“审核中”不等于权限已经正式生效。
5. 重新运行：

   ```bash
   python3 <skill-path>/scripts/setup_app_credentials.py --use
   lark-cli doctor
   lark-cli auth status --json --verify
   lark-cli whoami
   ```

6. 运行与目标对应的代表性只读命令，确认不再返回 `missing_scopes`。

测试版本的权限不自动等于正式版本权限；正式发布前要重新核对正式版本的权限和可用范围。

## 5. 遇到权限错误时如何提醒客户

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

## 6. 重要边界

- 具体 scope 名称和授权错误，以当前飞书开放平台、当前 `lark-cli` 版本和错误中的官方 `console_url` 为准。
- 客户现有权限蓝图只能作为能力覆盖参考，其中的写入、创建、更新、删除、上传和成员管理权限不属于本技能默认范围。
- bot 只能读取应用拥有、被授予应用访问权或租户策略允许访问的资源；一次搜索为空不能证明用户云盘为空。
