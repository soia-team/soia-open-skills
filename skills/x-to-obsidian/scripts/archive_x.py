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
    r"https?://(?:mobile\.)?(?:x|twitter|fxtwitter)\.com/([^/]+)/status/(\d+)",
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


def render_article_blocks(blocks: list[dict]) -> str:
    out: list[str] = []
    for b in blocks:
        text = (b.get("text") or "").rstrip()
        typ = b.get("type", "unstyled")
        if not text and typ == "unstyled":
            continue
        if typ == "header-two":
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
    # filesystem-illegal chars
    title = re.sub(r'[/\\:*?"<>|]+', "-", title)
    # punctuation
    title = re.sub(
        r"[（）()\[\]【】.,，。！!?？:：;；\"'""'']+", "", title
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


def build_frontmatter(
    tweet: dict,
    chain: list[dict],
    is_article: bool,
    captured_at_str: str,
    published_at_str: str,
    media: list[dict],
    lang: str,
) -> str:
    author = tweet["author"]
    article = tweet.get("article") or {}
    quoted = tweet.get("quote") or {}

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
        "topics: []",
        "people: []",
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
        blocks = article.get("content", {}).get("blocks", [])
        body = render_article_blocks(blocks)
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
        tweet, chain, is_article, captured_at_str, published_at_str, media, lang
    )

    metrics_line = (
        f"👁 {tweet.get('views',0):,} · "
        f"❤ {tweet.get('likes',0):,} · "
        f"🔖 {tweet.get('bookmarks',0):,}"
    )

    translation_section = ""
    if lang != "zh":
        translation_section = (
            "\n## Translation\n\n"
            "<!-- Ask your AI agent to translate if needed -->\n"
        )

    quoted = tweet.get("quote") or {}
    quoted_section = ""
    if quoted:
        qa = quoted.get("author", {})
        qtext = (quoted.get("text") or "").strip()
        quoted_section = (
            f"\n## Quoted Tweet\n\n"
            f"> [@{qa.get('screen_name','')}]({quoted.get('url','')}) | {qa.get('name','')}\n\n"
            f"{qtext}\n"
        )

    doc = f"""{fm}

# {title_raw}

> **Source** | [@{handle}]({tweet['url']}) | {published_at_str} CST
> **Method** | fxtwitter API ({body_meta})
> **Metrics** | {metrics_line}

## Summary

<!-- AI: fill 1-sentence summary, 30-80 chars -->

## Content

{body}
{translation_section}{quoted_section}
## My Thoughts

<!-- Left blank for the user -->

## Related

- Related articles:
- Topic MOC:
- Related books:
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
