#!/usr/bin/env python3
# @created_by unknown
# @created_at unknown
# @modified_by openai/gpt-5
# @modified_at 2026-07-10 17:58:15
# @version 0.2.0
# @description Estimate API-equivalent dispatch cost from structured model pricing.
# @changelog Use Decimal internally and expose exact decimal cost fields.
"""Estimate the API-equivalent cost of a dispatched call against model-catalog.yml.

This never reads real usage from a provider; it takes token counts you
already have (from a job's own output, or a plan you are about to run) and
multiplies them by the catalog's per-1M-token prices. Every invocation --
success, failure, or unknown model -- prints one fixed disclaimer line since
subscription-billed executors (Claude Code Pro/Max, ChatGPT plans, etc.) do
not actually deduct at these per-token API rates:

    订阅制下实际扣费≠此估算（api_equivalent_estimate）

Usage:
    python3 estimate_cost.py --model gpt-5.6-sol --input-tokens 50000 --output-tokens 8000
    python3 estimate_cost.py --model claude-sonnet-5 --input-tokens 900000 --output-tokens 4000 --long-context
    python3 estimate_cost.py --model sonnet-5 --input-tokens 1000 --output-tokens 1000 --cached-tokens 500 --json
    python3 estimate_cost.py --selftest

Exit codes: 0 = priced (confidence exact or estimated); 2 = model not found
in the catalog (confidence unavailable) or catalog failed to load.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib  # noqa: E402


SUBSCRIPTION_DISCLAIMER = "订阅制下实际扣费≠此估算（api_equivalent_estimate）"
MILLION = Decimal("1000000")


def _num(value: Any) -> Decimal | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    return None


def _legacy_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f").rstrip("0").rstrip(".")
    return text or "0"


def estimate(
    data: dict,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    cache_write_tokens: int = 0,
    cache_write_ttl: str = "5m",
    batch: bool = False,
    long_context: bool = False,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Programmatic API used by both the CLI below and run_matrix.py.

    Returns a dict; see module docstring / --json output for the shape.
    Never raises for an unknown model -- callers check result["confidence"].
    """
    resolution = catalog_lib.find_model(data, model)
    currency = data.get("currency", "USD")
    pricing_version = data.get("updated_at")

    if resolution["model"] is None:
        return {
            "requested_model": model,
            "model_id": None,
            "matched_alias": None,
            "currency": currency,
            "pricing_version": pricing_version,
            "confidence": "unavailable",
            "tier_used": None,
            "breakdown": None,
            "total_cost": None,
            "total_cost_decimal": None,
            "notes": [
                "unknown_pricing: model not found in catalog",
            ],
            "near_candidates": resolution["candidates"],
            "subscription_disclaimer": SUBSCRIPTION_DISCLAIMER,
        }

    entry = resolution["model"]
    notes: list[str] = []
    pricing = dict(entry.get("pricing") or {})
    pricing_date = as_of_date or str(data.get("updated_at") or "")
    future_pricing = pricing.pop("future_pricing", None)
    if isinstance(future_pricing, dict):
        effective_from = str(future_pricing.get("effective_from") or "")
        if effective_from and pricing_date >= effective_from:
            pricing.update({k: v for k, v in future_pricing.items() if k != "effective_from"})
            notes.append(f"selected date-effective pricing period beginning {effective_from}")
    confidence = "exact" if resolution["match"] == "exact" else "estimated"
    if resolution["match"] == "loose":
        notes.append(f"matched via loose/normalized alias resolution, not an exact model_id/alias hit")

    tier_used = "standard"
    input_rate = _num(pricing.get("input_per_1m"))
    output_rate = _num(pricing.get("output_per_1m"))
    cached_rate = _num(pricing.get("cached_input_per_1m"))

    threshold = None
    lc = pricing.get("long_context")
    if isinstance(lc, dict):
        threshold = lc.get("threshold_tokens")

    use_long_context = False
    if long_context or (isinstance(threshold, (int, float)) and input_tokens >= threshold):
        if isinstance(lc, dict) and _num(lc.get("input_per_1m")) is not None:
            use_long_context = True
        elif long_context:
            notes.append("long_context requested but this model has no long_context pricing tier; used standard rate")
            confidence = "estimated"

    if use_long_context:
        tier_used = "long_context"
        input_rate = _num(lc.get("input_per_1m"))
        output_rate = _num(lc.get("output_per_1m"))
        if threshold is not None and input_tokens < threshold and long_context:
            notes.append(f"long_context forced via --long-context even though input_tokens < threshold_tokens ({threshold})")

    if batch:
        batch_pricing = pricing.get("batch")
        if isinstance(batch_pricing, dict) and _num(batch_pricing.get("input_per_1m")) is not None:
            tier_used = "batch" if tier_used == "standard" else tier_used
            if tier_used == "batch":
                input_rate = _num(batch_pricing.get("input_per_1m"))
                output_rate = _num(batch_pricing.get("output_per_1m"))
            else:
                notes.append("batch requested but long_context tier took precedence; batch pricing for long-context rows is not modeled separately")
        else:
            notes.append("batch requested but this model has no batch pricing tier; used standard rate")
            confidence = "estimated"

    cache_write_rate: Decimal | None = None
    if cache_write_tokens:
        if "cache_write_5m_per_1m" in pricing or "cache_write_1h_per_1m" in pricing:
            key = "cache_write_1h_per_1m" if cache_write_ttl == "1h" else "cache_write_5m_per_1m"
            cache_write_rate = _num(pricing.get(key))
            if cache_write_rate is None:
                notes.append(f"no {key} price for this model; cache-write cost omitted")
                confidence = "estimated"
        else:
            cache_write_rate = _num(pricing.get("cache_write_per_1m"))
            if cache_write_rate is None:
                notes.append("no cache_write_per_1m price for this model; cache-write cost omitted")
                confidence = "estimated"

    if cached_tokens and cached_rate is None:
        notes.append("no cached_input_per_1m price for this model; cached-input cost omitted")
        confidence = "estimated"

    if input_rate is None or output_rate is None:
        confidence = "estimated"
        if input_rate is None:
            notes.append("no input price available for the selected tier; input cost omitted")
        if output_rate is None:
            notes.append("no output price available for the selected tier; output cost omitted")

    ordinary_input_tokens = max(input_tokens - cached_tokens, 0)
    if ordinary_input_tokens != input_tokens:
        notes.append("cached_tokens is treated as a subset of input_tokens (billed at the cached rate instead of the standard input rate)")

    input_cost = (Decimal(ordinary_input_tokens) / MILLION) * input_rate if input_rate is not None else None
    cached_cost = (Decimal(cached_tokens) / MILLION) * cached_rate if cached_tokens and cached_rate is not None else Decimal("0")
    cache_write_cost = (
        (Decimal(cache_write_tokens) / MILLION) * cache_write_rate
        if cache_write_tokens and cache_write_rate is not None
        else Decimal("0")
    )
    output_cost = (Decimal(output_tokens) / MILLION) * output_rate if output_rate is not None else None

    total = None
    if input_cost is not None and output_cost is not None:
        total = input_cost + cached_cost + cache_write_cost + output_cost

    return {
        "requested_model": model,
        "model_id": entry.get("model_id"),
        "matched_alias": model if model != entry.get("model_id") else None,
        "currency": currency,
        "pricing_version": pricing_version,
        "pricing_source": pricing.get("source_id"),
        "pricing_effective_date": pricing.get("effective_date"),
        "confidence": confidence,
        "tier_used": tier_used,
        "breakdown": {
            "input_tokens_billed": ordinary_input_tokens,
            "input_cost": _legacy_float(input_cost),
            "input_cost_decimal": _decimal_text(input_cost),
            "cached_tokens_billed": cached_tokens,
            "cached_input_cost": _legacy_float(cached_cost),
            "cached_input_cost_decimal": _decimal_text(cached_cost),
            "cache_write_tokens_billed": cache_write_tokens,
            "cache_write_cost": _legacy_float(cache_write_cost),
            "cache_write_cost_decimal": _decimal_text(cache_write_cost),
            "cache_write_ttl": cache_write_ttl if cache_write_tokens else None,
            "output_tokens_billed": output_tokens,
            "output_cost": _legacy_float(output_cost),
            "output_cost_decimal": _decimal_text(output_cost),
        },
        "total_cost": _legacy_float(total),
        "total_cost_decimal": _decimal_text(total),
        "notes": notes,
        "near_candidates": [],
        "subscription_disclaimer": SUBSCRIPTION_DISCLAIMER,
    }


