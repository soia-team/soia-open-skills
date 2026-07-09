#!/usr/bin/env bash
set -euo pipefail

# Public, reusable AI CLI upgrade helper. Keep machine-specific choices in env
# vars or the optional private config file, not in the script.

config_file="${SOIA_DEV_AI_CLI_UPGRADE_CONFIG_FILE:-${SOIA_DEV_AI_CLI_UPGRADE_ENV_FILE:-$HOME/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-ai-cli-upgrade/config.yml}}"
if [[ -f "$config_file" ]]; then
  eval "$(python3 - "$config_file" <<'PY'
from pathlib import Path
import os
import re
import shlex
import sys

key_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
path_like = {"LOG_DIR", "NPM_PREFIX"}
path = Path(sys.argv[1]).expanduser()
in_env = False
for raw_line in path.read_text(encoding="utf-8").splitlines():
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    indent = len(raw_line) - len(raw_line.lstrip(" "))
    if indent == 0:
        in_env = stripped == "env:"
        continue
    if not in_env or indent < 2 or ":" not in stripped:
        continue
    key, value = stripped.split(":", 1)
    key = key.strip()
    if not key_re.match(key):
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()
    if key in path_like:
        value = os.path.expandvars(os.path.expanduser(value))
    print(f"export {key}={shlex.quote(value)}")
PY
)"
fi

state_home="${XDG_STATE_HOME:-$HOME/.local/state}"
log_dir="${LOG_DIR:-$state_home/soia-dev-ai-cli-upgrade/logs}"
mkdir -p "$log_dir"
log_file="$log_dir/cli-upgrade-$(date +"%Y-%m-%d_%H-%M-%S").log"
npm_prefix="${NPM_PREFIX:-$HOME/.npm-global}"

dry_run="${DRY_RUN:-0}"
run_mode="LIVE"
[[ "$dry_run" == "1" ]] && run_mode="DRY_RUN"

# 选 arm64 npm（M 系列）。Homebrew 已迁 arm64 /opt/homebrew → 优先用 brew npm；
# 否则 fallback nvm arm64 npm（v24/v22）。注意：x64 npm 会装出 x64 binary 触发 Bun AVX 警告
_find_arm64_npm() {
  # 优先 Homebrew arm64 npm（迁移后统一 node 入口）
  if [[ -x /opt/homebrew/bin/npm && -x /opt/homebrew/bin/node ]]; then
    [[ "$(file /opt/homebrew/bin/node 2>/dev/null)" == *arm64* ]] && printf '%s' "/opt/homebrew/bin/npm" && return
  fi
  for d in \
    "$HOME/.nvm/versions/node/v24"*/bin \
    "$HOME/.nvm/versions/node/v22"*/bin \
    "$HOME/.nvm/versions/node/v2"*/bin; do
    [[ -x "$d/npm" && -x "$d/node" ]] || continue
    arch=$( file "$d/node" 2>/dev/null )
    [[ "$arch" == *arm64* ]] && printf '%s' "$d/npm" && return
  done
  local fallback
  fallback="$(command -v npm 2>/dev/null || true)"
  [[ -n "$fallback" ]] && printf '%s' "$fallback"
}
NPM_BIN="$(_find_arm64_npm)"
if [[ -z "$NPM_BIN" ]]; then
  printf 'ERROR: npm not found. Install Node.js/npm or set PATH before running this script.\n' >&2
  exit 1
fi
NPM_NODE="$(dirname "$NPM_BIN")/node"
NPM_ENV=(env -i HOME="$HOME" PATH="$(dirname "$NPM_BIN"):$npm_prefix/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin")

log() {
  printf '%s\n' "$*" | tee -a "$log_file"
}

extract_version() {
  local text="$1"
  local v
  v=$(printf '%s' "$text" | grep -Eo '([0-9]+\.){1,}[0-9]+([.-][0-9A-Za-z._+-]+)?' | head -n 1 || true)
  if [[ -n "$v" ]]; then
    printf '%s' "$v"
  else
    printf '%s' "$text"
  fi
}

get_version() {
  local cmd="$1"
  local bin="$npm_prefix/bin/$cmd"
  [[ ! -x "$bin" ]] && bin="$(command -v "$cmd" 2>/dev/null || true)"
  [[ -z "$bin" ]] && return 1
  local out=""
  # 只覆盖 PATH，确保 Homebrew arm64 node 优先（node-script CLI 的 env node 需要它；
  # 必须含 /opt/homebrew/bin，否则 brew 迁移后找不到 node 导致 version check 全 UNKNOWN）
  local clean_path="$npm_prefix/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin"
  if out="$(PATH="$clean_path" "$bin" --version 2>/dev/null)"; then
    extract_version "$out"; return 0
  fi
  if out="$(PATH="$clean_path" "$bin" version 2>/dev/null)"; then
    extract_version "$out"; return 0
  fi
  printf 'UNKNOWN'; return 0
}

