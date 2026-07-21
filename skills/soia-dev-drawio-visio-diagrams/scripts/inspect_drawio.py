#!/usr/bin/env python3
"""Inspect compressed or uncompressed draw.io XML without modifying it."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import sys
import urllib.parse
import zlib
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


class InspectionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_value(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def decode_diagram(diagram: ET.Element) -> ET.Element:
    children = list(diagram)
    if children:
        return children[0]
    payload = (diagram.text or "").strip()
    if not payload:
        raise InspectionError(f"diagram {diagram.attrib.get('name', '')!r} is empty")
    try:
        raw = base64.b64decode(payload)
        xml_text = urllib.parse.unquote(zlib.decompress(raw, -15).decode("utf-8"))
        return ET.fromstring(xml_text)
    except (ValueError, zlib.error, ET.ParseError, UnicodeDecodeError) as exc:
        raise InspectionError(f"cannot decode compressed diagram: {exc}") from exc


def inspect_drawio(path: Path, max_texts: int = 500) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise InspectionError(f"file not found: {path}")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise InspectionError(f"invalid draw.io XML: {exc}") from exc
    if root.tag != "mxfile":
        raise InspectionError(f"expected <mxfile>, got <{root.tag}>")

    pages: list[dict[str, Any]] = []
    all_texts: list[str] = []
    total_vertices = 0
    total_edges = 0
    for diagram in root.findall("diagram"):
        graph = decode_diagram(diagram)
        cells = graph.findall(".//mxCell")
        vertices = [cell for cell in cells if cell.attrib.get("vertex") == "1"]
        edges = [cell for cell in cells if cell.attrib.get("edge") == "1"]
        text_values = [cell.attrib.get("value", "") for cell in cells]
        text_values.extend(
            wrapper.attrib.get("label", "")
            for wrapper in graph.iter()
            if wrapper.tag in {"UserObject", "object"}
        )
        texts = []
        seen_texts: set[str] = set()
        for value in text_values:
            cleaned = clean_value(value)
            if cleaned and cleaned not in seen_texts:
                seen_texts.add(cleaned)
                texts.append(cleaned)
        all_texts.extend(texts[: max(0, max_texts - len(all_texts))])
        total_vertices += len(vertices)
        total_edges += len(edges)
        pages.append(
            {
                "id": diagram.attrib.get("id", ""),
                "name": diagram.attrib.get("name", ""),
                "cell_count": len(cells),
                "vertex_count": len(vertices),
                "edge_count": len(edges),
                "text_count": len(texts),
                "texts": texts[:max_texts],
            }
        )
    return {
        "path": str(path),
        "format": "drawio",
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "page_count": len(pages),
        "vertex_count": total_vertices,
        "edge_count": total_edges,
        "texts": all_texts,
        "texts_truncated": sum(page["text_count"] for page in pages) > len(all_texts),
        "pages": pages,
    }


def to_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# Draw.io 盘点：{Path(result['path']).name}",
        "",
        f"- SHA-256：`{result['sha256']}`",
        f"- 页面：{result['page_count']}；节点：{result['vertex_count']}；边：{result['edge_count']}",
        "",
    ]
    for page in result["pages"]:
        lines.extend(
            [
                f"## {page['name'] or '(未命名页面)'}",
                "",
                f"- 节点：{page['vertex_count']}；边：{page['edge_count']}；文字：{page['text_count']}",
            ]
        )
        lines.extend(f"  - {text}" for text in page["texts"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--max-texts", type=int, default=500)
    args = parser.parse_args()
    try:
        result = inspect_drawio(args.input, max_texts=max(1, args.max_texts))
    except (InspectionError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(to_markdown(result) if args.format == "markdown" else json.dumps(result, ensure_ascii=False, indent=2), end="" if args.format == "markdown" else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
