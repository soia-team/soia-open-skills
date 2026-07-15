#!/usr/bin/env bash
# @created_by  openai/gpt-5
# @created_at  2026-07-11 00:15:52
# @modified_by openai/gpt-5
# @modified_at 2026-07-11 12:00:00
# @version     0.2.0
# @description Offline regression tests for the AI CLI upgrade helper.
# @changelog   Cover agy dry-run/update/install plus explicit-only Gemini upgrade isolation.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
upgrade_script="$(cd "$script_dir/.." && pwd)/scripts/upgrade-ai-clis.sh"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/test-upgrade-ai-clis.XXXXXX")"
trap 'rm -rf -- "$test_root"' EXIT

passed=0
failed=0
run_output=""
run_rc=0

pass() {
  printf '[PASS] %s\n' "$1"
  passed=$((passed + 1))
}

fail() {
  printf '[FAIL] %s\n' "$1" >&2
  failed=$((failed + 1))
}

check() {
  local name="$1"
  shift
  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

contains() {
  [[ "$1" == *"$2"* ]]
}

run_upgrade() {
  if run_output="$(env "$@" /bin/bash "$upgrade_script" 2>&1)"; then
    run_rc=0
  else
    run_rc=$?
  fi
}

make_fake_agy() {
  local bin_dir="$1"
  mkdir -p "$bin_dir"
  cat >"$bin_dir/agy" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  --version|version)
    cat "$FAKE_AGY_STATE"
    ;;
  update)
    printf 'update\n' >>"$FAKE_AGY_MARKER"
    if [[ "${FAKE_AGY_UPDATE_RC:-0}" != "0" ]]; then
      exit "$FAKE_AGY_UPDATE_RC"
    fi
    printf '%s\n' "${FAKE_AGY_AFTER_VERSION:-1.0.0}" >"$FAKE_AGY_STATE"
    ;;
  *)
    exit 2
    ;;
esac
SH
  chmod +x "$bin_dir/agy"
}

make_fake_claude() {
  local bin_path="$1"
  mkdir -p "$(dirname "$bin_path")"
  cat >"$bin_path" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  --version|version)
    cat "$FAKE_CLAUDE_STATE"
    ;;
  update)
    printf 'update\n' >>"$FAKE_CLAUDE_MARKER"
    if [[ "${FAKE_CLAUDE_UPDATE_RC:-0}" != "0" ]]; then
      exit "$FAKE_CLAUDE_UPDATE_RC"
    fi
    printf '%s\n' "${FAKE_CLAUDE_AFTER_VERSION:-2.1.210}" >"$FAKE_CLAUDE_STATE"
    ;;
  *)
    exit 2
    ;;
esac
SH
  chmod +x "$bin_path"
}

run_case() {
  local case_dir="$1"
  shift
  mkdir -p "$case_dir/home" "$case_dir/logs" "$case_dir/tmp"
  run_upgrade \
    "HOME=$case_dir/home" \
    "LOG_DIR=$case_dir/logs" \
    "TMPDIR=$case_dir/tmp" \
    "SOIA_DEV_AI_CLI_UPGRADE_CONFIG_FILE=$case_dir/no-config.yml" \
    "$@"
}

# 1. A fresh log directory must not trip set -e/pipefail. Dry-run reads agy
# version and never calls update or npm.
case1="$test_root/dry-present"
mkdir -p "$case1/bin"
make_fake_agy "$case1/bin"
printf '1.0.0\n' >"$case1/state"
run_case "$case1" \
  "PATH=$case1/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=agy" "DRY_RUN=1" "NPM_BIN=$case1/missing-npm" \
  "FAKE_AGY_STATE=$case1/state" "FAKE_AGY_MARKER=$case1/update.marker"
check "fresh log dir dry-run exits zero" test "$run_rc" -eq 0
check "dry-run reports agy without update" contains "$run_output" "SKIP_DRY_RUN"
check "dry-run does not call agy update" test ! -e "$case1/update.marker"
check "dry-run writes one log" test "$(find "$case1/logs" -type f -name 'cli-upgrade-*.log' | wc -l | tr -d ' ')" -eq 1

