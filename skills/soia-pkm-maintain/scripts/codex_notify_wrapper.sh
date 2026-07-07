#!/bin/bash
# codex_notify_wrapper.sh — Codex config.toml 的 notify 只能挂一条命令，
# 这个 wrapper 负责「先调用用户原有的 notify 命令，再触发 vault 会话日志脚本」。
#
# 接入方式（写进 config.toml，见 ../references/session-log-setup.md）：
#   notify = ["/绝对路径/soia-pkm-maintain/scripts/codex_notify_wrapper.sh", "--vault", "<vault绝对路径>", "--log-dir", "<vault内日志目录>"]
#
# 不要改这个脚本来写死个人路径。vault 通过 --vault 或私有 env 文件里的 OBSIDIAN_VAULT 传入。
# 日志目录通过 --log-dir 或私有 env 文件里的 SOIA_SESSION_LOG_DIR 传入。
#
# 如果原本已有 notify 需要保留，用 --original-count N -- 传入原命令的固定参数：
#   notify = ["/path/codex_notify_wrapper.sh", "--vault", "<vault>", "--log-dir", "<vault内日志目录>", "--original-count", "2", "--", "/old/program", "turn-ended"]
# Codex 追加的事件 JSON 会被 wrapper 继续转发给原命令。

AGENT="Codex"
VAULT_PATH="${OBSIDIAN_VAULT:-}"
SESSION_LOG_DIR="${SOIA_SESSION_LOG_DIR:-}"
ORIGINAL_COUNT=0
EVENT_ARGS=()
POST_DASH=()

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

load_private_env() {
  local candidates=()
  [ -n "${SOIA_PKM_ENV_FILE:-}" ] && candidates+=("$SOIA_PKM_ENV_FILE")
  candidates+=("$HOME/.config/soia-pkm/env" "$HOME/.soia-pkm.env")
  local f
  for f in "${candidates[@]}"; do
    [ -f "$f" ] || continue
    set -a
    # shellcheck disable=SC1090
    . "$f"
    set +a
    break
  done
}

load_private_env
VAULT_PATH="${VAULT_PATH:-${OBSIDIAN_VAULT:-}}"

while [ $# -gt 0 ]; do
  case "$1" in
    --agent)
      AGENT="$2"
      shift 2
      ;;
    --vault)
      VAULT_PATH="$2"
      shift 2
      ;;
    --log-dir)
      SESSION_LOG_DIR="$2"
      shift 2
      ;;
    --original-count)
      ORIGINAL_COUNT="$2"
      shift 2
      ;;
    --)
      shift
      POST_DASH=("$@")
      break
      ;;
    *)
      EVENT_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ "$ORIGINAL_COUNT" -gt 0 ] && [ "${#POST_DASH[@]}" -ge "$ORIGINAL_COUNT" ]; then
  ORIGINAL_NOTIFY_CMD=("${POST_DASH[@]:0:$ORIGINAL_COUNT}")
  EVENT_ARGS+=("${POST_DASH[@]:$ORIGINAL_COUNT}")
  "${ORIGINAL_NOTIFY_CMD[@]}" "${EVENT_ARGS[@]}" || true
elif [ "${#POST_DASH[@]}" -gt 0 ]; then
  EVENT_ARGS+=("${POST_DASH[@]}")
fi

# 触发 vault 会话日志脚本；失败不应影响 Codex 主流程。
LOG_ARGS=(--agent "$AGENT" --vault "$VAULT_PATH")
[ -n "$SESSION_LOG_DIR" ] && LOG_ARGS+=(--log-dir "$SESSION_LOG_DIR")
"$SCRIPT_DIR/session_end_log.sh" "${LOG_ARGS[@]}" 2>/dev/null || true

exit 0
