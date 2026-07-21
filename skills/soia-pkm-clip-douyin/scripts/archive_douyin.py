#!/usr/bin/env python3
"""
archive_douyin.py — Archive a single Douyin (抖音) video into an Obsidian vault.

Data source: Douyin's own signed web API, reached via a real Playwright
Chromium session (there is no stdlib-only way to call it — the play URL is
protected by client-generated msToken/a_bogus signing). Once the signed video
URL is extracted, the actual MP4 download is a plain stdlib HTTP GET.

Usage:
    python3 archive_douyin.py <Douyin URL>
    python3 archive_douyin.py <Douyin URL> --force                # Force overwrite if archived
    python3 archive_douyin.py <Douyin URL> --vault /path/to/vault # Override vault path
    python3 archive_douyin.py <Douyin URL> --articles-dir <articles-subdir>
    python3 archive_douyin.py <Douyin URL> --metadata-only        # Skip video download

Environment variables (alternative to --vault):
    OBSIDIAN_VAULT     Path to your Obsidian vault
    OBSIDIAN_ARTICLES  Subdirectory within vault for archived articles
                       (defaults to "Articles")

Private config is auto-loaded from SOIA_PKM_CLIP_DOUYIN_CONFIG_FILE or the
skill-specific config.yml. Do not store secrets in the vault or committed
skill repo.

Dependencies:
    pip install playwright && python -m playwright install chromium
    (only required for the fetch step; the download step is pure stdlib)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from clip_douyin_env import env_source_hint, load_private_env

CST = timezone(timedelta(hours=8))

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

ID_PATTERNS = [
    re.compile(r"/video/(\d+)"),
    re.compile(r"modal_id=(\d+)"),
    re.compile(r"resource_id=(\d+)"),
]

DEFAULT_ARTICLES_DIR = "Articles"
FALLBACK_ARTICLES_WARNING = (
    "WARN: 未找到 articles 目录配置（--articles-dir / OBSIDIAN_ARTICLES / config.yml），"
    "已落默认 Articles/——该目录不是本 vault 的正式归档位，请确认或配置"
)

DEFAULT_TIMEOUT_S = 60


# ---------------------------------------------------------------------------
# Vault / article-dir resolution (mirrors soia-pkm-clip-x/scripts/archive_x.py)
# ---------------------------------------------------------------------------


def looks_like_vault(path: Path) -> bool:
    return (path / ".obsidian").is_dir() or (path / "AGENTS.md").is_file()


def discover_vault_from_cwd() -> Path | None:
    """Find a vault by walking up from the current working directory.

    Many AI CLIs run non-login shells, so shell startup exports may be absent. When
    the agent is already inside the vault, cwd-based discovery is more reliable
    than asking it to rediscover shell startup behavior.
    """
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if looks_like_vault(p):
            return p
    return None


def resolve_vault(cli_vault: str | None) -> Path:
    """Resolve the vault path from CLI arg, env var, or cwd discovery."""
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
# URL / video-id handling
# ---------------------------------------------------------------------------


def extract_video_id_from_text(url: str) -> str | None:
    for pattern in ID_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1)
    return None


def resolve_short_link(url: str, timeout: int = 15) -> str | None:
    """Best-effort redirect resolution for v.douyin.com-style short links.

    The three documented ID patterns only match a canonical or modal URL.
    Short links carry no numeric id in the URL text itself, so we need one
    plain HTTP round trip to follow the redirect chain before regex can work.
    """
    req = urllib.request.Request(url, headers={"User-Agent": DESKTOP_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.geturl()
    except Exception:
        return None


def parse_video_id(url: str) -> str:
    url = url.strip()
    vid = extract_video_id_from_text(url)
    if vid:
        return vid
    resolved = resolve_short_link(url)
    if resolved:
        vid = extract_video_id_from_text(resolved)
        if vid:
            return vid
    print(f"❌ 无法识别的抖音链接格式: {url}", file=sys.stderr)
    print(
        "   支持格式：https://www.douyin.com/video/<id> ・ 带 modal_id=<id> 或 "
        "resource_id=<id> 参数的链接 ・ v.douyin.com 短链（会尝试自动解析重定向）",
        file=sys.stderr,
    )
    sys.exit(1)


def normalize_url(video_id: str) -> str:
    return f"https://www.douyin.com/video/{video_id}"


# ---------------------------------------------------------------------------
# Playwright fetch — signed API interception
# ---------------------------------------------------------------------------


def find_aweme_in_json(obj, target_id: str):
    """Recursively search a parsed JSON response body for the aweme object.

    Content-based, not endpoint-based: any dict that has
    str(aweme_id) == target_id AND carries a "video" key is a positive match,
    regardless of which endpoint or list (e.g. an aweme_list[] from a mix/
    listing endpoint) happened to carry it.
    """
    if isinstance(obj, dict):
        if str(obj.get("aweme_id", "")) == target_id and "video" in obj:
            return obj
        for value in obj.values():
            found = find_aweme_in_json(value, target_id)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_aweme_in_json(item, target_id)
            if found is not None:
                return found
    return None


def fetch_aweme_via_playwright(
    video_id: str, timeout_s: int = DEFAULT_TIMEOUT_S, headless: bool = True
) -> dict | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖 playwright。", file=sys.stderr)
        print("   安装：pip install playwright && python -m playwright install chromium", file=sys.stderr)
        sys.exit(5)

    result: dict = {}

    def handle_response(response) -> None:
        if "aweme" in result:
            return
        try:
            url = response.url
        except Exception:
            return
        if "douyin.com" not in url:
            return
        try:
            content_type = response.headers.get("content-type", "")
        except Exception:
            content_type = ""
        if "json" not in content_type:
            return
        try:
            body = response.json()
        except Exception:
            return
        found = find_aweme_in_json(body, video_id)
        if found is not None:
            result["aweme"] = found

    print(f"🌐 打开 Playwright headless Chromium，拦截视频数据 aweme_id={video_id} …", file=sys.stderr)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(user_agent=DESKTOP_UA, locale="zh-CN")
            page = context.new_page()
            page.on("response", handle_response)
            target_url = normalize_url(video_id)
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            except Exception as exc:
                print(f"  ⚠️ 页面导航异常（继续轮询响应拦截结果）: {type(exc).__name__}: {exc}", file=sys.stderr)

            elapsed_ms = 0
            interval_ms = 1000
            while "aweme" not in result and elapsed_ms < timeout_s * 1000:
                page.wait_for_timeout(interval_ms)
                elapsed_ms += interval_ms
        finally:
            browser.close()

    return result.get("aweme")


# ---------------------------------------------------------------------------
# Video download (stdlib)
# ---------------------------------------------------------------------------


def collect_download_candidates(aweme: dict) -> list[str]:
    video = aweme.get("video") or {}
    candidates: list[str] = []
    for key in ("play_addr", "play_addr_h264", "download_addr"):
        addr = video.get(key) or {}
        for u in addr.get("url_list") or []:
            if u and u not in candidates:
                candidates.append(u)
    return candidates


def redact_url(u: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(u)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path} (query 已省略，含签名 token)"
    except Exception:
        return "<unparseable url>"


def looks_like_mp4(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            header = f.read(12)
    except OSError:
        return False
    return len(header) >= 8 and header[4:8] == b"ftyp"


def download_video(url: str, dest_path: Path, timeout: int = 60) -> int:
    """Download one candidate URL to dest_path. Returns byte count written.

    Raises on any failure (HTTP error, empty body, size mismatch, bad magic
    bytes) so the caller can move on to the next candidate.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DESKTOP_UA,
            "Referer": "https://www.douyin.com/",
            "Range": "bytes=0-",
        },
    )
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", None) or resp.getcode()
        if status not in (200, 206):
            raise RuntimeError(f"HTTP {status}")
        content_length = resp.getheader("Content-Length")
        expected = int(content_length) if content_length else None
        downloaded = 0
        chunk_size = 256 * 1024
        last_reported_pct = -1
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if expected:
                    pct = int(downloaded / expected * 100)
                    if pct >= last_reported_pct + 10:
                        print(f"  ⬇️ {pct}% ({downloaded/1024/1024:.1f}MB)", file=sys.stderr)
                        last_reported_pct = pct
                elif downloaded % (chunk_size * 20) < chunk_size:
                    print(f"  ⬇️ {downloaded/1024/1024:.1f}MB", file=sys.stderr)

    if downloaded == 0:
        raise RuntimeError("下载内容为空（0 字节）")
    if expected is not None and downloaded != expected:
        raise RuntimeError(f"字节数不匹配：下载 {downloaded}，Content-Length {expected}")
    if not looks_like_mp4(dest_path):
        raise RuntimeError("文件头不是有效的 MP4（缺少 ftyp box）")
    return downloaded


