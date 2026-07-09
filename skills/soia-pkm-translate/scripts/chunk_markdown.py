#!/usr/bin/env python3
"""Mechanical Markdown chunker for soia-pkm-translate.

Pure Python stdlib, no third-party dependency. This script only does the
mechanical work of splitting a Markdown document into translation-sized
chunks along heading and paragraph boundaries — it never translates
anything. Actual translation happens in the calling agent's context, using
the chunk list this script prints as `--json` output.

Usage:
    python3 chunk_markdown.py --file <path.md> [--json]
        [--threshold 4000] [--max-words 5000] [--output-dir <dir>]
    python3 chunk_markdown.py --selftest

Behavior:
    - If the document body (excluding YAML frontmatter) has fewer words
      than --threshold, chunking is not triggered: the whole body is
      returned as a single chunk.
    - Otherwise chunks are built by grouping blocks into heading-bounded
      sections, splitting any oversized section at paragraph/line
      boundaries, then packing blocks greedily up to --max-words per chunk.
    - Fenced code blocks are never split internally, regardless of size.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_THRESHOLD_WORDS = 4000
DEFAULT_MAX_WORDS = 5000

HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
FENCE_RE = re.compile(r"^(```+|~~~+)")
THEMATIC_BREAK_RE = re.compile(r"^\s*(?:-\s*){3,}$|^\s*(?:\*\s*){3,}$|^\s*(?:_\s*){3,}$")
CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+")
MD_STRIP_RE = re.compile(r"[#*`\[\]()>|_~-]")


@dataclass
class Block:
    kind: str  # heading | code | thematic_break | paragraph | section
    text: str
    words: int
    level: int = 0  # heading level; 0 for non-heading blocks


def count_words(text: str) -> int:
    """Word count: CJK characters counted individually, Latin/number tokens as words.

    Mirrors the convention used by comparable Markdown translation chunkers:
    CJK text has no whitespace word boundaries, so per-character counting
    approximates reading effort, while Latin text is counted per token.
    """
    cleaned = MD_STRIP_RE.sub(" ", text)
    cjk = CJK_RE.findall(cleaned)
    latin = LATIN_WORD_RE.findall(cleaned)
    return len(cjk) + len(latin)


def make_block(kind: str, lines: list[str], level: int = 0) -> Block:
    text = "\n".join(lines).strip("\n")
    return Block(kind=kind, text=text, words=count_words(text), level=level)


def extract_frontmatter(content: str) -> tuple[str, str]:
    """Split a leading YAML frontmatter block (--- ... ---) from the body."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return "", content
    for idx in range(1, len(lines)):
        if lines[idx].strip() in ("---", "..."):
            frontmatter = "\n".join(lines[: idx + 1])
            body = "\n".join(lines[idx + 1 :])
            return frontmatter, body.lstrip("\n")
    return "", content


def parse_blocks(body: str) -> list[Block]:
    """Split the document body into heading / code / thematic-break / paragraph blocks.

    Blank lines separate paragraph blocks. Fenced code blocks are captured
    whole (including any blank lines inside the fence) so code is never
    split mid-block.
    """
    lines = body.split("\n")
    blocks: list[Block] = []
    buffer: list[str] = []
    fence_marker: str | None = None

    def flush() -> None:
        nonlocal buffer
        if buffer and "".join(buffer).strip():
            blocks.append(make_block("paragraph", buffer))
        buffer = []

    index = 0
    while index < len(lines):
        line = lines[index]

        if fence_marker is not None:
            buffer.append(line)
            if line.strip().startswith(fence_marker):
                blocks.append(make_block("code", buffer))
                buffer = []
                fence_marker = None
            index += 1
            continue

        fence_match = FENCE_RE.match(line.strip())
        if fence_match:
            flush()
            fence_marker = fence_match.group(1)[:3]
            buffer = [line]
            index += 1
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush()
            blocks.append(make_block("heading", [line], level=len(heading_match.group(1))))
            index += 1
            continue

        if THEMATIC_BREAK_RE.match(line):
            flush()
            blocks.append(make_block("thematic_break", [line]))
            index += 1
            continue

        if not line.strip():
            flush()
            index += 1
            continue

        buffer.append(line)
        index += 1

    if fence_marker is not None and buffer:
        # Unterminated fence in the source: keep it as a block rather than
        # silently dropping content.
        blocks.append(make_block("code", buffer))
    else:
        flush()

    return blocks


def group_sections(blocks: list[Block]) -> list[list[Block]]:
    """Group blocks into sections, each starting at a heading (any level)."""
    sections: list[list[Block]] = []
    current: list[Block] = []
    for block in blocks:
        if block.kind == "heading" and current:
            sections.append(current)
            current = [block]
            continue
        current.append(block)
    if current:
        sections.append(current)
    return sections


