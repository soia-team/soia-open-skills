#!/usr/bin/env python3
"""Validate transform artifacts against source coverage and media-specific gates."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from pptx import Presentation
except Exception as exc:  # pragma: no cover - surfaced in validation output
    Presentation = None
    PPTX_IMPORT_ERROR = exc
else:
    PPTX_IMPORT_ERROR = None

try:
    from article_packet import Article, Concept, matched_terms, parse_article, qa_floor
except ImportError:  # pragma: no cover - direct execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from article_packet import Article, Concept, matched_terms, parse_article, qa_floor


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as fh:
        return max(0, sum(1 for _ in csv.reader(fh)) - 1)


def count_markdown_questions(text: str) -> tuple[int, int]:
    answer_section = ""
    marker = re.search(r"^##\s+答案", text, flags=re.MULTILINE)
    if marker:
        question_text = text[: marker.start()]
        answer_section = text[marker.start() :]
    else:
        question_text = text
    question_count = len(re.findall(r"^###\s+\d+[.、]", question_text, flags=re.MULTILINE))
    answer_count = len(re.findall(r"^###\s+\d+[.、]", answer_section, flags=re.MULTILINE))
    return question_count, answer_count


def covered_terms(text: str, terms: list[Concept]) -> list[str]:
    lower = text.lower()
    return [term for term, _, _ in terms if term.lower() in lower]


def deck_slide_count(path: Path) -> int:
    text = read_text(path)
    return len(re.findall(r"<section[^>]+class=[\"'][^\"']*\bslide\b", text, flags=re.I))


def pptx_slide_count(path: Path) -> tuple[int, str | None]:
    if not path.exists():
        return 0, "missing"
    if Presentation is None:
        return 0, f"python-pptx unavailable: {PPTX_IMPORT_ERROR}"
    prs = Presentation(str(path))
    return len(prs.slides), None


def infographic_block_count(path: Path) -> int:
    text = read_text(path)
    explicit = len(re.findall(r"data-block=[\"']info[\"']", text))
    if explicit:
        return explicit
    return len(
        re.findall(
            r"class=[\"'][^\"']*(?:card|panel|metric|flow-node|matrix-item|info-block)[^\"']*[\"']",
            text,
            flags=re.I,
        )
    )


def item(checks: list[dict[str, Any]], name: str, ok: bool, **details: Any) -> None:
    checks.append({"name": name, "ok": bool(ok), **details})


def validate_bundle(article: Article, out_dir: Path, terms: list[Concept] | None = None) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    terms = terms or matched_terms(article)
    floor = qa_floor(article, terms)
    checks: list[dict[str, Any]] = []

    report_md = out_dir / "report.md"
    report_html = out_dir / "report.html"
    report_pdf = out_dir / "report.pdf"
    report_text = read_text(report_md)
    report_covered = covered_terms(report_text, terms)
    item(
        checks,
        "report_markdown",
        report_md.exists()
        and len(report_text) >= floor["min_report_chars"]
        and len(report_covered) >= floor["min_terms"],
        chars=len(report_text),
        min_chars=floor["min_report_chars"],
        covered_terms=len(report_covered),
        min_terms=floor["min_terms"],
    )
    item(checks, "report_html", report_html.exists() and len(read_text(report_html)) >= 1000)
    item(checks, "report_pdf", report_pdf.exists() and report_pdf.stat().st_size > 10_000 if report_pdf.exists() else False)

    deck_html = out_dir / "deck.html"
    slide_count = deck_slide_count(deck_html)
    deck_text = read_text(deck_html)
    deck_covered = covered_terms(deck_text, terms)
    item(
        checks,
        "deck_html",
        deck_html.exists()
        and slide_count >= floor["min_slides"]
        and len(deck_covered) >= floor["min_terms"],
        slides=slide_count,
        min_slides=floor["min_slides"],
        covered_terms=len(deck_covered),
        min_terms=floor["min_terms"],
    )

    pptx = out_dir / "deck.pptx"
    pptx_count, pptx_error = pptx_slide_count(pptx)
    item(
        checks,
        "deck_pptx",
        pptx.exists() and pptx_count >= min(floor["min_slides"], 14),
        slides=pptx_count,
        min_slides=min(floor["min_slides"], 14),
        error=pptx_error,
    )

    infographic = out_dir / "infographic.html"
    block_count = infographic_block_count(infographic)
    item(
        checks,
        "infographic_html",
        infographic.exists() and block_count >= floor["min_infographic_blocks"],
        blocks=block_count,
        min_blocks=floor["min_infographic_blocks"],
    )
    infographic_png = out_dir / "infographic.png"
    item(
        checks,
        "infographic_png",
        infographic_png.exists() and infographic_png.stat().st_size > 10_000 if infographic_png.exists() else False,
    )

    quiz = out_dir / "quiz.md"
    quiz_text = read_text(quiz)
    question_count, answer_count = count_markdown_questions(quiz_text)
    item(
        checks,
        "quiz",
        quiz.exists()
        and question_count >= floor["min_questions"]
        and answer_count >= floor["min_questions"]
        and question_count == answer_count,
        questions=question_count,
        answers=answer_count,
        min_questions=floor["min_questions"],
    )

    flashcards = out_dir / "flashcards.csv"
    flash_count = csv_row_count(flashcards)
    item(
        checks,
        "flashcards",
        flashcards.exists() and flash_count >= floor["min_terms"],
        cards=flash_count,
        min_cards=floor["min_terms"],
    )

    data_table = out_dir / "data-table.csv"
    data_rows = csv_row_count(data_table)
    item(
        checks,
        "data_table",
        data_table.exists() and data_rows >= floor["min_terms"],
        rows=data_rows,
        min_rows=floor["min_terms"],
    )

    mindmap = out_dir / "mindmap.mmd"
    mindmap_text = read_text(mindmap)
    item(checks, "mindmap", mindmap.exists() and "mindmap" in mindmap_text and len(mindmap_text.splitlines()) >= floor["min_terms"])

    podcast = out_dir / "podcast-script.md"
    podcast_text = read_text(podcast)
    item(
        checks,
        "podcast_script",
        podcast.exists() and len(podcast_text) >= floor["min_podcast_chars"],
        chars=len(podcast_text),
        min_chars=floor["min_podcast_chars"],
    )

    video = out_dir / "video-script.md"
    video_text = read_text(video)
    scene_count = len(re.findall(r"^##\s+镜头", video_text, flags=re.MULTILINE))
    item(
        checks,
        "video_script",
        video.exists() and scene_count >= floor["min_video_scenes"],
        scenes=scene_count,
        min_scenes=floor["min_video_scenes"],
    )

    cinematic = out_dir / "cinematic-video-shotlist.md"
    cinematic_text = read_text(cinematic)
    shot_count = len(re.findall(r"^\d+[.、]", cinematic_text, flags=re.MULTILINE))
    item(
        checks,
        "cinematic_shotlist",
        cinematic.exists() and shot_count >= floor["min_cinematic_shots"],
        shots=shot_count,
        min_shots=floor["min_cinematic_shots"],
    )

    return {
        "ok": all(check["ok"] for check in checks),
        "source": str(article.path),
        "title": article.title,
        "out_dir": str(out_dir),
        "floor": floor,
        "terms": [{"term": term, "category": category} for term, category, _ in terms],
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", required=True, help="Source Markdown article")
    parser.add_argument("--out-dir", required=True, help="Directory containing generated artifacts")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any gate fails")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a compact text report")
    args = parser.parse_args()

    article = parse_article(Path(args.article))
    result = validate_bundle(article, Path(args.out_dir), matched_terms(article))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for check in result["checks"]:
            status = "ok" if check["ok"] else "FAIL"
            detail = ", ".join(f"{k}={v}" for k, v in check.items() if k not in {"name", "ok"} and v not in (None, ""))
            print(f"{status}\t{check['name']}\t{detail}")
    if args.strict and not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
