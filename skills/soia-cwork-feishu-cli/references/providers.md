# 飞书 Provider 规则

## 选择顺序

1. 用户当前请求明确指定的 profile 或 identity。
2. CLI 参数，例如 `--profile`、`--as bot`。
3. `SOIA_CWORK_FEISHU_CONFIG_FILE` 指向的私有配置。
4. 默认私有配置：
   `~/.config/soia-skills/soia-open-skills/cwork/soia-cwork-feishu-cli/config.yml`
5. 安全的只读自动发现。
6. 无法确认时停下并说明缺少配置，不猜账号或资源范围。

## 凭证边界

- App ID 可以出现在命令参数和非敏感回执中，但不需要主动展示。
- App Secret、access token、refresh token、device code 和授权链接不能进入日志、聊天、vault、git 或飞书文档。
- 应用凭证存放在私有配置或 lark-cli/provider-owned credential store；不要读取 keychain 原始文件或浏览器会话。
- App credentials 对应 bot 身份，不等于当前用户身份；它只支撑应用身份权限页签的 `tenant_access_token` 调用。
- 用户 OAuth 使用独立的 `user_access_token` 登录态；只有用户明确要求个人资源时才运行 `auth login`，并在命令中显式使用 `--as user`。
- 知识库/Wiki 与云盘/Drive 必须先分流，再选择对应身份和权限清单；不要把 Bot 的 Wiki 结果与用户云盘结果合并成一个“全量”。

## 缺配置时

1. 运行 `lark-cli doctor` 或 `lark-cli auth status --json` 检查，不要重试大量 API。
2. 提示用户复制 `assets/config.example.yml` 到私有配置路径并填写本地值。
3. 用 `scripts/setup_app_credentials.py` 通过 stdin 配置 profile。
4. 运行 `lark-cli auth status --json --verify` 和 `lark-cli whoami` 验证。
5. 仍缺 scope 时，引用 CLI 错误中的官方控制台链接，申请最小只读权限。

认证失败时先读取 [`errors.yml`](errors.yml)：`invalid_client` / `20140` 属于应用凭证或 profile 问题，不是缺 scope；已有 profile 只有在用户明确要求时才用 `setup_app_credentials.py --replace --use` 刷新。
