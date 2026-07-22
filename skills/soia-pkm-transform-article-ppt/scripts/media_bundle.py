#!/usr/bin/env python3
"""Plan and validate an article-to-PPT media bundle using only stdlib."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


PROVIDERS = {"auto", "local_editable", "notebooklm", "hybrid", "open_design"}
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
# The user-path patterns are written with [/] and [\\] character classes on
# purpose: regex semantics are identical, but the source line must not contain
# a literal `/Users/` or the repo audit's hardcoded-absolute-path check
# (scripts/audit_skills.py ABSOLUTE_PATH_RE) flags this detection pattern
# itself as a violation. Do not "simplify" back to plain slashes.
BANNED_TEXT = re.compile(
    r"(?:\b(?:notebook|source|artifact)_id\b|download_path|\[[A-Z0-9_]*PLACEHOLDER[A-Z0-9_]*\]|"
    r"[A-Z0-9_]+_PLACEHOLDER|[/]Users[/][^/\s]+[/]|[A-Za-z]:[\\]Users[\\])",
    re.IGNORECASE,
)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip().strip('"\'')
        fields[match.group(1)] = value
    return fields, text[end + 5 :]


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = re.sub(r"\s+", " ", value).strip(" ：:。.-")
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def extract_source(article: Path) -> dict[str, Any]:
    raw = read_text(article)
    frontmatter, body = parse_frontmatter(raw)
    headings = unique(
        [match.group(2) for match in re.finditer(r"^(#{1,4})\s+(.+?)\s*$", body, re.MULTILINE)]
    )
    title_match = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    title = frontmatter.get("title") or (title_match.group(1).strip() if title_match else article.stem)

    concepts: list[str] = []
    patterns = [
        r"\*\*\s*\d+[\.、]\s*([^*（(\n]{1,80})(?:[（(][^）)\n]+[）)])?\s*\*\*",
        r"^\s*[-*+]\s+\*\*([^*\n]{2,80})\*\*",
    ]
    for pattern in patterns:
        concepts.extend(match.group(1) for match in re.finditer(pattern, body, re.MULTILINE))
    concepts = unique(concepts)

    return {
        "path": str(article.resolve()),
        "title": title,
        "author": frontmatter.get("author", ""),
        "url": frontmatter.get("url", ""),
        "published_at": frontmatter.get("published_at", ""),
        "sections": headings[:40],
        "concepts": concepts[:200],
    }


def infer_slide_count(source: dict[str, Any]) -> int:
    concept_count = len(source["concepts"])
    section_count = len(source["sections"])
    if concept_count >= 12 or section_count >= 8:
        return 18
    if concept_count >= 6 or section_count >= 5:
        return 14
    return 10


def expected_entry(path: str, required: bool, **extra: Any) -> dict[str, Any]:
    return {"path": path, "required": required, **extra}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    article = Path(args.article).expanduser().resolve()
    if not article.is_file():
        raise FileNotFoundError(f"Article does not exist: {article}")
    if args.provider not in PROVIDERS:
        raise ValueError(f"Unsupported provider: {args.provider}")

    source = extract_source(article)
    slide_count = infer_slide_count(source) if args.slide_count == "auto" else int(args.slide_count)
    if slide_count < 1:
        raise ValueError("slide_count must be positive")
    if args.image_count < 0:
        raise ValueError("image_count cannot be negative")

    provider = "local_editable" if args.provider == "auto" else args.provider
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = article.stem
    local_required = provider in {"local_editable", "hybrid", "open_design"}
    notebook_required = provider in {"notebooklm", "hybrid"}

    prompt_entries = []
    if local_required:
        prompt_entries.append(expected_entry("prompts/ppt-local.txt", True, role="editable_pptx"))
    if notebook_required:
        prompt_entries.append(expected_entry("prompts/ppt-notebooklm.txt", True, role="notebooklm_pptx"))
    for index in range(1, args.image_count + 1):
        prompt_entries.append(expected_entry(f"prompts/image-{index:02d}.txt", True, role="visual_asset"))
    if args.infographic:
        prompt_entries.append(expected_entry("prompts/infographic.txt", True, role="infographic"))

    expected = {
        "editable_pptx": expected_entry(
            f"{stem}-editable.pptx",
            local_required,
            min_slides=max(1, slide_count - 2),
            editable_required=True,
            preview_dir="previews/editable",
        ),
        "notebooklm_pptx": expected_entry(
            f"{stem}-notebooklm.pptx",
            notebook_required,
            min_slides=max(1, slide_count - 4),
            editable_required=False,
            preview_dir="previews/notebooklm",
        ),
        "infographic": expected_entry(
            f"{stem}-infographic.png",
            bool(args.infographic),
            min_width=800,
            min_height=800,
        ),
        "visual_assets": {
            "directory": "assets/imagegen",
            "required": args.image_count > 0,
            "minimum_count": args.image_count,
            "min_width": 768,
            "min_height": 512,
        },
        "prompts": prompt_entries,
    }

    return {
        "schema_version": 1,
        "planned_at": now_iso(),
        "source": source,
        "request": {
            "provider": provider,
            "audience": args.audience,
            "style": args.style,
            "slide_count": slide_count,
            "image_count": args.image_count,
            "infographic": bool(args.infographic),
            "main_verdict": args.main_verdict,
        },
        "expected": expected,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def natural_slide_key(name: str) -> tuple[int, str]:
    match = re.search(r"slide(\d+)\.xml$", name)
    return (int(match.group(1)) if match else 10**9, name)


def inspect_pptx(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "valid_ooxml": False,
        "slides": 0,
        "text_slides": 0,
        "image_only_slides": 0,
        "editable_ratio": 0.0,
        "banned_text_matches": [],
    }
    if not path.is_file() or not zipfile.is_zipfile(path):
        return result

    with zipfile.ZipFile(path) as archive:
        names = sorted(
            [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)],
            key=natural_slide_key,
        )
        result["slides"] = len(names)
        text_slides = 0
        image_only = 0
        matches: set[str] = set()
        for name in names:
            root = ET.fromstring(archive.read(name))
            texts = [(node.text or "") for node in root.findall(".//a:t", NS)]
            pictures = root.findall(".//p:pic", NS)
            shapes = root.findall(".//p:sp", NS)
            joined = " ".join(texts)
            if joined.strip():
                text_slides += 1
            if pictures and not joined.strip() and not shapes:
                image_only += 1
            matches.update(match.group(0) for match in BANNED_TEXT.finditer(joined))

        result.update(
            {
                "valid_ooxml": len(names) > 0,
                "text_slides": text_slides,
                "image_only_slides": image_only,
                "editable_ratio": round(text_slides / len(names), 3) if names else 0.0,
                "banned_text_matches": sorted(matches),
            }
        )
    return result


def png_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def resolve(out_dir: Path, entry: dict[str, Any]) -> Path:
    return out_dir / entry["path"]


def add_problem(bucket: list[dict[str, str]], code: str, message: str) -> None:
    bucket.append({"code": code, "message": message})


def validate_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = json.loads(read_text(manifest_path))
    out_dir = manifest_path.parent
    expected = manifest["expected"]
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    artifacts: dict[str, Any] = {}

    for key in ("editable_pptx", "notebooklm_pptx"):
        entry = expected[key]
        path = resolve(out_dir, entry)
        if not path.exists():
            if entry["required"]:
                add_problem(errors, f"missing_{key}", f"Missing required file: {path}")
            continue

        inspection = inspect_pptx(path)
        artifacts[key] = inspection
        if not inspection["valid_ooxml"]:
            add_problem(errors, f"invalid_{key}", f"Not a valid PPTX OOXML file: {path}")
            continue
        if inspection["slides"] < entry["min_slides"]:
            add_problem(
                errors,
                f"short_{key}",
                f"{path.name} has {inspection['slides']} slides; expected at least {entry['min_slides']}",
            )
        if inspection["banned_text_matches"]:
            add_problem(
                errors,
                f"runtime_metadata_{key}",
                f"{path.name} contains forbidden runtime metadata/placeholders: {inspection['banned_text_matches']}",
            )
        if entry.get("editable_required") and inspection["editable_ratio"] < 0.6:
            add_problem(
                errors,
                "editable_deck_is_flattened",
                f"{path.name} editable text ratio is {inspection['editable_ratio']:.0%}; expected at least 60%",
            )
        if key == "notebooklm_pptx" and inspection["editable_ratio"] < 0.2:
            add_problem(
                warnings,
                "notebooklm_deck_is_flattened",
                f"{path.name} appears image-only; report it as flattened/non-editable",
            )

        preview_dir = out_dir / entry["preview_dir"]
        previews = sorted(preview_dir.glob("slide-*.png")) if preview_dir.is_dir() else []
        artifacts[f"{key}_previews"] = len(previews)
        if len(previews) != inspection["slides"]:
            add_problem(
                errors,
                f"preview_count_{key}",
                f"{path.name} has {inspection['slides']} slides but {len(previews)} rendered previews",
            )

    infographic = expected["infographic"]
    infographic_path = resolve(out_dir, infographic)
    if infographic["required"] or infographic_path.exists():
        dims = png_dimensions(infographic_path)
        artifacts["infographic"] = {"path": str(infographic_path), "dimensions": dims}
        if dims is None:
            add_problem(errors, "invalid_infographic", f"Missing or invalid PNG: {infographic_path}")
        elif dims[0] < infographic["min_width"] or dims[1] < infographic["min_height"]:
            add_problem(errors, "small_infographic", f"Infographic is too small: {dims[0]}x{dims[1]}")

    assets = expected["visual_assets"]
    asset_dir = out_dir / assets["directory"]
    asset_paths = sorted(asset_dir.glob("*.png")) if asset_dir.is_dir() else []
    artifacts["visual_assets"] = []
    if assets["required"] and len(asset_paths) < assets["minimum_count"]:
        add_problem(
            errors,
            "missing_visual_assets",
            f"Expected at least {assets['minimum_count']} PNG assets in {asset_dir}; found {len(asset_paths)}",
        )
    for path in asset_paths:
        dims = png_dimensions(path)
        artifacts["visual_assets"].append({"path": str(path), "dimensions": dims})
        if dims is None:
            add_problem(errors, "invalid_visual_asset", f"Invalid PNG: {path}")
        elif dims[0] < assets["min_width"] or dims[1] < assets["min_height"]:
            add_problem(warnings, "small_visual_asset", f"Visual asset is small: {path.name} {dims[0]}x{dims[1]}")

    for entry in expected["prompts"]:
        path = resolve(out_dir, entry)
        if entry["required"] and (not path.is_file() or not read_text(path).strip()):
            add_problem(errors, "missing_prompt", f"Missing or empty prompt: {path}")

    if args.strict and not args.visual_reviewed:
        add_problem(errors, "visual_review_pending", "Strict validation requires --visual-reviewed")
    elif not args.visual_reviewed:
        add_problem(warnings, "visual_review_pending", "Manual slide/image review is still required")
    if args.strict and not args.source_facts_reviewed:
        add_problem(errors, "source_facts_review_pending", "Strict validation requires --source-facts-reviewed")
    elif not args.source_facts_reviewed:
        add_problem(warnings, "source_facts_review_pending", "Source author/time/claims review is still required")

    report = {
        "schema_version": 1,
        "validated_at": now_iso(),
        "manifest": str(manifest_path),
        "status": "failed" if errors else "passed",
        "artifacts": artifacts,
        "errors": errors,
        "warnings": warnings,
        "manual_gates": {
            "visual_reviewed": bool(args.visual_reviewed),
            "source_facts_reviewed": bool(args.source_facts_reviewed),
        },
    }
    write_json(out_dir / "media-validation.json", report)
    return report, 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Create media-manifest.json from a Markdown source")
    plan.add_argument("--article", required=True)
    plan.add_argument("--out-dir", required=True)
    plan.add_argument("--provider", choices=sorted(PROVIDERS), default="auto")
    plan.add_argument("--audience", default="auto")
    plan.add_argument("--style", default="auto")
    plan.add_argument("--slide-count", default="auto")
    plan.add_argument("--image-count", type=int, default=3)
    plan.add_argument("--infographic", action="store_true")
    plan.add_argument("--main-verdict", default="")
    plan.add_argument("--json", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate files declared by media-manifest.json")
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--visual-reviewed", action="store_true")
    validate.add_argument("--source-facts-reviewed", action="store_true")
    validate.add_argument("--strict", action="store_true")
    validate.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "plan":
            manifest = build_manifest(args)
            output = Path(args.out_dir).expanduser().resolve() / "media-manifest.json"
            write_json(output, manifest)
            result = {"status": "planned", "manifest": str(output), "payload": manifest}
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else str(output))
            return 0

        report, exit_code = validate_manifest(args)
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report["status"])
        return exit_code
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ET.ParseError, zipfile.BadZipFile) as exc:
        payload = {"status": "error", "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