# 2. Native update is independent of npm and reports a real version delta.
case2="$test_root/live-update"
mkdir -p "$case2/bin"
make_fake_agy "$case2/bin"
printf '1.0.0\n' >"$case2/state"
run_case "$case2" \
  "PATH=$case2/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=agy" "DRY_RUN=0" "NPM_BIN=$case2/missing-npm" \
  "FAKE_AGY_STATE=$case2/state" "FAKE_AGY_MARKER=$case2/update.marker" \
  "FAKE_AGY_AFTER_VERSION=1.1.0"
check "agy update works without npm" test "$run_rc" -eq 0
check "agy update reports UPDATED" contains "$run_output" "UPDATED"
check "agy update command was called" test -s "$case2/update.marker"

# 3. A true updater failure is aggregated, logged, and returned non-zero after
# processing instead of being hidden behind DONE.
case3="$test_root/live-failure"
mkdir -p "$case3/bin"
make_fake_agy "$case3/bin"
printf '1.0.0\n' >"$case3/state"
run_case "$case3" \
  "PATH=$case3/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=agy" "DRY_RUN=0" \
  "FAKE_AGY_STATE=$case3/state" "FAKE_AGY_MARKER=$case3/update.marker" \
  "FAKE_AGY_UPDATE_RC=7"
check "failed agy update returns non-zero" test "$run_rc" -eq 1
check "failed agy update reports FAILED" contains "$run_output" "FAILED"
check "failure summary is explicit" contains "$run_output" "DONE_WITH_FAILURES"

# 4/5. Missing agy never touches the network in dry-run or without the explicit
# install gate.
case4="$test_root/missing"
mkdir -p "$case4/bin"
cat >"$case4/bin/curl" <<'SH'
#!/usr/bin/env bash
printf 'called\n' >>"$FAKE_CURL_MARKER"
exit 9
SH
chmod +x "$case4/bin/curl"
run_case "$case4" \
  "PATH=$case4/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=agy" "DRY_RUN=1" "AGY_INSTALL_DIR=$case4/install" \
  "FAKE_CURL_MARKER=$case4/curl.marker"
check "missing agy dry-run reports NOT_INSTALLED" contains "$run_output" "NOT_INSTALLED"
check "missing agy dry-run does not call curl" test ! -e "$case4/curl.marker"
run_case "$case4" \
  "PATH=$case4/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=agy" "DRY_RUN=0" "AGY_INSTALL=0" "AGY_INSTALL_DIR=$case4/install" \
  "FAKE_CURL_MARKER=$case4/curl.marker"
check "missing agy live run requires install gate" contains "$run_output" "MANUAL"
check "closed install gate does not call curl" test ! -e "$case4/curl.marker"

# 6. Gated install fetches only the official HTTPS endpoint, isolates vendor
# HOME/profile writes, and reports PATH follow-up without modifying real HOME.
case6="$test_root/install"
mkdir -p "$case6/bin" "$case6/home"
printf 'alias agy="legacy"\n' >"$case6/home/.zshrc"
before_profile="$(shasum -a 256 "$case6/home/.zshrc" | awk '{print $1}')"
cat >"$case6/fake-installer.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
target=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) target="$2"; shift 2 ;;
    *) exit 64 ;;
  esac
done
printf '%s\n' "$HOME" >"$FAKE_INSTALLER_HOME_RECORD"
printf 'vendor touched staging only\n' >>"$HOME/.zshrc"
mkdir -p "$target"
cat >"$target/agy" <<'BIN'
#!/usr/bin/env bash
case "${1:-}" in
  --version|version) printf '9.9.9\n' ;;
  update) printf 'already latest\n' ;;
  *) exit 2 ;;
esac
BIN
chmod +x "$target/agy"
SH
chmod +x "$case6/fake-installer.sh"
cat >"$case6/bin/curl" <<'SH'
#!/usr/bin/env bash
out=""
url=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    https://*) url="$1"; shift ;;
    *) shift ;;
  esac
