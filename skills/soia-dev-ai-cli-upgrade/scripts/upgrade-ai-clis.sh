#!/usr/bin/env bash
# @created_by  unknown
# @created_at  unknown
# @modified_by openai/gpt-5
# @modified_at 2026-07-21 13:32:00
# @version     0.3.0
# @description Audit and safely upgrade supported AI/developer CLIs.
# @changelog   Detect relative Homebrew formula symlinks and gate Claude @latest channel migration.
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
path_like = {"AGY_INSTALL_DIR", "LOG_DIR", "NPM_PREFIX"}
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

# logs are throwaway: default to the OS temp area (macOS $TMPDIR auto-purges
# after ~3 days idle; /tmp clears on reboot). Set LOG_DIR to keep an audit trail.
log_dir="${LOG_DIR:-${TMPDIR:-/tmp}/soia-dev-ai-cli-upgrade/logs}"
mkdir -p "$log_dir"
# retention: keep newest LOG_KEEP (default 10) upgrade logs, prune older ones
log_keep="${LOG_KEEP:-10}"
{ ls -1t "$log_dir"/cli-upgrade-*.log 2>/dev/null || true; } | tail -n +"$((log_keep + 1))" | while IFS= read -r old_log; do
  rm -f "$old_log"
done
log_file="$log_dir/cli-upgrade-$(date +"%Y-%m-%d_%H-%M-%S")-$$.log"
npm_prefix="${NPM_PREFIX:-$HOME/.npm-global}"
agy_install_dir="${AGY_INSTALL_DIR:-$HOME/.local/bin}"
agy_install="${AGY_INSTALL:-0}"
claude_channel="${CLAUDE_CHANNEL:-preserve}"

case "$claude_channel" in
  preserve|latest) ;;
  *)
    printf 'invalid CLAUDE_CHANNEL=%s; expected preserve or latest\n' "$claude_channel" >&2
    exit 2
    ;;
esac

dry_run="${DRY_RUN:-0}"
run_mode="LIVE"
[[ "$dry_run" == "1" ]] && run_mode="DRY_RUN"

# 选 arm64 npm（M 系列）。Homebrew 已迁 arm64 /opt/homebrew → 优先用 brew npm；
# 否则 fallback nvm arm64 npm（v24/v22）。注意：x64 npm 会装出 x64 binary 触发 Bun AVX 警告
_find_arm64_npm() {
  local arch fallback
  # 优先 Homebrew arm64 npm（迁移后统一 node 入口）
  if [[ -x /opt/homebrew/bin/npm && -x /opt/homebrew/bin/node ]]; then
    [[ "$(file /opt/homebrew/bin/node 2>/dev/null)" == *arm64* ]] && printf '%s' "/opt/homebrew/bin/npm" && return
  fi
  for d in \
    "$HOME/.nvm/versions/node/v24"*/bin \
    "$HOME/.nvm/versions/node/v22"*/bin \
    "$HOME/.nvm/versions/node/v2"*/bin; do
    [[ -x "$d/npm" && -x "$d/node" ]] || continue
    arch=$(file "$d/node" 2>/dev/null)
    [[ "$arch" == *arm64* ]] && printf '%s' "$d/npm" && return
  done
  fallback="$(command -v npm 2>/dev/null || true)"
  [[ -n "$fallback" ]] && printf '%s' "$fallback"
  return 0
}
NPM_BIN="${NPM_BIN:-}"
NPM_ENV=()

ensure_npm() {
  if [[ -z "$NPM_BIN" ]]; then
    NPM_BIN="$(_find_arm64_npm)"
  fi
  [[ -n "$NPM_BIN" && -x "$NPM_BIN" ]] || return 1
  NPM_ENV=(env -i HOME="$HOME" PATH="$(dirname "$NPM_BIN"):$npm_prefix/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin")
}

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

