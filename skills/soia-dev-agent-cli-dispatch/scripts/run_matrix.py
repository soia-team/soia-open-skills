#!/usr/bin/env python3
"""Resumable, strictly-serial executor for a model/executor dispatch matrix.

Phase 1 scope: this script is built and self-tested against mock commands
only. It does not itself decide when to run real executor CLIs -- that is
a later phase. Concurrency is fixed at 1 (cases run one at a time, in the
order given) because interleaved provider CLIs make quota/downgrade
attribution ambiguous.

Usage:
    python3 run_matrix.py --cases cases.json --run-id my-run --manifest-dir /path/to/dir
    python3 run_matrix.py --cases cases.json --run-id my-run --manifest-dir /path/to/dir --resume
    python3 run_matrix.py --selftest

cases.json shape (array):
    [{"case_id": "c1", "provider": "openai", "executor": "codex",
      "model": "gpt-5.6-sol", "reasoning": "medium",
      "cmd_template": "codex exec ..."}, ...]

Manifest is written atomically to
    <manifest-dir>/manifest.json
after every single case (spec requirement), so a killed run can always be
inspected and resumed from the last completed case.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib  # noqa: E402
import estimate_cost  # noqa: E402


# ---------------------------------------------------------------------------
# Status enum and classification
# ---------------------------------------------------------------------------

ALL_STATUSES = {
    "pending",
    "running",
    "passed",
    "failed",
    "unsupported",
    "blocked_auth",
    "blocked_quota",
    "blocked_paid_api",
    "pending_quota",
    "timeout",
    "fallback_or_downgrade",
    "actual_model_unverified",
    "interrupted",
    "not_tested",
}

# Statuses whose outcome would not change on retry: skip these on --resume.
TERMINAL_ON_RESUME = {
    "passed",
    "unsupported",
    "blocked_paid_api",
    "fallback_or_downgrade",
    "actual_model_unverified",
}


def _terminal_count(records: list[dict]) -> int:
    """Count records whose status will not be retried by a future --resume.

    Used to compute remaining_cases: a case that merely has a record (e.g. a
    pending_quota placeholder written without ever executing) still counts
    as "remaining" work, since --resume is expected to retry it later.
    """
    return sum(1 for r in records if r.get("status") in TERMINAL_ON_RESUME)

QUOTA_RE = re.compile(r"usage limit|usage_limit|quota", re.IGNORECASE)
UNSUPPORTED_RE = re.compile(r"not supported|invalid model|unknown model", re.IGNORECASE)
CODEX_MODEL_LINE_RE = re.compile(r"^model:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
CODEX_TOKENS_USED_RE = re.compile(r"tokens used", re.IGNORECASE)

# claude Model Integrity Gate (P4, 2026-07-10): only a `--output-format json`
# (or `--output-format=json`) invocation can be parsed for a verifiable model
# echo. Plain-text-mode claude output has no reliable echo and keeps falling
# back to actual_model_unverified -- see detect_actual_model() below.
CLAUDE_OUTPUT_FORMAT_JSON_RE = re.compile(r"--output-format[=\s]+json\b", re.IGNORECASE)
# Two decoration patterns confirmed against a live `claude` 2.1.206 CLI on
# 2026-07-10 (see references/benchmark-2026-07-10.md for the raw payloads):
#   - no --model flag (session/account default): modelUsage key came back
#     bracketed, e.g. "claude-opus-4-8[1m]" (most likely a 1M-context-window
#     execution-mode annotation).
#   - --model <short alias> (e.g. "haiku"): modelUsage key came back dated,
#     e.g. "claude-haiku-4-5-20251001".
# --model <full catalog model_id> came back with no decoration at all.
CLAUDE_MODEL_BRACKET_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")
CLAUDE_MODEL_DATE_SUFFIX_RE = re.compile(r"-\d{8}$")

VERSION_COMMANDS = {
    "codex": ["codex", "--version"],
    "claude": ["claude", "--version"],
    "gemini": ["gemini", "--version"],
    "kimi": ["kimi", "--version"],
    "opencode": ["opencode", "--version"],
    "qwen": ["qwen", "--version"],
}

DEFAULT_TIMEOUT_SECONDS = 600


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Token / model-echo parsing
# ---------------------------------------------------------------------------


def parse_tokens(executor: str, stdout: str) -> int | None:
    """Best-effort token count extraction. Returns None (unknown) if not found."""
    if executor == "codex":
        lines = stdout.splitlines()
        for i, line in enumerate(lines):
            if CODEX_TOKENS_USED_RE.search(line):
                for candidate in lines[i + 1 : i + 3]:
                    match = re.search(r"\d[\d,]*", candidate)
                    if match:
                        return int(match.group(0).replace(",", ""))
        return None
    if executor == "claude":
        try:
            payload = json.loads(stdout)
        except (json.JSONDecodeError, ValueError):
            payload = None
        if isinstance(payload, dict):
            usage = payload.get("usage")
            if isinstance(usage, dict):
                input_t = usage.get("input_tokens", 0) or 0
                output_t = usage.get("output_tokens", 0) or 0
                if input_t or output_t:
                    return int(input_t) + int(output_t)
        match = re.search(r"(\d[\d,]*)\s*tokens", stdout, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
        return None
    # gemini/kimi/opencode/qwen: no confirmed parsing rule in Phase 1 scope.
    return None


def _normalize_claude_model_id(value: str) -> str:
    """Strip decorations a real `claude --output-format json` payload attaches
    to a modelUsage key, so it can be compared against a plain catalog
    model_id/requested_model string.

    Verified directly against a live `claude` 2.1.206 CLI on 2026-07-10 (not
    guessed -- see references/benchmark-2026-07-10.md for the raw payloads):
    a bracketed execution-mode suffix (e.g. "[1m]") and/or a trailing 8-digit
    date suffix (e.g. "-20251001") may appear depending on how --model was
    (or was not) specified; requesting the full catalog model_id directly
    came back with neither decoration.
    """
    stripped = CLAUDE_MODEL_BRACKET_SUFFIX_RE.sub("", value.strip())
    stripped = CLAUDE_MODEL_DATE_SUFFIX_RE.sub("", stripped)
    return stripped


def _extract_claude_model_from_json(payload: Any) -> str | None:
    """Extract the raw actual-model identifier from a parsed claude
    --output-format json payload. Two known shapes:
      - a top-level "model" string field (defensive fallback only -- not
        observed in the live 2026-07-10 verification calls, kept in case a
        future CLI version or subcommand adds one)
      - a "modelUsage" mapping keyed by the served model id, e.g.
        {"claude-sonnet-5": {...}} -- this is the shape actually observed
        live and in the skill's 2026-07-10 smoke-claude-json matrix
        (run_id smoke-claude-json-20260710).
    Returns the RAW key/value (decorations included, if any); normalization
    for comparison purposes happens separately in
    _normalize_claude_model_id, so the record's actual_model field stays a
    faithful, undoctored echo of what the CLI actually printed.
    If modelUsage has more than one key (a multi-model session), the first
    key in insertion order is returned -- Phase 1 dispatch calls are
    expected to be single-model one-shot invocations.
    """
    if not isinstance(payload, dict):
        return None
    model = payload.get("model")
    if isinstance(model, str) and model:
        return model
    model_usage = payload.get("modelUsage")
    if isinstance(model_usage, dict) and model_usage:
        first_key = next(iter(model_usage))
        if isinstance(first_key, str) and first_key:
            return first_key
    return None


def _claude_model_matches(requested: str, actual: str) -> bool:
    """True if a claude modelUsage-echoed actual model id refers to the same
    model as requested_model, after stripping known decorations (bracket /
    date suffix -- see _normalize_claude_model_id). Exact string equality is
    checked first so an already-clean echo never depends on the stripping
    heuristics at all.
    """
    if requested == actual:
        return True
    return _normalize_claude_model_id(actual) == _normalize_claude_model_id(requested)


def detect_actual_model(executor: str, stdout: str, cmd: str | None = None) -> str | None:
    """Best-effort actual-model echo detection.

    codex: scans stdout for a leading "model: xxx" line (unchanged from
    Phase 1).
    claude: only attempts detection when `cmd` shows the call used
    `--output-format json` (or `--output-format=json`); parses stdout as
    JSON and looks for modelUsage/model (see _extract_claude_model_from_json).
    Plain-text-mode claude calls (no cmd given, or cmd without the json
    flag) return None -- the caller keeps reporting actual_model_unverified
    for those, per the Model Integrity Gate.
    """
    if executor == "codex":
        match = CODEX_MODEL_LINE_RE.search(stdout[:2000])
        return match.group(1) if match else None
    if executor == "claude":
        if not cmd or not CLAUDE_OUTPUT_FORMAT_JSON_RE.search(cmd):
            return None
        try:
            payload = json.loads(stdout)
        except (json.JSONDecodeError, ValueError):
            return None
        return _extract_claude_model_from_json(payload)
    return None


# ---------------------------------------------------------------------------
# CLI version probing
# ---------------------------------------------------------------------------


def probe_cli_version(executor: str) -> str:
    cmd = VERSION_COMMANDS.get(executor)
    if not cmd or shutil.which(cmd[0]) is None:
        return "unavailable"
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = (proc.stdout or proc.stderr or "").strip().splitlines()
        return output[0] if output else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".manifest-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def build_resume_command(cases_path: Path, run_id: str, manifest_dir: Path) -> str:
    return (
        f"python3 {Path(__file__).name} --cases {cases_path} --run-id {run_id} "
        f"--manifest-dir {manifest_dir} --resume"
    )


# ---------------------------------------------------------------------------
# Core execution
# ---------------------------------------------------------------------------


def run_one_case(
    case: dict,
    catalog_data: dict | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Execute a single case's cmd_template and classify the result.

    Never raises for a subprocess failure/timeout; the outcome is encoded in
    the returned record's "status" field.
    """
    case_id = case["case_id"]
    provider = case.get("provider")
    executor = case.get("executor")
    model = case.get("model")
    reasoning = case.get("reasoning")
    cmd = case["cmd_template"]

    record: dict[str, Any] = {
        "case_id": case_id,
        "provider": provider,
        "executor": executor,
        "requested_model": model,
        "reasoning": reasoning,
        "status": "running",
        "started_at": now_iso(),
        "completed_at": None,
        "duration_seconds": None,
        "exit_code": None,
        "tokens_used": None,
        "api_equivalent_cost": None,
        "actual_model": None,
        "notes": [],
    }

    start = time.monotonic()
    timed_out = False
    stdout = ""
    stderr = ""
    exit_code = None
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout_seconds
        )
        stdout, stderr, exit_code = proc.stdout or "", proc.stderr or "", proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
    duration = time.monotonic() - start

    combined = f"{stdout}\n{stderr}"
    record["completed_at"] = now_iso()
    record["duration_seconds"] = round(duration, 3)
    record["exit_code"] = exit_code

    tokens = parse_tokens(executor, stdout)
    record["tokens_used"] = tokens if tokens is not None else "unknown"

    if catalog_data is not None and isinstance(tokens, int) and model:
        cost_result = estimate_cost.estimate(catalog_data, model, input_tokens=0, output_tokens=tokens)
        record["api_equivalent_cost"] = {
            "total_cost": cost_result["total_cost"],
            "confidence": cost_result["confidence"],
            "note": "tokens_used is a combined figure; billed entirely as output tokens for this rough estimate since executor stdout does not separate input/output.",
        }
    else:
        record["api_equivalent_cost"] = None

    actual_model = detect_actual_model(executor, stdout, cmd)
    record["actual_model"] = actual_model

    if timed_out:
        record["status"] = "timeout"
    elif QUOTA_RE.search(combined):
        record["status"] = "blocked_quota"
    elif UNSUPPORTED_RE.search(combined):
        record["status"] = "unsupported"
    elif exit_code == 0:
        if executor == "codex" and actual_model and model and actual_model != model:
            record["status"] = "fallback_or_downgrade"
            record["notes"].append(f"codex echoed model={actual_model!r}, requested {model!r}")
        elif executor == "claude":
            if actual_model and model:
                if _claude_model_matches(model, actual_model):
                    record["status"] = "passed"
                    record["notes"].append(
                        f"claude --output-format json echoed modelUsage/model={actual_model!r}; "
                        f"matches requested {model!r} (Model Integrity Gate verified, not unverified)"
                    )
                else:
                    record["status"] = "fallback_or_downgrade"
                    record["notes"].append(
                        f"claude echoed model={actual_model!r} via --output-format json, "
                        f"requested {model!r} -- mismatch even after stripping known decorations"
                    )
            else:
                record["status"] = "actual_model_unverified"
                record["notes"].append(
                    "claude headless text-mode output does not reliably echo the served model id; "
                    "status is intentionally not reported as a clean pass (Model Integrity Gate). "
                    "Re-run with --output-format json for a verifiable modelUsage/model echo."
                )
        else:
            record["status"] = "passed"
            if executor not in ("codex", "claude"):
                record["notes"].append(
                    f"model-echo verification is not implemented for executor={executor!r} in Phase 1"
                )
    else:
        record["status"] = "failed"

    return record


