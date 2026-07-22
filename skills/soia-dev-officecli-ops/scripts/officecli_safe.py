#!/usr/bin/env python3
"""Run an allowlisted OfficeCLI mutation against a new output file."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from officecli_env import check_environment, resolve_binary


OFFICE_SUFFIXES = {".docx", ".xlsx", ".pptx"}
MUTATING_COMMANDS = {
    "create",
    "set",
    "add",
    "remove",
    "move",
    "swap",
    "batch",
    "raw-set",
    "add-part",
    "refresh",
}


def normalized(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def build_plan(
    *,
    input_path: Path | None,
    output_path: Path,
    office_args: list[str],
    overwrite: bool,
) -> dict[str, Any]:
    if office_args and office_args[0] == "--":
        office_args = office_args[1:]
    if not office_args:
        raise ValueError("an OfficeCLI mutation command is required after --")

    command = office_args[0].lower()
    if command not in MUTATING_COMMANDS:
        raise ValueError(f"command '{command}' is not in the mutation allowlist")

    output = normalized(output_path)
    if output.suffix.lower() not in OFFICE_SUFFIXES:
        raise ValueError("output must end in .docx, .xlsx, or .pptx")

    source: Path | None = None
    if command == "create":
        if input_path is not None:
            raise ValueError("create does not accept --input")
        if len(office_args) != 1:
            raise ValueError("create accepts no extra arguments in the safe wrapper")
    else:
        if input_path is None:
            raise ValueError(f"{command} requires --input")
        source = normalized(input_path)
        if not source.is_file():
            raise ValueError("input file does not exist")
        if source.suffix.lower() not in OFFICE_SUFFIXES:
            raise ValueError("input must end in .docx, .xlsx, or .pptx")
        if source.suffix.lower() != output.suffix.lower():
            raise ValueError("input and output Office formats must match")
        if source == output:
            raise ValueError("in-place mutation is disabled; choose a different --output")

    if output.exists() and not overwrite:
        raise ValueError("output already exists; explicit --overwrite confirmation is required")

    return {
        "command": command,
        "source": str(source) if source else None,
        "output": str(output),
        "overwrite": overwrite,
        "office_args": office_args,
        "actions": [
            "replace_existing_output" if output.exists() else "create_output",
            "copy_source" if source else "create_blank_document",
            f"officecli_{command}",
            "close_resident",
            "validate_schema",
            "scan_issues",
        ],
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
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-4000:],
    }
    try:
        result["json"] = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        pass
    return result


def execute_plan(plan: dict[str, Any], *, binary: str, timeout: int) -> dict[str, Any]:
    output = Path(plan["output"])
    source = Path(plan["source"]) if plan["source"] else None
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        output.unlink()
    if source:
        shutil.copy2(source, output)

    office_args = list(plan["office_args"])
    mutation_argv = [binary, office_args[0], str(output), *office_args[1:]]
    mutation = run_command(mutation_argv, timeout)
    steps: dict[str, Any] = {"mutation": mutation}

    if mutation["returncode"] != 0:
        return {"success": False, "output": str(output), "steps": steps}

    steps["close"] = run_command([binary, "close", str(output)], timeout)
    steps["validate"] = run_command([binary, "validate", str(output), "--json"], timeout)
    steps["issues"] = run_command(
        [binary, "view", str(output), "issues", "--json"], timeout
    )
    validate_payload = steps["validate"].get("json", {})
    issues_payload = steps["issues"].get("json", {})
    schema_clean = bool(validate_payload.get("success"))
    issue_count = issues_payload.get("data", {}).get("count")
    success = (
        all(step["returncode"] == 0 for step in steps.values())
        and schema_clean
        and output.is_file()
    )
    return {
        "success": success,
        "output": str(output),
        "schema_clean": schema_clean,
        "issue_count": issue_count,
        "steps": steps,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Existing Office source file.")
    parser.add_argument("--output", type=Path, required=True, help="New Office output file.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per OfficeCLI command.")
    parser.add_argument("office_args", nargs=argparse.REMAINDER, help="Mutation command after --.")
    args = parser.parse_args(argv)

    try:
        plan = build_plan(
            input_path=args.input,
            output_path=args.output,
            office_args=args.office_args,
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