def split_oversized_block(block: Block, max_words: int) -> list[Block]:
    """Split a single block that exceeds max_words, falling back to line splitting.

    Headings, thematic breaks, and code blocks are never split.
    """
    if block.words <= max_words or block.kind in ("heading", "thematic_break", "code"):
        return [block]

    lines = block.text.split("\n")
    if len(lines) <= 1:
        return [block]

    pieces: list[Block] = []
    buffer: list[str] = []
    buffer_words = 0
    for line in lines:
        line_words = count_words(line)
        if buffer and buffer_words + line_words > max_words:
            pieces.append(make_block(block.kind, buffer))
            buffer = [line]
            buffer_words = line_words
            continue
        buffer.append(line)
        buffer_words += line_words

    if buffer:
        pieces.append(make_block(block.kind, buffer))
    return pieces


def normalize_blocks(blocks: list[Block], max_words: int) -> list[Block]:
    """Merge small sections into single blocks; split oversized sections at boundaries."""
    normalized: list[Block] = []
    for section in group_sections(blocks):
        section_words = sum(b.words for b in section)
        if section_words <= max_words:
            merged_text = "\n\n".join(b.text for b in section)
            normalized.append(make_block("section", merged_text.split("\n")))
            continue
        for block in section:
            normalized.extend(split_oversized_block(block, max_words))
    return normalized


def build_chunks(blocks: list[Block], max_words: int) -> list[list[Block]]:
    """Greedily pack normalized blocks into chunks capped at max_words each."""
    normalized = normalize_blocks(blocks, max_words)
    chunks: list[list[Block]] = []
    current: list[Block] = []
    current_words = 0

    for block in normalized:
        if current and current_words + block.words > max_words:
            chunks.append(current)
            current = [block]
            current_words = block.words
            continue
        current.append(block)
        current_words += block.words

    if current:
        chunks.append(current)
    return chunks


def first_heading_text(chunk_blocks: list[Block]) -> str:
    for block in chunk_blocks:
        for line in block.text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
    return ""