resolve_bin() {
  local tool="$1"
  local cmd="$2"
  local from_path=""

  from_path="$(command -v "$cmd" 2>/dev/null || true)"
  if [[ "$tool" == "agy" ]]; then
    if [[ -n "$from_path" ]]; then
      printf '%s' "$from_path"
      return 0
    fi
    if [[ -x "$agy_install_dir/agy" ]]; then
      printf '%s' "$agy_install_dir/agy"
      return 0
    fi
    return 1
  fi

  if [[ -x "$npm_prefix/bin/$cmd" ]]; then
    printf '%s' "$npm_prefix/bin/$cmd"
    return 0
  fi
  if [[ -n "$from_path" ]]; then
    printf '%s' "$from_path"
    return 0
  fi
  return 1
}

get_version() {
  local bin="$1"
  local out="" node_path=""
  [[ -x "$bin" ]] || return 1
  # npm-installed launchers commonly use `#!/usr/bin/env node`. Resolve npm
  # lazily for those binaries so dry-run works with nvm/non-Homebrew Node too,
  # while an agy-only run still has no npm dependency.
  if [[ "$bin" == "$npm_prefix/bin/"* ]]; then
    ensure_npm || true
  fi
  # 只覆盖 PATH，确保 Homebrew arm64 node 优先（node-script CLI 的 env node 需要它；
  # 必须含 /opt/homebrew/bin，否则 brew 迁移后找不到 node 导致 version check 全 UNKNOWN）
  if [[ -n "$NPM_BIN" ]]; then
    node_path="$(dirname "$NPM_BIN"):"
  fi
  local clean_path="${node_path}$npm_prefix/bin:$agy_install_dir:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin"
  if out="$(PATH="$clean_path" "$bin" --version 2>/dev/null)"; then
    extract_version "$out"; return 0
  fi
  if out="$(PATH="$clean_path" "$bin" version 2>/dev/null)"; then
    extract_version "$out"; return 0
  fi
  printf 'UNKNOWN'; return 0
}

binary_note() {
  local tool="$1"
  local cmd="$2"
  local bin="$3"
  local from_path=""
  local note="path=$bin"

  if [[ "$tool" == "agy" ]]; then
    from_path="$(command -v "$cmd" 2>/dev/null || true)"
    if [[ -z "$from_path" ]]; then
      note="$note; PATH missing"
    elif [[ ! "$from_path" -ef "$bin" ]]; then
      note="$note; PATH resolves to $from_path"
    fi
  fi
  printf '%s' "$note"
}

agy_install_tmp=""
cleanup_agy_install_tmp() {
  if [[ -n "$agy_install_tmp" && -d "$agy_install_tmp" ]]; then
    rm -rf "$agy_install_tmp"
  fi
  agy_install_tmp=""
}
trap cleanup_agy_install_tmp EXIT