def download_first_working(candidates: list[str], dest_path: Path, timeout: int = 60):
    """Try each candidate URL in priority order. Returns (bytes, url) or (None, attempts)."""
    attempts: list[tuple[str, str]] = []
    for i, url in enumerate(candidates, 1):
        print(f"⬇️  尝试候选直链 [{i}/{len(candidates)}] …", file=sys.stderr)
        try:
            size = download_video(url, dest_path, timeout=timeout)
            return size, url
        except Exception as exc:
            attempts.append((redact_url(url), f"{type(exc).__name__}: {exc}"))
            if dest_path.exists():
                try:
                    dest_path.unlink()
                except OSError:
                    pass
    return None, attempts


# ---------------------------------------------------------------------------
# Dedup / preserved-fields (mirrors archive_x.py's mechanism)
# ---------------------------------------------------------------------------


def find_existing_archive(article_root: Path, video_id: str) -> Path | None:
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
        # The stored url: is args.url verbatim, which may be a /video/<id>
        # link, a modal_id=/resource_id= link, or a resolved short link —
        # there's no single fixed prefix to anchor on (unlike archive_x.py's
        # f"/status/{status_id}", which archive_x.py can rely on because X
        # URLs always take that one shape). A bare substring test would
        # false-positive when video_id is a digit-run inside an unrelated
        # stored URL (another video's longer id, or a query value that
        # happens to contain these digits) — require non-digit boundaries
        # on both sides instead, which stays format-agnostic while still
        # ruling out that false-positive class.
        if m and re.search(rf"(?<!\d){re.escape(video_id)}(?!\d)", m.group(1)):
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

    m = re.search(r"##\s*摘要\s*\n\n(.*?)\n\n##", text, re.DOTALL)
    if m:
        body = m.group(1).strip()
        if body and not body.startswith("<!--"):
            preserved["summary"] = body

    return preserved


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def sanitize_title_for_filename(title: str, limit: int = 50) -> str:
    title = re.sub(r'[/\\:*?"<>|：；;]+', "-", title)
    title = re.sub(r"[（）()\[\]【】.,，。！!?？\"'""'']+", "", title)
    title = re.sub(r"[\U00010000-\U0010ffff]", "", title)
    title = re.sub(r"\s+", "-", title.strip())
    title = re.sub(r"-+", "-", title)
    return title[:limit].rstrip("-")


