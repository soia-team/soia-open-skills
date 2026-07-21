#!/usr/bin/env python3
"""
archive_rednote.py — Archive a single Xiaohongshu (rednote / 小红书) note into
an Obsidian vault.

Data source: the note's own server-side-rendered detail page
(`window.__INITIAL_STATE__`), fetched with a plain stdlib HTTP GET — no
login, no cookies, no third-party API required for public notes.

Usage:
    python3 archive_rednote.py <rednote share URL>
    python3 archive_rednote.py <URL> --force                # overwrite if already archived
    python3 archive_rednote.py <URL> --vault /path/to/vault # override vault path
    python3 archive_rednote.py <URL> --articles-dir <articles-subdir>
    python3 archive_rednote.py <URL> --metadata-only         # skip video/image download

The URL MUST be a full share link copied from Xiaohongshu's own 分享 button
("复制链接"), including its `xsec_token` query parameter — a stripped or
hand-typed URL missing that token will not render the real note.

Environment variables (alternative to --vault):
    OBSIDIAN_VAULT     Path to your Obsidian vault
    OBSIDIAN_ARTICLES  Subdirectory within vault for archived articles
                       (defaults to "Articles")
    XHS_COOKIE         Optional login cookie, only needed for notes that
                       require an authenticated session to render fully.
                       Never printed or logged.

Private config is auto-loaded from SOIA_PKM_CLIP_REDNOTE_CONFIG_FILE or the
skill-specific config.yml. Do not store secrets in the vault or committed
skill repo.

Downloaded video/image binaries are saved outside the vault, under
~/Downloads/soia-pkm-clip-rednote/<note_id>/ — the vault note only records
that path in its `media_local_path` frontmatter field.
"""
from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from clip_rednote_env import env_source_hint, load_private_env

CST = timezone(timedelta(hours=8))

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
REFERER = "https://www.xiaohongshu.com/"

NOTE_ID_PATTERNS = [
    re.compile(r"/explore/([0-9a-zA-Z]+)"),
    re.compile(r"/discovery/item/([0-9a-zA-Z]+)"),
    re.compile(r"[?&]note_id=([0-9a-zA-Z]+)"),
]

# Hosts this skill is allowed to fetch. Required before any request is made
# with args.url: unlike soia-pkm-clip-x (which only ever extracts an id from
# the input URL and then fetches a fixed, trusted API host), this skill has
# no such proxy — it fetches the user-supplied URL directly, and (per
# fetch_note_html) attaches XHS_COOKIE to that request when configured. An
# unvalidated host here is a real credential-exfiltration vector: a URL like
# "https://attacker.example/explore/x?note_id=x" matches the id regexes fine
# and would otherwise send the user's real Xiaohongshu session cookie to
# attacker.example. Checked with urllib.parse.urlparse(...).hostname
# (authority-based, not a substring/regex match on the raw URL string, so it
# can't be bypassed by embedding an allowed hostname elsewhere in the URL).
ALLOWED_HOST_SUFFIXES = ("xiaohongshu.com", "xhslink.com")


def validate_host(url: str) -> None:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if any(host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_HOST_SUFFIXES):
        return
    print(f"❌ 不是小红书链接（host={host or '(无法解析)'}）：{url}", file=sys.stderr)
    print("   本技能只抓取 xiaohongshu.com / xhslink.com 域名下的链接，拒绝抓取其他主机", file=sys.stderr)
    sys.exit(1)

DEFAULT_ARTICLES_DIR = "Articles"
FALLBACK_ARTICLES_WARNING = (
    "WARN: 未找到 articles 目录配置（--articles-dir / OBSIDIAN_ARTICLES / config.yml），"
    "已落默认 Articles/——该目录不是本 vault 的正式归档位，请确认或配置"
)

DOWNLOAD_ROOT = Path.home() / "Downloads" / "soia-pkm-clip-rednote"


# ---------------------------------------------------------------------------
# Vault / articles-dir resolution (same shape as soia-pkm-clip-x's archive_x.py)
# ---------------------------------------------------------------------------


def looks_like_vault(path: Path) -> bool:
    return (path / ".obsidian").is_dir() or (path / "AGENTS.md").is_file()