# Detect how claude was installed so the right upgrade command is used.
# Returns one of: native | npm | brew | desktop | unknown
detect_claude_method() {
  local bin="$1"
  local link_target
  link_target="$(readlink "$bin" 2>/dev/null || true)"

  # Desktop app — Application Support/Claude/claude-code/
  case "$bin" in
    *"/Application Support/Claude/"*) printf 'desktop'; return ;;
  esac
  case "$link_target" in
    *"/Application Support/Claude/"*) printf 'desktop'; return ;;
  esac

  # Native install — symlink points into ~/.local/share/claude/versions/
  case "$link_target" in
    *"/.local/share/claude/"*) printf 'native'; return ;;
  esac
  case "$bin" in
    "$HOME"/.local/share/claude/*) printf 'native'; return ;;
  esac

  # npm install — binary under npm prefix or symlink through node_modules
  case "$bin" in
    "$npm_prefix"/*) printf 'npm'; return ;;
  esac
  case "$link_target" in
    *"/node_modules/"*) printf 'npm'; return ;;
  esac

  # Homebrew cask — check brew list before falling through
  if command -v brew >/dev/null 2>&1; then
    if brew list --cask claude-code@latest >/dev/null 2>&1 || \
       brew list --cask claude-code >/dev/null 2>&1; then
      printf 'brew'; return
    fi
  fi

  # Unknown — fall back to native update command (current official default)
  printf 'unknown'
}

# Return the installed brew cask name for claude-code, or exit 1 if not found.
detect_brew_claude_cask() {
  command -v brew >/dev/null 2>&1 || return 1
  if brew list --cask claude-code@latest >/dev/null 2>&1; then
    printf 'claude-code@latest'
  elif brew list --cask claude-code >/dev/null 2>&1; then
    printf 'claude-code'
  else
    return 1
  fi
}

# Safely move the Homebrew Claude installation from the stable cask to the
# @latest cask. Fetch before uninstalling and restore the stable cask if the
# target install fails. The caller must gate this behind CLAUDE_CHANNEL=latest.
migrate_brew_claude_to_latest() {
  local current_cask="$1"
  [[ "$current_cask" == "claude-code@latest" ]] && return 0
  [[ "$current_cask" == "claude-code" ]] || return 1

  if ! brew fetch --cask claude-code@latest >>"$log_file" 2>&1; then
    return 1
  fi
  if ! brew uninstall --cask claude-code >>"$log_file" 2>&1; then
    return 1
  fi
  if brew install --cask claude-code@latest >>"$log_file" 2>&1; then
    return 0
  fi

  printf '%s\n' 'claude @latest install failed; restoring stable cask' >>"$log_file"
  brew install --cask claude-code >>"$log_file" 2>&1 || true
  return 1
}

# Returns 0 if the binary was installed via npm (under npm prefix or symlink
# through node_modules), 1 otherwise.
is_npm_install() {
  local bin="$1"
  local link_target
  link_target="$(readlink "$bin" 2>/dev/null || true)"
  case "$bin" in
    "$npm_prefix"/*) return 0 ;;
  esac
  case "$link_target" in
    *"/node_modules/"*) return 0 ;;
  esac
  return 1
}

# Returns a non-empty recommendation string when the binary's install method
# differs from the tool's officially recommended one; empty otherwise.
recommend_install_note() {
  local tool="$1" bin="$2"
  case "$tool" in
    codex)
      is_npm_install "$bin" && \
        printf 'npm detected (legacy); recommend: native curl installer (curl -fsSL https://chatgpt.com/codex/install.sh | sh)'
      ;;
    qwen)
      is_npm_install "$bin" && \
        printf 'npm detected; recommend: native curl installer'
      ;;
    opencode)
      is_npm_install "$bin" && \
        printf 'npm detected; recommend: native curl installer (curl -fsSL https://opencode.ai/install | bash)'
      ;;
    kimi)
      is_npm_install "$bin" && \
        printf 'npm detected; recommend: brew install kimi-code'
      ;;
    claude)
      [[ "$(detect_claude_method "$bin")" == "npm" ]] && \
        printf 'npm detected (legacy); recommend: native installer (claude.ai/download)'
      ;;
  esac
  return 0
}

# Detect if a binary was installed via a Homebrew formula by checking whether
# its resolved path runs through the Homebrew Cellar.
# Prints the formula name and returns 0 on success, returns 1 otherwise.
# Does NOT handle casks (no Cellar path); use brew list --cask for those.
detect_brew_formula_from_bin() {
  local bin="$1"
  command -v brew >/dev/null 2>&1 || return 1

  local link_target resolved_target homebrew_prefix
  link_target="$(readlink "$bin" 2>/dev/null || true)"
  homebrew_prefix="$(brew --prefix 2>/dev/null)" || return 1
  homebrew_prefix="$(cd "$homebrew_prefix" 2>/dev/null && pwd -P)" || return 1

  # Homebrew bin links are normally relative (for example
  # ../Cellar/kimi-code/0.27.0/bin/kimi). Resolve the parent directory before
  # matching so a valid formula install is not mistaken for a native install.
  resolved_target="$link_target"
  if [[ -n "$link_target" ]]; then
    local target_path target_dir target_base physical_dir
    target_path="$link_target"
    [[ "$target_path" == /* ]] || target_path="$(dirname "$bin")/$target_path"
    target_dir="$(dirname "$target_path")"
    target_base="$(basename "$target_path")"
    physical_dir="$(cd "$target_dir" 2>/dev/null && pwd -P || true)"
    if [[ -n "$physical_dir" ]]; then
      resolved_target="$physical_dir/$target_base"
    fi
  fi

  local check formula
  for check in "$resolved_target" "$link_target" "$bin"; do
    [[ -z "$check" ]] && continue
    case "$check" in
      "$homebrew_prefix"/Cellar/*)
        formula="${check#"$homebrew_prefix/Cellar/"}"
        formula="${formula%%/*}"
        [[ -n "$formula" ]] && printf '%s' "$formula" && return 0
        ;;
    esac
  done
  return 1
}

install_agy() {
  local installer_url="https://antigravity.google/cli/install.sh"
  local installer_file staging_home

  command -v curl >/dev/null 2>&1 || return 1
  agy_install_tmp="$(mktemp -d "${TMPDIR:-/tmp}/soia-agy-install.XXXXXX")" || return 1
  installer_file="$agy_install_tmp/install.sh"
  staging_home="$agy_install_tmp/home"
  mkdir -p "$staging_home"

  if ! curl --proto '=https' --tlsv1.2 -fsSL -o "$installer_file" "$installer_url" >>"$log_file" 2>&1; then
    cleanup_agy_install_tmp
    return 1
  fi
  if ! bash -n "$installer_file" >>"$log_file" 2>&1; then
    cleanup_agy_install_tmp
    return 1
  fi

  # The vendor installer normally edits shell profiles to remove aliases and add
  # PATH entries. A temporary HOME contains those side effects while --dir puts
  # the verified native binary in the user-selected installation directory.
  if ! HOME="$staging_home" bash "$installer_file" --dir "$agy_install_dir" >>"$log_file" 2>&1; then
    cleanup_agy_install_tmp
    return 1
  fi
  cleanup_agy_install_tmp
  [[ -x "$agy_install_dir/agy" ]]
}

had_failure=0
print_result() {
  local tool="$1" cmd="$2" old="$3" new="$4" status="$5" note="$6"
  [[ "$status" == "FAILED" ]] && had_failure=1
  printf '%-10s %-12s %-18s %-18s %-14s %s\n' "$tool" "$cmd" "$old" "$new" "$status" "$note" | tee -a "$log_file"
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
    agy)      cmd="agy" ;;
    qwen)     cmd="qwen";     package="@qwen-code/qwen-code" ;;
    mmx)      cmd="mmx";      package="mmx-cli" ;;
    kimi)     cmd="kimi";     package="@moonshot-ai/kimi-code" ;;
    opencode) cmd="opencode"; package="opencode-ai" ;;
    qodercli) cmd="qodercli" ;;
    cursor)   cmd="cursor" ;;
    *)        cmd="$tool" ;;
  esac

  local bin path_bin
  bin="$(resolve_bin "$tool" "$cmd" || true)"
  if [[ -z "$bin" ]]; then
    if [[ "$tool" == "agy" && "$dry_run" != "1" && "$agy_install" == "1" ]]; then
      if ! install_agy; then
        print_result "$tool" "$cmd" "-" "-" "FAILED" "official installer failed; see log"
        return
      fi
      bin="$agy_install_dir/agy"
      local installed_version install_note install_status
      installed_version="$(get_version "$bin")"
      install_note="$(binary_note "$tool" "$cmd" "$bin"); official installer"
      path_bin="$(command -v "$cmd" 2>/dev/null || true)"
      install_status="INSTALLED"
      if [[ -z "$path_bin" || ! "$path_bin" -ef "$bin" ]]; then
        install_status="MANUAL"
      fi
      if [[ -z "$installed_version" || "$installed_version" == "UNKNOWN" ]]; then
        print_result "$tool" "$cmd" "-" "-" "FAILED" "version check failed after official install; path=$bin"
      else
        print_result "$tool" "$cmd" "-" "$installed_version" "$install_status" "$install_note"
      fi
      return
    fi
    if [[ "$tool" == "agy" && "$dry_run" != "1" ]]; then
      print_result "$tool" "$cmd" "-" "-" "MANUAL" "not installed; set AGY_INSTALL=1 for official install"
    else
      print_result "$tool" "$cmd" "-" "-" "NOT_INSTALLED" "command not found"
    fi
    return
  fi

  local old_version new_version status note
  old_version="$(get_version "$bin")"
  local _rec_note
  _rec_note="$(recommend_install_note "$tool" "$bin")"

  if [[ "$dry_run" == "1" ]]; then
    local _dry_note
    _dry_note="$(binary_note "$tool" "$cmd" "$bin"); no upgrade"
    if [[ "$tool" == "claude" && "$(detect_claude_method "$bin")" == "brew" ]]; then
      local _dry_cask
      _dry_cask="$(detect_brew_claude_cask || true)"
      if [[ -n "$_dry_cask" ]]; then
        _dry_note="$_dry_note; channel=$_dry_cask"
        if [[ "$_dry_cask" == "claude-code" && "$claude_channel" == "latest" ]]; then
          _dry_note="$_dry_note; would switch to claude-code@latest"
        elif [[ "$_dry_cask" == "claude-code" ]]; then
          _dry_note="$_dry_note; preserved (set CLAUDE_CHANNEL=latest only with channel-switch authorization)"
        fi
      fi
    fi
    [[ -n "$_rec_note" ]] && _dry_note="$_dry_note; $_rec_note"
    print_result "$tool" "$cmd" "$old_version" "N/A" "SKIP_DRY_RUN" "$_dry_note"
    return
  fi

  case "$tool" in
    codex|mmx)
      # Self-update handles native, brew cask, and npm automatically (per official docs)
      if ! "$bin" update >>"$log_file" 2>&1; then
        print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
          "$cmd update failed; path=$bin"
        return
      fi
      ;;
    gemini|qwen|opencode|kimi)
      local brew_formula=""
      brew_formula="$(detect_brew_formula_from_bin "$bin")" || true
      if [[ -n "$brew_formula" ]]; then
        if ! brew upgrade "$brew_formula" >>"$log_file" 2>&1; then
          print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
            "brew upgrade $brew_formula failed; path=$bin"
          return
        fi
      elif is_npm_install "$bin"; then
        if ! ensure_npm; then
          print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "npm not found for $package"
          return
        fi
        if ! "${NPM_ENV[@]}" "$NPM_BIN" install -g --prefix "$npm_prefix" \
          "$package" >>"$log_file" 2>&1; then
          print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
            "npm install -g $package failed"
          return
        fi
      else
        # Standalone/native install
        case "$tool" in
          gemini|qwen)
            if ! "$bin" update >>"$log_file" 2>&1; then
              print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
                "$cmd update failed; path=$bin"
              return
            fi
            ;;
          kimi)
            if ! "$bin" upgrade >>"$log_file" 2>&1; then
              print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
                "kimi upgrade failed; path=$bin"
              return
            fi
            ;;
          opencode)
            print_result "$tool" "$cmd" "$old_version" "$old_version" "MANUAL" \
              "native install; re-run: curl -fsSL https://opencode.ai/install | bash; path=$bin"
            return
            ;;
        esac
      fi
      ;;
    claude)
      local install_method cask
      install_method="$(detect_claude_method "$bin")"
      case "$install_method" in
        native|unknown)
          if ! "$bin" update >>"$log_file" 2>&1; then
            print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
              "claude update failed; path=$bin"
            return
          fi
          ;;
        brew)
          if ! cask="$(detect_brew_claude_cask)"; then
            print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
              "brew cask detection failed; path=$bin"
            return
          fi
          if [[ "$cask" == "claude-code" && "$claude_channel" == "latest" ]]; then
            if ! migrate_brew_claude_to_latest "$cask"; then
              print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
                "Claude channel switch to claude-code@latest failed; stable cask restore attempted"
              return
            fi
            cask="claude-code@latest"
          elif ! brew upgrade --cask "$cask" >>"$log_file" 2>&1; then
            print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
              "brew upgrade --cask $cask failed; path=$bin"
            return
          fi
          ;;
        npm)
          if ! ensure_npm; then
            print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
              "npm not found for $package"
            return
          fi
          if ! "${NPM_ENV[@]}" "$NPM_BIN" install -g --prefix "$npm_prefix" \
            "$package" >>"$log_file" 2>&1; then
            print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" \
              "npm install -g $package failed"
            return
          fi
          ;;
        desktop)
          print_result "$tool" "$cmd" "$old_version" "$old_version" "MANUAL" \
            "Desktop-managed; update via Claude Desktop app; path=$bin"
          return
          ;;
      esac
      ;;
    agy)
      if ! "$bin" update >>"$log_file" 2>&1; then
        print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "agy update failed; path=$bin"
        return
      fi
      ;;
    qodercli)
      if ! "$bin" update >>"$log_file" 2>&1; then
        print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "qodercli update failed"
        return
      fi
      ;;
    cursor)
      if [[ -z "${CURSOR_UPGRADE_CMD:-}" ]]; then
        print_result "$tool" "$cmd" "$old_version" "$old_version" "MANUAL" "no default updater; set CURSOR_UPGRADE_CMD"
        return
      fi
      if ! bash -lc "$CURSOR_UPGRADE_CMD" >>"$log_file" 2>&1; then
        print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "CURSOR_UPGRADE_CMD failed"
        return
      fi
      ;;
    *)
      print_result "$tool" "$cmd" "$old_version" "$old_version" "MANUAL" "no upgrader config"
      return
      ;;
  esac

  bin="$(resolve_bin "$tool" "$cmd" || true)"
  if [[ -z "$bin" ]]; then
    print_result "$tool" "$cmd" "$old_version" "$old_version" "FAILED" "command missing after upgrade"
    return
  fi
  new_version="$(get_version "$bin")"
  if [[ -z "$new_version" || "$new_version" == "UNKNOWN" ]]; then
    status="FAILED"; note="version check failed after upgrade"; new_version="$old_version"
  elif [[ "$new_version" != "$old_version" ]]; then
    status="UPDATED"; note="upgraded; $(binary_note "$tool" "$cmd" "$bin")"
  else
    status="ALREADY_LATEST"; note="no version delta; $(binary_note "$tool" "$cmd" "$bin")"
  fi
  if [[ "$tool" == "agy" ]]; then
    path_bin="$(command -v "$cmd" 2>/dev/null || true)"
    if [[ -z "$path_bin" || ! "$path_bin" -ef "$bin" ]]; then
      status="MANUAL"
      note="update complete; $(binary_note "$tool" "$cmd" "$bin")"
    fi
  fi
  [[ -n "$_rec_note" ]] && note="$note; $_rec_note"
  if [[ "$tool" == "claude" && "$(detect_claude_method "$bin")" == "brew" ]]; then
    local final_cask
    final_cask="$(detect_brew_claude_cask || true)"
    [[ -n "$final_cask" ]] && note="$note; channel=$final_cask"
    if [[ "$final_cask" == "claude-code" && "$claude_channel" == "preserve" ]]; then
      note="$note; stable channel preserved"
    fi
  fi

  print_result "$tool" "$cmd" "$old_version" "$new_version" "$status" "$note"
}

print_header

# Gemini CLI remains supported for Standard/Enterprise, API-key, and Vertex AI
# users, but it is intentionally opt-in. Including it in the default batch would
# reinstall a CLI that consumer Google-login users have just migrated away from.
default_tools=(codex claude agy kimi mmx qwen opencode qodercli cursor)
all_tools=("${default_tools[@]}")

tool_selector="${TOOLS:-${NPM_PACKAGES:-}}"
if [[ -n "$tool_selector" ]]; then
  selected=()
  IFS=',' read -r -a selected <<<"$tool_selector"
  all_tools=()
  for tool in "${selected[@]}"; do
    tool="${tool#"${tool%%[![:space:]]*}"}"
    tool="${tool%"${tool##*[![:space:]]}"}"
    [[ -n "$tool" ]] && all_tools+=("$tool")
  done
fi

for tool in "${all_tools[@]}"; do
  upgrade_tool "$tool"
done

if [[ "$had_failure" == "1" ]]; then
  log "DONE_WITH_FAILURES. detail log: $log_file"
  exit 1
fi
log "DONE. detail log: $log_file"
