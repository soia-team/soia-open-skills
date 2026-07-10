#!/usr/bin/env python3
# @created_by openai/gpt-5
# @created_at 2026-07-10 17:58:15
# @modified_by openai/gpt-5
# @modified_at 2026-07-10 17:58:15
# @version 0.1.0
# @description Select a verified executor model and reasoning effort from model-catalog.yml.
# @changelog Initial creation.
"""Mechanically route an executor family to a verified model/effort pair."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib  # noqa: E402


class RouteError(Exception):
    pass


PREFERRED_EFFORTS = {
    "easy": ["low", "medium", "high", "xhigh", "max"],
    "medium": ["medium", "high", "low", "xhigh", "max"],
    "hard": ["high", "xhigh", "max", "medium", "low"],
}


def _models_for_executor(data: dict, executor: str) -> list[dict[str, Any]]:
    result = []
    for provider in (data.get("providers") or {}).values():
        if isinstance(provider, dict) and provider.get("executor_cli") == executor:
            result.extend(model for model in provider.get("models", []) if isinstance(model, dict))
    return result


def _choose_effort(model: dict[str, Any], complexity: str, requested: str | None) -> tuple[str | None, str]:
    levels = model.get("supported_reasoning_levels") or []
    confidence = model.get("reasoning_levels_confidence")
    if requested:
        if requested in levels:
            return requested, "explicit"
        if confidence == "unverified":
            return requested, "explicit_unverified"
        raise RouteError(f"reasoning effort {requested!r} is not verified for {model.get('model_id')!r}")
    default = model.get("default_reasoning_level")
    for candidate in PREFERRED_EFFORTS[complexity]:
        if candidate in levels:
            return candidate, "verified_auto"
    if default in levels:
        return default, "verified_auto"
    return None, "explicit_unverified"


def _cost_range(model: dict[str, Any]) -> dict[str, str | None]:
    pricing = model.get("pricing") or {}
    input_rate = pricing.get("input_per_1m")
    output_rate = pricing.get("output_per_1m")
    if not isinstance(input_rate, (int, float)) or not isinstance(output_rate, (int, float)):
        return {"basis": "1M input + 1M output, standard tier", "min_usd": None, "max_usd": None}
    total = Decimal(str(input_rate)) + Decimal(str(output_rate))
    value = format(total, "f").rstrip("0").rstrip(".") or "0"
    return {"basis": "1M input + 1M output, standard tier", "min_usd": value, "max_usd": value}


def route_model(data: dict, executor: str, complexity: str, requested_model: str | None = None, requested_reasoning: str | None = None) -> dict[str, Any]:
    if complexity not in PREFERRED_EFFORTS:
        raise RouteError(f"invalid complexity {complexity!r}")
    if requested_model:
        resolution = catalog_lib.find_model(data, requested_model)
        model = resolution.get("model")
        provider = resolution.get("provider")
        if not isinstance(model, dict) or not provider:
            raise RouteError(f"model {requested_model!r} not found in catalog")
        provider_block = (data.get("providers") or {}).get(provider) or {}
        if provider_block.get("executor_cli") != executor:
            raise RouteError(f"model {requested_model!r} does not belong to executor {executor!r}")
        effort, effort_status = _choose_effort(model, complexity, requested_reasoning)
        selection_status = effort_status if effort_status == "explicit_unverified" else "explicit"
        reason = "explicit model/reasoning selection takes precedence"
    else:
        candidates = [
            model for model in _models_for_executor(data, executor)
            if complexity in (model.get("routing_profile") or [])
            and model.get("discovered_at") and model.get("discovery_evidence")
            and model.get("supported_reasoning_levels")
            and model.get("reasoning_levels_confidence") in {"smoke_tested", "verified"}
        ]
        if not candidates:
            raise RouteError(f"no verified {complexity!r} routing candidate for executor {executor!r}")
        candidates.sort(key=lambda item: item.get("model_id", ""))
        model = candidates[0]
        effort, selection_status = _choose_effort(model, complexity, None)
        reason = f"catalog routing_profile={complexity}; discovery and reasoning evidence are present"
    return {
        "executor": executor,
        "selected_model": model.get("model_id"),
        "selected_reasoning_effort": effort,
        "task_complexity": complexity,
        "selection_reason": reason,
        "estimated_cost_range": _cost_range(model),
        "catalog_version": data.get("updated_at"),
        "selection_status": selection_status,
        "routing_evidence": model.get("discovery_evidence"),
    }


def run_selftest() -> int:
    data = catalog_lib.load_catalog(Path(__file__).resolve().parents[1] / "references" / "model-catalog.yml")
    checks: list[tuple[str, bool]] = []
    checks.append(("codex easy -> luna low", route_model(data, "codex", "easy")["selected_model"] == "gpt-5.6-luna" and route_model(data, "codex", "easy")["selected_reasoning_effort"] == "low"))
    checks.append(("codex medium -> terra medium", route_model(data, "codex", "medium")["selected_model"] == "gpt-5.6-terra" and route_model(data, "codex", "medium")["selected_reasoning_effort"] == "medium"))
    checks.append(("codex hard -> sol high", route_model(data, "codex", "hard")["selected_model"] == "gpt-5.6-sol" and route_model(data, "codex", "hard")["selected_reasoning_effort"] == "high"))
    explicit = route_model(data, "codex", "easy", "gpt-5.6-sol", "xhigh")
    checks.append(("explicit model/effort wins", explicit["selected_model"] == "gpt-5.6-sol" and explicit["selected_reasoning_effort"] == "xhigh" and explicit["selection_status"] == "explicit"))
    try:
        route_model(data, "claude", "hard")
    except RouteError:
        checks.append(("no verified claude hard candidate blocks", True))
    else:
        checks.append(("no verified claude hard candidate blocks", False))
    receipt = route_model(data, "claude", "medium")
    checks.append(("route receipt has fixed fields", all(key in receipt for key in ("selected_model", "selected_reasoning_effort", "task_complexity", "selection_reason", "estimated_cost_range", "catalog_version", "selection_status"))))
    print("=== route_model.py selftest ===")
    for name, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    passed_count = sum(1 for _, passed in checks if passed)
    print(f"{passed_count}/{len(checks)} checks passed")
    return 0 if passed_count == len(checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executor", choices=["codex", "claude", "gemini", "kimi", "opencode", "qwen"])
    parser.add_argument("--complexity", choices=["easy", "medium", "hard"])
    parser.add_argument("--model")
    parser.add_argument("--reasoning")
    parser.add_argument("--catalog")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return run_selftest()
    if not args.executor or not args.complexity:
        parser.error("--executor and --complexity are required unless --selftest is used")
    catalog_path = Path(args.catalog) if args.catalog else Path(__file__).resolve().parents[1] / "references" / "model-catalog.yml"
    try:
        data = catalog_lib.load_catalog(catalog_path)
        validation = catalog_lib.validate_catalog(data)
        if validation["errors"]:
            raise RouteError("invalid catalog: " + "; ".join(validation["errors"][:5]))
        result = route_model(data, args.executor, args.complexity, args.model, args.reasoning)
    except (OSError, catalog_lib.CatalogError, RouteError) as exc:
        print(json.dumps({"selection_status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
