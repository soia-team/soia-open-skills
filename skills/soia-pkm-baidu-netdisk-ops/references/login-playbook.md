# 百度网盘登录与设备码兼容流程

本参考只描述官方 `bdpan` 的登录，不改变应用目录边界，也不保存任何账号、授权码、二维码地址或 token。

## 客户可见的最短流程

1. 让客户先登录百度网盘账号，并确认愿意授权当前 Agent 访问百度网盘。
2. Agent 先执行 `bdpan help login`，检查当前版本是否包含 `--device-code`。
3. 存在该选项时，Agent 直接执行本技能的 `scripts/device_login.py`。该入口自动传入官方 CLI 的 `--accept-disclaimer`，不会把安全确认提示暴露给客户，也不会要求客户输入授权码。客户不需要运行终端命令。
4. CLI 输出二维码图片地址后，Agent 执行 `scripts/decode_qr.py <二维码图片地址>`，将脚本输出的设备授权地址转成普通 Markdown 链接发给客户。客户用百度 App 扫码，或在浏览器打开该地址完成授权。
5. 等待设备码登录进程结束；设备码通常有短时有效期，过期就重新发起一次，不复用旧地址。
6. 如果当前版本没有 `--device-code`，Agent 才自动执行上游 `baidu-drive/scripts/login.sh --yes`。这里的 `--yes` 只确认登录脚本已经向客户展示过的安全须知；客户不需要在终端输入 `Y`，但旧版 OOB 流程可能要求客户在聊天中提供网页授权码。
7. 通过 `whoami` 和 `--json ls` 验收登录与应用目录访问。两者都通过后，才向客户报告“登录完成”。

## Agent 操作约束

- 设备码兼容入口只允许官方 provider；社区 provider 仍按 `baidupan-cli login` 的自身流程处理。
- `device_login.py` 固定调用已配置的 `bdpan login --device-code --accept-disclaimer`，不接受任意 shell 参数，不读取或打印 `~/.config/bdpan/config.json`。
- `login.sh --yes` 和 `bdpan login --accept-disclaimer` 只由 Agent 在已进入登录流程后自动传入；它们不是让客户确认授权的替代品。真正的网盘授权仍必须由客户在百度页面或 App 中完成。
- 二维码解析器只读取本地图片或 HTTPS 图片地址并输出二维码内的地址；它不识别账号密码、不提取 token，也不应把原始图片或地址写进仓库。
- 不把 CLI 输出中的用户码、错误堆栈或 token 写入仓库、配置、测试 fixture 或持久化日志；当前聊天中可以临时展示完成授权所需的地址，授权结束后不再复述。
- 返回地址前核对其为 HTTPS、主机为 `openapi.baidu.com`、路径为 `/device`；不符合时停止，不把二维码内容当作可信授权地址。
- `whoami` 成功不代表应用目录读取成功；必须再做一次 `--json ls`。命令退出码为 0 也不代表业务成功，若返回 JSON 错误对象，应按失败处理。

## 何时停止

- `bdpan help login` 没有 `--device-code`：停止并提示客户等待上游登录脚本或 CLI 更新，不猜测新参数。
- 二维码无法解码：不要手工改写地址；请客户重新生成二维码，或让客户直接使用 CLI 显示的二维码进行扫码。
- `whoami` 通过但 `ls` 失败：按应用目录权限/授权范围问题报告，不能说成“已完全可用”。
