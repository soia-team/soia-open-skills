#!/usr/bin/env python3
# @created_by openai/gpt-5
# @created_at 2026-07-11
# @modified_by openai/gpt-5
# @modified_at 2026-07-11
# @version 0.1.0
# @description Run a Claude Code prompt file through stdin without shell quoting or option confusion.
# @changelog Initial version with dry-run, timeout handling, and an offline stdin regression test.
"""Run a persisted prompt through Claude Code without putting it in argv.

Prompts may begin with YAML frontmatter (``---``), contain shell metacharacters,
or exceed a comfortable command-line length. Passing the prompt through stdin
avoids both shell interpolation and CLI option confusion.

The script writes Claude stdout unchanged to stdout so JSON mode remains
machine-readable. Diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

DEFAULT_TIMEOUT_SECONDS = 900


def build_command(args: argparse.Namespace) -> list[str]:
    command = [
        args.claude_bin,
        "--permission-mode",
        args.permission_mode,
        "--print",
        "--output-format",
        args.output_format,
    ]
    if args.tools:
        command.extend(["--tools", args.tools])
    if args.model:
        command.extend(["--model", args.model])
    if args.effort:
        command.extend(["--effort", args.effort])
    if not args.persist_session:
        command.append("--no-session-persistence")
    return command


def run_with_stdin(command: Sequence[str], prompt: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_selftest() -> int:
    prompt = "---\ntitle: regression fixture\n---\nReview this file.\n"
    probe = [
        sys.executable,
        "-c",
        (
            "import json,sys; data=sys.stdin.read(); "
            "print(json.dumps({'starts_with_yaml': data.startswith('---'), "
            "'chars': len(data)}))"
        ),
    ]
    result = run_with_stdin(probe, prompt, timeout=10)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {}
    checks = {
        "process_passed": result.returncode == 0,
        "yaml_frontmatter_reached_stdin": payload.get("starts_with_yaml") is True,
        "prompt_not_truncated": payload.get("chars") == len(prompt),
        "prompt_not_in_argv": prompt not in probe,
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    return 0 if all(checks.values()) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Claude Code prompt file through stdin and preserve stdout."
    )
    parser.add_argument("--prompt-file", type=Path, help="UTF-8 prompt file to send through stdin.")
    parser.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    parser.add_argument("--model", help="Explicit Claude model id or alias.")
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Claude reasoning effort supported by the installed CLI.",
    )
    parser.add_argument("--permission-mode", default="dontAsk")
    parser.add_argument("--tools", help="Comma-separated Claude tool allowlist, e.g. Read,Grep,Glob.")
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="json",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--persist-session", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.selftest:
        return run_selftest()
    if args.prompt_file is None:
        print("ERROR: --prompt-file is required unless --selftest is used", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("ERROR: --timeout must be positive", file=sys.stderr)
        return 2
    try:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read prompt file: {exc}", file=sys.stderr)
        return 2
    if not prompt.strip():
        print("ERROR: prompt file is empty", file=sys.stderr)
        return 2

    command = build_command(args)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "command": command,
                    "prompt_file": str(args.prompt_file),
                    "prompt_chars": len(prompt),
                    "transport": "stdin",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    try:
        result = run_with_stdin(command, prompt, timeout=args.timeout)
    except FileNotFoundError:
        print(f"ERROR: Claude CLI not found: {args.claude_bin}", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired:
        print(f"ERROR: Claude CLI timed out after {args.timeout}s", file=sys.stderr)
        return 124

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
