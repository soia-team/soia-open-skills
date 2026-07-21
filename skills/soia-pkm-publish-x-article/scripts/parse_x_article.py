#!/usr/bin/env python3
"""Parse a Markdown article into X Articles publishing data.

Adapted from wshuyi/x-article-publisher-skill (MIT License, Copyright (c) 2024
wshuyi) — see repository THIRD_PARTY_NOTICES.md. Changes in this adaptation:
frontmatter title extraction, no implicit image auto-search outside the vault
(explicit --search-dir instead), stdlib only.

Extracts:
- title: frontmatter `title:` > first H1 > first H2 > first non-empty line
- cover_image: the first image, if the article starts with one
- content_images: remaining images with block_index for reverse-order insertion
- dividers: `---` positions (X ignores <hr>; insert via editor menu)
- html: rich-text HTML for clipboard paste (images/dividers stripped)

Usage:
    python3 parse_x_article.py <markdown_file>                 # JSON to stdout
    python3 parse_x_article.py <markdown_file> --html-only     # HTML to stdout
    python3 parse_x_article.py <markdown_file> --search-dir DIR  # extra image lookup dir

block_index is 0-based: the element should be inserted AFTER the block at that
index of the pasted body. after_text keeps the previous block's tail (<=80
chars) for human verification in the editor.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path


def find_image_file(resolved_path: str, filename: str, search_dirs: list[Path]) -> tuple[str, bool]:
    """Return (usable_path, exists), trying explicit search dirs when missing."""
    if os.path.isfile(resolved_path):
        return resolved_path, True
    for search_dir in search_dirs:
        candidate = search_dir / filename
        if candidate.is_file():
            print(
                f"[parse_x_article] image not at '{resolved_path}', using '{candidate}'",
                file=sys.stderr,
            )
            return str(candidate), True
    print(f"[parse_x_article] WARNING: image not found: '{resolved_path}'", file=sys.stderr)
    return resolved_path, False


def split_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Split YAML frontmatter; return ({key: scalar}, body). Non-scalar values ignored."""
    meta: dict[str, str] = {}
    if not content.startswith("---"):
        return meta, content
    end = content.find("\n---", 3)
    if end == -1:
        return meta, content
    for line in content[3:end].splitlines():
        if ":" not in line or line.startswith((" ", "\t", "-")):
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip("'\"")
        if value:
            meta[key.strip()] = value
    return meta, content[end + 4 :].lstrip("\n")


def split_into_blocks(markdown: str) -> list[str]:
    """Split markdown into logical blocks; code fences stay one block."""
    blocks: list[str] = []
    current: list[str] = []
    in_code = False
    code_lines: list[str] = []

    for line in markdown.split("\n"):
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                in_code = False
                if code_lines:
                    blocks.append("___CODE___" + "\n".join(code_lines) + "___END___")
                code_lines = []
            else:
                if current:
                    blocks.append("\n".join(current))
                    current = []
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            if current:
                blocks.append("\n".join(current))
                current = []
            continue

        if re.match(r"^---+$", stripped):
            if current:
                blocks.append("\n".join(current))
                current = []
            blocks.append("___DIVIDER___")
            continue

        if stripped.startswith(("#", ">")):
            if current:
                blocks.append("\n".join(current))
                current = []
            blocks.append(stripped)
            continue

        if re.match(r"^!\[.*\]\(.*\)$", stripped):
            if current:
                blocks.append("\n".join(current))
                current = []
            blocks.append(stripped)
            continue

        current.append(line)

    if current:
        blocks.append("\n".join(current))
    if code_lines:
        blocks.append("___CODE___" + "\n".join(code_lines) + "___END___")
    return blocks


def _tail_text(clean_blocks: list[str]) -> str:
    """Last visible line of the previous block, cleaned to match editor text."""
    if not clean_blocks:
        return ""
    prev = clean_blocks[-1].strip()
    prev = re.sub(r"___CODE___|___END___", "", prev)
    lines = [l for l in prev.split("\n") if l.strip()]
    if not lines:
        return ""
    text = lines[-1]
    # Strip markdown markers so the text is searchable in the rendered editor.
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"^[#>\-\d.\s]+", "", text)
    return text[:80]