def discover_vault_from_cwd() -> Path | None:
    """Find a vault by walking up from the current working directory.

    Many AI CLIs run non-login shells, so shell startup exports may be
    absent. When the agent is already inside the vault, cwd-based discovery
    is more reliable than asking it to rediscover shell startup behavior.
    """
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if looks_like_vault(p):
            return p
    return None


def resolve_vault(cli_vault: str | None) -> Path:
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
                print(f"   Private env sources checked: {env_source_hint()}.", file=sys.stderr)
                sys.exit(1)
            print(f"ℹ️  Auto-detected vault from cwd: {p}", file=sys.stderr)
    if not p.exists() or not p.is_dir():
        print(f"❌ Vault path does not exist: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def resolve_article_root(vault: Path, cli_articles_dir: str | None = None) -> Path:
    sub = cli_articles_dir or os.environ.get("OBSIDIAN_ARTICLES")
    if sub:
        return vault / sub
    print(FALLBACK_ARTICLES_WARNING, file=sys.stderr)
    return vault / DEFAULT_ARTICLES_DIR


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


def parse_note_id(url: str) -> str:
    for pattern in NOTE_ID_PATTERNS:
        m = pattern.search(url.strip())
        if m:
            return m.group(1)
    print(f"❌ 无法从链接中解析笔记 ID：{url}", file=sys.stderr)
    print("   请从小红书 App「分享」→「复制链接」粘贴完整链接（需包含 xsec_token）", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Fetch + parse window.__INITIAL_STATE__
# ---------------------------------------------------------------------------


def fetch_note_html(url: str, timeout: int = 20) -> str:
    headers = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    cookie = os.environ.get("XHS_COOKIE")
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            content_encoding = r.headers.get("Content-Encoding", "")
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}：请求笔记页面失败 {url}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
    if content_encoding == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    return raw.decode("utf-8", errors="replace")


def extract_initial_state(html_text: str) -> dict | None:
    marker = "window.__INITIAL_STATE__"
    idx = html_text.find(marker)
    if idx == -1:
        return None
    eq_idx = html_text.find("=", idx + len(marker))
    if eq_idx == -1:
        return None
    end_idx = html_text.find("</script>", eq_idx)
    if end_idx == -1:
        return None
    blob = html_text[eq_idx + 1:end_idx].strip()
    if blob.endswith(";"):
        blob = blob[:-1].rstrip()
    blob = html.unescape(blob)
    blob = re.sub(r"\bundefined\b", "null", blob)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def find_note_detail_map(obj) -> dict | None:
    """Recursively search a parsed __INITIAL_STATE__ object for a dict
    containing the key 'noteDetailMap'.
    """
    if isinstance(obj, dict):
        candidate = obj.get("noteDetailMap")
        if isinstance(candidate, dict):
            return candidate
        for v in obj.values():
            found = find_note_detail_map(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_note_detail_map(item)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------


def safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def collect_video_candidates(note: dict) -> list[str]:
    """h264 masterUrl/backupUrls first, then h265/av1 as further fallbacks."""
    video = note.get("video") or {}
    media = video.get("media") or {}
    stream = media.get("stream") or {}
    candidates: list[str] = []
    for codec in ("h264", "h265", "av1"):
        items = stream.get(codec) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            master = item.get("masterUrl")
            if master:
                candidates.append(master)
            for backup in item.get("backupUrls") or []:
                if backup:
                    candidates.append(backup)
    return candidates


def collect_image_urls(note: dict) -> list[str]:
    urls: list[str] = []
    for item in note.get("imageList") or []:
        if not isinstance(item, dict):
            continue
        url = item.get("urlDefault") or item.get("url") or item.get("urlPre")
        if url:
            urls.append(url)
    return urls


# ---------------------------------------------------------------------------
# Media download
# ---------------------------------------------------------------------------


def download_file(url: str, dest: Path, referer: str, timeout: int = 30) -> tuple[bool, str | None]:
    headers = {"User-Agent": UA, "Referer": referer}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    except OSError as e:
        return False, f"write failed: {e}"
    return True, None


def guess_ext(url: str, default: str = "jpg") -> str:
    try:
        path = urllib.parse.urlparse(url).path
    except ValueError:
        return default
    ext = Path(path).suffix.lstrip(".").lower()
    if ext and re.fullmatch(r"[a-z0-9]{1,5}", ext):
        return ext
    return default


def try_download_video(candidates: list[str], dest: Path) -> Path | None:
    for i, url in enumerate(candidates, 1):
        ok, err = download_file(url, dest, REFERER)
        if ok:
            print(f"  ✓ 视频已下载（候选 {i}/{len(candidates)}）: {dest}", file=sys.stderr)
            return dest
        print(f"  ⚠️ 视频候选直链 {i}/{len(candidates)} 下载失败（{err}）", file=sys.stderr)
    if candidates:
        print("  ⚠️ 视频下载失败：所有候选直链均不可用（签名可能已过期，可重新运行脚本获取新直链）", file=sys.stderr)
    return None


def download_images(urls: list[str], images_dir: Path) -> list[Path]:
    saved: list[Path] = []
    for i, url in enumerate(urls, 1):
        dest = images_dir / f"{i:02d}.{guess_ext(url)}"
        ok, err = download_file(url, dest, REFERER)
        if ok:
            saved.append(dest)
        else:
            print(f"  ⚠️ 图片 {i}/{len(urls)} 下载失败（{err}）", file=sys.stderr)
    return saved


# ---------------------------------------------------------------------------
# Dedup / preserved-fields (same mechanism as archive_x.py)
# ---------------------------------------------------------------------------


def find_existing_archive(article_root: Path, note_id: str) -> Path | None:
    if not article_root.exists():
        return None
    id_pattern = re.compile(rf"(?:/|=){re.escape(note_id)}(?:[/?&\"'\s]|$)")
    for f in article_root.rglob("*.md"):
        if "_template" in f.parts or "_templates" in f.parts or "_MOC" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r"^url:\s*(.+)$", text, re.MULTILINE)
        if m and id_pattern.search(m.group(1)):
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


# ---------------------------------------------------------------------------
# Filename
# ---------------------------------------------------------------------------


def sanitize_for_filename(text: str, limit: int = 50) -> str:
    text = text or ""
    # filesystem-illegal chars + separator-like punctuation (colon/semicolon,
    # half- and full-width) — replace with a dash rather than deleting
    text = re.sub(r'[/\\:*?"<>|：；;]+', "-", text)
    # wrapping punctuation (brackets/quotes) — safe to strip
    text = re.sub(r"[（）()\[\]【】.,，。！!?？\"'“”‘’]+", "", text)
    # emoji (supplementary plane)
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:limit].rstrip("-")