def chunk_markdown_text(raw: str, threshold: int, max_words: int) -> dict:
    """Chunk raw Markdown text (frontmatter + body) and return a manifest dict."""
    frontmatter, body = extract_frontmatter(raw)
    blocks = parse_blocks(body)
    total_words = sum(b.words for b in blocks)
    triggered = total_words >= threshold

    if not triggered:
        chunk_groups = [blocks] if blocks else [[]]
    else:
        chunk_groups = build_chunks(blocks, max_words)
        if not chunk_groups:
            chunk_groups = [[]]

    chunks = []
    for position, chunk_blocks in enumerate(chunk_groups, start=1):
        text = "\n\n".join(b.text for b in chunk_blocks)
        chunks.append(
            {
                "index": position,
                "words": count_words(text),
                "heading": first_heading_text(chunk_blocks),
                "text": text,
            }
        )

    return {
        "total_words": total_words,
        "threshold": threshold,
        "max_words": max_words,
        "triggered": triggered,
        "has_frontmatter": bool(frontmatter),
        "frontmatter": frontmatter,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def chunk_markdown_file(path: Path, threshold: int, max_words: int) -> dict:
    raw = path.read_text(encoding="utf-8")
    result = chunk_markdown_text(raw, threshold, max_words)
    result["source"] = str(path)
    return result


def write_chunk_files(result: dict, output_dir: Path) -> Path:
    """Write frontmatter.md (if any) and chunk-NN.md files under output_dir/chunks/."""
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    if result.get("has_frontmatter"):
        (chunks_dir / "frontmatter.md").write_text(result["frontmatter"] + "\n", encoding="utf-8")

    for chunk in result["chunks"]:
        name = f"chunk-{chunk['index']:02d}.md"
        (chunks_dir / name).write_text(chunk["text"] + "\n", encoding="utf-8")

    return chunks_dir


def manifest_without_text(result: dict) -> dict:
    """Return a copy of the manifest without the full chunk text (for --json summaries)."""
    manifest = dict(result)
    manifest["frontmatter"] = bool(result.get("frontmatter"))
    manifest["chunks"] = [
        {"index": c["index"], "words": c["words"], "heading": c["heading"]}
        for c in result["chunks"]
    ]
    return manifest


def run_selftest() -> int:
    """Self-contained checks using built-in sample documents. No file I/O required."""
    checks: list[tuple[str, bool, str]] = []

    # Sample 1: short document, multiple headings, well under threshold.
    short_doc = (
        "---\n"
        "title: sample\n"
        "---\n"
        "# Intro\n\n"
        "This is a short paragraph.\n\n"
        "## Details\n\n"
        "Another short paragraph with a few more words in it.\n"
    )
    short_result = chunk_markdown_text(short_doc, threshold=DEFAULT_THRESHOLD_WORDS, max_words=DEFAULT_MAX_WORDS)
    checks.append(
        (
            "short document under threshold returns exactly one chunk",
            short_result["chunk_count"] == 1 and not short_result["triggered"],
            f"chunk_count={short_result['chunk_count']} triggered={short_result['triggered']}",
        )
    )
    checks.append(
        (
            "frontmatter is detected and excluded from body word count",
            short_result["has_frontmatter"] and short_result["total_words"] < 50,
            f"has_frontmatter={short_result['has_frontmatter']} total_words={short_result['total_words']}",
        )
    )

    # Sample 2: long document, engineered to exceed the threshold with
    # precisely countable filler words, split across many sections.
    def make_section(heading: str, word_count: int) -> str:
        filler = " ".join(["word"] * word_count)
        return f"## {heading}\n\n{filler}\n"

    long_doc = "# Long Sample\n\n" + "\n".join(
        make_section(f"Section {i}", 900) for i in range(1, 8)
    )  # ~6300 words body, above the 4000-word threshold
    long_result = chunk_markdown_text(long_doc, threshold=DEFAULT_THRESHOLD_WORDS, max_words=DEFAULT_MAX_WORDS)
    over_cap = [c for c in long_result["chunks"] if c["words"] > DEFAULT_MAX_WORDS]
    checks.append(
        (
            "long document above threshold triggers multi-chunk splitting",
            long_result["triggered"] and long_result["chunk_count"] > 1,
            f"chunk_count={long_result['chunk_count']} triggered={long_result['triggered']}",
        )
    )
    checks.append(
        (
            "every chunk stays within max_words cap",
            len(over_cap) == 0,
            f"over_cap_chunks={len(over_cap)}",
        )
    )
    reconstructed_words = sum(c["words"] for c in long_result["chunks"])
    checks.append(
        (
            "chunk word counts roughly reconstruct total body word count",
            abs(reconstructed_words - long_result["total_words"]) <= long_result["chunk_count"],
            f"reconstructed={reconstructed_words} total={long_result['total_words']}",
        )
    )

    # Sample 3: a single oversized fenced code block must never be split,
    # even though it exceeds max_words on its own.
    huge_code_body = "```text\n" + "\n".join(f"line {i} of code" for i in range(1, 2000)) + "\n```\n"
    code_doc = "# Code Sample\n\n" + huge_code_body
    code_result = chunk_markdown_text(code_doc, threshold=DEFAULT_THRESHOLD_WORDS, max_words=DEFAULT_MAX_WORDS)
    code_chunk_texts = [c["text"] for c in code_result["chunks"]]
    fence_intact = any(text.count("```") >= 2 for text in code_chunk_texts) or any(
        "```text" in text and text.strip().endswith("```") for text in code_chunk_texts
    )
    checks.append(
        (
            "oversized fenced code block is kept intact, never split",
            fence_intact,
            f"chunk_count={code_result['chunk_count']}",
        )
    )

    # Sample 4: round-trip through a real temp file to exercise --file path.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "sample.md"
        tmp_path.write_text(long_doc, encoding="utf-8")
        file_result = chunk_markdown_file(tmp_path, threshold=DEFAULT_THRESHOLD_WORDS, max_words=DEFAULT_MAX_WORDS)
        checks.append(
            (
                "chunk_markdown_file reads from disk and matches in-memory result",
                file_result["chunk_count"] == long_result["chunk_count"],
                f"file_chunks={file_result['chunk_count']} text_chunks={long_result['chunk_count']}",
            )
        )

    print("=== chunk_markdown.py selftest ===")
    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"[{status}] {name} ({detail})")

    print(f"{sum(1 for _, p, _ in checks if p)}/{len(checks)} selftest checks passed.")
    return 0 if all_passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", help="Path to the Markdown file to chunk.")
    parser.add_argument("--json", action="store_true", help="Print the chunk manifest as JSON.")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD_WORDS, help="Word count that triggers chunking.")
    parser.add_argument("--max-words", type=int, default=DEFAULT_MAX_WORDS, help="Max words per chunk.")
    parser.add_argument("--output-dir", help="If set, write chunk-NN.md files (and frontmatter.md) under <output-dir>/chunks/.")
    parser.add_argument("--selftest", action="store_true", help="Run built-in self-checks and exit.")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.file:
        parser.error("--file is required unless --selftest is used")

    path = Path(args.file).expanduser()
    if not path.is_file():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 1

    result = chunk_markdown_file(path, threshold=args.threshold, max_words=args.max_words)

    if args.output_dir:
        chunks_dir = write_chunk_files(result, Path(args.output_dir).expanduser())
        result["chunks_dir"] = str(chunks_dir)

    if args.json:
        print(json.dumps(manifest_without_text(result), ensure_ascii=False, indent=2))
    else:
        print(f"Source: {result['source']}")
        print(f"Total words: {result['total_words']} (threshold={result['threshold']}, max_words={result['max_words']})")
        print(f"Chunking triggered: {result['triggered']}")
        print(f"Chunk count: {result['chunk_count']}")
        for chunk in result["chunks"]:
            heading = chunk["heading"] or "(no heading)"
            print(f"  chunk {chunk['index']:02d}: {chunk['words']} words — {heading}")
        if "chunks_dir" in result:
            print(f"Chunk files written to: {result['chunks_dir']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
