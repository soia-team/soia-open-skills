#!/bin/bash
# session_end_log.sh — 把 vault 未提交的改动摘要追加到 Agent 工作日志
# （soia-pkm-maintain skill 机械层；工作流③ AI 会话日志接入的底层脚本）
#
# 用法：
#   session_end_log.sh --vault <vault路径> [--agent <名称>] [--log-dir <vault内相对目录>]
#   session_end_log.sh [--agent <名称>]  # 也可从私有 config.yml 读取 OBSIDIAN_VAULT
#
# 参数：
#   --vault <path>   vault 根目录（未传时取私有 config.yml 里的 OBSIDIAN_VAULT；两者都没有则静默退出）
#   --agent <name>   agent 名称，决定日志子目录和节流状态文件（默认 Claude-Code；
#                    Codex 场景传 --agent Codex）
#   --log-dir <rel>  vault 内日志根目录；也可用私有 config.yml 的 SOIA_SESSION_LOG_DIR 覆盖
#
# 触发场景与节流：
#   - Claude Code 的 SessionEnd hook 每次会话结束触发一次，天然是"一次会话一条快照"。
#   - Codex 的 notify 是按"回合(turn)结束"触发，一次会话可能触发几十次；直接每次都写
#     日志会刷屏。所以本脚本用 git status --porcelain 输出内容的 md5 做节流：跟上次
#     落盘时的状态一致就直接退出，不重复写快照，只有改动内容变化时才追加。
#   - 节流状态文件：<vault>/.git/soia-session-log-<agent>.state
#   - 节流对比前会先过滤掉本脚本自己写的日志目录（默认 30_日志与思考/20_Agent工作日志，
#     可由 --log-dir / SOIA_SESSION_LOG_DIR 覆盖），
#     否则第一次创建当天日志文件后，这个新文件本身在 git status 里从"不存在"变成
#     "??"，会被误判成"内容变了"，多写一条空快照——过滤掉这个自引用噪音后，只有
#     vault 里其他地方的真实改动才会触发新快照。
#     已知局限：如果整个 "30_日志与思考" 目录在这之前从未被 git 追踪过（全新 vault
#     的第一次运行），git 会把它折叠成单独一行 "?? 30_日志与思考/"，这时过滤会连带
#     忽略该目录下同一时刻的其他真实改动——只影响"有史以来第一次运行"这一次，之后
#     该目录进入 git 追踪，不再出现折叠行。
#
# 行为：
#   - 过滤掉自身日志目录后如果没有任何未提交改动，静默退出（exit 0）。
#   - 幂等：同一份改动重复调用只会落一条快照。
#   - 不做任何 git 操作（不 add/commit/push），只读 git status。

AGENT="Claude-Code"
SESSION_LOG_DIR="${SOIA_SESSION_LOG_DIR:-30_日志与思考/20_Agent工作日志}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

load_private_env() {
  command -v python3 >/dev/null 2>&1 || return 0
  [ -f "$SCRIPT_DIR/maintain_env.py" ] || return 0
  eval "$(python3 "$SCRIPT_DIR/maintain_env.py" 2>/dev/null || true)"
}

load_private_env
SESSION_LOG_DIR="${SOIA_SESSION_LOG_DIR:-$SESSION_LOG_DIR}"
VAULT="${OBSIDIAN_VAULT:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --agent)
      AGENT="$2"
      shift 2
      ;;
    --vault)
      VAULT="$2"
      shift 2
      ;;
    --log-dir)
      SESSION_LOG_DIR="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

[ -z "$VAULT" ] && exit 0
cd "$VAULT" 2>/dev/null || exit 0

RAW_CHANGES=$(git -c core.quotepath=false status --porcelain 2>/dev/null)
[ -z "$RAW_CHANGES" ] && exit 0
SESSION_LOG_DIR="${SESSION_LOG_DIR#/}"
SESSION_LOG_DIR="${SESSION_LOG_DIR%/}"
# 过滤掉本脚本自己的日志目录：既过滤完整路径（正常情况），也过滤 git 把全新目录
# 折叠成单独一行的情况（仅发生在该目录第一次被追踪之前）
CHANGES=$(printf '%s\n' "$RAW_CHANGES" | awk -v log="$SESSION_LOG_DIR" '
  {
    path=$0
    sub(/^..[[:space:]]+/, "", path)
    if (path == log || index(path, log "/") == 1) next
    print
  }
')
[ -z "$CHANGES" ] && exit 0  # 剩下的改动只有本脚本自己的日志目录，视为无实质改动

STATE_DIR="$VAULT/.git"
STATE_FILE="$STATE_DIR/soia-session-log-${AGENT}.state"

if command -v md5 >/dev/null 2>&1; then
  HASH=$(printf '%s' "$CHANGES" | md5)
else
  HASH=$(printf '%s' "$CHANGES" | md5sum | awk '{print $1}')
fi

if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE" 2>/dev/null)" = "$HASH" ]; then
  exit 0  # 与上次快照一致：节流命中，不重复写（应对 Codex 每回合触发的场景）
fi

TODAY=$(date +%F)
NOW=$(date +%H:%M)
LOGDIR="$VAULT/$SESSION_LOG_DIR/$(date +%Y)/$AGENT"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/$TODAY.md"
if [ ! -f "$LOGFILE" ]; then
  printf -- '---\ntitle: "%s 会话改动日志 - %s"\nagent: %s\ndate: %s\n---\n\n# %s 会话改动日志 (%s)\n' \
    "$AGENT" "$TODAY" "$AGENT" "$TODAY" "$AGENT" "$TODAY" > "$LOGFILE"
fi
{
  printf '\n## %s 会话结束快照\n\n' "$NOW"
  printf '按区统计（未提交文件数）：\n\n'
  echo "$CHANGES" | awk '{print $NF}' | cut -d/ -f1 | sort | uniq -c | sort -rn | awk '{printf "- %s × %s\n", $2, $1}'
  printf '\n<details><summary>git status 明细</summary>\n\n```\n%s\n```\n\n</details>\n' "$CHANGES"
} >> "$LOGFILE"

mkdir -p "$STATE_DIR"
printf '%s' "$HASH" > "$STATE_FILE"
exit 0
