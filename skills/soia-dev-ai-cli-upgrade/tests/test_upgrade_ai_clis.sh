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

printf '%s\n' "=== test_upgrade_ai_clis.sh: $passed passed, $failed failed ==="
[[ "$failed" -eq 0 ]]
