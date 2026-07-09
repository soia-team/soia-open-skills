#!/usr/bin/env python3
"""
sync_telegram_saved.py — Sync X URLs from Telegram Saved Messages via MTProto API.

Advanced path (the recommended path is sync_telegram_export.py — Telegram Desktop
JSON export, which is fully offline, zero-risk, and ToS-compliant).

Use this only if:
  - You have a Telegram api_id + api_hash (from https://my.telegram.org/auth)
  - You have a residential IP matching your phone-number country
  - You want live sync without manual JSON export

Setup (one-time):
  1. Visit https://my.telegram.org/auth, log in with your phone number
  2. Go to "API development tools", create an app
  3. Get api_id and api_hash
  4. Run generate_telegram_session.py to get a session string

Environment variables:
    TELEGRAM_API_ID         from my.telegram.org
    TELEGRAM_API_HASH       from my.telegram.org
    TELEGRAM_SESSION_STRING from generate_telegram_session.py
    OBSIDIAN_VAULT          Path to your Obsidian vault
    OBSIDIAN_ARTICLES       Subdirectory for articles
                            (defaults to "Articles")

Private config is auto-loaded from SOIA_PKM_CLIP_X_CONFIG_FILE or the
skill-specific config.yml. Do not store secrets in the vault or committed skill repo.

Usage:
    python3 sync_telegram_saved.py
    python3 sync_telegram_saved.py --days 30
    python3 sync_telegram_saved.py --all
    python3 sync_telegram_saved.py --dry-run
    python3 sync_telegram_saved.py --vault /path/to/vault
    python3 sync_telegram_saved.py --articles-dir <articles-subdir>

Dependencies: pip install telethon
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from soia_env import env_source_hint, load_private_env

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print(
        "❌ telethon not installed. Run: pip3 install telethon",
        file=sys.stderr,
    )
    sys.exit(1)

ARCHIVE_SCRIPT = Path(__file__).parent / "archive_x.py"

X_URL_RE = re.compile(
    r"https?://(?:mobile\.)?(?:x|twitter|fxtwitter)\.com/[^/\s]+/status/\d+",
    re.IGNORECASE,
)

CST = timezone(timedelta(hours=8))

DEFAULT_ARTICLES_DIR = "Articles"


def looks_like_vault(path: Path) -> bool:
    return (path / ".obsidian").is_dir() or (path / "AGENTS.md").is_file()


def discover_vault_from_cwd() -> Path | None:
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
                print("❌ No vault path found. Run from the vault root, set OBSIDIAN_VAULT, or pass --vault <path>.", file=sys.stderr)
                print(f"   private config sources checked: {env_source_hint()}.", file=sys.stderr)
                sys.exit(1)
            print(f"ℹ️  Auto-detected vault from cwd: {p}", file=sys.stderr)
    if not p.exists() or not p.is_dir():
        print(f"❌ Vault not found: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def resolve_article_root(vault: Path, cli_articles_dir: str | None = None) -> Path:
    sub = cli_articles_dir or os.environ.get("OBSIDIAN_ARTICLES")
    if sub:
        return vault / sub
    return vault / DEFAULT_ARTICLES_DIR


def find_archived_status_ids(article_root: Path) -> set[str]:
    sids = set()
    if not article_root.exists():
        return sids
    for f in article_root.rglob("*.md"):
        if "_template" in f.parts or "_templates" in f.parts or "_MOC" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r"^url:\s*(.+)$", text, re.MULTILINE)
        if m:
            sid_m = re.search(r"/status/(\d+)", m.group(1))
            if sid_m:
                sids.add(sid_m.group(1))
    return sids


def extract_status_id(url: str) -> str | None:
    m = re.search(r"/status/(\d+)", url)
    return m.group(1) if m else None


def normalize_url(url: str) -> str:
    url = re.sub(r"\?.*$", "", url)
    url = re.sub(
        r"^https?://(mobile\.)?(twitter|fxtwitter)\.com",
        "https://x.com",
        url,
        flags=re.IGNORECASE,
    )
    url = re.sub(
        r"^https?://mobile\.x\.com",
        "https://x.com",
        url,
        flags=re.IGNORECASE,
    )
    return url


async def collect_x_urls(since_dt: datetime | None, limit: int | None) -> tuple[list[dict], int]:
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session_string = os.environ["TELEGRAM_SESSION_STRING"]

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.start()

    results = []
    seen_urls = set()
    n_scanned = 0
    async for msg in client.iter_messages("me", limit=limit):
        n_scanned += 1
        if since_dt and msg.date < since_dt:
            break

        texts = []
        if msg.text:
            texts.append(msg.text)
        if msg.message and msg.message != msg.text:
            texts.append(msg.message)
        if msg.entities:
            for e in msg.entities:
                if hasattr(e, "url") and e.url:
                    texts.append(e.url)
        if msg.web_preview and hasattr(msg.web_preview, "url"):
            texts.append(msg.web_preview.url or "")

        for t in texts:
            for url in X_URL_RE.findall(t):
                url_norm = normalize_url(url)
                if url_norm in seen_urls:
                    continue
                seen_urls.add(url_norm)
                results.append({
                    "url": url_norm,
                    "msg_date": msg.date.astimezone(CST),
                    "msg_id": msg.id,
                    "msg_text_preview": (t[:80] + "...") if len(t) > 80 else t,
                })

    await client.disconnect()
    return results, n_scanned


def call_archive(url: str, vault: Path, articles_dir: str | None = None, force: bool = False) -> tuple[str, str]:
    args = ["python3", str(ARCHIVE_SCRIPT), url, "--vault", str(vault)]
    if articles_dir:
        args.extend(["--articles-dir", articles_dir])
    if force:
        args.append("--force")
    proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        if "SKIP:" in out:
            return "skipped", "already archived"
        if "Archived" in out or "✓" in out:
            return "archived", out.split("\n")[0]
    return "failed", out[-300:] if out else f"exit {proc.returncode}"


def main():
    load_private_env()

    ap = argparse.ArgumentParser(description="Sync Telegram Saved Messages via MTProto API")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--vault", help="Override OBSIDIAN_VAULT")
    ap.add_argument("--articles-dir", help="Article archive dir relative to vault (overrides OBSIDIAN_ARTICLES)")
    args = ap.parse_args()

    vault = resolve_vault(args.vault)
    article_root = resolve_article_root(vault, args.articles_dir)

    missing = [
        v
        for v in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION_STRING")
        if not os.environ.get(v)
    ]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}", file=sys.stderr)
        print(f"Load them from a private config.yml ({env_source_hint()}) or run generate_telegram_session.py first.", file=sys.stderr)
        sys.exit(1)

    if args.all:
        since_dt = None
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=args.days)

    print(
        f"📱 Scanning Telegram Saved Messages "
        f"({'all' if args.all else f'last {args.days} days'})...",
        file=sys.stderr,
    )

    urls, n_scanned = asyncio.run(collect_x_urls(since_dt, args.limit))
    existing = find_archived_status_ids(article_root)

    print(f"   Scanned {n_scanned} messages, found {len(urls)} X URLs", file=sys.stderr)
    print(f"   Already in vault: {len(existing)}", file=sys.stderr)

    to_archive = []
    already = []
    for u in urls:
        sid = extract_status_id(u["url"])
        if sid and sid in existing:
            already.append(u)
        else:
            to_archive.append(u)

    print(f"\n📊 To archive: {len(to_archive)} | Already: {len(already)}\n", file=sys.stderr)

    if args.dry_run:
        print("🔍 Dry run — to archive:")
        for i, u in enumerate(to_archive, 1):
            d = u["msg_date"].strftime("%Y-%m-%d %H:%M")
            print(f"  {i:3d}. [{d}] {u['url']}")
            print(f"        {u['msg_text_preview']}")
        return

    if not to_archive:
        print("✅ Nothing new to archive", file=sys.stderr)
        return

    print(f"🚀 Archiving {len(to_archive)}...", file=sys.stderr)
    ok, skip, fail = 0, 0, 0
    for i, u in enumerate(to_archive, 1):
        print(f"[{i}/{len(to_archive)}] {u['url']}", file=sys.stderr)
        status, msg = call_archive(u["url"], vault, articles_dir=args.articles_dir, force=args.force)
        if status == "archived":
            print(f"  ✓ {msg}", file=sys.stderr)
            ok += 1
        elif status == "skipped":
            print(f"  ⏭️", file=sys.stderr)
            skip += 1
        else:
            print(f"  ❌ {msg}", file=sys.stderr)
            fail += 1

    print(f"\n=== Done ===\n  ✓ New: {ok}\n  ⏭️ Skipped: {skip}\n  ❌ Failed: {fail}", file=sys.stderr)


if __name__ == "__main__":
    main()
