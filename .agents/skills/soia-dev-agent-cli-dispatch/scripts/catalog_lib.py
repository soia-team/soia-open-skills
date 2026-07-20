#!/usr/bin/env python3
# @created_by unknown
# @created_at unknown
# @modified_by openai/gpt-5
# @modified_at 2026-07-10 17:58:15
# @version 0.2.0
# @description Parse, validate, and resolve the dispatch model catalog.
# @changelog Enforce routing, discovery, pricing-source, and actual-model alias contracts.
"""Restricted YAML-subset parser and schema validator for model-catalog.yml.

This is NOT a general YAML parser. It only understands the subset that
scripts in this skill emit and consume: 2-space indentation, block maps,
block lists of scalars or maps, one inline flow list per line (``[a, b]``),
quoted/unquoted scalars, ``null``/``true``/``false``, and full-line ``#``
comments. It exists so that ``estimate_cost.py`` and ``run_matrix.py`` have
zero third-party dependencies (stdlib only).

Usage:
    python3 catalog_lib.py --selftest
    python3 catalog_lib.py --path ../references/model-catalog.yml --validate

The functions below are also imported directly by ``estimate_cost.py`` and
``run_matrix.py``.
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path
from typing import Any


class CatalogError(Exception):
    """Raised for structural problems while parsing the restricted YAML subset."""


# ---------------------------------------------------------------------------
# Tokenizing
# ---------------------------------------------------------------------------

_LINE_RE = re.compile(r"^( *)(\S.*)$")


def _tokenize(text: str) -> list[tuple[int, str]]:
    """Strip blank lines and full-line comments, return (indent, content) pairs.

    Raises CatalogError on odd (non-2-step) indentation or tab characters,
    since those are outside the supported subset.
    """
    lines: list[tuple[int, str]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw:
            raise CatalogError(f"line {lineno}: tabs are not supported, use spaces")
        stripped = raw.rstrip()
        if not stripped.strip():
            continue
        if stripped.lstrip().startswith("#"):
            continue
        match = _LINE_RE.match(stripped)
        if not match:
            continue
        indent = len(match.group(1))
        if indent % 2 != 0:
            raise CatalogError(f"line {lineno}: indentation must be a multiple of 2 spaces")
        content = match.group(2)
        lines.append((indent, content))
    return lines


# ---------------------------------------------------------------------------
# Scalar parsing
# ---------------------------------------------------------------------------

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def parse_scalar(text: str) -> Any:
    """Parse a single scalar value (already stripped of the surrounding key)."""
    value = text.strip()
    if value == "":
        return None
    if value == "null" or value == "~":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = []
        for part in inner.split(","):
            items.append(parse_scalar(part.strip()))
        return items
    if _INT_RE.match(value):
        return int(value)
    if _FLOAT_RE.match(value):
        return float(value)
    return value


def _split_key_value(content: str) -> tuple[str, str | None]:
    """Split 'key: value' or 'key:' into (key, value_or_None).

    Only the first ':' followed by a space (or end-of-line) is treated as
    the key/value separator, so values may themselves contain ':' (e.g. a
    URL) as long as authors keep that URL quoted or free of ': ' sequences.
    """
    idx = content.find(":")
    while idx != -1:
        after = content[idx + 1 :]
        if after == "" or after.startswith(" "):
            key = content[:idx].strip()
            value = after.strip()
            return key, (value if value != "" else None)
        idx = content.find(":", idx + 1)
    raise CatalogError(f"cannot find 'key: value' separator in line: {content!r}")


# ---------------------------------------------------------------------------
# Block parsing (recursive, indent-stack based)
# ---------------------------------------------------------------------------


def _parse_dict_block(lines: list[tuple[int, str]], i: int, indent: int) -> tuple[dict, int]:
    result: dict[str, Any] = {}
    n = len(lines)
    while i < n:
        cur_indent, content = lines[i]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise CatalogError(f"unexpected indentation at: {content!r}")
        if content.startswith("- "):
            # This dict block is done; a list at this indent belongs to the parent key.
            break
        key, inline_value = _split_key_value(content)
        i += 1
        if inline_value is not None:
            result[key] = parse_scalar(inline_value)
            continue
        # Bare 'key:' -> look ahead for a nested block (dict or list) at indent+2.
        if i < n and lines[i][0] > indent:
            child_indent = lines[i][0]
            if lines[i][1].startswith("- "):
                value, i = _parse_list_block(lines, i, child_indent)
            else:
                value, i = _parse_dict_block(lines, i, child_indent)
            result[key] = value
        else:
            result[key] = None
    return result, i


def _parse_list_block(lines: list[tuple[int, str]], i: int, indent: int) -> tuple[list, int]:
    result: list[Any] = []
    n = len(lines)
    while i < n:
        cur_indent, content = lines[i]
        if cur_indent != indent:
            break
        if not content.startswith("- "):
            break
        after_dash = content[2:]
        child_indent = indent + 2
        if ":" in after_dash and _looks_like_key_value(after_dash):
            # First field of a nested map; splice a synthetic line so the
            # dict parser sees it at the map's own indent level.
            spliced = [(child_indent, after_dash)]
            j = i + 1
            while j < n and lines[j][0] >= child_indent:
                spliced.append(lines[j])
                j += 1
            value, _ = _parse_dict_block(spliced, 0, child_indent)
            result.append(value)
            i = j
        else:
            result.append(parse_scalar(after_dash))
            i += 1
    return result, i


def _looks_like_key_value(text: str) -> bool:
    """Heuristic: 'foo: bar' is a key/value pair, '[a, b]' or 'plain text' is not."""
    try:
        key, _ = _split_key_value(text)
    except CatalogError:
        return False
    # A bare scalar containing ':' but not shaped like an identifier key
    # (e.g. a URL scalar) would rarely appear as a raw list item in our
    # generated files; require the key to look like an identifier.
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_.\-]*$", key))


def parse_yaml_subset(text: str) -> dict:
    """Parse the restricted subset into nested dict/list/scalar Python values."""
    lines = _tokenize(text)
    if not lines:
        return {}
    if lines[0][0] != 0:
        raise CatalogError("top-level document must start at indentation 0")
    value, i = _parse_dict_block(lines, 0, 0)
    if i != len(lines):
        raise CatalogError(f"trailing unparsed content starting at line index {i}")
    return value


def load_catalog(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return parse_yaml_subset(text)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

REQUIRED_TOP_KEYS = ("schema_version", "updated_at", "currency", "pricing_unit", "sources", "providers")
REQUIRED_PROVIDER_KEYS = ("executor_cli", "models")
REQUIRED_MODEL_KEYS = (
    "model_id", "display_name", "aliases", "model_family", "availability",
    "context_window", "supported_reasoning_levels", "reasoning_levels_confidence",
    "default_reasoning_level", "pricing", "routing_profile", "discovered_at",
    "discovery_evidence",
)
NON_NULL_MODEL_KEYS = (
    "model_id", "display_name", "aliases", "model_family", "availability",
    "supported_reasoning_levels", "reasoning_levels_confidence", "pricing",
)
PRICE_KEY_HINT = re.compile(r"per_1m|per_1m_tokens|per_hour")


def _walk_price_fields(node: Any, path: str, errors: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            child_path = f"{path}.{key}" if path else key
            if isinstance(value, (int, float)) and PRICE_KEY_HINT.search(key):
                if value < 0:
                    errors.append(f"negative price at {child_path}: {value}")
            _walk_price_fields(value, child_path, errors)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            _walk_price_fields(item, f"{path}[{idx}]", errors)


def validate_catalog(data: dict) -> dict[str, list[str]]:
    """Validate the parsed catalog. Returns {"errors": [...], "warnings": [...]}.

    Hard rejects (errors): missing top-level keys, a provider block missing
    executor_cli/models, duplicate model_id across the whole catalog, and
    any negative *_per_1m / *_per_hour price.
    Soft flags (warnings): models whose reasoning levels are unverified or
    unspecified, since those are candidates, not confirmed facts.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"missing required top-level key: {key}")

    providers = data.get("providers")
    if not isinstance(providers, dict):
        errors.append("providers must be a mapping")
        providers = {}

    seen_model_ids: dict[str, str] = {}
    for provider_name, provider_block in providers.items():
        if not isinstance(provider_block, dict):
            errors.append(f"provider {provider_name!r} must be a mapping")
            continue
        for req_key in REQUIRED_PROVIDER_KEYS:
            if req_key not in provider_block:
                errors.append(f"provider {provider_name!r} missing required key: {req_key}")
        models = provider_block.get("models")
        if models is None:
            continue
        if not isinstance(models, list):
            errors.append(f"provider {provider_name!r}.models must be a list")
            continue
        for idx, model in enumerate(models):
            if not isinstance(model, dict):
                errors.append(f"provider {provider_name!r}.models[{idx}] must be a mapping")
                continue
            for req_key in REQUIRED_MODEL_KEYS:
                if req_key not in model:
                    errors.append(
                        f"provider {provider_name!r}.models[{idx}] missing required key: {req_key}"
                    )
            for req_key in NON_NULL_MODEL_KEYS:
                if req_key in model and model[req_key] in (None, ""):
                    errors.append(f"provider {provider_name!r}.models[{idx}] key must not be null: {req_key}")
            model_id = model.get("model_id")
            if isinstance(model_id, str) and model_id:
                if model_id in seen_model_ids:
                    errors.append(
                        f"duplicate model_id {model_id!r} (providers: "
                        f"{seen_model_ids[model_id]!r} and {provider_name!r})"
                    )
                else:
                    seen_model_ids[model_id] = provider_name

            confidence = model.get("reasoning_levels_confidence")
            levels = model.get("supported_reasoning_levels")
            if not isinstance(levels, list):
                errors.append(f"model {model_id!r}: supported_reasoning_levels must be a list")
                levels = []
            if confidence not in {"unverified", "official_docs", "smoke_tested", "verified"}:
                errors.append(f"model {model_id!r}: invalid reasoning_levels_confidence {confidence!r}")
            if confidence == "unverified" or not levels:
                warnings.append(
                    f"model {model_id!r}: supported_reasoning_levels unverified or empty"
                )

            default_level = model.get("default_reasoning_level")
            if default_level is not None and default_level not in levels:
                errors.append(f"model {model_id!r}: default_reasoning_level {default_level!r} is not supported")

            routing_profile = model.get("routing_profile")
            if routing_profile is not None and not isinstance(routing_profile, list):
                errors.append(f"model {model_id!r}: routing_profile must be a list or null")
            if routing_profile:
                invalid_profiles = sorted(set(routing_profile) - {"easy", "medium", "hard"})
                if invalid_profiles:
                    errors.append(f"model {model_id!r}: invalid routing_profile values {invalid_profiles}")
                if not model.get("discovered_at") or not model.get("discovery_evidence"):
                    errors.append(f"model {model_id!r}: routed models require discovered_at and discovery_evidence")
                if not levels:
                    errors.append(f"model {model_id!r}: routed models require verified reasoning levels")

            if confidence in {"smoke_tested", "verified"} and (
                not model.get("discovered_at") or not model.get("discovery_evidence")
            ):
                errors.append(f"model {model_id!r}: verified reasoning requires discovery evidence")

            for alias_key in ("aliases", "actual_model_aliases"):
                aliases = model.get(alias_key, [])
                if not isinstance(aliases, list) or any(not isinstance(alias, str) or not alias for alias in aliases):
                    errors.append(f"model {model_id!r}: {alias_key} must be a list of non-empty strings")

            pricing = model.get("pricing")
            if isinstance(pricing, dict):
                _walk_price_fields(pricing, f"models[{model_id}].pricing", errors)
                if not pricing.get("effective_date") or not pricing.get("source_id"):
                    errors.append(f"model {model_id!r}: pricing requires effective_date and source_id")
                future_pricing = pricing.get("future_pricing")
                if future_pricing is not None:
                    if not isinstance(future_pricing, dict):
                        errors.append(f"model {model_id!r}: future_pricing must be a mapping")
                    else:
                        for key in ("effective_from", "effective_date", "source_id", "input_per_1m", "output_per_1m"):
                            if future_pricing.get(key) in (None, ""):
                                errors.append(f"model {model_id!r}: future_pricing missing {key}")
            elif "pricing" in model:
                errors.append(f"model {model_id!r}.pricing must be a mapping")

    return {"errors": errors, "warnings": warnings}