done
printf '%s\n' "$url" >"$FAKE_CURL_URL_RECORD"
cp "$FAKE_INSTALLER_SOURCE" "$out"
SH
chmod +x "$case6/bin/curl"
run_case "$case6" \
  "HOME=$case6/home" \
  "PATH=$case6/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=agy" "DRY_RUN=0" "AGY_INSTALL=1" \
  "AGY_INSTALL_DIR=$case6/install" \
  "FAKE_INSTALLER_SOURCE=$case6/fake-installer.sh" \
  "FAKE_INSTALLER_HOME_RECORD=$case6/installer-home" \
  "FAKE_CURL_URL_RECORD=$case6/curl-url"
after_profile="$(shasum -a 256 "$case6/home/.zshrc" | awk '{print $1}')"
check "gated install creates agy" test -x "$case6/install/agy"
check "gated install reports PATH follow-up" contains "$run_output" "MANUAL"
check "installer source is fixed official HTTPS URL" contains "$(cat "$case6/curl-url")" "https://antigravity.google/cli/install.sh"
check "real shell profile is unchanged" test "$before_profile" = "$after_profile"
check "installer ran with isolated HOME" test "$(cat "$case6/installer-home")" != "$case6/home"
check "isolated installer HOME is cleaned" test ! -d "$(cat "$case6/installer-home")"

# 7. Gemini remains an npm lane while agy uses its own native update command.
case7="$test_root/channel-isolation"
mkdir -p "$case7/bin" "$case7/prefix/bin"
make_fake_agy "$case7/bin"
printf '1.0.0\n' >"$case7/agy-state"
printf '0.50.0\n' >"$case7/gemini-state"
cat >"$case7/prefix/bin/gemini" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --version|version) cat "$case7/gemini-state" ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case7/prefix/bin/gemini"
cat >"$case7/fake-npm" <<SH
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"$case7/npm-args"
printf '0.51.0\n' >"$case7/gemini-state"
SH
chmod +x "$case7/fake-npm"
run_case "$case7" \
  "PATH=$case7/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=gemini,agy" "DRY_RUN=0" \
  "NPM_PREFIX=$case7/prefix" "NPM_BIN=$case7/fake-npm" \
  "FAKE_AGY_STATE=$case7/agy-state" "FAKE_AGY_MARKER=$case7/agy-update.marker" \
  "FAKE_AGY_AFTER_VERSION=1.1.0"
check "combined Gemini/agy run succeeds" test "$run_rc" -eq 0
check "Gemini stays on official npm package" contains "$(cat "$case7/npm-args")" "@google/gemini-cli"
check "npm is not used for agy" test "$(grep -c 'antigravity\|agy' "$case7/npm-args" || true)" -eq 0
check "agy native update still runs" test -s "$case7/agy-update.marker"

# 8. A default consumer-safe run must not reinstall a missing Gemini CLI.
# Gemini remains available through explicit TOOLS=gemini (covered above), but
# consumers who removed it during migration must not get it back implicitly.
case8="$test_root/default-no-gemini"
mkdir -p "$case8/bin" "$case8/prefix/bin"
cat >"$case8/fake-npm" <<SH
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"$case8/npm-args"
SH
chmod +x "$case8/fake-npm"
run_case "$case8" \
  "PATH=$case8/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "DRY_RUN=0" "NPM_PREFIX=$case8/prefix" "NPM_BIN=$case8/fake-npm"
check "default run does not reinstall Gemini CLI" test ! -e "$case8/prefix/bin/gemini"
gemini_npm_count=0
if [[ -e "$case8/npm-args" ]]; then
  gemini_npm_count="$(grep -c '@google/gemini-cli' "$case8/npm-args" || true)"
fi
check "default run never asks npm for Gemini CLI" test "$gemini_npm_count" -eq 0

# 9. Native install (symlink → ~/.local/share/claude/versions/) → must use
# `claude update`, never npm.
case9="$test_root/claude-native"
mkdir -p "$case9/fakehome/.local/share/claude/versions" "$case9/fakehome/.local/bin"
make_fake_claude "$case9/fakehome/.local/share/claude/versions/fake-claude"
ln -sf "$case9/fakehome/.local/share/claude/versions/fake-claude" \
  "$case9/fakehome/.local/bin/claude"
