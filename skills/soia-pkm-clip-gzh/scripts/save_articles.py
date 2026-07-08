#!/usr/bin/env python3
"""
save_articles.py — Shared helpers for soia-pkm-clip-gzh.

Not meant to be run directly. Imported by fetch_api.py (Route A) and
fetch_cookie.py (Route B):
  - vault / output-dir resolution (CLI arg > env var > cwd auto-discovery)
  - a dependency-free HTML -> Markdown-ish converter (stdlib html.parser only,
    matching this repo's zero-third-party-dependency convention)
  - filename / frontmatter building matching the clip family's shared layout
  - idempotent article writing (skip already-archived urls unless --force)

Per SKILL_SPEC.md ("no hardcoded personal/vault-specific paths in scripts"),
DEFAULT_OUT_DIR below is intentionally a generic, non-personal path. This
skill's SKILL.md documents a recommended vault-specific value as something
each user sets via --out / OBSIDIAN_GZH_OUT, not as a public code default.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

CST = timezone(timedelta(hours=8))

DEFAULT_OUT_DIR = "Inbox/gzh-articles"

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
BLOCK_TAGS = {"p", "section", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "tr"}


# ---------------------------------------------------------------------------
# vault / path resolution (mirrors soia-pkm-clip-x/scripts/archive_x.py)
# ---------------------------------------------------------------------------

def looks_like_vault(path: Path) -> bool:
    return (path / ".obsidian").is_dir() or (path / "AGENTS.md").is_file()


def discover_vault_from_cwd() -> Optional[Path]:
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if looks_like_vault(p):
            return p
    return None


def resolve_vault(cli_vault: Optional[str]) -> Path:
    if cli_vault:
        p = Path(cli_vault).expanduser().resolve()
    else:
        env = os.environ.get("OBSIDIAN_VAULT")
        if env:
            p = Path(env).expanduser().resolve()
        else:
            p = discover_vault_from_cwd()
            if not p:
                print("❌ No vault path found.", file=sys.stderr)
                print("   Fix: run from the vault root, set OBSIDIAN_VAULT, or pass --vault <path>.", file=sys.stderr)
                sys.exit(1)
            print(f"ℹ️  Auto-detected vault from cwd: {p}", file=sys.stderr)
    if not p.exists() or not p.is_dir():
        print(f"❌ Vault path does not exist: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def resolve_out_dir(vault: Path, cli_out: Optional[str]) -> Path:
    sub = cli_out or os.environ.get("OBSIDIAN_GZH_OUT")
    if sub:
        return vault / sub
    return vault / DEFAULT_OUT_DIR


# ---------------------------------------------------------------------------
# filename sanitizing (same rules as archive_x.py's sanitize_title_for_filename)
# ---------------------------------------------------------------------------

def sanitize_title_for_filename(title: str, limit: int = 50) -> str:
    if not title:
        return "未命名"
    title = re.sub(r'[/\\:*?"<>|：；;]+', "-", title)
    title = re.sub(r"[（）()\[\]【】.,，。！!?？\"'“”‘’]+", "", title)
    title = re.sub(r"[\U00010000-\U0010ffff]", "", title)  # emoji
    title = re.sub(r"\s+", "-", title.strip())
    title = re.sub(r"-+", "-", title)
    return title[:limit].rstrip("-") or "未命名"


# ---------------------------------------------------------------------------
# HTML -> Markdown (stdlib html.parser only, no bs4/lxml/requests)
# ---------------------------------------------------------------------------

class _HTMLToMarkdown(HTMLParser):
    """Convert a self-contained HTML fragment (e.g. the API's news_item.content
    field) into Markdown-ish text. Not a full renderer — unknown tags are
    ignored but their text content still passes through."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._in_link = False
        self._link_href: Optional[str] = None
        self._link_text: list[str] = []
        self._skip_depth = 0  # inside <script>/<style>

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "br":
            self.parts.append("\n")
        elif tag == "img":
            src = attrs_d.get("data-src") or attrs_d.get("src") or ""
            if src:
                self.parts.append(f"\n\n![]({src})\n\n")
        elif tag == "a":
            self._in_link = True
            self._link_href = attrs_d.get("href") or ""
            self._link_text = []
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n\n" + "#" * min(int(tag[1]), 4) + " ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "li":
            self.parts.append("- ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "a" and self._in_link:
            text = "".join(self._link_text).strip()
            if self._link_href and text:
                self.parts.append(f"[{text}]({self._link_href})")
            elif text:
                self.parts.append(text)
            self._in_link = False
            self._link_href = None
            self._link_text = []
        elif tag in BLOCK_TAGS or tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_link:
            self._link_text.append(data)
        else:
            self.parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_markdown(content_html: str) -> str:
    """Convert a standalone HTML fragment to Markdown-ish text."""
    if not content_html:
        return ""
    parser = _HTMLToMarkdown()
    try:
        parser.feed(content_html)
    except Exception:
        # Never let a malformed fragment block an otherwise-good fetch —
        # degrade to a crude tag-strip instead of crashing the whole run.
        return re.sub(r"<[^>]+>", "", content_html).strip()
    return parser.get_text()


class _ArticleBodyExtractor(HTMLParser):
    """Extract + convert to Markdown the element with id="js_content" out of a
    *full page* HTML document (used by Route B, which fetches the public
    article page directly). Tracks element depth in a void-tag-aware way so
    it correctly detects when it has exited the target container — a plain
    tag-count without void-tag awareness would get stuck open on the first
    bare <img>/<br> and swallow the rest of the page.
    """

    def __init__(self, target_id: str = "js_content"):
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.depth = 0
        self.found = False
        self.parts: list[str] = []
        self._in_link = False
        self._link_href: Optional[str] = None
        self._link_text: list[str] = []

    def _enter(self, tag, attrs_d):
        if tag == "br":
            self.parts.append("\n")
        elif tag == "img":
            src = attrs_d.get("data-src") or attrs_d.get("src") or ""
            if src:
                self.parts.append(f"\n\n![]({src})\n\n")
        elif tag == "a":
            self._in_link = True
            self._link_href = attrs_d.get("href") or ""
            self._link_text = []
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n\n" + "#" * min(int(tag[1]), 4) + " ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "li":
            self.parts.append("- ")

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if self.depth == 0:
            if attrs_d.get("id") == self.target_id:
                self.depth = 1
                self.found = True
            return
        if tag not in VOID_TAGS:
            self.depth += 1
        self._enter(tag, attrs_d)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.depth == 0:
            return
        if tag not in VOID_TAGS:
            self.depth -= 1
        if self.depth == 0:
            return  # this closed the target container itself
        if tag == "a" and self._in_link:
            text = "".join(self._link_text).strip()
            if self._link_href and text:
                self.parts.append(f"[{text}]({self._link_href})")
            elif text:
                self.parts.append(text)
            self._in_link = False
        elif tag in BLOCK_TAGS or tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n\n")

    def handle_data(self, data):
        if self.depth == 0:
            return
        if self._in_link:
            self._link_text.append(data)
        else:
            self.parts.append(data)

    def get_markdown(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def extract_js_content_markdown(page_html: str, target_id: str = "js_content") -> tuple[str, bool]:
    """Pull WeChat's article body (#js_content) out of a full article page and
    convert it to Markdown. Returns (markdown, found)."""
    if not page_html:
        return "", False
    parser = _ArticleBodyExtractor(target_id)
    try:
        parser.feed(page_html)
    except Exception:
        return "", False
    return parser.get_markdown(), parser.found


# ---------------------------------------------------------------------------
# dedupe + frontmatter + write
# ---------------------------------------------------------------------------

def find_existing_by_url(out_dir: Path, url: str) -> Optional[Path]:
    if not out_dir.exists() or not url:
        return None
    for f in out_dir.rglob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r'^url:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if m and m.group(1).strip() == url.strip():
            return f
    return None


def _yaml_escape(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def build_frontmatter(article: dict, route: str, captured_at: str) -> str:
    lines = [
        "---",
        "tags: [公众号原创, 待归位]",
        "source: 公众号自有",
        f'url: "{_yaml_escape(article.get("url", ""))}"',
        f'title: "{_yaml_escape(article.get("title", ""))}"',
        f'author: "{_yaml_escape(article.get("author", ""))}"',
        f'published_at: "{_yaml_escape(article.get("published_at", ""))}"',
        f'captured_at: "{captured_at}"',
        f"route: {route}",
        f'content_complete: {"true" if article.get("content_complete") else "false"}',
        "topics: []",
        "---",
    ]
    return "\n".join(lines)


def save_article(
    vault: Path,
    out_dir: Path,
    article: dict,
    route: str,
    account_name: str = "",
    force: bool = False,
) -> Optional[Path]:
    """Write one article dict to <out_dir>/<year>/<filename>.md.

    article keys: title, url, author, published_at ("YYYY-MM-DD HH:MM" or
    ""), content (Markdown body), content_complete (bool).
    Returns the written path, or None if skipped (already archived, no
    --force).
    """
    url = article.get("url", "")
    existing = find_existing_by_url(out_dir, url) if url else None
    if existing and not force:
        print(f"⚠️  Already archived, skip: {existing.relative_to(vault)}", file=sys.stderr)
        return None

    published_at = article.get("published_at") or ""
    year = published_at[:4] if published_at[:4].isdigit() else str(datetime.now(CST).year)
    date_part = published_at[:10] if len(published_at) >= 10 else datetime.now(CST).strftime("%Y-%m-%d")

    title_part = sanitize_title_for_filename(article.get("title", ""), 50)
    account_part = sanitize_title_for_filename(account_name, 20) if account_name else "公众号"
    filename = f"{date_part}-公众号-{account_part}-{title_part}.md"

    year_dir = out_dir / year
    year_dir.mkdir(parents=True, exist_ok=True)

    if existing and force:
        out_path = existing
    else:
        out_path = year_dir / filename
        if out_path.exists():
            digest = re.sub(r"\D", "", url)[-6:] or str(abs(hash(url)))[:6]
            out_path = year_dir / f"{filename[:-3]}-{digest}.md"

    captured_at = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    fm = build_frontmatter(article, route, captured_at)
    title = article.get("title", "") or "(无标题)"
    account_display = account_name or "公众号"

    doc = f"""{fm}

# {title}

> [!source]- 来源信息
> **来源**｜[{account_display}]({url})｜{published_at or "未知时间"} CST
> **抓取方式**｜route={route}

## 摘要

<!-- AI 补充：1 句话 30-80 字浓缩 -->

## 原文

{article.get('content', '') or '<!-- 正文抓取失败或为空，content_complete=false，需要人工核对原文链接 -->'}

## 我的看法

<!-- 留空给用户后续手写 -->

## 关联

- 相关文章：
- 关联书目：
"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path