def find_model(data: dict, requested: str) -> dict[str, Any]:
    """Loosely resolve a requested model string to a catalog entry.

    Matching order: exact model_id -> exact alias -> case-insensitive
    model_id/alias -> case-insensitive display_name -> normalized
    (lowercase, spaces/underscores -> hyphens) substring match. Returns a
    dict with keys: match ("exact"|"loose"|None), model (entry or None),
    provider (name or None), candidates (list of near-miss model_ids for
    unknown_pricing reporting).
    """

    def normalize(value: str) -> str:
        return re.sub(r"[\s_]+", "-", value.strip().lower())

    target = requested.strip()
    target_norm = normalize(target)

    all_models: list[tuple[str, dict]] = []
    providers = data.get("providers", {})
    if isinstance(providers, dict):
        for provider_name, provider_block in providers.items():
            if not isinstance(provider_block, dict):
                continue
            for model in provider_block.get("models", []) or []:
                if isinstance(model, dict):
                    all_models.append((provider_name, model))

    # 1. Exact model_id match.
    for provider_name, model in all_models:
        if model.get("model_id") == target:
            return {"match": "exact", "model": model, "provider": provider_name, "candidates": []}

    # 2. Exact alias match.
    for provider_name, model in all_models:
        if target in (model.get("aliases") or []):
            return {"match": "exact", "model": model, "provider": provider_name, "candidates": []}

    # 3. Case/format-normalized model_id, alias, or display_name match.
    for provider_name, model in all_models:
        candidates_norm = {normalize(str(model.get("model_id", "")))}
        candidates_norm.add(normalize(str(model.get("display_name", ""))))
        for alias in model.get("aliases") or []:
            candidates_norm.add(normalize(str(alias)))
        if target_norm in candidates_norm:
            return {"match": "loose", "model": model, "provider": provider_name, "candidates": []}

    # No match: build near-miss candidates for the caller to report.
    import difflib

    pool = {}
    for _, model in all_models:
        mid = model.get("model_id")
        if isinstance(mid, str):
            pool[mid] = mid
        for alias in model.get("aliases") or []:
            pool[str(alias)] = model.get("model_id")
    close = difflib.get_close_matches(target, list(pool.keys()), n=5, cutoff=0.4)
    candidates = sorted({pool[c] for c in close if pool.get(c)})
    return {"match": None, "model": None, "provider": None, "candidates": candidates}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "model-catalog.yml"