printf '2.1.209\n' >"$case9/claude-state"
run_case "$case9" \
  "PATH=$case9/fakehome/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=claude" "DRY_RUN=0" "NPM_BIN=$case9/missing-npm" \
  "FAKE_CLAUDE_STATE=$case9/claude-state" \
  "FAKE_CLAUDE_MARKER=$case9/claude-update.marker" \
  "FAKE_CLAUDE_AFTER_VERSION=2.1.210"
check "native claude: run exits zero" test "$run_rc" -eq 0
check "native claude: reports UPDATED" contains "$run_output" "UPDATED"
check "native claude: update command was called" test -s "$case9/claude-update.marker"

# 10. npm install (binary under $npm_prefix/bin/) → must use npm install -g.
case10="$test_root/claude-npm"
mkdir -p "$case10/prefix/bin"
cat >"$case10/prefix/bin/claude" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --version|version) printf '2.1.208\n' ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case10/prefix/bin/claude"
cat >"$case10/fake-npm" <<SH
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"$case10/npm-args"
SH
chmod +x "$case10/fake-npm"
run_case "$case10" \
  "PATH=/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=claude" "DRY_RUN=0" \
  "NPM_PREFIX=$case10/prefix" "NPM_BIN=$case10/fake-npm"
check "npm claude: run exits zero" test "$run_rc" -eq 0
check "npm claude: npm called with claude-code package" \
  contains "$(cat "$case10/npm-args" || true)" "@anthropic-ai/claude-code"
check "npm claude: update not called" test ! -e "$case10/claude-update.marker"

# 11. Desktop-managed binary (symlink → path containing "Application Support/Claude")
# → must report MANUAL and never call update or npm.
case11="$test_root/claude-desktop"
mkdir -p "$case11/Application Support/Claude/claude-code" "$case11/bin"
cat >"$case11/Application Support/Claude/claude-code/claude" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  --version|version) printf '2.1.209\n' ;;
  update) printf 'should-not-reach\n'; exit 0 ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case11/Application Support/Claude/claude-code/claude"
ln -sf "$case11/Application Support/Claude/claude-code/claude" "$case11/bin/claude"
cat >"$case11/fake-npm" <<SH
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"$case11/npm-args"
SH
chmod +x "$case11/fake-npm"
run_case "$case11" \
  "PATH=$case11/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=claude" "DRY_RUN=0" \
  "NPM_BIN=$case11/fake-npm"
check "desktop claude: run exits zero" test "$run_rc" -eq 0
check "desktop claude: reports MANUAL" contains "$run_output" "MANUAL"
check "desktop claude: npm was not called" test ! -e "$case11/npm-args"

# 12. Brew formula gemini (symlink → Homebrew Cellar) → must call
# `brew upgrade gemini-cli`, not npm or self-update.
case12="$test_root/gemini-brew-formula"
mkdir -p "$case12/homebrew/Cellar/gemini-cli/0.50.0/bin" "$case12/homebrew/bin" "$case12/bin"
cat >"$case12/homebrew/Cellar/gemini-cli/0.50.0/bin/gemini" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  --version|version) printf '0.50.0\n' ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case12/homebrew/Cellar/gemini-cli/0.50.0/bin/gemini"
ln -sf "$case12/homebrew/Cellar/gemini-cli/0.50.0/bin/gemini" "$case12/homebrew/bin/gemini"
cat >"$case12/bin/brew" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --prefix) printf '%s\n' "$case12/homebrew" ;;
  upgrade)  printf '%s\n' "\$*" >>"$case12/brew-args" ;;
  list)     exit 0 ;;
  *)        exit 1 ;;
esac
SH
chmod +x "$case12/bin/brew"
run_case "$case12" \
  "PATH=$case12/homebrew/bin:$case12/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=gemini" "DRY_RUN=0" \
  "NPM_BIN=$case12/missing-npm"
