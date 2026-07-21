#!/usr/bin/env python3
"""Build an ordered mkdir plan from a structure contract and registered batches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath


def normalize(value: str) -> str:
    return "/" + "/".join(part for part in str(value).split("/") if part)


def within(path: str, root: str) -> bool:
    normalized_path = normalize(path)
    normalized_root = normalize(root)
    return normalized_path == normalized_root or normalized_path.startswith(normalized_root + "/")


def ancestors(path: str) -> set[str]:
    current = PurePosixPath(normalize(path))
    result: set[str] = set()
    while str(current) != "/":
        result.add(str(current))
        current = current.parent
    return result


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected object")
            rows.append(value)
    return rows


def contract_paths(contract: dict) -> set[str]:
    paths: set[str] = set()
    for key in ("numbered_layers", "guide_layers", "required_guides", "chunk_layers"):
        for rule in contract.get(key, []):
            parent = str(rule.get("parent", "")).strip()
            if parent:
                paths.add(normalize(parent))
            guide = str(rule.get("guide_name", "")).strip()
            if parent and guide:
                paths.add(normalize(parent + "/" + guide))
            if key == "chunk_layers" and parent:
                for child in rule.get("required_children", []):
                    paths.add(normalize(parent + "/" + str(child)))
    review_root = str(contract.get("review_root", "")).strip()
    if review_root:
        paths.add(normalize(review_root))
    return paths


def batch_target_paths(run_dir: Path, manifest: dict) -> set[str]:
    paths: set[str] = set()
    for batch_index, batch in enumerate(manifest.get("batches", []), 1):
        # Structure batches are generated outputs of this script. Reading an
        # older structure plan back as input makes removed paths immortal on
        # every regeneration. Callers mark them explicitly so the builder is
        # driven only by the contract and semantic action batches.
        if str(batch.get("kind", "")).strip() == "structure":
            continue
        plan_value = str(batch.get("plan", "")).strip()
        if not plan_value:
            raise ValueError(f"batch {batch_index}: missing plan")
        plan_path = (run_dir / plan_value).resolve()
        if run_dir.resolve() not in plan_path.parents:
            raise ValueError(f"batch {batch_index}: plan escapes run dir: {plan_value}")
        for action in read_jsonl(plan_path):
            op = action.get("op")
            target = str(action.get("to", "")).strip()
            if not target:
                raise ValueError(f"batch {batch_index}: action has no target")
            if op in {"mkdir", "mv"}:
                paths.add(normalize(target))
            elif op == "rename":
                paths.add(str(PurePosixPath(normalize(target)).parent))
    return paths


def build_plan(contract: dict, run_dir: Path, manifest: dict, prefix: str) -> list[dict]:
    leaf_paths = contract_paths(contract) | batch_target_paths(run_dir, manifest)
    all_paths: set[str] = set()
    for path in leaf_paths:
        all_paths.update(ancestors(path))
    ordered = sorted(all_paths, key=lambda value: (value.count("/"), value))
    return [
        {
            "action_id": f"{prefix}-MK{index:04d}",
            "op": "mkdir",
            "to": path,
            "reason": "create ordered structure parent from contract and registered plans",
        }
        for index, path in enumerate(ordered, 1)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--action-prefix", default="STRUCT")
    parser.add_argument("--include-root", action="append", default=[])
    args = parser.parse_args()
    try:
        contract = read_json(args.contract)
        manifest = read_json(args.run_manifest)
        actions = build_plan(contract, args.run_manifest.resolve().parent, manifest, args.action_prefix)
        if args.include_root:
            actions = [
                action for action in actions
                if any(within(action["to"], root) for root in args.include_root)
            ]
            for index, action in enumerate(actions, 1):
                action["action_id"] = f"{args.action_prefix}-MK{index:04d}"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            for action in actions:
                handle.write(json.dumps(action, ensure_ascii=False, separators=(",", ":")) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"mkdir_actions": len(actions)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
