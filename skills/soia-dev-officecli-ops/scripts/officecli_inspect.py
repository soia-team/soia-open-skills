#!/usr/bin/env python3
"""Inspect an Office file through a disposable copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from officecli_env import check_environment, resolve_binary


OFFICE_SUFFIXES = {".docx", ".xlsx", ".pptx"}
READ_COMMANDS = {"view", "get", "query", "validate"}


def normalized(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_plan(
    *,
    input_path: Path,
    office_args: list[str],
    artifact_output: Path | None,
    overwrite: bool,
) -> dict[str, Any]:
    if office_args and office_args[0] == "--":
        office_args = office_args[1:]
    if not office_args:
        raise ValueError("an OfficeCLI read command is required after --")

    command = office_args[0].lower()
    if command not in READ_COMMANDS:
        raise ValueError(f"command '{command}' is not in the read allowlist")

    source = normalized(input_path)
    if not source.is_file():
        raise ValueError("input file does not exist")
    if source.suffix.lower() not in OFFICE_SUFFIXES:
        raise ValueError("input must end in .docx, .xlsx, or .pptx")

    output: Path | None = None
    if artifact_output is not None:
        if command != "view":
            raise ValueError("--artifact-output is supported only for view commands")
        output = normalized(artifact_output)
        if output.exists() and not overwrite:
            raise ValueError("artifact output exists; explicit --overwrite confirmation is required")

    return {
        "command": command,
        "source": str(source),
        "office_args": office_args,
        "artifact_output": str(output) if output else None,
        "overwrite": overwrite,
        "actions": ["copy_to_temporary_file", f"officecli_{command}", "close_temporary_resident"],
    }


def run_command(argv: list[str], timeout: int) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "OFFICECLI_SKIP_UPDATE": "1"},
    )
    result: dict[str, Any] = {
        "argv": argv[1:],
        "returncode": completed.returncode,
        "stdout": completed.stdout[-16000:],
        "stderr": completed.stderr[-4000:],
    }
    try:
        result["json"] = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        pass
    return result


def execute_plan(plan: dict[str, Any], *, binary: str, timeout: int) -> dict[str, Any]:
    source = Path(plan["source"])
    source_hash_before = sha256_file(source)
    artifact_output = Path(plan["artifact_output"]) if plan["artifact_output"] else None
    if artifact_output:
        artifact_output.parent.mkdir(parents=True, exist_ok=True)
        if artifact_output.exists():
            artifact_output.unlink()

    with tempfile.TemporaryDirectory(prefix="soia-officecli-inspect-") as directory:
        temporary = Path(directory) / source.name
        shutil.copy2(source, temporary)
        office_args = list(plan["office_args"])
        argv = [binary, office_args[0], str(temporary), *office_args[1:]]
        if artifact_output:
            argv.extend(["-o", str(artifact_output)])
        inspection = run_command(argv, timeout)
        close = run_command([binary, "close", str(temporary)], timeout)

    source_hash_after = sha256_file(source)
    source_unchanged = source_hash_before == source_hash_after
    success = inspection["returncode"] == 0 and close["returncode"] == 0 and source_unchanged
    if artifact_output:
        success = success and artifact_output.is_file() and artifact_output.stat().st_size > 0
    return {
        "success": success,
        "source_unchanged": source_unchanged,
        "source_sha256": source_hash_after,
        "artifact_output": str(artifact_output) if artifact_output else None,
        "inspection": inspection,
        "close": close,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Office source file.")
    parser.add_argument("--artifact-output", type=Path, help="Optional view HTML/PNG output.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing artifact output.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without executing.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per OfficeCLI command.")
    parser.add_argument("office_args", nargs=argparse.REMAINDER, help="Read command after --.")
    args = parser.parse_args(argv)

    try:
        plan = build_plan(
            input_path=args.input,
            office_args=args.office_args,
            artifact_output=args.artifact_output,
            overwrite=args.overwrite,
        )
    except ValueError as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"success": True, "dry_run": True, "plan": plan}, ensure_ascii=False, indent=2))
        return 0

    environment = check_environment()
    binary = resolve_binary()
    if environment["status"] != "ok" or not binary:
        print(json.dumps({"success": False, "environment": environment}, ensure_ascii=False), file=sys.stderr)
        return 3

    try:
        result = execute_plan(plan, binary=binary, timeout=args.timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        print(
            json.dumps({"success": False, "error": type(exc).__name__}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 4

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
