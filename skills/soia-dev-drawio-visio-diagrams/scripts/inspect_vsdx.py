#!/usr/bin/env python3
"""Safely inspect a VSDX package without modifying or extracting it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET


VISIO_NS = "http://schemas.microsoft.com/office/visio/2012/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MAX_ENTRIES = 10_000
MAX_TOTAL_UNCOMPRESSED = 100 * 1024 * 1024
MAX_XML_BYTES = 20 * 1024 * 1024


class InspectionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def safe_member_name(name: str) -> bool:
    member = PurePosixPath(name)
    return not member.is_absolute() and ".." not in member.parts and "\\" not in name


def read_xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise InspectionError(f"missing required VSDX part: {name}") from exc
    if info.file_size > MAX_XML_BYTES:
        raise InspectionError(f"XML part exceeds {MAX_XML_BYTES} bytes: {name}")
    try:
        return ET.fromstring(archive.read(name))
    except ET.ParseError as exc:
        raise InspectionError(f"invalid XML in {name}: {exc}") from exc


def inspect_vsdx(path: Path, max_texts: int = 500) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise InspectionError(f"file not found: {path}")
    if path.suffix.lower() != ".vsdx":
        raise InspectionError("expected a .vsdx file")
    if not zipfile.is_zipfile(path):
        raise InspectionError("VSDX is not a valid ZIP/OOXML package")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise InspectionError(f"package has too many entries: {len(infos)}")
        unsafe = [info.filename for info in infos if not safe_member_name(info.filename)]
        if unsafe:
            raise InspectionError(f"unsafe ZIP member path: {unsafe[0]}")
        total_uncompressed = sum(info.file_size for info in infos)
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
            raise InspectionError(
                f"package expands to {total_uncompressed} bytes; limit is {MAX_TOTAL_UNCOMPRESSED}"
            )
        names = {info.filename for info in infos}
        for required in ("[Content_Types].xml", "visio/document.xml", "visio/pages/pages.xml"):
            if required not in names:
                raise InspectionError(f"missing required VSDX part: {required}")

        pages_root = read_xml(archive, "visio/pages/pages.xml")
        rels_root = read_xml(archive, "visio/pages/_rels/pages.xml.rels")
        rel_targets = {
            rel.attrib.get("Id", ""): rel.attrib.get("Target", "")
            for rel in rels_root.findall(f"{{{REL_NS}}}Relationship")
        }

        pages: list[dict[str, Any]] = []
        all_texts: list[str] = []
        total_shapes = 0
        total_connect_records = 0
        for page in pages_root.findall(f"{{{VISIO_NS}}}Page"):
            relation = page.find(f"{{{VISIO_NS}}}Rel")
            rel_id = relation.attrib.get(f"{{{DOC_REL_NS}}}id", "") if relation is not None else ""
            target = rel_targets.get(rel_id, "")
            if not target:
                raise InspectionError(f"page relationship is missing for {page.attrib.get('Name', rel_id)}")
            page_part = str(PurePosixPath("visio/pages") / target)
            if not safe_member_name(page_part):
                raise InspectionError(f"unsafe page target: {target}")
            page_root = read_xml(archive, page_part)
            shapes = page_root.findall(f".//{{{VISIO_NS}}}Shape")
            connect_records = page_root.findall(f".//{{{VISIO_NS}}}Connect")
            connector_ids = {
                item.attrib.get("FromSheet", "") for item in connect_records if item.attrib.get("FromSheet")
            }
            texts: list[str] = []
            shape_summaries: list[dict[str, str]] = []
            for shape in shapes:
                text_node = shape.find(f"{{{VISIO_NS}}}Text")
                text = clean_text("".join(text_node.itertext())) if text_node is not None else ""
                if text:
                    texts.append(text)
                    if len(all_texts) < max_texts:
                        all_texts.append(text)
                shape_summaries.append(
                    {
                        "id": shape.attrib.get("ID", ""),
                        "name": shape.attrib.get("Name", shape.attrib.get("NameU", "")),
                        "type": shape.attrib.get("Type", ""),
                        "text": text,
                    }
                )
            total_shapes += len(shapes)
            total_connect_records += len(connect_records)
            pages.append(
                {
                    "id": page.attrib.get("ID", ""),
                    "name": page.attrib.get("Name", page.attrib.get("NameU", "")),
                    "part": page_part,
                    "shape_count": len(shapes),
                    "connector_shape_count": len(connector_ids),
                    "connect_record_count": len(connect_records),
                    "text_count": len(texts),
                    "texts": texts[:max_texts],
                    "shapes": shape_summaries[:max_texts],
                }
            )

        media = sorted(
            name
            for name in names
            if name.startswith("visio/media/") or name.startswith("docProps/thumbnail")
        )
        return {
            "path": str(path),
            "format": "vsdx",
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "package_entries": len(infos),
            "uncompressed_size": total_uncompressed,
            "page_count": len(pages),
            "shape_count": total_shapes,
            "connect_record_count": total_connect_records,
            "media_count": len(media),
            "media": media,
            "texts": all_texts,
            "texts_truncated": sum(page["text_count"] for page in pages) > len(all_texts),
            "pages": pages,
        }


def to_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# VSDX 盘点：{Path(result['path']).name}",
        "",
        f"- SHA-256：`{result['sha256']}`",
        f"- 文件大小：{result['size']} bytes",
        f"- 页面：{result['page_count']}",
        f"- 形状：{result['shape_count']}",
        f"- 连接记录：{result['connect_record_count']}",
        f"- 媒体：{result['media_count']}",
        "",
    ]
    for page in result["pages"]:
        lines.extend(
            [
                f"## {page['name'] or '(未命名页面)'}",
                "",
                f"- 形状：{page['shape_count']}；连接形状：{page['connector_shape_count']}；连接记录：{page['connect_record_count']}",
                "- 文字：",
            ]
        )
        if page["texts"]:
            lines.extend(f"  - {text}" for text in page["texts"])
        else:
            lines.append("  - （未提取到非空文字）")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--max-texts", type=int, default=500)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = inspect_vsdx(args.input, max_texts=max(1, args.max_texts))
    except (InspectionError, OSError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "markdown":
        print(to_markdown(result), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