def _print_text(result: dict[str, Any]) -> None:
    print(f"requested_model: {result['requested_model']}")
    print(f"model_id: {result['model_id']}")
    print(f"confidence: {result['confidence']}")
    print(f"pricing_version: {result['pricing_version']}")
    print(f"currency: {result['currency']}")
    if result["tier_used"]:
        print(f"tier_used: {result['tier_used']}")
    breakdown = result.get("breakdown")
    if breakdown:
        print("breakdown:")
        print(f"  input:       {breakdown['input_tokens_billed']} tok -> {breakdown['input_cost']}")
        print(f"  cached:      {breakdown['cached_tokens_billed']} tok -> {breakdown['cached_input_cost']}")
        print(f"  cache_write: {breakdown['cache_write_tokens_billed']} tok ({breakdown['cache_write_ttl'] or 'n/a'}) -> {breakdown['cache_write_cost']}")
        print(f"  output:      {breakdown['output_tokens_billed']} tok -> {breakdown['output_cost']}")
    print(f"total_cost: {result['total_cost']}")
    print(f"total_cost_decimal: {result.get('total_cost_decimal')}")
    if result["near_candidates"]:
        print(f"near_candidates: {', '.join(result['near_candidates'])}")
    for note in result["notes"]:
        print(f"note: {note}")
    print(result["subscription_disclaimer"], file=sys.stderr)


