# 百度网盘 CLI 选择与接口事实

## 调研结论（2026-07-15）

应优先使用百度官方开放平台发布的 `baidu-drive` Skill：[`baidu-netdisk/bdpan-storage`](https://github.com/baidu-netdisk/bdpan-storage)。它通过官方 Skill 脚本安装和登录 `bdpan` CLI，并把能力限制在 `/apps/bdpan/` 应用目录；这是目前最符合“官方 CLI 或二次封装”要求的路线。

官方入口：

- [百度网盘开放平台](https://pan.baidu.com/union)
- [百度网盘 Skill 开发者页面](https://pan.baidu.com/apaastobui/developer#/developer/skill)
- [官方 Skill README](https://github.com/baidu-netdisk/bdpan-storage/tree/main/skills/baidu-drive)
- [官方 Skill SKILL.md](https://github.com/baidu-netdisk/bdpan-storage/blob/main/skills/baidu-drive/SKILL.md)
- [官方命令参考](https://github.com/baidu-netdisk/bdpan-storage/blob/main/skills/baidu-drive/reference/bdpan-commands.md)
- [官方认证说明](https://github.com/baidu-netdisk/bdpan-storage/blob/main/skills/baidu-drive/reference/authentication.md)

| 候选 | 证据与能力 | 结论 |
|---|---|---|
| `baidu-netdisk/bdpan-storage` → `baidu-drive` | 百度网盘官方仓库；上游 Skill 通过百度 CDN 安装 `bdpan`；支持登录、`ls`、搜索、上传下载、分享/转存、移动/复制/重命名、建目录，并内置特定 Claw 环境的记忆备份/恢复；当前仓库 Skill 版本见 `VERSION` | 默认、首选依赖 |
| [`mqhe2007/baidupan-cli`](https://github.com/mqhe2007/baidupan-cli) | 社区 Rust 封装，基于开放平台 API，支持设备码 OAuth、JSON、文件管理、分片上传下载和批量任务；需要用户自建 AppKey/SecretKey/应用名 | 备选参考；不作为默认后端 |
| `BaiduPCS-Go` 及其衍生项目 | 功能广，但多使用旧式账号、BDUSS 或非本技能优先的登录语义 | 不作为默认自动化后端 |

这里的“官方 CLI”应准确理解为：百度官方发布的 Agent Skill + 百度 CDN 提供的 `bdpan` 二进制安装器，而不是把第三方仓库误标成百度官方 CLI。`mqhe2007/baidupan-cli` 适合需要自行管理开放平台应用、测试应用目录原子操作的用户，但与官方 Skill 的固定应用目录和登录门禁不同。两者通过本技能配置显式选择，不自动混用登录态。

## 官方 `bdpan` 接口合同

来源：官方 [`SKILL.md`](https://github.com/baidu-netdisk/bdpan-storage/blob/main/skills/baidu-drive/SKILL.md)、[`bdpan-commands.md`](https://github.com/baidu-netdisk/bdpan-storage/blob/main/skills/baidu-drive/reference/bdpan-commands.md)、[`install.sh`](https://github.com/baidu-netdisk/bdpan-storage/blob/main/skills/baidu-drive/scripts/install.sh)。安装前应重新查看上游，因为 CLI 和 Skill 会更新。

- 安装由上游 `scripts/install.sh` 完成；当前上游文档说明脚本从百度 CDN 下载并执行，未承诺本地 SHA256 校验。安装前应审查脚本、版本和网络来源；更新使用上游脚本，不能静默更新。
- 登录由上游 `scripts/login.sh` 完成。Agent 不直接执行 `bdpan login`，也不使用 `--yes` 绕过人工授权。
- provider 配置位于 `~/.config/bdpan/config.json`；Agent 不读取、不打印、不复制，也不主动设置 `BDPAN_CONFIG_PATH`、`BDPAN_BIN`、`BDPAN_INSTALL_DIR`。
- 用户命令使用相对路径，例如 `资料/a.pdf`；官方应用根是 `/apps/bdpan/`，用户界面通常显示为 `我的应用数据/bdpan/`。禁止 `..`、`~` 和越出应用根的路径。
- 主要命令为 `whoami`、`ls`、`search`、`upload`、`download`、`transfer`、`share`、`mv`、`cp`、`rename`、`mkdir`。官方 Skill 有意不提供 `rm/delete`。
- `ls --json` 通常返回数组，核心字段为 `fs_id`、`path`、`server_filename`、`size`、`isdir`、`md5`、`server_mtime`。扫描器以 `server_filename` 和当前递归父目录组合虚拟路径，不把人类展示路径当作命令路径。
- `share` 使用可能收费的能力；必须单独提醒和确认。分享链接转存需要用户提供提取码，不能猜测或代填。

## 官方登录的设备码路径

2026-07-20 的真实验证发现：当前 `bdpan` 3.8.3 的登录帮助同时提供
`--get-auth-url` 和 `--device-code`，但上游 `scripts/login.sh` 使用的授权链接路径可能在“获取授权链接失败”处终止；这不是用户账号或应用目录配置错误。

处理顺序：

1. Agent 先执行 `bdpan help login`，检查当前版本是否包含 `--device-code`。
2. 若支持设备码，直接使用本技能的 `scripts/device_login.py`，让 CLI 自动确认免责声明、生成设备码和二维码图片地址，并等待授权完成；客户不在终端输入 `Y` 或授权码。
3. 使用 `scripts/decode_qr.py` 解析二维码图片地址，向客户返回二维码内的设备授权地址；客户用百度 App/浏览器授权，Agent 不替客户确认。
4. 若当前版本没有 `--device-code`，才自动执行上游 `baidu-drive/scripts/login.sh --yes`；旧版 OOB 流程可能需要客户在聊天中提供网页授权码，但不需要客户操作终端。
5. 授权完成后必须重新执行 `whoami` 与 `--json ls`，分别证明登录态和应用目录访问都可用。

设备码是短时一次性凭据。不要重放过期地址，不要把设备码、二维码内文、token 或用户身份写入仓库和回执。若 `--device-code` 不存在，停止并等待上游 CLI/Skill 更新，不猜测参数。

## 上传前向测试的失败判定

2026-07-20 的真实前向测试中，`whoami` 和应用根目录 `ls --json` 均成功，但上传一个小型 PNG 到应用根目录时，`bdpan` 返回业务 JSON `code: 1`、`errno=-10`；随后回读目标显示“目录不存在”，证明没有成功创建文件。

遇到这个组合时：

1. 不把登录成功或 `ls` 成功说成“上传可用”。
2. 不连续重试同一个上传请求；先检查百度网盘网页显示的容量是否已满/超额。
3. 再检查百度开放平台当前应用是否开通网盘上传能力；百度开发者中心的 FAQ 说明，网盘上传能力需要在开放平台申请开通。[百度开发者中心 FAQ](https://developer.baidu.com/article/details/293412)
4. 处理容量或能力开通后，再用不冲突的测试文件名重试，并用 `ls --json` 回读确认最终落点。

## 官方 Skill 内置记忆能力

官方 `baidu-drive` Skill 还包含记忆备份/恢复，这与独立的 Baidu Drive Backup Plugin 不同。它只在 KimiClaw、MaxClaw、QClaw、OpenClaw 环境启用，并识别以下意图：

- `备份记忆` / `把记忆存到网盘` → `backup`
- `查看记忆备份` / `备份列表` → `list`
- `恢复记忆` / `恢复 2026-03-16 的备份` → `restore <日期>`，需要确认日期

“帮我记住”“整理记忆”“清理记忆”是本地操作；“备份代码/文件”不是记忆备份。记忆操作必须由上游 `scripts/memory-backup.sh` 生成 manifest、执行路径安全检查和恢复前 safety-net；禁止直接对记忆目录执行裸 `bdpan upload/download`。不支持的 Claw 环境应报错并停止。

## 社区 CLI 的保留边界

若用户明确要求使用 `mqhe2007/baidupan-cli`，将配置切换为：

```yaml
schema_version: 1
provider: community
binary: baidupan-cli
env:
  BAIDUPAN_APP_KEY: "<YOUR_APP_KEY>"
  BAIDUPAN_APP_SECRET: "<YOUR_SECRET_KEY>"
  BAIDUPAN_APP_NAME: "<YOUR_APP_NAME>"
```

社区 CLI 的 `/` 是 `/apps/<BAIDUPAN_APP_NAME>`，不是用户普通网盘根目录；它支持 `rm`，但本技能仍要求先确认删除范围。配置完成后先验证 `whoami`、`ls /`，再做小文件上传/下载前向测试。
