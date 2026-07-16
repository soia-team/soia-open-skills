#!/usr/bin/env python3
# @created_by  openai/gpt-5
# @created_at  2026-07-11
# @modified_by  openai/gpt-5
# @modified_at  2026-07-11
# @version  0.1.2
# @description  Archive one public WeChat article into an Obsidian vault.
# @changelog  Reject symlink escapes, unsafe URL authorities, and invalid metadata controls/timestamps.
"""Archive one public WeChat article into an Obsidian vault.

The implementation is dependency-free and intentionally self-contained so a
single-skill npx installation remains runnable. It borrows the proven
HTMLParser approach used by soia-pkm-clip-wechat-account without importing across skills.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional


CST = timezone(timedelta(hours=8))
DEFAULT_ARTICLES_DIR = "Articles"
FALLBACK_ARTICLES_WARNING = (
    "WARN: 未找到 articles 目录配置（--articles-dir / OBSIDIAN_ARTICLES / config.yml），"
    "已落默认 Articles/——该目录不是本 vault 的正式归档位，请确认或配置"
)
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 soia-pkm-clip-wechat-article/0.1"
)
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
BLOCK_TAGS = {
    "p", "section", "div", "article", "h1", "h2", "h3", "h4",
    "h5", "h6", "li", "blockquote", "tr",
}
BLOCK_PAGE_MARKERS = (
    "环境异常",
    "访问过于频繁",
    "请先登录",
    "verify you are human",
    "操作频繁，请稍后再试",
)


@dataclass
class Article:
    title: str
    author: str
    publisher: str
    published_at: str
    url: str
    body: str
    content_complete: bool
    body_chars: int
    image_count: int
    warnings: list[str]


def looks_like_vault(path: Path) -> bool:
    return (path / ".obsidian").is_dir()


def discover_vault_from_cwd() -> Optional[Path]:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if looks_like_vault(candidate):
            return candidate
    return None


def resolve_vault(cli_vault: Optional[str]) -> Path:
    if cli_vault:
        vault = Path(cli_vault).expanduser().resolve()
    elif os.environ.get("OBSIDIAN_VAULT"):
        vault = Path(os.environ["OBSIDIAN_VAULT"]).expanduser().resolve()
    else:
        discovered = discover_vault_from_cwd()
        if discovered is None:
            raise ValueError(
                "No vault found; run inside a vault, set OBSIDIAN_VAULT, "
                "or pass --vault <path>."
            )
        vault = discovered
    if not vault.is_dir():
        raise ValueError(f"Vault directory does not exist: {vault}")
    return vault


def resolve_contained_path(root: Path, candidate: Path, label: str) -> Path:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve(strict=False)
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside {root_resolved}: {candidate}") from exc
    return candidate_resolved


def resolve_article_root(vault: Path, cli_articles_dir: Optional[str]) -> Path:
    configured = cli_articles_dir or os.environ.get("OBSIDIAN_ARTICLES")
    if not configured:
        print(FALLBACK_ARTICLES_WARNING, file=sys.stderr)
        configured = DEFAULT_ARTICLES_DIR
    path = Path(configured).expanduser()
    candidate = path.resolve() if path.is_absolute() else (vault / path).resolve()
    return resolve_contained_path(vault, candidate, "Article directory")


def validate_wechat_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme != "https":
        raise ValueError("WeChat article URL must use https.")
    if (parsed.hostname or "").lower() != "mp.weixin.qq.com":
        raise ValueError("WeChat article URL host must be exactly mp.weixin.qq.com.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("WeChat article URL must not contain userinfo.")
    if parsed.port not in (None, 443):
        raise ValueError("WeChat article URL must use the default HTTPS port.")
    if not (parsed.path == "/s" or parsed.path.startswith("/s/")):
        raise ValueError("WeChat article URL path must be /s or /s/<article-id>.")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_wechat_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_html(url: str, timeout: int = 20) -> str:
    safe_url = validate_wechat_url(url)
    request = urllib.request.Request(
        safe_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
            "Referer": "https://mp.weixin.qq.com/",
        },
    )
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} fetching WeChat article") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error fetching WeChat article: {exc.reason}") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"WeChat response exceeds {MAX_RESPONSE_BYTES} bytes")
    return raw.decode("utf-8", "replace")


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.scripts: list[str] = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        attrs_d = {str(key).lower(): value or "" for key, value in attrs}
        if tag == "meta":
            key = (
                attrs_d.get("property")
                or attrs_d.get("name")
                or attrs_d.get("itemprop")
                or ""
            ).lower()
            content = attrs_d.get("content", "")
            if key and content and key not in self.meta:
                self.meta[key] = content.strip()
        elif tag == "script":
            self._in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts.append(data)


class _TextByIdParser(HTMLParser):
    def __init__(self, target_ids: set[str]):
        super().__init__(convert_charrefs=True)
        self.target_ids = target_ids
        self.values: dict[str, list[str]] = {target: [] for target in target_ids}
        self._active: Optional[str] = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if self._active:
            if tag not in VOID_TAGS:
                self._depth += 1
            return
        element_id = attrs_d.get("id")
        if element_id in self.target_ids:
            self._active = element_id
            self._depth = 1

    def handle_endtag(self, tag):
        if not self._active or tag in VOID_TAGS:
            return
        self._depth -= 1
        if self._depth == 0:
            self._active = None

    def handle_data(self, data):
        if self._active:
            self.values[self._active].append(data)

    def text(self, target_id: str) -> str:
        return re.sub(r"\s+", " ", "".join(self.values.get(target_id, []))).strip()


class _ArticleBodyExtractor(HTMLParser):
    def __init__(self, target_id: str = "js_content"):
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.depth = 0
        self.found = False
        self.parts: list[str] = []
        self._in_link = False
        self._link_href = ""
        self._link_text: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if self.depth == 0:
            if attrs_d.get("id") == self.target_id:
                self.depth = 1
                self.found = True
            return
        if tag not in VOID_TAGS:
            self.depth += 1
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
        elif tag == "li":
            self.parts.append("\n\n- ")
        elif tag == "blockquote":
            self.parts.append("\n\n> ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.depth == 0:
            return
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag not in VOID_TAGS:
            self.depth -= 1
        if self.depth == 0:
            return
        if self._skip_depth:
            return
        if tag == "a" and self._in_link:
            text = re.sub(r"\s+", " ", "".join(self._link_text)).strip()
            if self._link_href and text:
                self.parts.append(f"[{text}]({self._link_href})")
            elif text:
                self.parts.append(text)
            self._in_link = False
            self._link_href = ""
            self._link_text = []
        elif tag in BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_data(self, data):
        if self.depth == 0 or self._skip_depth:
            return
        if self._in_link:
            self._link_text.append(data)
        else:
            self.parts.append(data)

    def get_markdown(self) -> str:
        raw = html.unescape("".join(self.parts))
        raw = raw.replace("\u200b", "").replace("\ufeff", "")
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r" *\n *", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        # WeChat commonly nests <p> inside <blockquote>. The block parser adds
        # a paragraph break after the quote marker; collapse that exact shape
        # so Markdown renders a real quote instead of an empty standalone ">".
        raw = re.sub(r"(?m)^>\s*\n\n(?=\S)", "> ", raw)
        return raw.strip()


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return html.unescape(match.group(1)).strip()
    return ""


def _timestamp_to_cst(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if re.fullmatch(r"\d{9,13}", value):
        timestamp = int(value)
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(CST).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (OSError, OverflowError, ValueError):
            return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(CST)
    return parsed.strftime("%Y-%m-%d %H:%M")


def normalize_canonical_url(candidate: str, fallback: str) -> str:
    fallback_url = validate_wechat_url(fallback)
    if candidate:
        try:
            candidate_url = validate_wechat_url(html.unescape(candidate))
            candidate_parts = urllib.parse.urlsplit(candidate_url)
            fallback_parts = urllib.parse.urlsplit(fallback_url)
            if (
                candidate_parts.path == fallback_parts.path
                and not fallback_parts.query
            ):
                return fallback_url
            return candidate_url
        except ValueError:
            pass
    return fallback_url


def parse_page(page_html: str, input_url: str) -> Article:
    metadata = _MetadataParser()
    metadata.feed(page_html)
    ids = _TextByIdParser({"activity-name", "js_name", "publish_time"})
    ids.feed(page_html)
    body_parser = _ArticleBodyExtractor()
    body_parser.feed(page_html)

    scripts = "\n".join(metadata.scripts)
    title = ids.text("activity-name") or metadata.meta.get("og:title", "")
    author = metadata.meta.get("author", "") or metadata.meta.get("article:author", "")
    publisher = ids.text("js_name") or _first_match(
        scripts,
        [
            r"\bnickname\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"\baccount_name\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ],
    )
    published_raw = ids.text("publish_time") or _first_match(
        scripts,
        [
            r"\bcreateTime\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"\bpublish_time\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"\boriCreateTime\s*[:=]\s*['\"]?(\d{9,13})",
            r"\bct\s*[:=]\s*['\"]?(\d{9,13})",
        ],
    )
    published_at = _timestamp_to_cst(
        published_raw
        or metadata.meta.get("article:published_time", "")
        or metadata.meta.get("date", "")
    )
    canonical_url = normalize_canonical_url(metadata.meta.get("og:url", ""), input_url)
    body = body_parser.get_markdown()
    visible = re.sub(r"!\[\]\([^)]+\)", "", body)
    visible = re.sub(r"[\s#>*\x60\-\[\]()]+", "", visible)
    body_chars = len(visible)
    image_count = len(re.findall(r"!\[\]\([^)]+\)", body))
    warnings: list[str] = []
    if not title:
        warnings.append("title_missing")
    if not author:
        warnings.append("author_missing")
    if not publisher:
        warnings.append("publisher_missing")
    if not published_at:
        warnings.append("published_at_missing")
    if not body_parser.found:
        warnings.append("js_content_missing")
    if body_chars < 200:
        warnings.append("body_too_short")
    lowered = body[:1200].lower()
    if any(marker.lower() in lowered for marker in BLOCK_PAGE_MARKERS):
        warnings.append("blocked_page_marker")
    complete = body_parser.found and body_chars >= 200 and "blocked_page_marker" not in warnings
    return Article(
        title=title,
        author=author,
        publisher=publisher,
        published_at=published_at,
        url=canonical_url,
        body=body,
        content_complete=complete,
        body_chars=body_chars,
        image_count=image_count,
        warnings=warnings,
    )


def sanitize_filename(value: str, limit: int) -> str:
    value = re.sub(r'[/\\:*?"<>|：；;]+', "-", value or "")
    value = re.sub(r"[（）()\[\]【】.,，。！!?？\"'“”‘’]+", "", value)
    value = re.sub(r"[\U00010000-\U0010ffff]", "", value)
    value = re.sub(r"\s+", "-", value.strip())
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:limit].rstrip("-") or "未命名"


def yaml_escape(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f\x85\u2028\u2029]+", " ", value or "")
    return cleaned.replace("\\", "\\\\").replace('"', '\\"').strip()


def find_existing_by_url(article_root: Path, url: str) -> Optional[Path]:
    if not article_root.is_dir():
        return None
    for path in article_root.rglob("*.md"):
        if "_MOC" in path.parts or "_模板" in path.parts:
            continue
        try:
            path = resolve_contained_path(article_root, path, "Existing archive")
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(
                f"Cannot inspect existing archive for URL dedupe: {path}: {exc}"
            ) from exc
        match = re.search(r'^url:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if match and match.group(1).strip() == url:
            return path
    return None


def choose_output_path(article_root: Path, article: Article) -> Path:
    date_part = article.published_at[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_part):
        date_part = datetime.now(CST).strftime("%Y-%m-%d")
    year, month = date_part[:4], date_part[5:7]
    byline = article.author or article.publisher or "未知作者"
    filename = (
        f"{date_part}-公众号-{sanitize_filename(byline, 24)}-"
        f"{sanitize_filename(article.title, 72)}.md"
    )
    output = article_root / year / month / filename
    if output.exists():
        suffix = hashlib.sha256(article.url.encode("utf-8")).hexdigest()[:8]
        output = output.with_name(f"{output.stem}-{suffix}.md")
    return output


def build_document(article: Article, captured_at: str) -> str:
    source_name = article.publisher or article.author or "公众号"
    lines = [
        "---",
        "tags: [文章摘抄]",
        f'title: "{yaml_escape(article.title)}"',
        "source: 公众号",
        f'url: "{yaml_escape(article.url)}"',
        f'author: "{yaml_escape(article.author)}"',
        f'publisher: "{yaml_escape(article.publisher)}"',
        f'published_at: "{yaml_escape(article.published_at)}"',
        f'captured_at: "{captured_at}"',
        "language: zh",
        "type: article",
        "topics: []",
        "people: []",
        f"content_complete: {'true' if article.content_complete else 'false'}",
        "---",
        "",
        f"# {article.title or '未命名公众号文章'}",
        "",
        "> [!source]- 来源信息",
        f"> **来源**｜[{source_name}]({article.url})｜{article.published_at or '未知时间'} CST",
        "> **抓取方式**｜public-static-html",
        "",
        "## 摘要",
        "",
        "<!-- AI 补充：1 句话 30-80 字浓缩 -->",
        "",
        "## 原文",
        "",
        article.body
        or "<!-- 正文抓取失败或为空，content_complete=false，需要人工核对原文链接 -->",
        "",
        "## 我的看法",
        "",
        "<!-- 留空给用户后续手写 -->",
        "",
        "## 关联",
        "",
        "- 相关文章：",
        "- 关联书目：",
        "",
    ]
    return "\n".join(lines)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def receipt(status: str, path: Optional[Path], vault: Path, article: Article) -> dict:
    resolved_path = path.resolve(strict=False) if path else None
    resolved_vault = vault.resolve()
    return {
        "status": status,
        "path": str(resolved_path) if resolved_path else None,
        "relative_path": (
            str(resolved_path.relative_to(resolved_vault)) if resolved_path else None
        ),
        "title": article.title,
        "author": article.author,
        "publisher": article.publisher,
        "published_at": article.published_at,
        "content_complete": article.content_complete,
        "body_chars": article.body_chars,
        "image_count": article.image_count,
        "warnings": article.warnings,
    }


def archive(
    article: Article,
    vault: Path,
    article_root: Path,
    dry_run: bool,
    allow_incomplete: bool,
) -> tuple[dict, Optional[Path]]:
    article_root = resolve_contained_path(vault, article_root, "Article directory")
    existing = find_existing_by_url(article_root, article.url)
    if existing:
        return receipt("skipped", existing, vault, article), existing
    if not article.content_complete and not allow_incomplete:
        raise RuntimeError(
            "Content quality gate failed; no file written. "
            f"Warnings: {', '.join(article.warnings) or 'unknown'}"
        )
    output = choose_output_path(article_root, article)
    output = resolve_contained_path(vault, output, "Output path")
    if dry_run:
        return receipt("dry_run", output, vault, article), output
    captured_at = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    output = resolve_contained_path(vault, output, "Output path")
    atomic_write_text(output, build_document(article, captured_at))
    return receipt("archived", output, vault, article), output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Archive one public WeChat article into an Obsidian vault."
    )
    parser.add_argument("url", nargs="?", help="https://mp.weixin.qq.com/s/... article URL")
    parser.add_argument("--vault", help="Obsidian vault path; otherwise env or cwd discovery")
    parser.add_argument(
        "--articles-dir",
        help="Vault-relative article root; overrides OBSIDIAN_ARTICLES",
    )
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate, write nothing")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Allow writing content_complete=false after a failed quality gate",
    )
    parser.add_argument("--json", action="store_true", help="Print a stable JSON receipt")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.url:
        parser.print_help()
        return 2
    if args.timeout <= 0:
        print("ERROR: --timeout must be positive", file=sys.stderr)
        return 2
    try:
        url = validate_wechat_url(args.url)
        vault = resolve_vault(args.vault)
        article_root = resolve_article_root(vault, args.articles_dir)
        print(f"Fetching WeChat article: {url}", file=sys.stderr)
        article = parse_page(fetch_html(url, timeout=args.timeout), url)
        result, path = archive(
            article,
            vault,
            article_root,
            dry_run=args.dry_run,
            allow_incomplete=args.allow_incomplete,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        prefix = {
            "archived": "ARCHIVED",
            "skipped": "SKIP",
            "dry_run": "DRY-RUN",
        }[result["status"]]
        print(f"{prefix}: {path.relative_to(vault) if path else '-'}")
        print(
            f"title={article.title!r} body_chars={article.body_chars} "
            f"images={article.image_count} complete={article.content_complete}",
            file=sys.stderr,
        )
        if article.warnings:
            print(f"warnings={','.join(article.warnings)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