def run_selftest() -> int:
    catalog_path = Path(__file__).resolve().parents[1] / "references" / "model-catalog.yml"
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, condition, detail))

    if not catalog_path.is_file():
        print(f"FATAL: catalog not found at {catalog_path}")
        return 1
    data = catalog_lib.load_catalog(catalog_path)

    # 1. Sonnet-5 promotional price, exact 1M in + 1M out (matches the
    #    source's own "1M input + 1M output" column: $2 + $10 = $12).
    r = estimate(data, "claude-sonnet-5", 1_000_000, 1_000_000)
    check(
        "sonnet-5 promo: 1M in + 1M out == $12.00",
        r["confidence"] == "exact" and r["total_cost_decimal"] == "12",
        f"got {r['total_cost']}",
    )

    # 2. Same alias resolved after promo window via the distinct catalog row:
    #    standard price 1M in + 1M out = $3 + $15 = $18.
    r_future = estimate(data, "claude-sonnet-5", 1_000_000, 1_000_000, as_of_date="2026-09-01")
    check(
        "sonnet-5 standard (post 2026-09-01): 1M in + 1M out == $18.00",
        r_future["confidence"] == "exact" and r_future["total_cost_decimal"] == "18",
        f"got {r_future['total_cost']}",
    )

    # 3. Long-context auto-detection: gpt-5.6-sol above the 272K threshold
    #    should bill at $10/$45 per 1M instead of $5/$30.
    r_lc = estimate(data, "gpt-5.6-sol", 300_000, 1_000_000)
    expected_lc = (300_000 / 1_000_000) * 10 + (1_000_000 / 1_000_000) * 45
    check(
        "gpt-5.6-sol auto long_context above 272K threshold",
        r_lc["tier_used"] == "long_context" and abs(r_lc["total_cost"] - expected_lc) < 1e-9,
        f"got tier={r_lc['tier_used']} total={r_lc['total_cost']}",
    )
    r_short = estimate(data, "gpt-5.6-sol", 100_000, 1_000_000)
    check(
        "gpt-5.6-sol standard tier below 272K threshold",
        r_short["tier_used"] == "standard",
        f"got tier={r_short['tier_used']}",
    )

    # 4. Claude cache-write TTL split: 5m vs 1h must give different costs.
    r_5m = estimate(data, "claude-opus-4-6", 0, 0, cache_write_tokens=1_000_000, cache_write_ttl="5m")
    r_1h = estimate(data, "claude-opus-4-6", 0, 0, cache_write_tokens=1_000_000, cache_write_ttl="1h")
    check(
        "claude cache-write 5m ($6.25) != 1h ($10) per 1M",
        abs(r_5m["breakdown"]["cache_write_cost"] - 6.25) < 1e-9
        and abs(r_1h["breakdown"]["cache_write_cost"] - 10.0) < 1e-9,
        f"5m={r_5m['breakdown']['cache_write_cost']} 1h={r_1h['breakdown']['cache_write_cost']}",
    )

    # 5. Unknown model: confidence unavailable, null total, candidates offered.
    r_unknown = estimate(data, "claude-sonnet-4-999-nonexistent", 1000, 1000)
    check(
        "unknown model -> confidence unavailable, total_cost None",
        r_unknown["confidence"] == "unavailable" and r_unknown["total_cost"] is None,
        f"got confidence={r_unknown['confidence']} total={r_unknown['total_cost']}",
    )

    # 6. Batch tier halves (roughly) the standard rate for a model that has one.
    #    Token counts are kept below terra's 272K long-context threshold so the
    #    batch tier isn't shadowed by auto long-context detection (check 3).
    r_batch = estimate(data, "gpt-5.6-terra", 200_000, 200_000, batch=True)
    expected_batch = 0.2 * 1.25 + 0.2 * 7.5
    check(
        "gpt-5.6-terra batch tier == $1.75 per 200K in + 200K out",
        r_batch["tier_used"] == "batch" and abs(r_batch["total_cost"] - expected_batch) < 1e-9,
        f"got tier={r_batch['tier_used']} total={r_batch['total_cost']}",
    )

    # 7. Model with no batch tier: --batch is a no-op with a note, not a crash.
    r_nobatch = estimate(data, "gpt-5.3-codex", 1000, 1000, batch=True)
    check(
        "model without batch tier: falls back to standard with a note",
        r_nobatch["tier_used"] == "standard" and any("no batch pricing tier" in n for n in r_nobatch["notes"]),
        f"got tier={r_nobatch['tier_used']} notes={r_nobatch['notes']}",
    )

    # 8. Cached input tokens are billed at the cached rate, not double-counted.
    #    Kept below luna's 272K long-context threshold so this isolates the
    #    cached-token subtraction logic from tier selection (check 3).
    r_cached = estimate(data, "gpt-5.6-luna", 100_000, 0, cached_tokens=40_000)
    expected_cached = (60_000 / 1_000_000) * 1 + (40_000 / 1_000_000) * 0.1
    check(
        "cached_tokens billed at cached rate, subtracted from standard input",
        abs(r_cached["total_cost"] - expected_cached) < 1e-9,
        f"got {r_cached['total_cost']}, expected {expected_cached}",
    )

    print("=== estimate_cost.py selftest ===")
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
    print(f"{passed_count}/{total} checks passed (>=5 required by spec)")
    return 0 if all_passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", help="Model id, alias, or display name (loosely matched).")
    parser.add_argument("--input-tokens", type=int, default=0)
    parser.add_argument("--output-tokens", type=int, default=0)
    parser.add_argument("--cached-tokens", type=int, default=0, help="Subset of --input-tokens billed at the cached-input rate.")
    parser.add_argument("--cache-write-tokens", type=int, default=0)
    parser.add_argument(
        "--cache-write-ttl",
        choices=["5m", "1h"],
        default="5m",
        help="Which cache-write rate to use for models that split pricing by TTL (currently Anthropic). Ignored for other models.",
    )
    parser.add_argument("--batch", action="store_true", help="Use the model's batch/flex pricing tier if available.")
    parser.add_argument(
        "--long-context",
        action="store_true",
        help="Force the model's long-context pricing tier. Applied automatically when input_tokens meets the model's threshold_tokens even without this flag.",
    )
    parser.add_argument("--catalog", help="Override path to model-catalog.yml.")
    parser.add_argument("--pricing-date", help="ISO date used to select date-effective pricing, e.g. 2026-09-01.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.model:
        parser.error("--model is required unless --selftest is used")

    catalog_path = Path(args.catalog) if args.catalog else Path(__file__).resolve().parents[1] / "references" / "model-catalog.yml"
    try:
        data = catalog_lib.load_catalog(catalog_path)
    except (catalog_lib.CatalogError, OSError) as exc:
        print(f"error: failed to load catalog {catalog_path}: {exc}", file=sys.stderr)
        print(SUBSCRIPTION_DISCLAIMER, file=sys.stderr)
        return 2

    result = estimate(
        data,
        model=args.model,
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
        cached_tokens=args.cached_tokens,
        cache_write_tokens=args.cache_write_tokens,
        cache_write_ttl=args.cache_write_ttl,
        batch=args.batch,
        long_context=args.long_context,
        as_of_date=args.pricing_date,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(SUBSCRIPTION_DISCLAIMER, file=sys.stderr)
    else:
        _print_text(result)

    return 2 if result["confidence"] == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