def run_selftest() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, condition, detail))

    # 1. Basic scalar parsing.
    check("scalar: quoted string", parse_scalar('"2026-07-10"') == "2026-07-10")
    check("scalar: null", parse_scalar("null") is None)
    check("scalar: int", parse_scalar("5") == 5 and isinstance(parse_scalar("5"), int))
    check("scalar: float", parse_scalar("0.5") == 0.5)
    check("scalar: bool true", parse_scalar("true") is True)
    check("scalar: inline empty list", parse_scalar("[]") == [])
    check("scalar: inline list", parse_scalar("[low, medium, high]") == ["low", "medium", "high"])
    check("scalar: bare string", parse_scalar("available") == "available")

    # 2. Nested dict + list-of-maps + inline list round trip.
    sample = """\
schema_version: 1
updated_at: "2026-07-10"
providers:
  openai:
    executor_cli: codex
    models:
      - model_id: gpt-5.6-sol
        display_name: "GPT-5.6 Sol"
        aliases: [sol, gpt-5.6-sol]
        availability: available
        supported_reasoning_levels: [low, medium, high, xhigh]
        pricing:
          input_per_1m: 5
          output_per_1m: 30
          long_context:
            threshold_tokens: 272000
            input_per_1m: 10
            output_per_1m: 45
      - model_id: gpt-5.6-terra
        display_name: "GPT-5.6 Terra"
        aliases: []
        availability: available
        pricing:
          input_per_1m: 2.5
          output_per_1m: 15
sources:
  - id: pricing-2026-07-10
    path: references/model-pricing-2026-07-10.md
    date: "2026-07-10"
"""
    parsed = parse_yaml_subset(sample)
    check("parse: top-level keys", set(parsed.keys()) >= {"schema_version", "providers", "sources"})
    check("parse: schema_version int", parsed.get("schema_version") == 1)
    models = parsed["providers"]["openai"]["models"]
    check("parse: two models found", len(models) == 2)
    check("parse: first model_id", models[0]["model_id"] == "gpt-5.6-sol")
    check("parse: aliases inline list", models[0]["aliases"] == ["sol", "gpt-5.6-sol"])
    check(
        "parse: nested long_context dict",
        models[0]["pricing"]["long_context"]["threshold_tokens"] == 272000,
    )
    check("parse: second model empty aliases", models[1]["aliases"] == [])
    check(
        "parse: sources list of maps",
        parsed["sources"][0]["id"] == "pricing-2026-07-10" and parsed["sources"][0]["date"] == "2026-07-10",
    )

    # 3. Schema validation: duplicate model_id rejected.
    dup = {
        "schema_version": 1,
        "updated_at": "2026-07-10",
        "currency": "USD",
        "pricing_unit": "per_1m_tokens",
        "sources": [],
        "providers": {
            "openai": {
                "executor_cli": "codex",
                "models": [
                    {"model_id": "a", "display_name": "A", "availability": "available", "pricing": {"input_per_1m": 1}},
                    {"model_id": "a", "display_name": "A2", "availability": "available", "pricing": {"input_per_1m": 1}},
                ],
            }
        },
    }
    result = validate_catalog(dup)
    check("validate: duplicate model_id rejected", any("duplicate model_id" in e for e in result["errors"]))

    # 4. Schema validation: missing provider key rejected.
    missing_provider_key = {
        "schema_version": 1,
        "updated_at": "2026-07-10",
        "currency": "USD",
        "pricing_unit": "per_1m_tokens",
        "sources": [],
        "providers": {"openai": {"models": []}},
    }
    result = validate_catalog(missing_provider_key)
    check(
        "validate: missing executor_cli rejected",
        any("missing required key: executor_cli" in e for e in result["errors"]),
    )

    # 5. Schema validation: negative price rejected.
    negative_price = {
        "schema_version": 1,
        "updated_at": "2026-07-10",
        "currency": "USD",
        "pricing_unit": "per_1m_tokens",
        "sources": [],
        "providers": {
            "openai": {
                "executor_cli": "codex",
                "models": [
                    {
                        "model_id": "b",
                        "display_name": "B",
                        "availability": "available",
                        "pricing": {"input_per_1m": -1},
                    }
                ],
            }
        },
    }
    result = validate_catalog(negative_price)
    check("validate: negative price rejected", any("negative price" in e for e in result["errors"]))

    # 6. Schema validation: unverified reasoning levels flagged as warning, not error.
    unverified = {
        "schema_version": 1,
        "updated_at": "2026-07-10",
        "currency": "USD",
        "pricing_unit": "per_1m_tokens",
        "sources": [],
        "providers": {
            "openai": {
                "executor_cli": "codex",
                "models": [
                    {
                        "model_id": "c",
                        "display_name": "C",
                        "aliases": [],
                        "model_family": "c",
                        "availability": "available",
                        "context_window": None,
                        "pricing": {"input_per_1m": 1, "output_per_1m": 2, "effective_date": "2026-07-10", "source_id": "test"},
                        "supported_reasoning_levels": [],
                        "reasoning_levels_confidence": "unverified",
                        "default_reasoning_level": None,
                        "routing_profile": None,
                        "discovered_at": None,
                        "discovery_evidence": None,
                    }
                ],
            }
        },
    }
    result = validate_catalog(unverified)
    check(
        "validate: unverified reasoning level -> warning not error",
        any("unverified" in w for w in result["warnings"]) and not result["errors"],
    )

    invalid_routing = copy.deepcopy(unverified)
    invalid_routing["providers"]["openai"]["models"][0]["routing_profile"] = ["medium"]
    result = validate_catalog(invalid_routing)
    check(
        "validate: routed model without discovery evidence rejected",
        any("routed models require" in e for e in result["errors"]),
    )

    # 7. find_model: exact, alias, loose, and unknown resolution.
    catalog_path = _default_catalog_path()
    if catalog_path.is_file():
        real_data = load_catalog(catalog_path)
        real_result = validate_catalog(real_data)
        check(
            f"real catalog ({catalog_path.name}): parses with 0 errors",
            not real_result["errors"],
            "; ".join(real_result["errors"][:5]),
        )
        exact = find_model(real_data, "gpt-5.6-sol")
        check("find_model: exact model_id in real catalog", exact["match"] == "exact")
        unknown = find_model(real_data, "totally-unknown-model-xyz")
        check("find_model: unknown model returns no match", unknown["match"] is None)
    else:
        check("real catalog file present", False, f"not found at {catalog_path}")

    # Report.
    print("=== catalog_lib.py selftest ===")
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", help="Path to a catalog YAML file to load.")
    parser.add_argument("--validate", action="store_true", help="Validate the loaded catalog and print findings.")
    parser.add_argument("--selftest", action="store_true", help="Run built-in self-tests and exit.")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    path = Path(args.path) if args.path else _default_catalog_path()
    try:
        data = load_catalog(path)
    except (CatalogError, OSError) as exc:
        print(f"error: failed to load {path}: {exc}", file=sys.stderr)
        return 2

    if args.validate:
        result = validate_catalog(data)
        for err in result["errors"]:
            print(f"ERROR: {err}")
        for warn in result["warnings"]:
            print(f"WARN: {warn}")
        if not result["errors"] and not result["warnings"]:
            print("No findings.")
        return 1 if result["errors"] else 0

    print(f"Parsed {path}: top-level keys = {sorted(data.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