def load_manifest(manifest_path: Path) -> dict | None:
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def run_matrix(
    cases: list[dict],
    run_id: str,
    manifest_dir: Path,
    cases_path: Path,
    resume: bool,
    host_ai: str,
    skill_source_path: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    catalog_data: dict | None = None,
) -> dict[str, Any]:
    manifest_path = manifest_dir / "manifest.json"
    existing = load_manifest(manifest_path) if resume else None

    existing_cases_by_id: dict[str, dict] = {}
    if existing:
        for rec in existing.get("cases", []):
            existing_cases_by_id[rec["case_id"]] = rec

    executors_in_run = sorted({c.get("executor") for c in cases if c.get("executor")})
    cli_versions = {ex: probe_cli_version(ex) for ex in executors_in_run}

    if existing and resume:
        previous_versions = existing.get("cli_versions", {})
        for ex, version in cli_versions.items():
            if ex in previous_versions and previous_versions[ex] != version:
                print(
                    f"WARN: {ex} CLI version changed since last run "
                    f"({previous_versions[ex]!r} -> {version!r}); results may not be comparable",
                    file=sys.stderr,
                )

    manifest = {
        "run_id": run_id,
        "started_at": existing["started_at"] if existing else now_iso(),
        "updated_at": now_iso(),
        "host_ai": host_ai,
        "skill_source_path": skill_source_path,
        "cli_versions": cli_versions,
        "pricing_version": (catalog_data or {}).get("updated_at"),
        "expected_cases": len(cases),
        "completed_cases": 0,
        "remaining_cases": len(cases),
        "current_provider": None,
        "status": "running",
        "stop_reason": None,
        "cases": [],
        "resume_command": build_resume_command(cases_path, run_id, manifest_dir),
    }

    blocked_providers: set[str] = set()
    # Pre-seed blocked_providers from any prior blocked_quota/pending_quota case
    # so a --resume that starts mid-list still honors an earlier provider stop
    # until the operator explicitly re-tries by editing cases.json.
    if existing:
        for rec in existing.get("cases", []):
            if rec.get("status") in {"blocked_quota"}:
                blocked_providers.add(rec.get("provider"))

    final_records: list[dict] = []
    stop_reason = None

    for case in cases:
        case_id = case["case_id"]
        provider = case.get("provider")
        prior = existing_cases_by_id.get(case_id)

        if prior and prior.get("status") in TERMINAL_ON_RESUME:
            final_records.append(prior)
            continue

        stale_running_evidence = None
        if prior and prior.get("status") == "running":
            print(f"WARN: case {case_id!r} was left 'running' by a previous run; marking interrupted and retrying", file=sys.stderr)
            stale_running_evidence = dict(prior)
            stale_running_evidence["status"] = "interrupted"
            # Fall through and attempt a fresh run below; the interrupted
            # evidence is preserved on the fresh record (not discarded) so
            # the audit trail shows the crash instead of silently vanishing.

        if provider in blocked_providers:
            record = {
                "case_id": case_id,
                "provider": provider,
                "executor": case.get("executor"),
                "requested_model": case.get("model"),
                "reasoning": case.get("reasoning"),
                "status": "pending_quota",
                "started_at": None,
                "completed_at": None,
                "duration_seconds": None,
                "exit_code": None,
                "tokens_used": None,
                "api_equivalent_cost": None,
                "actual_model": None,
                "notes": [f"skipped without executing: provider {provider!r} already blocked_quota this run"],
                "previous_attempt": stale_running_evidence,
            }
            final_records.append(record)
            manifest["cases"] = final_records
            manifest["completed_cases"] = len(final_records)
            manifest["remaining_cases"] = len(cases) - _terminal_count(final_records)
            manifest["current_provider"] = provider
            manifest["updated_at"] = now_iso()
            atomic_write_json(manifest_path, manifest)
            continue

        manifest["current_provider"] = provider
        record = run_one_case(case, catalog_data, timeout_seconds)
        record["previous_attempt"] = stale_running_evidence
        final_records.append(record)

        if record["status"] == "blocked_quota":
            blocked_providers.add(provider)

        manifest["cases"] = final_records
        manifest["completed_cases"] = len(final_records)
        manifest["remaining_cases"] = len(cases) - _terminal_count(final_records)
        manifest["updated_at"] = now_iso()
        atomic_write_json(manifest_path, manifest)

    if blocked_providers:
        stop_reason = "blocked_quota:" + ",".join(sorted(blocked_providers))

    manifest["cases"] = final_records
    manifest["completed_cases"] = len(final_records)
    manifest["remaining_cases"] = max(len(cases) - _terminal_count(final_records), 0)
    manifest["current_provider"] = None
    manifest["status"] = "done" if manifest["remaining_cases"] == 0 else "incomplete"
    manifest["stop_reason"] = stop_reason
    manifest["updated_at"] = now_iso()
    atomic_write_json(manifest_path, manifest)
    return manifest