check "brew formula gemini: run exits zero" test "$run_rc" -eq 0
check "brew formula gemini: brew upgrade called with formula name" \
  contains "$(cat "$case12/brew-args" || true)" "gemini-cli"
check "brew formula gemini: npm was not invoked" test ! -e "$case12/npm-args"

# 13. codex always uses its self-update command (handles native/brew/npm internally).
case13="$test_root/codex-self-update"
mkdir -p "$case13/bin"
printf '1.9.0\n' >"$case13/codex-state"
cat >"$case13/bin/codex" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --version|version) cat "$case13/codex-state" ;;
  update)
    printf 'update\n' >>"$case13/codex-update.marker"
    printf '2.0.0\n' >"$case13/codex-state"
    ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case13/bin/codex"
cat >"$case13/fake-npm" <<SH
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"$case13/npm-args"
SH
chmod +x "$case13/fake-npm"
run_case "$case13" \
  "PATH=$case13/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=codex" "DRY_RUN=0" \
  "NPM_BIN=$case13/fake-npm"
check "codex self-update: run exits zero" test "$run_rc" -eq 0
check "codex self-update: update command called" test -s "$case13/codex-update.marker"
check "codex self-update: npm not directly invoked" test ! -e "$case13/npm-args"

# 14. codex binary under npm prefix (npm-detected) → dry-run note must include
# official curl recommendation.
case14="$test_root/codex-npm-note"
mkdir -p "$case14/prefix/bin"
cat >"$case14/prefix/bin/codex" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --version|version) printf '1.8.0\n' ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case14/prefix/bin/codex"
run_case "$case14" \
  "PATH=$case14/prefix/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=codex" "DRY_RUN=1" \
  "NPM_PREFIX=$case14/prefix"
check "codex npm note: dry-run contains recommendation" \
  contains "$run_output" "recommend"

# 15. claude binary under npm prefix → dry-run note must mention native installer.
case15="$test_root/claude-npm-note"
mkdir -p "$case15/prefix/bin"
cat >"$case15/prefix/bin/claude" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --version|version) printf '2.1.208\n' ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case15/prefix/bin/claude"
run_case "$case15" \
  "PATH=$case15/prefix/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=claude" "DRY_RUN=1" \
  "NPM_PREFIX=$case15/prefix"
check "claude npm note: dry-run mentions native installer" \
  contains "$run_output" "native installer"

# 16. kimi binary under npm prefix → dry-run note must recommend brew formula.
case16="$test_root/kimi-npm-note"
mkdir -p "$case16/prefix/bin"
cat >"$case16/prefix/bin/kimi" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --version|version) printf '0.3.0\n' ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case16/prefix/bin/kimi"
run_case "$case16" \
  "PATH=$case16/prefix/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=kimi" "DRY_RUN=1" \
  "NPM_PREFIX=$case16/prefix"
check "kimi npm note: dry-run recommends brew formula" \
  contains "$run_output" "brew install kimi-code"

# 17. opencode binary under npm prefix → live upgrade note must contain
# recommendation even after successful npm run.
case17="$test_root/opencode-npm-note"
mkdir -p "$case17/prefix/bin"
cat >"$case17/prefix/bin/opencode" <<SH
#!/usr/bin/env bash
case "\${1:-}" in
  --version|version) printf '0.1.0\n' ;;
  *) exit 2 ;;
esac
SH
chmod +x "$case17/prefix/bin/opencode"
cat >"$case17/fake-npm" <<SH
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"$case17/npm-args"
SH
chmod +x "$case17/fake-npm"
run_case "$case17" \
  "PATH=$case17/prefix/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  "TOOLS=opencode" "DRY_RUN=0" \
  "NPM_PREFIX=$case17/prefix" "NPM_BIN=$case17/fake-npm"
check "opencode npm note: live upgrade contains recommendation" \
  contains "$run_output" "recommend"

printf '%s\n' "=== test_upgrade_ai_clis.sh: $passed passed, $failed failed ==="
[[ "$failed" -eq 0 ]]
