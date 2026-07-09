#!/usr/bin/env python3
"""Build a generic article packet for transform providers.

The extractor is intentionally source-driven: it does not contain a domain
glossary, personal paths, account data, or examples from one user's vault.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


MIN_LONG_REPORT_CHARS = 4500
MIN_LONG_PODCAST_CHARS = 1800


@dataclass(frozen=True)
class Article:
    path: Path
    title: str
    author: str
    url: str
    published_at: str
    body: str
    plain_text: str
    sections: list[tuple[str, str]]


Concept = tuple[str, str, str]


STOP_TERMS = {
    "导读",
    "正文",
    "原文",
    "文章",
    "来源",
    "链接",
    "总结",
    "摘要",
    "小结",
    "结论",
    "更多",
    "其他",
    "这个",
    "那个",
    "一种",
    "一个",
    "两个",
    "三个",
    "为什么",
    "怎么做",
    "如何",
    "概念",
    "案例",
    "问题",
    "答案",
    "注意",
    "说明",
    "附录",
    "API（X Article",
    "Article",
    "CST",
    "source",
    "metadata",
    "views",
    "likes",
    "bookmarks",
}
STOP_KEYS = {term.casefold() for term in STOP_TERMS}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    rest = text[end + 4 :].lstrip()
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data, rest


def strip_markdown(value: str) -> str:
    value = re.sub(r"```[A-Za-z0-9_-]*\n?", "", value)
    value = value.replace("```", "")
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"__([^_]+)__", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"^>\s?", "", value, flags=re.MULTILINE)
    return value.strip()


def is_source_metadata_line(raw: str, cleaned: str, in_source_block: bool) -> bool:
    if in_source_block:
        return True
    if raw.startswith("> [!source]"):
        return True
    if any(marker in cleaned for marker in ("来源信息", "抓取方式", "元数据")):
        return True
    if re.search(r"(views|likes|bookmarks|retweets|replies|quotes)\s*[:：]?\s*\d", cleaned, flags=re.I):
        return True
    if re.fullmatch(r"[👁❤❤️🔖·,\d\s]+", cleaned):
        return True
    return False


def clean_heading(value: str) -> str:
    value = strip_markdown(value)
    value = re.sub(r"^\s*(第?[一二三四五六七八九十百千0-9]+[、.．:：-]?)\s*", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -—:：")
    return value or "正文"


def parse_article(path: Path) -> Article:
    path = path.expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    title = fm.get("title", "").strip()
    first_h1 = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    if first_h1:
        title = strip_markdown(first_h1.group(1))
    if not title:
        title = path.stem

    sections: list[tuple[str, str]] = []
    current_title = "导读"
    current_lines: list[str] = []
    in_source_block = False
    for raw in body.splitlines():
        heading = re.match(r"^(#{2,4})\s+(.+)$", raw)
        if heading:
            if current_lines:
                sections.append((clean_heading(current_title), "\n".join(current_lines).strip()))
            current_title = heading.group(2).strip()
            current_lines = []
            in_source_block = False
            continue
        if raw.startswith("# "):
            continue
        if raw.startswith("> [!source]"):
            in_source_block = True
            continue
        if in_source_block and raw.startswith(">"):
            continue
        if in_source_block and raw.strip():
            in_source_block = False
        cleaned = strip_markdown(raw)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if is_source_metadata_line(raw, cleaned, in_source_block):
            continue
        if cleaned:
            current_lines.append(cleaned)
    if current_lines:
        sections.append((clean_heading(current_title), "\n".join(current_lines).strip()))

    if not sections:
        plain = strip_markdown(body)
        sections = [("正文", plain)]
    plain_text = "\n".join(content for _, content in sections)
    return Article(
        path=path,
        title=title,
        author=fm.get("author", ""),
        url=fm.get("url", ""),
        published_at=fm.get("published_at", ""),
        body=body.strip(),
        plain_text=plain_text,
        sections=sections,
    )


def section_excerpt(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", strip_markdown(text)).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ，。；,.;") + "..."


def split_candidate_terms(value: str) -> list[str]:
    value = clean_heading(value)
    value = re.sub(r"^(什么是|如何理解|为什么|怎么|怎样|一文看懂|看懂)", "", value)
    pieces = re.split(r"[，,、/／|｜;；:：()（）\[\]【】《》<>]+| 和 | 与 | 及 | or | vs\.? ", value, flags=re.I)
    out: list[str] = []
    for piece in pieces:
        piece = normalize_term(piece)
        if usable_term(piece):
            out.append(piece)
    return out


def normalize_term(value: str) -> str:
    value = strip_markdown(value)
    value = re.sub(r"^[\-*•\d.、\s]+", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -—:：，。；;,.")
    if len(value) > 32:
        value = re.split(r"[。！？!?，,；;:：]", value)[0].strip()
    return value


def usable_term(value: str) -> bool:
    if not value:
        return False
    if value in STOP_TERMS or value.casefold() in STOP_KEYS:
        return False
    if len(value) < 2 or len(value) > 28:
        return False
    if re.fullmatch(r"\d+(\.\d+)?", value):
        return False
    if re.search(r"[，。！？!?；;]", value):
        return False
    if value.startswith(("http", "www.")):
        return False
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", value))
    ascii_count = len(re.findall(r"[A-Za-z]", value))
    return chinese_count >= 2 or ascii_count >= 2


def sentence_for_term(text: str, term: str) -> str:
    cleaned = re.sub(r"\s+", " ", strip_markdown(text))
    if not cleaned:
        return ""
    chunks = [s.strip() for s in re.split(r"(?<=[。！？!?；;])\s*|\n+", cleaned) if s.strip()]
    for chunk in chunks:
        if term.lower() in chunk.lower():
            return section_excerpt(chunk, 130)
    return section_excerpt(chunks[0], 130) if chunks else ""


def add_candidate(
    store: OrderedDict[str, Concept],
    term: str,
    category: str,
    source_text: str,
) -> None:
    term = normalize_term(term)
    if not usable_term(term):
        return
    key = term.casefold()
    category = clean_heading(category)
    definition = sentence_for_term(source_text, term)
    if not definition:
        definition = f"原文在「{category}」中讨论这一点；转换时需要保留它与上下文的关系。"
    if key in store:
        _, old_category, old_definition = store[key]
        old_is_intro = old_category in {"导读", "摘要", "原文"}
        new_is_specific = category not in {"导读", "摘要", "原文"}
        if old_is_intro and new_is_specific:
            store[key] = (term, category, definition)
        elif category == old_category and len(definition) > len(old_definition):
            store[key] = (term, category, definition)
        return
    store[key] = (term, category, definition)


def matched_terms(article: Article, max_terms: int = 48) -> list[Concept]:
    """Extract source-grounded concepts without a built-in domain glossary."""
    found: OrderedDict[str, Concept] = OrderedDict()

    for section_title, content in article.sections:
        category = clean_heading(section_title)
        for term in split_candidate_terms(section_title):
            add_candidate(found, term, category, content)

        for term in re.findall(r"\*\*([^*]{2,40})\*\*", content):
            add_candidate(found, term, category, content)
        for term in re.findall(r"`([^`]{2,32})`", content):
            add_candidate(found, term, category, content)
        for term in re.findall(r"[「『]([^」』]{2,24})[」』]", content):
            add_candidate(found, term, category, content)
        for term in re.findall(r"(?m)^\s*[-*•]\s*([^：:\n]{2,28})[：:]", content):
            add_candidate(found, term, category, content)
        for term in re.findall(r"(?<![A-Za-z0-9])([A-Z][A-Za-z0-9+.#/_-]{1,24})(?![A-Za-z0-9])", content):
            add_candidate(found, term, category, content)

    if len(found) < 8:
        for section_title, content in article.sections:
            category = clean_heading(section_title)
            for sentence in re.split(r"[。！？!?；;\n]", content):
                sentence = sentence.strip()
                if 4 <= len(sentence) <= 32:
                    add_candidate(found, sentence, category, content)
                    if len(found) >= 8:
                        break
            if len(found) >= 8:
                break

    return list(found.values())[:max_terms]


def theme_rows(terms: list[Concept]) -> list[tuple[str, list[Concept]]]:
    grouped: OrderedDict[str, list[Concept]] = OrderedDict()
    for term in terms:
        grouped.setdefault(term[1], []).append(term)
    return list(grouped.items())


def qa_floor(article: Article, terms: list[Concept]) -> dict[str, int]:
    term_count = len(terms)
    section_count = len(article.sections)
    body_len = len(article.plain_text)
    complexity = max(term_count, section_count * 2, body_len // 700)

    if complexity >= 24:
        min_slides = 18
    elif complexity >= 16 or body_len >= 4500:
        min_slides = 14
    elif complexity >= 10:
        min_slides = 10
    else:
        min_slides = 8

    min_terms = max(4, min(term_count, 24))
    min_questions = 12 if complexity >= 16 else max(6, min(10, min_terms))
    min_report_chars = (
        MIN_LONG_REPORT_CHARS
        if body_len >= 4500 or term_count >= 16
        else max(1800, min(3600, body_len // 2))
    )
    min_podcast_chars = MIN_LONG_PODCAST_CHARS if body_len >= 3500 or term_count >= 12 else 1000

    return {
        "min_terms": min_terms,
        "min_slides": min_slides,
        "max_slides": 18,
        "min_infographic_blocks": max(6, min(12, max(min_terms, section_count * 2))),
        "min_report_chars": min_report_chars,
        "min_podcast_chars": min_podcast_chars,
        "min_questions": min_questions,
        "min_video_scenes": 8 if complexity >= 10 else 6,
        "min_cinematic_shots": 10 if complexity >= 10 else 8,
    }