# ---------------------------------------------------------------------------
# Frontmatter + body
# ---------------------------------------------------------------------------


def build_frontmatter(
    url: str,
    author: str,
    published_at_str: str,
    captured_at_str: str,
    fm_type: str,
    media_local_path: str,
    counts: dict,
    metrics_hidden: bool,
    preserved: dict,
) -> str:
    lines = [
        "---",
        "tags: [视频摘抄]",
        "source: 小红书",
        f"url: {url}",
        f"author: {author}",
        f"published_at: {published_at_str}",
        f"captured_at: {captured_at_str}",
        "language: zh",
        f"type: {fm_type}",
        preserved.get("topics") or "topics: []",
        preserved.get("people") or "people: []",
        f'media_local_path: "{media_local_path}"',
        "content_complete: true",
        "metrics:",
        f"  likes: {counts['likes']}",
        f"  collects: {counts['collects']}",
        f"  comments: {counts['comments']}",
        f"  shares: {counts['shares']}",
    ]
    if metrics_hidden:
        lines.append("  # 互动数据未公开（原始字段为空/未公开，未当作 0 呈现）")
    lines.append("---")
    return "\n".join(lines)


def main():
    load_private_env()

    ap = argparse.ArgumentParser(description="Archive a Xiaohongshu (rednote) note into Obsidian vault.")
    ap.add_argument("url", nargs="?", help="rednote share URL (xiaohongshu.com/explore/... with xsec_token)")
    ap.add_argument("--force", action="store_true", help="Force re-archive even if already exists")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT env)")
    ap.add_argument("--articles-dir", help="Article archive dir relative to vault (overrides OBSIDIAN_ARTICLES)")
    ap.add_argument("--metadata-only", action="store_true", help="Fetch metadata + text only, skip video/image download")
    args = ap.parse_args()

    if not args.url:
        ap.print_help()
        sys.exit(1)

    # Reject non-Xiaohongshu hosts before any parsing or network request —
    # args.url is fetched directly (and, when XHS_COOKIE is set, that cookie
    # is attached to the request), so an unvalidated host here would send
    # the user's real login cookie to whatever host the input happens to
    # point at. See ALLOWED_HOST_SUFFIXES / validate_host for detail.
    validate_host(args.url)

    vault = resolve_vault(args.vault)
    article_root = resolve_article_root(vault, args.articles_dir)

    note_id = parse_note_id(args.url)

    existing = find_existing_archive(article_root, note_id)
    if existing and not args.force:
        rel = existing.relative_to(vault)
        print(f"⚠️  Already archived: {rel}", file=sys.stderr)
        print(f"   Note ID: {note_id}", file=sys.stderr)
        print("   Use --force to re-archive (will overwrite topics/people)", file=sys.stderr)
        print(f"SKIP: {rel}")
        sys.exit(0)

    if existing and args.force:
        print(f"⚠️  Force-overwriting: {existing.relative_to(vault)}", file=sys.stderr)

    preserved = extract_preserved_fields(existing)

    print(f"📖 Fetching rednote note {note_id}", file=sys.stderr)
    html_text = fetch_note_html(args.url)
    state = extract_initial_state(html_text)
    if state is None:
        print("❌ 页面里没有找到 __INITIAL_STATE__，笔记可能需要有效登录态或 xsec_token 已失效", file=sys.stderr)
        print("   可尝试：重新从 App 复制最新分享链接；或设置 XHS_COOKIE 后重试", file=sys.stderr)
        sys.exit(2)

    note_detail_map = find_note_detail_map(state)
    entry = (note_detail_map or {}).get(note_id) if isinstance(note_detail_map, dict) else None
    note = entry.get("note") if isinstance(entry, dict) else None
    if not isinstance(note, dict):
        print(f"❌ 页面数据里没有找到笔记 {note_id}，可能 xsec_token 已失效或笔记需要登录态", file=sys.stderr)
        print("   可尝试：重新从 App 复制最新分享链接；或设置 XHS_COOKIE 后重试", file=sys.stderr)
        sys.exit(2)

    title = (note.get("title") or "").strip() or f"小红书笔记-{note_id}"
    desc = note.get("desc") or ""
    note_type_raw = note.get("type") or "normal"
    fm_type = "video" if note_type_raw == "video" else "image"
    author = ((note.get("user") or {}).get("nickname") or "").strip() or "未知作者"

    ts_ms = note.get("time") or 0
    dt_cst = (
        datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone(CST)
        if ts_ms
        else datetime.now(CST)
    )
    published_at_str = dt_cst.strftime("%Y-%m-%d %H:%M")
    captured_at_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M")

    tags = [
        t.get("name") for t in (note.get("tagList") or [])
        if isinstance(t, dict) and t.get("name")
    ]

    interact = note.get("interactInfo") or {}
    counts = {
        "likes": safe_int(interact.get("likedCount")),
        "collects": safe_int(interact.get("collectedCount")),
        "comments": safe_int(interact.get("commentCount")),
        "shares": safe_int(interact.get("shareCount")),
    }
    metrics_hidden = sum(counts.values()) == 0

    # --- media ---
    note_dir = DOWNLOAD_ROOT / note_id
    video_candidates = collect_video_candidates(note) if fm_type == "video" else []
    image_urls = collect_image_urls(note)

    video_path: Path | None = None
    image_paths: list[Path] = []

    if not args.metadata_only:
        if video_candidates:
            video_path = try_download_video(video_candidates, note_dir / "video.mp4")
        if image_urls:
            image_paths = download_images(image_urls, note_dir / "images")

    # video_path/image_paths only reflect THIS run's fresh download attempt.
    # On a --force re-archive, the signed video URL may have expired since
    # the note was first archived (SKILL.md documents this as expected —
    # the URL carries a short-lived signature) while the earlier download
    # is still sitting untouched on disk at note_dir. Falling back to
    # "media_local_path = ''" in that case would falsely claim media was
    # never fetched and silently drop a still-valid local pointer, even
    # though nothing was deleted. Check what's actually on disk before
    # concluding there's nothing to point at.
    has_existing_media = (note_dir / "video.mp4").is_file() or (
        (note_dir / "images").is_dir() and any((note_dir / "images").iterdir())
    )
    media_local_path = str(note_dir) if (video_path or image_paths or has_existing_media) else ""

    media_incomplete = (not args.metadata_only) and (
        (fm_type == "video" and video_candidates and not video_path)
        or (image_urls and not image_paths)
    )
    show_candidates = args.metadata_only or media_incomplete

    fm = build_frontmatter(
        args.url, author, published_at_str, captured_at_str, fm_type,
        media_local_path, counts, metrics_hidden, preserved,
    )

    if metrics_hidden:
        metrics_line = "互动数据未公开"
    else:
        metrics_line = (
            f"👍 {counts['likes']:,} · ⭐ {counts['collects']:,} · "
            f"💬 {counts['comments']:,} · 🔁 {counts['shares']:,}"
        )

    type_zh = "视频" if fm_type == "video" else "图集"
    if args.metadata_only:
        media_note = "未下载（--metadata-only）"
    elif fm_type == "video":
        media_note = "视频已下载" if video_path else ("视频下载失败" if video_candidates else "未找到视频直链")
    else:
        media_note = (
            f"已下载 {len(image_paths)}/{len(image_urls)} 张" if image_urls
            else "未找到图片直链"
        )
    method_val = f"stdlib HTTP + __INITIAL_STATE__ 解析（{type_zh}，{media_note}）"

    tags_line = ""
    if tags:
        tags_line = f"\n> **标签**｜{' '.join('#' + t for t in tags)}"

    candidates_section = ""
    if show_candidates:
        cand_urls = ([video_candidates[0]] if video_candidates else []) + image_urls
        if cand_urls:
            candidates_section = (
                "\n## 媒体候选（未下载）\n\n"
                + "\n".join(f"- {u}" for u in cand_urls)
                + "\n"
            )

    doc = f"""{fm}

# {title}

> [!source]- 来源信息
> **来源**｜[笔记链接]({args.url})｜{author}｜{published_at_str} CST
> **抓取方式**｜{method_val}
> **元数据**｜{metrics_line}{tags_line}

## 摘要

{preserved.get('summary') or '<!-- AI 补充：1 句话 30-80 字浓缩 -->'}

## 原文

{desc}
{candidates_section}
## 我的看法

<!-- 留空给用户后续手写 -->

## 关联

- 相关文章：
- 关联书目：
"""

    # write
    year_dir = article_root / str(dt_cst.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    if existing and args.force:
        out_path = existing
    else:
        fn_title = sanitize_for_filename(title, 50)
        fn_author = sanitize_for_filename(author, 20)
        filename = f"{dt_cst.strftime('%Y-%m-%d')}-rednote-{fn_author}-{fn_title}.md"
        out_path = year_dir / filename
        if out_path.exists():
            out_path = year_dir / f"{filename[:-3]}-{note_id[-6:]}.md"
    out_path.write_text(doc, encoding="utf-8")

    rel = out_path.relative_to(vault)
    print(f"✓ Archived: {rel}")
    print(f"  Type: {type_zh}")
    print(f"  Author: {author}")
    print(f"  Published: {published_at_str} CST")
    print("  Language: zh")
    print(f"  Media path: {media_local_path or '(未下载)'}")
    print(f"  Metrics: {metrics_line}")
    print()
    print("👉 Next step (AI):")
    print(f"   1. Open {rel}")
    print("   2. Fill '## 摘要' (30-80 字)")
    print("   3. Fill frontmatter topics / people")
    if show_candidates:
        print("   4. 媒体未完整下载：如需重试，重新运行脚本（直链带签名，可能已过期）")


if __name__ == "__main__":
    main()
