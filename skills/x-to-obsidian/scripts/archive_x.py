#!/usr/bin/env python3
"""
archive_x.py — Archive an X (Twitter) tweet / thread / Article into Obsidian vault.

Data source: api.fxtwitter.com (public, no auth required).

Usage:
    python3 archive_x.py <X URL>
    python3 archive_x.py <X URL> --force                # Force overwrite if archived
    python3 archive_x.py <X URL> --vault /path/to/vault # Override vault path

Environment variables (alternative to --vault):
    OBSIDIAN_VAULT     Path to your Obsidian vault (required if --vault not given)
    OBSIDIAN_ARTICLES  Subdirectory within vault for archived articles
                       (default: "Articles")
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))

URL_RE = re.compile(
    r"https?://(?:mobile\.)?(?:x|twitter|fxtwitter)\.com/([^/]+)/(?:status|article)/(\d+)",
    re.IGNORECASE,
)


def resolve_vault(cli_vault: str | None) -> Path:
    """Resolve the vault path from CLI arg or env var."""
    if cli_vault:
        p = Path(cli_vault).expanduser().resolve()
    else:
        env = os.environ.get("OBSIDIAN_VAULT")
        if not env:
            print("❌ No vault path. Set OBSIDIAN_VAULT env or pass --vault <path>", file=sys.stderr)
            print("   Example: export OBSIDIAN_VAULT=~/Documents/MyVault", file=sys.stderr)
            sys.exit(1)
        p = Path(env).expanduser().resolve()
    if not p.exists():
        print(f"❌ Vault path does not exist: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def resolve_article_root(vault: Path) -> Path:
    sub = os.environ.get("OBSIDIAN_ARTICLES", "Articles")
    return vault / sub


def parse_url(url: str) -> tuple[str, str]:
    m = URL_RE.search(url.strip())
    if not m:
        raise SystemExit(f"❌ Not a valid X URL: {url}")
    return m.group(1), m.group(2)


def http_get_json(url: str, timeout: int = 15) -> dict | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 x-to-obsidian/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ HTTP {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ⚠️ {type(e).__name__}: {e}", file=sys.stderr)
        return None


def fetch_tweet(handle: str, status_id: str) -> dict | None:
    return http_get_json(f"https://api.fxtwitter.com/{handle}/status/{status_id}")


def walk_thread(handle: str, status_id: str, max_depth: int = 50) -> list[dict]:
    """Walk back through replying_to chain to get full self-thread."""
    chain: list[dict] = []
    cur_h, cur_id = handle, status_id
    visited = set()
    for _ in range(max_depth):
        if cur_id in visited:
            break
        visited.add(cur_id)
        try:
            resp = fetch_tweet(cur_h, cur_id)
        except Exception:
            break
        if not resp or resp.get("code") != 200:
            break
        t = resp.get("tweet") or {}
        if not isinstance(t, dict):
            break
        chain.append(t)
        replying = t.get("replying_to_status")
        if not replying or not isinstance(replying, dict):
            break
        author_obj = replying.get("author")
        prev_handle = (
            author_obj.get("screen_name") if isinstance(author_obj, dict) else None
        )
        prev_id = replying.get("id")
        cur_author = t.get("author") or {}
        cur_handle = (
            cur_author.get("screen_name") if isinstance(cur_author, dict) else None
        )
        if not prev_id or not prev_handle or prev_handle != cur_handle:
            break
        cur_h, cur_id = prev_handle, str(prev_id)
    chain.reverse()
    return chain


def apply_inline_markup(
    text: str,
    inline_style_ranges: list[dict],
    entity_ranges: list[dict],
    entity_map: dict,
) -> str:
    """Apply Draft.js inlineStyleRanges (BOLD/ITALIC) and LINK entityRanges to Markdown."""
    if not text:
        return text

    n = len(text)
    bold = [False] * n
    italic = [False] * n
    for r in inline_style_ranges or []:
        style = r.get("style", "")
        offset = r.get("offset", 0)
        length = r.get("length", 0)
        end = min(offset + length, n)
        if style.upper() == "BOLD":
            for i in range(offset, end):
                bold[i] = True
        elif style.upper() == "ITALIC":
            for i in range(offset, end):
                italic[i] = True

    # link_url[i] holds the target URL when position i sits inside a LINK entity span
    link_url: list[str | None] = [None] * n
    for r in entity_ranges or []:
        ent = entity_map.get(str(r.get("key"))) or {}
        if ent.get("type") != "LINK":
            continue
        url = (ent.get("data") or {}).get("url")
        if not url:
            continue
        offset = r.get("offset", 0)
        length = r.get("length", 0)
        end = min(offset + length, n)
        for i in range(offset, end):
            link_url[i] = url

    result: list[str] = []
    prev_b, prev_i, prev_link = False, False, None
    for idx, ch in enumerate(text):
        cur_b, cur_i, cur_link = bold[idx], italic[idx], link_url[idx]
        # close in reverse nesting order: italic, bold, link
        if prev_i and not cur_i:
            result.append("*")
        if prev_b and not cur_b:
            result.append("**")
        if prev_link and cur_link != prev_link:
            result.append(f"]({prev_link})")
        # open in nesting order: link, bold, italic
        if cur_link and cur_link != prev_link:
            result.append("[")
        if cur_b and not prev_b:
            result.append("**")
        if cur_i and not prev_i:
            result.append("*")
        result.append(ch)
        prev_b, prev_i, prev_link = cur_b, cur_i, cur_link
    if prev_i:
        result.append("*")
    if prev_b:
        result.append("**")
    if prev_link:
        result.append(f"]({prev_link})")
    return "".join(result)


def render_atomic_block(
    entity_ranges: list[dict], entity_map: dict, media_by_id: dict, source_url: str
) -> str | None:
    """Render the entity behind an `atomic` block: code (MARKDOWN), DIVIDER, or MEDIA.

    Atomic blocks carry no real text of their own (just a placeholder space) —
    the actual content lives in content.entityMap, keyed by the block's entityRanges.
    """
    for r in entity_ranges or []:
        ent = entity_map.get(str(r.get("key"))) or {}
        typ = ent.get("type")
        data = ent.get("data") or {}
        if typ == "DIVIDER":
            return "---"
        if typ == "MARKDOWN":
            md = data.get("markdown", "")
            return md.rstrip() if md else None
        if typ == "MEDIA":
            images = []
            for item in data.get("mediaItems") or []:
                media = media_by_id.get(str(item.get("mediaId")))
                url = ((media or {}).get("media_info") or {}).get("original_img_url")
                if url:
                    images.append(f"![]({url})")
            if images:
                return "\n\n".join(images)
            # couldn't resolve a direct URL — point back to the source instead of a silent gap
            return f"*[图片：见原文]({source_url})*" if source_url else None
    return None


def render_article_blocks(
    blocks: list[dict], entity_map: dict, media_by_id: dict, source_url: str = ""
) -> str:
    out: list[str] = []
    for b in blocks:
        raw_text = (b.get("text") or "").rstrip()
        typ = b.get("type", "unstyled")
        entity_ranges = b.get("entityRanges") or []

        if typ == "atomic":
            rendered = render_atomic_block(entity_ranges, entity_map, media_by_id, source_url)
            if rendered:
                out.append(rendered)
            continue

        if not raw_text and typ in ("unstyled", "header-one", "header-two", "header-three", "header-four"):
            continue
        if re.fullmatch(r"MPH_MARKER_\d+", raw_text):
            # internal fxtwitter placeholder token, not authored content
            continue
        inline_styles = b.get("inlineStyleRanges") or []
        text = apply_inline_markup(raw_text, inline_styles, entity_ranges, entity_map)
        if typ == "header-one":
            out.append(f"\n## {text}\n")
        elif typ == "header-two":
            out.append(f"\n## {text}\n")
        elif typ == "header-three":
            out.append(f"\n### {text}\n")
        elif typ == "header-four":
            out.append(f"\n#### {text}\n")
        elif typ == "unordered-list-item":
            out.append(f"- {text}")
        elif typ == "ordered-list-item":
            out.append(f"1. {text}")
        elif typ == "blockquote":
            for line in text.split("\n"):
                out.append(f"> {line}")
        else:
            out.append(text)
    return "\n\n".join(out)


def render_thread(chain: list[dict]) -> str:
    parts: list[str] = []
    for i, t in enumerate(chain, 1):
        text = (
            t.get("raw_text", {}).get("text") or t.get("text") or ""
        ).strip()
        media = t.get("media") or {}
        for m in (media.get("photos") or []):
            if isinstance(m, dict):
                text += f"\n\n![]({m.get('url','')})"
        parts.append(
            f"**[{i}/{len(chain)}]** {text}" if len(chain) > 1 else text
        )
    return "\n\n---\n\n".join(parts)


def render_single(tweet: dict) -> str:
    text = (
        tweet.get("raw_text", {}).get("text") or tweet.get("text") or ""
    ).strip()
    media = tweet.get("media") or {}
    if isinstance(media, dict):
        for m in (media.get("photos") or []):
            if isinstance(m, dict):
                text += f"\n\n![]({m.get('url','')})"
    return text


def collect_media(tweets: list[dict]) -> list[dict]:
    media: list[dict] = []
    for t in tweets:
        m = t.get("media") or {}
        if not isinstance(m, dict):
            continue
        for p in (m.get("photos") or []):
            if isinstance(p, dict):
                media.append({"type": "image", "url": p.get("url", "")})
        for v in (m.get("videos") or []):
            if isinstance(v, dict):
                media.append({
                    "type": "video",
                    "url": v.get("url", ""),
                    "thumbnail": v.get("thumbnail_url", ""),
                })
        mosaic = m.get("mosaic")
        mosaic_items = (
            mosaic
            if isinstance(mosaic, list)
            else ([mosaic] if isinstance(mosaic, dict) else [])
        )
        for g in mosaic_items:
            if not isinstance(g, dict):
                continue
            fmts = g.get("formats")
            if isinstance(fmts, dict):
                media.append({
                    "type": "mosaic",
                    "url": fmts.get("jpeg") or fmts.get("webp") or "",
                })
    return media


def sanitize_title_for_filename(title: str, limit: int = 50) -> str:
    # filesystem-illegal chars + separator-like punctuation (colon/semicolon,
    # half- and full-width) — these join two meaningful phrases, so replace
    # with a dash rather than deleting (deleting would merge the phrases
    # into one confusing run, e.g. "A：B" -> "AB" instead of "A-B")
    title = re.sub(r'[/\\:*?"<>|：；;]+', "-", title)
    # wrapping punctuation (brackets/quotes) — safe to strip since they
    # enclose rather than separate text
    title = re.sub(
        r"[（）()\[\]【】.,，。！!?？\"'""'']+", "", title
    )
    # emoji (supplementary plane)
    title = re.sub(r"[\U00010000-\U0010ffff]", "", title)
    # whitespace
    title = re.sub(r"\s+", "-", title.strip())
    # collapse dashes
    title = re.sub(r"-+", "-", title)
    return title[:limit].rstrip("-")


def detect_language(text: str, hint: str | None) -> str:
    if hint and hint not in (None, "", "und"):
        return hint
    if not text:
        return "und"
    # Japanese: kana takes precedence over CJK Han
    hira = sum(1 for ch in text if "぀" <= ch <= "ゟ")
    kata = sum(1 for ch in text if "゠" <= ch <= "ヿ")
    if (hira + kata) / max(len(text), 1) > 0.05:
        return "ja"
    # Korean: Hangul
    hangul = sum(1 for ch in text if "가" <= ch <= "힯")
    if hangul / max(len(text), 1) > 0.1:
        return "ko"
    # Chinese
    cn = sum(1 for ch in text if "一" <= ch <= "鿿")
    if cn / max(len(text), 1) > 0.15:
        return "zh"
    if re.search(r"[a-zA-Z]", text):
        return "en"
    return "und"


def find_existing_archive(article_root: Path, status_id: str) -> Path | None:
    if not article_root.exists():
        return None
    for f in article_root.rglob("*.md"):
        if "_template" in f.parts or "_templates" in f.parts or "_MOC" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r"^url:\s*(.+)$", text, re.MULTILINE)
        if m and f"/status/{status_id}" in m.group(1):
            return f
    return None


def extract_preserved_fields(existing_path: Path | None) -> dict:
    """Pull hand-filled topics/people/summary out of an already-archived file
    so --force (re-running to pick up a script fix) doesn't wipe out curation
    work a human or AI did after the first archive.
    """
    preserved = {"topics": None, "people": None, "summary": None}
    if not existing_path or not existing_path.exists():
        return preserved
    try:
        text = existing_path.read_text(encoding="utf-8")
    except Exception:
        return preserved

    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        for key in ("topics", "people"):
            m = re.search(rf"^{key}:\s*\n((?:  - .*\n?)+)", fm, re.MULTILINE)
            if m:
                preserved[key] = f"{key}:\n" + m.group(1).rstrip("\n")
                continue
            m = re.search(rf"^{key}:\s*(\[.+?\])\s*$", fm, re.MULTILINE)
            if m and m.group(1).strip() != "[]":
                preserved[key] = f"{key}: {m.group(1)}"

    m = re.search(r"##\s*(?:摘要|Summary)\s*\n\n(.*?)\n\n##", text, re.DOTALL)
    if m:
        body = m.group(1).strip()
        if body and not body.startswith("<!--"):
            preserved["summary"] = body

    return preserved


def build_frontmatter(
    tweet: dict,
    chain: list[dict],
    is_article: bool,
    captured_at_str: str,
    published_at_str: str,
    media: list[dict],
    lang: str,
    preserved: dict | None = None,
) -> str:
    author = tweet["author"]
    article = tweet.get("article") or {}
    quoted = tweet.get("quote") or {}
    preserved = preserved or {}

    lines = [
        "---",
        "tags: [文章摘抄]",
        "source: X",
        f"url: {tweet['url']}",
        f"author: {author.get('name','')}",
        f'handle: "@{author.get("screen_name","")}"',
        f"published_at: {published_at_str}",
        f"captured_at: {captured_at_str}",
        f"language: {lang}",
        f"type: {'article' if is_article else ('thread' if len(chain) > 1 else 'tweet')}",
        preserved.get("topics") or "topics: []",
        preserved.get("people") or "people: []",
    ]
    if media:
        lines.append("media:")
        for m in media:
            lines.append(f"  - type: {m['type']}")
            lines.append(f"    url: {m['url']}")
    else:
        lines.append("media: 0")
    if quoted:
        qa = quoted.get("author", {})
        qtext = (
            (quoted.get("text") or "")
            .replace("\n", " ")
            .replace('"', "'")[:200]
        )
        lines.append("quoted_tweet:")
        lines.append(f"  url: {quoted.get('url','')}")
        lines.append(f"  author: {qa.get('screen_name','')}")
        lines.append(f'  text: "{qtext}"')
    lines.append("content_complete: true")
    if is_article:
        lines.append(f'article_id: "{article.get("id","")}"')
        preview = (
            (article.get("preview_text") or "")
            .replace("\n", " ")
            .replace('"', "'")[:200]
        )
        lines.append(f'preview_text: "{preview}"')
    if len(chain) > 1:
        lines.append(f'thread_root_id: "{chain[0].get("id","")}"')
        lines.append(f"thread_count: {len(chain)}")
    lines.append("metrics:")
    lines.append(f"  views: {tweet.get('views',0)}")
    lines.append(f"  likes: {tweet.get('likes',0)}")
    lines.append(f"  bookmarks: {tweet.get('bookmarks',0)}")
    lines.append(f"  retweets: {tweet.get('retweets',0)}")
    lines.append(f"  replies: {tweet.get('replies',0)}")
    lines.append(f"  quotes: {tweet.get('quotes',0)}")
    lines.append("---")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Archive X tweet/thread/Article into Obsidian vault.")
    ap.add_argument("url", nargs="?", help="X URL (x.com / twitter.com / fxtwitter.com)")
    ap.add_argument("--force", action="store_true", help="Force re-archive even if already exists")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT env)")
    args = ap.parse_args()

    if not args.url:
        ap.print_help()
        sys.exit(1)

    vault = resolve_vault(args.vault)
    article_root = resolve_article_root(vault)

    handle, status_id = parse_url(args.url)

    existing = find_existing_archive(article_root, status_id)
    if existing and not args.force:
        rel = existing.relative_to(vault)
        print(f"⚠️  Already archived: {rel}", file=sys.stderr)
        print(f"   Author: @{handle}  Status ID: {status_id}", file=sys.stderr)
        print(f"   Use --force to re-archive (will overwrite topics/people)", file=sys.stderr)
        print(f"SKIP: {rel}")
        sys.exit(0)

    if existing and args.force:
        print(f"⚠️  Force-overwriting: {existing.relative_to(vault)}", file=sys.stderr)

    preserved = extract_preserved_fields(existing)

    print(f"📖 Fetching @{handle} / {status_id}", file=sys.stderr)

    resp = fetch_tweet(handle, status_id)
    if not resp or resp.get("code") != 200:
        code = resp.get("code") if resp else "N/A"
        print(f"❌ fxtwitter failed (code={code})", file=sys.stderr)
        sys.exit(2)

    tweet = resp["tweet"]
    article = tweet.get("article") or {}
    is_article = bool(article)

    # thread walk
    if tweet.get("replying_to_status") and not is_article:
        chain = walk_thread(handle, status_id)
        if not chain:
            chain = [tweet]
    else:
        chain = [tweet]
    root = chain[0] if chain else tweet

    # timestamps
    ts = root.get("created_timestamp", 0)
    dt_cst = (
        datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(CST)
        if ts
        else datetime.now(CST)
    )
    published_at_str = dt_cst.strftime("%Y-%m-%d %H:%M")
    captured_at_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M")

    # title
    if is_article:
        title_raw = article.get("title", "").strip()
    elif len(chain) > 1:
        title_raw = (
            chain[0].get("raw_text", {}).get("text")
            or chain[0].get("text", "")
        ).strip().split("\n")[0]
    else:
        title_raw = (
            tweet.get("raw_text", {}).get("text") or tweet.get("text", "")
        ).strip().split("\n")[0]
    title_raw = title_raw or f"@{handle}-{status_id}"

    fn_title = sanitize_title_for_filename(title_raw, 50)
    filename = f"{dt_cst.strftime('%Y-%m-%d')}-X-{handle}-{fn_title}.md"

    # body
    if is_article:
        content = article.get("content", {})
        blocks = content.get("blocks", [])
        entity_map = {
            str(e["key"]): e["value"]
            for e in content.get("entityMap", [])
            if isinstance(e, dict)
        }
        media_by_id = {
            str(m["media_id"]): m
            for m in article.get("media_entities", [])
            if isinstance(m, dict)
        }
        body = render_article_blocks(blocks, entity_map, media_by_id, tweet.get("url", ""))
        body_meta = f"X Article ({len(blocks)} blocks)"
    elif len(chain) > 1:
        body = render_thread(chain)
        body_meta = f"thread ({len(chain)} tweets)"
    else:
        body = render_single(tweet)
        body_meta = "single tweet"

    media = collect_media(chain)
    sample_text = body[:1000] if body else ""
    lang = detect_language(sample_text, root.get("lang"))

    fm = build_frontmatter(
        tweet, chain, is_article, captured_at_str, published_at_str, media, lang,
        preserved=preserved,
    )

    metrics_line = (
        f"👁 {tweet.get('views',0):,} · "
        f"❤ {tweet.get('likes',0):,} · "
        f"🔖 {tweet.get('bookmarks',0):,}"
    )

    # UI language for section headings. Default: zh (Chinese).
    # Set X_ARCHIVE_LANG=en to use English headings.
    ui_lang = os.environ.get("X_ARCHIVE_LANG", "zh").lower()
    if ui_lang == "en":
        L = {
            "source": "Source", "method": "Method", "metrics": "Metrics",
            "summary": "Summary", "summary_hint": "<!-- AI: fill 1-sentence summary, 30-80 chars -->",
            "content": "Content", "translation": "Translation",
            "translation_hint": "<!-- Ask your AI agent to translate if needed -->",
            "thoughts": "My Thoughts", "thoughts_hint": "<!-- Left blank for the user -->",
            "related": "Related", "rel_articles": "- Related articles:",
            "rel_moc": "- Topic MOC:", "rel_books": "- Related books:",
            "quoted": "Quoted Tweet", "sep": " | ", "method_val": f"fxtwitter API ({body_meta})",
            "source_header": "Source Info",
        }
    else:
        L = {
            "source": "来源", "method": "抓取方式", "metrics": "元数据",
            "summary": "摘要", "summary_hint": "<!-- AI 补充：1 句话 30-80 字浓缩 -->",
            "content": "原文", "translation": "中文译文",
            "translation_hint": "<!-- 如需翻译，对 AI 说「翻译这篇」 -->",
            "thoughts": "我的看法", "thoughts_hint": "<!-- 留空给用户后续手写 -->",
            "related": "关联", "rel_articles": "- 相关文章：",
            "rel_moc": "- 主题 MOC：", "rel_books": "- 关联书目：",
            "quoted": "引用 / 嵌套推文", "sep": " ｜ ", "method_val": f"fxtwitter API（{body_meta}）",
            "source_header": "来源信息",
        }

    translation_section = ""
    if lang != "zh":
        translation_section = (
            f"\n## {L['translation']}\n\n"
            f"{L['translation_hint']}\n"
        )

    quoted = tweet.get("quote") or {}
    quoted_section = ""
    if quoted:
        qa = quoted.get("author", {})
        qtext = (quoted.get("text") or "").strip()
        quoted_section = (
            f"\n## {L['quoted']}\n\n"
            f"> [@{qa.get('screen_name','')}]({quoted.get('url','')}){L['sep']}{qa.get('name','')}\n\n"
            f"{qtext}\n"
        )

    doc = f"""{fm}

