#!/usr/bin/env python3
"""Inspect ProcessOn exports without modifying source files."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import struct
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


SUPPORTED_SUFFIXES = {
    ".pos",
    ".xmind",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".pdf",
    ".vsdx",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\u00a0", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def dedupe_text(values: Iterable[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for line in value.splitlines():
            cleaned = clean_text(line)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
                if len(result) >= limit:
                    return result
    return result


def walk_titles(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        title = node.get("title")
        if isinstance(title, str):
            yield title
        for key in ("children", "leftChildren"):
            children = node.get(key)
            if isinstance(children, list):
                for child in children:
                    yield from walk_titles(child)
    elif isinstance(node, list):
        for child in node:
            yield from walk_titles(child)


def inspect_pos(path: Path, text_limit: int) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    meta = payload.get("meta") if isinstance(payload, dict) else {}
    meta = meta if isinstance(meta, dict) else {}
    diagram_info = meta.get("diagramInfo")
    diagram_info = diagram_info if isinstance(diagram_info, dict) else {}
    diagram = payload.get("diagram")
    diagram = diagram if isinstance(diagram, dict) else {}
    elements = diagram.get("elements")

    title = clean_text(diagram_info.get("title"))
    category = clean_text(diagram_info.get("category"))
    texts: list[str] = []
    element_count = 0

    if isinstance(elements, dict) and isinstance(elements.get("elements"), dict):
        flow_elements = elements["elements"]
        element_count = len(flow_elements)
        for element in flow_elements.values():
            if not isinstance(element, dict):
                continue
            blocks = element.get("textBlock")
            if isinstance(blocks, list):
                for block in blocks:
                    if isinstance(block, dict):
                        value = block.get("text")
                        if isinstance(value, str):
                            texts.append(value)
        if not title:
            title = clean_text(elements.get("title"))
    elif isinstance(elements, dict):
        if not title:
            title = clean_text(elements.get("title"))
        texts.extend(walk_titles(elements))

        def count_nodes(node: Any) -> int:
            if isinstance(node, dict):
                return 1 + sum(
                    count_nodes(child)
                    for key in ("children", "leftChildren")
                    for child in (node.get(key) or [])
                    if isinstance(node.get(key), list)
                )
            return 0

        element_count = count_nodes(elements)

    extracted = dedupe_text(([title] if title else []) + texts, text_limit)
    return {
        "kind": "processon-pos",
        "title": title or None,
        "category": category or None,
        "schema_version": meta.get("version"),
        "export_time": meta.get("exportTime"),
        "element_count": element_count,
        "text_count": len(extracted),
        "text": extracted,
    }


def inspect_xmind(path: Path, text_limit: int) -> dict[str, Any]:
    texts: list[str] = []
    source = None
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "content.json" in names:
            source = "content.json"
            payload = json.loads(archive.read("content.json").decode("utf-8"))

            def walk_json(node: Any) -> None:
                if isinstance(node, dict):
                    title = node.get("title")
                    if isinstance(title, str):
                        texts.append(title)
                    for value in node.values():
                        walk_json(value)
                elif isinstance(node, list):
                    for value in node:
                        walk_json(value)

            walk_json(payload)
        elif "content.xml" in names:
            source = "content.xml"
            root = ElementTree.fromstring(archive.read("content.xml"))
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] == "title" and element.text:
                    texts.append(element.text)
        else:
            raise ValueError("XMind archive has neither content.json nor content.xml")

    extracted = dedupe_text(texts, text_limit)
    return {
        "kind": "xmind",
        "source": source,
        "title": extracted[0] if extracted else None,
        "text_count": len(extracted),
        "text": extracted,
    }


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    return None


def gif_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 10 and data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    return None


def jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in (0xD8, 0xD9):
            continue
        if offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset : offset + 2], "big")
        if length < 2 or offset + length > len(data):
            break
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            return width, height
        offset += length
    return None


def webp_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if chunk == b"VP8L" and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    return None


def inspect_image(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    dimensions = (
        png_dimensions(data)
        or gif_dimensions(data)
        or jpeg_dimensions(data)
        or webp_dimensions(data)
    )
    return {
        "kind": "image",
        "width": dimensions[0] if dimensions else None,
        "height": dimensions[1] if dimensions else None,
    }


def inspect_svg(path: Path, text_limit: int) -> dict[str, Any]:
    root = ElementTree.parse(path).getroot()
    values = [
        "".join(element.itertext())
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] in {"text", "title", "desc"}
    ]
    extracted = dedupe_text(values, text_limit)
    return {
        "kind": "svg",
        "width": root.attrib.get("width"),
        "height": root.attrib.get("height"),
        "view_box": root.attrib.get("viewBox"),
        "text_count": len(extracted),
        "text": extracted,
    }


def inspect_vsdx(path: Path) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        raise ValueError("VSDX is not a valid ZIP/OOXML package")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {"[Content_Types].xml", "visio/document.xml", "visio/pages/pages.xml"}
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"VSDX missing required parts: {', '.join(missing)}")
        page_parts = sorted(
            name
            for name in names
            if re.fullmatch(r"visio/pages/page\d+\.xml", name)
        )
    return {
        "kind": "visio-vsdx",
        "package_entries": len(names),
        "page_part_count": len(page_parts),
    }


def inspect_file(path: Path, text_limit: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": path.name,
        "suffix": path.suffix.lower(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    suffix = result["suffix"]
    if suffix == ".pos":
        result.update(inspect_pos(path, text_limit))
    elif suffix == ".xmind":
        result.update(inspect_xmind(path, text_limit))
    elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        result.update(inspect_image(path))
    elif suffix == ".svg":
        result.update(inspect_svg(path, text_limit))
    elif suffix == ".pdf":
        result.update({"kind": "pdf"})
    elif suffix == ".vsdx":
        result.update(inspect_vsdx(path))
    else:
        result.update({"kind": "unknown"})
    return result


def collect_files(source: Path, recursive: bool) -> list[Path]:
    if source.is_file():
        return [source]
    if not source.is_dir():
        raise FileNotFoundError(source)
    iterator = source.rglob("*") if recursive else source.glob("*")
    return sorted(
        path
        for path in iterator
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# ProcessOn export inspection",
        "",
        f"- files: {manifest['file_count']}",
        f"- failures: {manifest['failure_count']}",
        "",
    ]
    for item in manifest["files"]:
        lines.extend(
            [
                f"## {item['name']}",
                "",
                f"- kind: {item.get('kind')}",
                f"- bytes: {item.get('bytes')}",
                f"- sha256: `{item.get('sha256')}`",
            ]
        )
        for key in (
            "title",
            "category",
            "schema_version",
            "export_time",
            "element_count",
            "width",
            "height",
            "view_box",
            "text_count",
        ):
            value = item.get(key)
            if value not in (None, ""):
                lines.append(f"- {key}: {value}")
        if item.get("text"):
            lines.extend(["", "### Extracted text", ""])
            lines.extend(f"- {value}" for value in item["text"])
        lines.append("")
    if manifest["failures"]:
        lines.extend(["## Failures", ""])
        for failure in manifest["failures"]:
            lines.append(f"- {failure['name']}: {failure['error']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect ProcessOn POS/XMind/image/SVG/PDF exports read-only."
    )
    parser.add_argument("source", help="Export file or directory.")
    parser.add_argument(
        "--recursive", action="store_true", help="Recursively inspect a directory."
    )
    parser.add_argument(
        "--format", choices=("json", "markdown"), default="json", help="Output format."
    )
    parser.add_argument("--output", help="Write the report to this file.")
    parser.add_argument(
        "--text-limit",
        type=int,
        default=500,
        help="Maximum unique text items per structured export.",
    )
    args = parser.parse_args()

    if args.text_limit < 1:
        parser.error("--text-limit must be positive")

    source = Path(args.source).expanduser()
    try:
        files = collect_files(source, args.recursive)
    except FileNotFoundError:
        print("Source not found.", file=sys.stderr)
        return 2

    inspected: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for path in files:
        try:
            inspected.append(inspect_file(path, args.text_limit))
        except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            failures.append({"name": path.name, "error": f"{type(exc).__name__}: {exc}"})

    manifest: dict[str, Any] = {
        "source_type": "file" if source.is_file() else "directory",
        "file_count": len(inspected),
        "failure_count": len(failures),
        "files": inspected,
        "failures": failures,
    }
    output = (
        json.dumps(manifest, ensure_ascii=False, indent=2)
        if args.format == "json"
        else render_markdown(manifest)
    )

    if args.output:
        destination = Path(args.output).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