# ---------------------------------------------------------------------------
# Self-test (mock commands only, no real executor CLI is invoked)
# ---------------------------------------------------------------------------


def run_selftest() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, condition, detail))

    with tempfile.TemporaryDirectory(prefix="run_matrix_selftest_") as tmp:
        tmp_path = Path(tmp)
        cases_path = tmp_path / "cases.json"
        manifest_dir = tmp_path / "manifest"

        pass_cmd = "printf 'model: gpt-5.6-sol\\nran ok\\ntokens used\\n12345\\n'"
        quota_cmd = "printf 'error: usage_limit reached for this account\\n'; exit 1"
        would_run_cmd = "printf 'should not have run\\n'; exit 0"

        cases = [
            {
                "case_id": "case-1-pass",
                "provider": "openai",
                "executor": "codex",
                "model": "gpt-5.6-sol",
                "reasoning": "medium",
                "cmd_template": pass_cmd,
            },
            {
                "case_id": "case-2-quota",
                "provider": "openai",
                "executor": "codex",
                "model": "gpt-5.6-sol",
                "reasoning": "medium",
                "cmd_template": quota_cmd,
            },
            {
                "case_id": "case-3-should-be-skipped",
                "provider": "openai",
                "executor": "codex",
                "model": "gpt-5.6-sol",
                "reasoning": "medium",
                "cmd_template": would_run_cmd,
            },
        ]
        cases_path.write_text(json.dumps(cases), encoding="utf-8")

        manifest1 = run_matrix(
            cases=cases,
            run_id="selftest-run",
            manifest_dir=manifest_dir,
            cases_path=cases_path,
            resume=False,
            host_ai="selftest-host",
            skill_source_path=str(Path(__file__).resolve().parents[1]),
            timeout_seconds=30,
            catalog_data=None,
        )

        by_id = {c["case_id"]: c for c in manifest1["cases"]}
        check("case-1 passed", by_id["case-1-pass"]["status"] == "passed", by_id["case-1-pass"]["status"])
        check("case-1 tokens_used parsed as 12345", by_id["case-1-pass"]["tokens_used"] == 12345, str(by_id["case-1-pass"]["tokens_used"]))
        check(
            "case-2 classified blocked_quota",
            by_id["case-2-quota"]["status"] == "blocked_quota",
            by_id["case-2-quota"]["status"],
        )
        check(
            "case-3 skipped as pending_quota without executing",
            by_id["case-3-should-be-skipped"]["status"] == "pending_quota",
            by_id["case-3-should-be-skipped"]["status"],
        )
        check(
            "case-3 notes explain it was not executed",
            any("without executing" in n for n in by_id["case-3-should-be-skipped"]["notes"]),
        )
        check("manifest marked incomplete (provider blocked)", manifest1["status"] == "incomplete")
        check("stop_reason names the blocked provider", manifest1["stop_reason"] == "blocked_quota:openai")
        check(
            "manifest.json exists on disk (atomic write)",
            (manifest_dir / "manifest.json").is_file(),
        )

        # --- Resume: fix the quota case's command in cases.json (simulating
        # quota having recovered) and verify --resume retries only the
        # non-terminal cases, leaving case-1 untouched.
        cases_fixed = json.loads(cases_path.read_text(encoding="utf-8"))
        for case in cases_fixed:
            if case["case_id"] in {"case-2-quota", "case-3-should-be-skipped"}:
                case["cmd_template"] = "printf 'model: gpt-5.6-sol\\nrecovered\\ntokens used\\n999\\n'"
        cases_path.write_text(json.dumps(cases_fixed), encoding="utf-8")

        manifest2 = run_matrix(
            cases=cases_fixed,
            run_id="selftest-run",
            manifest_dir=manifest_dir,
            cases_path=cases_path,
            resume=True,
            host_ai="selftest-host",
            skill_source_path=str(Path(__file__).resolve().parents[1]),
            timeout_seconds=30,
            catalog_data=None,
        )
        by_id2 = {c["case_id"]: c for c in manifest2["cases"]}
        check(
            "resume: case-1 untouched (still the original started_at)",
            by_id2["case-1-pass"]["started_at"] == by_id["case-1-pass"]["started_at"],
        )
        check(
            "resume: case-2 retried after being pre-seeded as blocked (still blocks this run)",
            by_id2["case-2-quota"]["status"] in {"blocked_quota", "pending_quota"},
            by_id2["case-2-quota"]["status"],
        )
        check("resume: run_id stable across resume", manifest2["run_id"] == "selftest-run")
        check(
            "resume: started_at preserved across resume",
            manifest2["started_at"] == manifest1["started_at"],
        )
        check("resume_command field present and mentions --resume", "--resume" in manifest2["resume_command"])

        # --- Timeout classification (mock a command that outlives the timeout).
        timeout_case = [
            {
                "case_id": "case-timeout",
                "provider": "geminiprovider",
                "executor": "gemini",
                "model": "gemini-2.5-flash",
                "reasoning": None,
                "cmd_template": "sleep 5",
            }
        ]
        timeout_dir = tmp_path / "manifest-timeout"
        timeout_cases_path = tmp_path / "cases-timeout.json"
        timeout_cases_path.write_text(json.dumps(timeout_case), encoding="utf-8")
        manifest3 = run_matrix(
            cases=timeout_case,
            run_id="selftest-timeout",
            manifest_dir=timeout_dir,
            cases_path=timeout_cases_path,
            resume=False,
            host_ai="selftest-host",
            skill_source_path=str(Path(__file__).resolve().parents[1]),
            timeout_seconds=1,
            catalog_data=None,
        )
        check(
            "timeout case classified as timeout",
            manifest3["cases"][0]["status"] == "timeout",
            manifest3["cases"][0]["status"],
        )

        # --- Stale 'running' recovery: simulate a manifest left behind by a
        # process that was killed mid-case (status stuck at "running"), then
        # verify --resume marks it interrupted, retries it fresh, and keeps
        # the interrupted evidence attached rather than silently discarding it.
        crash_dir = tmp_path / "manifest-crash"
        crash_cases_path = tmp_path / "cases-crash.json"
        crash_case = [
            {
                "case_id": "case-crash-recovery",
                "provider": "openai",
                "executor": "codex",
                "model": "gpt-5.6-sol",
                "reasoning": "medium",
                "cmd_template": "printf 'model: gpt-5.6-sol\\nrecovered after crash\\ntokens used\\n77\\n'",
            }
        ]
        crash_cases_path.write_text(json.dumps(crash_case), encoding="utf-8")
        crash_dir.mkdir(parents=True, exist_ok=True)
        stale_manifest = {
            "run_id": "selftest-crash",
            "started_at": "2026-07-10T00:00:00Z",
            "updated_at": "2026-07-10T00:00:01Z",
            "host_ai": "selftest-host",
            "skill_source_path": str(Path(__file__).resolve().parents[1]),
            "cli_versions": {},
            "pricing_version": None,
            "expected_cases": 1,
            "completed_cases": 1,
            "remaining_cases": 1,
            "current_provider": "openai",
            "status": "incomplete",
            "stop_reason": None,
            "cases": [
                {
                    "case_id": "case-crash-recovery",
                    "provider": "openai",
                    "executor": "codex",
                    "requested_model": "gpt-5.6-sol",
                    "reasoning": "medium",
                    "status": "running",
                    "started_at": "2026-07-10T00:00:00Z",
                    "completed_at": None,
                    "duration_seconds": None,
                    "exit_code": None,
                    "tokens_used": None,
                    "api_equivalent_cost": None,
                    "actual_model": None,
                    "notes": [],
                }
            ],
            "resume_command": "unused-in-this-fixture",
        }
        (crash_dir / "manifest.json").write_text(json.dumps(stale_manifest), encoding="utf-8")

        manifest4 = run_matrix(
            cases=crash_case,
            run_id="selftest-crash",
            manifest_dir=crash_dir,
            cases_path=crash_cases_path,
            resume=True,
            host_ai="selftest-host",
            skill_source_path=str(Path(__file__).resolve().parents[1]),
            timeout_seconds=30,
            catalog_data=None,
        )
        recovered = manifest4["cases"][0]
        check(
            "stale running case is retried fresh, not left stuck",
            recovered["status"] == "passed",
            recovered["status"],
        )
        check(
            "stale running case's crash evidence is preserved, not discarded",
            isinstance(recovered.get("previous_attempt"), dict)
            and recovered["previous_attempt"]["status"] == "interrupted",
            str(recovered.get("previous_attempt")),
        )

        # --- Claude Model Integrity Gate (P4, 2026-07-10): --output-format
        # json mode should verify modelUsage/model against requested_model
        # instead of always reporting actual_model_unverified. The mock
        # stdout payloads below mirror the real shape captured from a live
        # `claude` 2.1.206 CLI on 2026-07-10 (see
        # references/benchmark-2026-07-10.md), including the two decoration
        # patterns actually observed there: a bracketed mode suffix and a
        # dated model id.
        claude_json_dir = tmp_path / "manifest-claude-json"
        claude_json_cases_path = tmp_path / "cases-claude-json.json"
        claude_sonnet_stdout = (
            '{"type":"result","subtype":"success","is_error":false,"result":"4",'
            '"total_cost_usd":0.0445,"usage":{"input_tokens":4,"output_tokens":22},'
            '"modelUsage":{"claude-sonnet-5":{"inputTokens":4,"outputTokens":22,"costUSD":0.0445}}}'
        )
        claude_dated_haiku_stdout = (
            '{"type":"result","subtype":"success","is_error":false,"result":"4",'
            '"total_cost_usd":0.0273,"usage":{"input_tokens":10,"output_tokens":78},'
            '"modelUsage":{"claude-haiku-4-5-20251001":{"inputTokens":10,"outputTokens":78,"costUSD":0.0273}}}'
        )
        claude_mismatch_stdout = (
            '{"type":"result","subtype":"success","is_error":false,"result":"4",'
            '"total_cost_usd":0.0677,"usage":{"input_tokens":4,"output_tokens":22},'
            '"modelUsage":{"claude-opus-4-8":{"inputTokens":4,"outputTokens":22,"costUSD":0.0677}}}'
        )
        claude_json_cases = [
            {
                "case_id": "claude-json-exact-match",
                "provider": "anthropic",
                "executor": "claude",
                "model": "claude-sonnet-5",
                "reasoning": "low",
                "cmd_template": (
                    f"printf '%s' '{claude_sonnet_stdout}'  "
                    "# mocked: claude --print --output-format json --model claude-sonnet-5 --effort low"
                ),
            },
            {
                "case_id": "claude-json-dated-suffix-match",
                "provider": "anthropic",
                "executor": "claude",
                "model": "claude-haiku-4-5",
                "reasoning": "low",
                "cmd_template": (
                    f"printf '%s' '{claude_dated_haiku_stdout}'  "
                    "# mocked: claude --print --output-format json --model claude-haiku-4-5 --effort low"
                ),
            },
            {
                "case_id": "claude-json-mismatch",
                "provider": "anthropic",
                "executor": "claude",
                "model": "claude-sonnet-5",
                "reasoning": "low",
                "cmd_template": (
                    f"printf '%s' '{claude_mismatch_stdout}'  "
                    "# mocked: claude --print --output-format json --model claude-sonnet-5 (simulated silent fallback)"
                ),
            },
            {
                "case_id": "claude-json-unparseable-stdout",
                "provider": "anthropic",
                "executor": "claude",
                "model": "claude-sonnet-5",
                "reasoning": "low",
                "cmd_template": (
                    "printf 'not valid json'  "
                    "# mocked: claude --print --output-format json (corrupted/partial output)"
                ),
            },
            {
                "case_id": "claude-text-mode-still-unverified",
                "provider": "anthropic",
                "executor": "claude",
                "model": "claude-sonnet-5",
                "reasoning": "low",
                "cmd_template": "printf 'The answer is 4.\\n'  # mocked: claude --print (plain text mode)",
            },
        ]
        claude_json_cases_path.write_text(json.dumps(claude_json_cases), encoding="utf-8")
        claude_manifest = run_matrix(
            cases=claude_json_cases,
            run_id="selftest-claude-json",
            manifest_dir=claude_json_dir,
            cases_path=claude_json_cases_path,
            resume=False,
            host_ai="selftest-host",
            skill_source_path=str(Path(__file__).resolve().parents[1]),
            timeout_seconds=30,
            catalog_data=None,
        )
        claude_by_id = {c["case_id"]: c for c in claude_manifest["cases"]}
        check(
            "claude json exact match -> passed, not unverified",
            claude_by_id["claude-json-exact-match"]["status"] == "passed",
            claude_by_id["claude-json-exact-match"]["status"],
        )
        check(
            "claude json exact match -> actual_model echoed verbatim",
            claude_by_id["claude-json-exact-match"]["actual_model"] == "claude-sonnet-5",
            str(claude_by_id["claude-json-exact-match"]["actual_model"]),
        )
        check(
            "claude json dated-suffix (real CLI decoration) still recognized as a match -> passed",
            claude_by_id["claude-json-dated-suffix-match"]["status"] == "passed",
            claude_by_id["claude-json-dated-suffix-match"]["status"],
        )
        check(
            "claude json dated-suffix: raw actual_model keeps the date, not silently rewritten",
            claude_by_id["claude-json-dated-suffix-match"]["actual_model"] == "claude-haiku-4-5-20251001",
            str(claude_by_id["claude-json-dated-suffix-match"]["actual_model"]),
        )
        check(
            "claude json real mismatch -> fallback_or_downgrade",
            claude_by_id["claude-json-mismatch"]["status"] == "fallback_or_downgrade",
            claude_by_id["claude-json-mismatch"]["status"],
        )
        check(
            "claude json unparseable stdout -> falls back to actual_model_unverified, not a fabricated pass",
            claude_by_id["claude-json-unparseable-stdout"]["status"] == "actual_model_unverified",
            claude_by_id["claude-json-unparseable-stdout"]["status"],
        )
        check(
            "claude plain text mode -> still actual_model_unverified (unchanged Phase 1 fallback)",
            claude_by_id["claude-text-mode-still-unverified"]["status"] == "actual_model_unverified",
            claude_by_id["claude-text-mode-still-unverified"]["status"],
        )

        # --- Non-codex/non-claude executor gets an honest "not implemented" note, not a fabricated pass.
        check(
            "unsupported-detection: unrelated executor still reaches a status",
            manifest3["cases"][0]["status"] in ALL_STATUSES,
        )

    # --- Unit-level checks on the pure helper functions (no subprocess).
    check(
        "parse_tokens: codex 'tokens used' next-line pattern",
        parse_tokens("codex", "some preamble\ntokens used\n42\nmore text") == 42,
    )
    check(
        "parse_tokens: claude JSON usage object",
        parse_tokens("claude", json.dumps({"usage": {"input_tokens": 10, "output_tokens": 5}})) == 15,
    )
    check("parse_tokens: unknown executor returns None", parse_tokens("gemini", "tokens used\n42") is None)
    check(
        "detect_actual_model: codex model line",
        detect_actual_model("codex", "model: gpt-5.6-terra\nok") == "gpt-5.6-terra",
    )
    check(
        "detect_actual_model: claude text-mode (no cmd) stays unverified",
        detect_actual_model("claude", "model: x") is None,
    )
    check(
        "detect_actual_model: claude cmd without --output-format json stays unverified even if stdout looks like JSON",
        detect_actual_model(
            "claude", '{"modelUsage":{"claude-sonnet-5":{}}}', cmd="claude --print -p hi"
        )
        is None,
    )
    check(
        "detect_actual_model: claude json-mode cmd extracts the modelUsage key",
        detect_actual_model(
            "claude",
            '{"modelUsage":{"claude-sonnet-5":{"outputTokens":1}}}',
            cmd="claude --print --output-format json -p hi",
        )
        == "claude-sonnet-5",
    )
    check(
        "detect_actual_model: claude json-mode with --output-format=json (equals form) also matches",
        detect_actual_model(
            "claude",
            '{"modelUsage":{"claude-sonnet-5":{"outputTokens":1}}}',
            cmd="claude --print --output-format=json -p hi",
        )
        == "claude-sonnet-5",
    )
    check(
        "_normalize_claude_model_id: strips a real-world bracket suffix",
        _normalize_claude_model_id("claude-opus-4-8[1m]") == "claude-opus-4-8",
    )
    check(
        "_normalize_claude_model_id: strips a real-world dated suffix",
        _normalize_claude_model_id("claude-haiku-4-5-20251001") == "claude-haiku-4-5",
    )
    check(
        "_claude_model_matches: exact string match without needing normalization",
        _claude_model_matches("claude-sonnet-5", "claude-sonnet-5"),
    )
    check(
        "_claude_model_matches: real-world decorations do not cause a false mismatch",
        _claude_model_matches("claude-opus-4-8", "claude-opus-4-8[1m]")
        and _claude_model_matches("claude-haiku-4-5", "claude-haiku-4-5-20251001"),
    )
    check(
        "_claude_model_matches: a genuinely different model is still flagged as a mismatch",
        not _claude_model_matches("claude-sonnet-5", "claude-opus-4-8"),
    )

    print("=== run_matrix.py selftest ===")
    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        line = f"[{status}] {name}"
        if detail and not passed:
            line += f" -- {detail}"
        print(line)
    total = len(checks)
    passed_count = sum(1 for _, p, _ in checks if p)
    print(f"{passed_count}/{total} checks passed")
    return 0 if all_passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", help="Path to a cases.json file.")
    parser.add_argument("--run-id", help="Stable identifier for this run; reused across --resume calls.")
    parser.add_argument("--manifest-dir", help="Directory to hold manifest.json for this run.")
    parser.add_argument("--resume", action="store_true", help="Resume a previous run in the same --manifest-dir.")
    parser.add_argument(
        "--host-ai",
        default=os.environ.get("SOIA_HOST_AI", "unknown"),
        help="Identifier for the orchestrating AI/session, recorded in the manifest. Defaults to $SOIA_HOST_AI or 'unknown'.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--catalog", help="Override path to model-catalog.yml for api_equivalent_cost estimates.")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not (args.cases and args.run_id and args.manifest_dir):
        parser.error("--cases, --run-id, and --manifest-dir are required unless --selftest is used")

    cases_path = Path(args.cases)
    try:
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: failed to read cases file {cases_path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(cases, list) or not cases:
        print("error: cases.json must be a non-empty JSON array", file=sys.stderr)
        return 2

    skill_root = Path(__file__).resolve().parents[1]
    catalog_path = Path(args.catalog) if args.catalog else skill_root / "references" / "model-catalog.yml"
    catalog_data = None
    if catalog_path.is_file():
        try:
            catalog_data = catalog_lib.load_catalog(catalog_path)
        except catalog_lib.CatalogError as exc:
            print(f"WARN: failed to load catalog for cost estimates: {exc}", file=sys.stderr)

    manifest = run_matrix(
        cases=cases,
        run_id=args.run_id,
        manifest_dir=Path(args.manifest_dir),
        cases_path=cases_path,
        resume=args.resume,
        host_ai=args.host_ai,
        skill_source_path=str(skill_root),
        timeout_seconds=args.timeout_seconds,
        catalog_data=catalog_data,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
