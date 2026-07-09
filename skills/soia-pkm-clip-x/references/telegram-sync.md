# clip-x · Telegram 我的收藏同步

把手机随手转发到 Telegram「我的收藏」(Saved Messages) 的 X 链接，批量归档进 vault。两条路径。

## A. JSON 导出（推荐 · 零风险 · 零依赖 · ToS 合规）

中国大陆用户**优先用这条**。

**导出步骤**：

```
Telegram Desktop
  → Settings → Advanced → Export Telegram data
  → 勾「私聊」(Personal chats) + 选 Machine-readable JSON
  → 得到 result.json
```

**同步命令**：

```bash
python3 sync_telegram_export.py <result.json> --dry-run          # 看清单，不实跑
python3 sync_telegram_export.py <result.json>                    # 实跑
python3 sync_telegram_export.py <result.json> --since 2026-06-01 # 只处理某日后
python3 sync_telegram_export.py <result.json> --limit 30         # 限量（最新优先）
```

- 自动按 URL 去重、跳过已归档。
- 每月重新导出一次即可增量同步（只处理新增）。
- 不需要任何 Telegram API 凭证，Telegram 官方支持，零风控。

## B. MTProto API（高阶 · 国内慎用）

想「不导出就能实时拉」时用。需要：

- 到 `https://my.telegram.org/auth` 申请 `api_id` / `api_hash`
- `python3 generate_telegram_session.py` 拿 `session_string`（一次性 setup）
- 住宅 IP（中国大陆用户必须走 HK / JP 住宅段；机房 IP 必触发 ERROR）
- 把 `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` / `TELEGRAM_SESSION_STRING` 放进私有 `config.yml`（`$SOIA_PKM_CLIP_X_CONFIG_FILE` 或 `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-x/config.yml`），不要放进 vault 或提交到开源 skill 仓库

**命令**：

```bash
python3 generate_telegram_session.py    # 一次性 setup
python3 sync_telegram_saved.py --dry-run
python3 sync_telegram_saved.py --days 30
python3 sync_telegram_saved.py --all
```

> ⚠️ **国内用户优先用方案 A**。my.telegram.org 创建 app 在大陆几乎必踩 IP 风控，反复尝试会触发账号级 24–72h 冻结。
