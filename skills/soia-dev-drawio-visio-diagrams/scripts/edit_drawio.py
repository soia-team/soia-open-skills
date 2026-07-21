#!/usr/bin/env python3
"""Apply a bounded JSON upgrade plan to an uncompressed draw.io XML file."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


class EditError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_style(value: str) -> tuple[list[str], dict[str, str]]:
    flags: list[str] = []
    properties: dict[str, str] = {}
    for token in value.split(";"):
        if not token:
            continue
        if "=" in token:
            key, val = token.split("=", 1)
            properties[key] = val
        else:
            flags.append(token)
    return flags, properties


def render_style(flags: list[str], properties: dict[str, str]) -> str:
    tokens = [*flags, *(f"{key}={value}" for key, value in properties.items())]
    return ";".join(tokens) + (";" if tokens else "")


def load_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditError(f"cannot read plan: {exc}") from exc
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise EditError("plan schema_version must be 1")
    return plan


def require_new_output(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.exists():
        raise EditError(f"refusing to overwrite existing output: {path}")
    if not path.parent.is_dir():
        raise EditError(f"output directory does not exist: {path.parent}")
    return path


def apply_plan(input_path: Path, plan_path: Path, output_path: Path) -> dict[str, Any]:
    input_path = input_path.expanduser().resolve()
    plan_path = plan_path.expanduser().resolve()
    output_path = require_new_output(output_path)
    if not input_path.is_file():
        raise EditError(f"input not found: {input_path}")
    try:
        tree = ET.parse(input_path)
    except ET.ParseError as exc:
        raise EditError(f"invalid draw.io XML: {exc}") from exc
    root = tree.getroot()
    if root.tag != "mxfile":
        raise EditError(f"expected <mxfile>, got <{root.tag}>")
    diagrams = root.findall("diagram")
    if not diagrams or any(not list(diagram) for diagram in diagrams):
        raise EditError("edit_drawio requires uncompressed <diagram><mxGraphModel> XML")
    plan = load_plan(plan_path)
    receipt: dict[str, Any] = {
        "action": "edit",
        "input": str(input_path),
        "input_sha256": sha256_file(input_path),
        "plan": str(plan_path),
        "changes": {"rename_pages": 0, "replace_text": 0, "set_style": 0, "set_geometry": 0},
    }

    for item in plan.get("rename_pages", []):
        source, target = item.get("from"), item.get("to")
        if not isinstance(source, str) or not isinstance(target, str) or not target:
            raise EditError("rename_pages entries require non-empty string from/to")
        matches = [diagram for diagram in diagrams if diagram.attrib.get("name", "") == source]
        if not matches:
            raise EditError(f"rename_pages matched no page: {source!r}")
        for diagram in matches:
            diagram.set("name", target)
            receipt["changes"]["rename_pages"] += 1

    cells = root.findall(".//mxCell")
    cells_by_id = {cell.attrib.get("id", ""): cell for cell in cells if cell.attrib.get("id")}
    wrappers = [element for element in root.iter() if element.tag in {"UserObject", "object"}]
    for wrapper in wrappers:
        wrapper_id = wrapper.attrib.get("id")
        wrapped_cell = wrapper.find("mxCell")
        if wrapper_id and wrapped_cell is not None:
            cells_by_id[wrapper_id] = wrapped_cell
    for item in plan.get("replace_text", []):
        source, target, mode = item.get("from"), item.get("to"), item.get("match", "exact")
        if not isinstance(source, str) or not isinstance(target, str) or not source:
            raise EditError("replace_text entries require non-empty string from and string to")
        if mode not in {"exact", "substring"}:
            raise EditError("replace_text match must be exact or substring")
        matched = 0
        labelled_elements = [*cells, *wrappers]
        for element in labelled_elements:
            attribute = "value" if element.tag == "mxCell" else "label"
            current = element.attrib.get(attribute)
            if current is None:
                continue
            if mode == "exact" and current == source:
                element.set(attribute, target)
                matched += 1
            elif mode == "substring" and source in current:
                element.set(attribute, current.replace(source, target))
                matched += 1
        if not matched:
            raise EditError(f"replace_text matched no cell: {source!r}")
        receipt["changes"]["replace_text"] += matched

    for item in plan.get("set_style", []):
        cell_id, updates = item.get("cell_id"), item.get("properties")
        if not isinstance(cell_id, str) or cell_id not in cells_by_id or not isinstance(updates, dict):
            raise EditError(f"invalid set_style target/properties: {cell_id!r}")
        cell = cells_by_id[cell_id]
        flags, properties = parse_style(cell.attrib.get("style", ""))
        for key, value in updates.items():
            if not isinstance(key, str) or not key:
                raise EditError("style property names must be non-empty strings")
            if value is None:
                properties.pop(key, None)
            elif isinstance(value, (str, int, float, bool)):
                properties[key] = str(value).lower() if isinstance(value, bool) else str(value)
            else:
                raise EditError(f"unsupported style value for {key!r}")
        cell.set("style", render_style(flags, properties))
        receipt["changes"]["set_style"] += 1

    allowed_geometry = {"x", "y", "width", "height"}
    for item in plan.get("set_geometry", []):
        cell_id = item.get("cell_id")
        if not isinstance(cell_id, str) or cell_id not in cells_by_id:
            raise EditError(f"unknown set_geometry cell_id: {cell_id!r}")
        unknown = set(item) - allowed_geometry - {"cell_id"}
        if unknown:
            raise EditError(f"unsupported geometry fields: {sorted(unknown)}")
        cell = cells_by_id[cell_id]
        geometry = cell.find("mxGeometry")
        if geometry is None:
            raise EditError(f"cell has no mxGeometry: {cell_id}")
        for key in allowed_geometry:
            if key not in item:
                continue
            value = item[key]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise EditError(f"geometry {key} must be a finite number")
            geometry.set(key, str(value))
        receipt["changes"]["set_geometry"] += 1

    if not any(receipt["changes"].values()):
        raise EditError("plan produced no changes")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    receipt.update(
        {
            "output": str(output_path),
            "output_size": output_path.stat().st_size,
            "output_sha256": sha256_file(output_path),
        }
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = apply_plan(args.input, args.plan, args.output)
    except (EditError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