print_header() {
  log "------------------------------------------------------------"
  log "AI CLI Upgrade Log"
  log "Date: $(date '+%F %T %z')"
  log "Mode: $run_mode"
  log "Log: $log_file"
  log "------------------------------------------------------------"
  printf '%-10s %-12s %-18s %-18s %-14s %s\n' "TOOL" "COMMAND" "OLD" "NEW" "STATUS" "NOTE" | tee -a "$log_file"
}

upgrade_tool() {
  local tool="$1"
  local cmd package
  package=""

  case "$tool" in
    codex)    cmd="codex";    package="@openai/codex" ;;
    claude)   cmd="claude";   package="@anthropic-ai/claude-code" ;;
    gemini)   cmd="gemini";   package="@google/gemini-cli" ;;
    qwen)     cmd="qwen";     package="@qwen-code/qwen-code" ;;
    mmx)      cmd="mmx";      package="mmx-cli" ;;
    kimi)     cmd="kimi" ;;
    opencode) cmd="opencode"; package="opencode-ai" ;;
    qodercli) cmd="qodercli" ;;
    cursor)   cmd="cursor" ;;
    *)        cmd="$tool" ;;
  esac

  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "-" "-" "NOT_INSTALLED" "command not found" | tee -a "$log_file"
    return
  fi

  local old_version new_version status note
  old_version="$(get_version "$cmd")"

  if [[ "$dry_run" == "1" ]]; then
    printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "N/A" "SKIP_DRY_RUN" "skip upgrade by DRY_RUN=1" | tee -a "$log_file"
    return
  fi

  case "$tool" in
    codex|claude|gemini|qwen|mmx|opencode)
      if ! "${NPM_ENV[@]}" "$NPM_BIN" install -g --prefix "$npm_prefix" "$package" >>"$log_file" 2>&1; then
        printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "npm install -g $package failed" | tee -a "$log_file"
        return
      fi
      ;;
    kimi)
      # kimi 已从 Python(uv kimi-cli) 迁移到 brew 的 kimi-code（TS 单二进制，命令仍叫 kimi）2026-06-16
      if ! command -v brew >/dev/null 2>&1; then
        printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "brew not installed" | tee -a "$log_file"
        return
      fi
      brew upgrade kimi-code >>"$log_file" 2>&1 || true   # 已最新时 brew 返回非0，不算失败
      if ! brew list kimi-code >/dev/null 2>&1; then
        if ! brew install kimi-code >>"$log_file" 2>&1; then
          printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "brew install/upgrade kimi-code failed" | tee -a "$log_file"
          return
        fi
      fi
      ;;
    qodercli)
      if ! qodercli update >>"$log_file" 2>&1; then
        printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "qodercli update failed" | tee -a "$log_file"
        return
      fi
      ;;
    cursor)
      if [[ -z "${CURSOR_UPGRADE_CMD:-}" ]]; then
        printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$old_version" "MANUAL" "no default updater; set CURSOR_UPGRADE_CMD" | tee -a "$log_file"
        return
      fi
      if ! bash -lc "$CURSOR_UPGRADE_CMD" >>"$log_file" 2>&1; then
        printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "CURSOR_UPGRADE_CMD failed" | tee -a "$log_file"
        return
      fi
      ;;
    *)
      printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$old_version" "MANUAL" "no upgrader config" | tee -a "$log_file"
      return
      ;;
  esac

  new_version="$(get_version "$cmd")"
  if [[ -z "$new_version" || "$new_version" == "UNKNOWN" ]]; then
    status="FAILED"; note="version check failed after upgrade"; new_version="$old_version"
  elif [[ "$new_version" != "$old_version" ]]; then
    status="UPDATED"; note="upgraded"
  else
    status="ALREADY_LATEST"; note="no version delta"
  fi

  printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old_version" "$new_version" "$status" "$note" | tee -a "$log_file"
}

print_header

default_tools=(codex claude gemini kimi mmx qwen opencode qodercli cursor)
all_tools=("${default_tools[@]}")

if [[ -n "${NPM_PACKAGES:-}" ]]; then
  selected=()
  IFS=',' read -r -a selected <<<"$NPM_PACKAGES"
  all_tools=("${selected[@]}")
fi

for tool in "${all_tools[@]}"; do
  upgrade_tool "$tool"
done

log "DONE. detail log: $log_file"