def format_duration(ms: int) -> str:
    if not ms:
        return "0:00"
    total_seconds = int(ms / 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def build_frontmatter(
    aweme: dict,
    url_given: str,
    published_at_str: str,
    captured_at_str: str,
    media_local_path: str,
    metadata_only: bool,
    preserved: dict | None = None,
) -> str:
    preserved = preserved or {}
    author = aweme.get("author") or {}
    stats = aweme.get("statistics") or {}

    lines = [
        "---",
        "tags: [视频摘抄]",
        "source: 抖音",
        f"url: {url_given}",
        f"author: {author.get('nickname', '')}",
        f"published_at: {published_at_str}",
        f"captured_at: {captured_at_str}",
        "language: zh",
        "type: video",
        preserved.get("topics") or "topics: []",
        preserved.get("people") or "people: []",
        f'media_local_path: "{media_local_path}"',
        "content_complete: true",
        "metrics:",
        f"  likes: {stats.get('digg_count', 0)}",
        f"  comments: {stats.get('comment_count', 0)}",
        f"  collects: {stats.get('collect_count', 0)}",
        f"  shares: {stats.get('share_count', 0)}",
        f"  plays: {stats.get('play_count', 0)}",
        f"  admires: {stats.get('admire_count', 0)}",
        f"  recommends: {stats.get('recommend_count', 0)}",
        "---",
    ]
    if metadata_only:
        lines.insert(-1, "media_fetched: false")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    load_private_env()

    ap = argparse.ArgumentParser(description="Archive a Douyin video into an Obsidian vault.")
    ap.add_argument("url", nargs="?", help="Douyin URL (www.douyin.com/video/<id> or v.douyin.com short link)")
    ap.add_argument("--force", action="store_true", help="Force re-archive even if already exists")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT env)")
    ap.add_argument("--articles-dir", help="Article archive dir relative to vault (overrides OBSIDIAN_ARTICLES)")
    ap.add_argument(
        "--metadata-only",
        action="store_true",
        help="Fetch metadata + caption text only; skip downloading the video file",
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        help=f"Seconds to wait for the signed aweme response before giving up (default: {DEFAULT_TIMEOUT_S})",
    )
    args = ap.parse_args()

    if not args.url:
        ap.print_help()
        sys.exit(1)

    vault = resolve_vault(args.vault)
    article_root = resolve_article_root(vault, args.articles_dir)

    video_id = parse_video_id(args.url)

    existing = find_existing_archive(article_root, video_id)
    if existing and not args.force:
        rel = existing.relative_to(vault)
        print(f"⚠️  Already archived: {rel}", file=sys.stderr)
        print(f"   Video ID: {video_id}", file=sys.stderr)
        print("   Use --force to re-archive (will overwrite topics/people)", file=sys.stderr)
        print(f"SKIP: {rel}")
        sys.exit(0)

    if existing and args.force:
        print(f"⚠️  Force-overwriting: {existing.relative_to(vault)}", file=sys.stderr)

    preserved = extract_preserved_fields(existing)

    aweme = fetch_aweme_via_playwright(video_id, timeout_s=args.timeout)
    if not aweme:
        print(f"❌ 超时（{args.timeout}s）未找到视频数据（aweme_id={video_id}）", file=sys.stderr)
        print(
            "   可能原因：视频已删除 / 设为私密 / 所在地区不可见，或抖音改版了接口结构。",
            file=sys.stderr,
        )
        sys.exit(3)

    author = aweme.get("author") or {}
    video_info = aweme.get("video") or {}
    desc = (aweme.get("desc") or "").strip()
    title_raw = desc.split("\n")[0].strip() if desc else f"抖音视频-{video_id}"
    nickname = author.get("nickname", "") or "未知作者"

    create_ts = aweme.get("create_time", 0)
    dt_cst = (
        datetime.fromtimestamp(create_ts, tz=timezone.utc).astimezone(CST)
        if create_ts
        else datetime.now(CST)
    )
    published_at_str = dt_cst.strftime("%Y-%m-%d %H:%M")
    captured_at_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    duration_str = format_duration(video_info.get("duration", 0))

    media_local_path = ""
    media_status_line = ""
    candidates = collect_download_candidates(aweme)

    if args.metadata_only:
        print(f"ℹ️  --metadata-only：跳过视频下载，候选下载直链 {len(candidates)} 个（未下载）", file=sys.stderr)
        media_status_line = (
            f"**媒体状态** ｜ 未下载（--metadata-only），候选直链 {len(candidates)} 个；"
            f"签名直链有效期短，如需视频请重新运行本脚本"
        )
    else:
        if not candidates:
            print("❌ 未在响应中找到任何可下载的视频直链（play_addr / play_addr_h264 / download_addr 均为空）", file=sys.stderr)
            sys.exit(4)

        download_dir = Path.home() / "Downloads" / "soia-pkm-clip-douyin" / video_id
        dest_path = download_dir / "video.mp4"
        print(f"⬇️  开始下载视频到本地（{len(candidates)} 个候选直链）…", file=sys.stderr)
        size, result = download_first_working(candidates, dest_path)
        if size is None:
            print(f"❌ 视频下载失败，已尝试全部 {len(candidates)} 个候选直链：", file=sys.stderr)
            for i, (u, err) in enumerate(result, 1):
                print(f"   [{i}] {u} -> {err}", file=sys.stderr)
            sys.exit(4)
        media_local_path = str(dest_path.resolve())
        print(f"✓ 视频已下载：{media_local_path} ({size/1024/1024:.1f}MB)", file=sys.stderr)
        media_status_line = f"**媒体状态** ｜ 已下载 · {size/1024/1024:.1f}MB · {media_local_path}"

    stats = aweme.get("statistics") or {}
    metrics_line = (
        f"❤ {stats.get('digg_count', 0):,} · "
        f"💬 {stats.get('comment_count', 0):,} · "
        f"⭐ {stats.get('collect_count', 0):,} · "
        f"🔁 {stats.get('share_count', 0):,}"
    )

    fm = build_frontmatter(
        aweme,
        args.url,
        published_at_str,
        captured_at_str,
        media_local_path,
        args.metadata_only,
        preserved=preserved,
    )

    doc = f"""{fm}

# {title_raw}

> [!source]- 来源信息
> **来源** ｜ [@{nickname}]({args.url}) ｜ {published_at_str} CST
> **抓取方式** ｜ Playwright 网络拦截（douyin.com 签名 API），时长 {duration_str}
> **元数据** ｜ {metrics_line}
> {media_status_line}

## 摘要

{preserved.get('summary') or '<!-- AI 补充：1 句话 30-80 字浓缩 -->'}

## 原文

{desc or '*（无文案）*'}

## 我的看法

<!-- 留空给用户后续手写 -->

## 关联

- 相关文章：
- 关联书目：
"""

    fn_title = sanitize_title_for_filename(title_raw, 50)
    fn_author = sanitize_title_for_filename(nickname, 20)
    filename = f"{dt_cst.strftime('%Y-%m-%d')}-抖音-{fn_author}-{fn_title}.md"

    year_dir = article_root / str(dt_cst.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    if existing and args.force:
        out_path = existing
    else:
        out_path = year_dir / filename
        if out_path.exists():
            out_path = year_dir / f"{filename[:-3]}-{video_id[-6:]}.md"
    out_path.write_text(doc, encoding="utf-8")

    rel = out_path.relative_to(vault)
    print(f"✓ Archived: {rel}")
    print("  Type: video")
    print(f"  Author: {nickname}")
    print(f"  Published: {published_at_str} CST")
    print("  Language: zh")
    print(f"  Media path: {media_local_path or '(未下载 / --metadata-only)'}")
    print(f"  Metrics: {metrics_line}")
    print()
    print("👉 Next step (AI):")
    print(f"   1. Open {rel}")
    print("   2. Fill '## 摘要' (30-80 chars)")
    print("   3. Fill frontmatter topics / people")


if __name__ == "__main__":
    main()