def extract_images_and_dividers(
    markdown: str, base_path: Path, search_dirs: list[Path]
) -> tuple[list[dict], list[dict], str, int]:
    blocks = split_into_blocks(markdown)
    images: list[dict] = []
    dividers: list[dict] = []
    clean_blocks: list[str] = []
    img_re = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")

    for block in blocks:
        stripped = block.strip()

        if stripped == "___DIVIDER___":
            dividers.append({"block_index": len(clean_blocks), "after_text": _tail_text(clean_blocks)})
            continue

        match = img_re.match(stripped)
        if match:
            raw_path = urllib.parse.unquote(match.group(2).split(" ")[0])
            resolved = raw_path if os.path.isabs(raw_path) else str(base_path / raw_path)
            path, exists = find_image_file(resolved, os.path.basename(raw_path), search_dirs)
            images.append(
                {
                    "path": path,
                    "original_path": resolved,
                    "exists": exists,
                    "alt": match.group(1),
                    "block_index": len(clean_blocks),
                    "after_text": _tail_text(clean_blocks),
                }
            )
            continue

        clean_blocks.append(block)

    return images, dividers, "\n\n".join(clean_blocks), len(clean_blocks)


def extract_title(meta: dict[str, str], markdown: str) -> tuple[str, str]:
    """Title precedence: frontmatter title > H1 (removed from body) > H2 > first line."""
    if meta.get("title"):
        # An H1 identical to the frontmatter title would duplicate; drop it.
        # Skip leading image lines (cover) — the H1 may sit right after them.
        lines = markdown.strip().split("\n")
        for idx, line in enumerate(lines):
            s = line.strip()
            if not s or s.startswith("!["):
                continue
            if s.startswith("# ") and s[2:].strip() == meta["title"]:
                lines.pop(idx)
                markdown = "\n".join(lines)
            break
        return meta["title"], markdown

    lines = markdown.strip().split("\n")
    for idx, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if s.startswith("# "):
            lines.pop(idx)
            return s[2:].strip(), "\n".join(lines)
        if s.startswith("## "):
            return s[3:].strip(), markdown
        if not s.startswith("!["):
            return s[:100], markdown
    return "Untitled", markdown


def markdown_to_html(markdown: str) -> str:
    """Markdown → HTML limited to what the X Articles editor accepts on paste."""
    html = markdown

    def code_to_blockquote(match: re.Match) -> str:
        lines = match.group(1).strip().split("\n")
        return "<blockquote>" + "<br>".join(l for l in lines if l.strip()) + "</blockquote>"

    html = re.sub(r"___CODE___(.*?)___END___", code_to_blockquote, html, flags=re.DOTALL)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", html)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)
    html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)
    html = re.sub(r"^\d+\. (.+)$", r"<oli>\1</oli>", html, flags=re.MULTILINE)
    html = re.sub(r"^[-*] (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"((?:<li>.*?</li>\n?)+)", r"<ul>\1</ul>", html)
    html = re.sub(r"((?:<oli>.*?</oli>\n?)+)", lambda m: "<ol>" + m.group(1).replace("oli>", "li>") + "</ol>", html)

    parts: list[str] = []
    for part in html.split("\n\n"):
        part = part.strip()
        if not part:
            continue
        if part.startswith(("<h2>", "<h3>", "<blockquote>", "<ul>", "<ol>")):
            parts.append(part)
        else:
            parts.append("<p>" + part.replace("\n", "<br>") + "</p>")
    return "".join(parts)


def parse_article(filepath: str, search_dirs: list[Path]) -> dict:
    path = Path(filepath).resolve()
    content = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(content)
    title, body = extract_title(meta, body)
    images, dividers, clean_md, total_blocks = extract_images_and_dividers(body, path.parent, search_dirs)

    # The cover slot is only taken by an image that opens the article
    # (block_index 0). An article whose first image appears mid-body has no
    # cover candidate — the caller must ask the user before continuing.
    cover = images[0] if images and images[0]["block_index"] == 0 else None
    content_images = images[1:] if cover else images

    missing = [img for img in images if not img["exists"]]
    return {
        "title": title,
        "cover_image": cover["path"] if cover else None,
        "cover_exists": cover["exists"] if cover else False,
        "content_images": content_images,
        "dividers": dividers,
        "html": markdown_to_html(clean_md),
        "total_blocks": total_blocks,
        "source_file": str(path.absolute()),
        "missing_images": len(missing),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Markdown for X Articles draft upload")
    parser.add_argument("file", help="Markdown file")
    parser.add_argument("--html-only", action="store_true", help="print body HTML only")
    parser.add_argument(
        "--search-dir",
        action="append",
        default=[],
        help="extra directory to look for images referenced with broken paths (repeatable)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 1

    result = parse_article(args.file, [Path(d).expanduser() for d in args.search_dir])
    if args.html_only:
        print(result["html"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