# {title_raw}

> [!source]- {L['source_header']}
> **{L['source']}**{L['sep']}[@{handle}]({tweet['url']}){L['sep']}{published_at_str} CST
> **{L['method']}**{L['sep']}{L['method_val']}
> **{L['metrics']}**{L['sep']}{metrics_line}

## {L['summary']}

{preserved.get('summary') or L['summary_hint']}

## {L['content']}

{body}
{translation_section}{quoted_section}
<div class="no-print">

## {L['thoughts']}

{L['thoughts_hint']}

## {L['related']}

{L['rel_articles']}
{L['rel_moc']}
{L['rel_books']}

</div>
"""

    # write
    year_dir = article_root / str(dt_cst.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    if existing and args.force:
        out_path = existing
    else:
        out_path = year_dir / filename
        if out_path.exists():
            out_path = year_dir / f"{filename[:-3]}-{status_id[-6:]}.md"
    out_path.write_text(doc, encoding="utf-8")

    rel = out_path.relative_to(vault)
    print(f"✓ Archived: {rel}")
    print(
        f"  Type: {'X Article' if is_article else ('thread (' + str(len(chain)) + ')' if len(chain) > 1 else 'tweet')}"
    )
    print(f"  Author: @{handle} ({tweet['author'].get('name','')})")
    print(f"  Published: {published_at_str} CST")
    print(f"  Language: {lang}")
    print(f"  Content length: {len(body):,} chars")
    print(f"  Media: {len(media)}")
    print(f"  Metrics: {metrics_line}")
    print()
    print("👉 Next step (AI):")
    print(f"   1. Open {rel}")
    print(f"   2. Fill '## Summary' (30-80 chars)")
    print(f"   3. Fill frontmatter topics / people")
    if lang != "zh":
        print(f"   4. (Optional) Fill '## Translation' if user asks")


if __name__ == "__main__":
    main()
