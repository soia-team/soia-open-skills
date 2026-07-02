#!/usr/bin/env python3
"""
sync_telegram_export.py — Parse a Telegram Desktop JSON export, extract X URLs,
                          and batch-archive new ones into Obsidian vault.

Telegram Desktop → Settings → Advanced → Export Telegram data → JSON.
This script reads the resulting `result.json`, finds all x.com URLs in your
Saved Messages, dedupes against your vault, and calls archive_x.py for each
new one.

No Telegram API credentials, no MTProto, no IP risk — fully offline parser.

Usage:
    python3 sync_telegram_export.py <result.json>
    python3 sync_telegram_export.py <result.json> --dry-run
    python3 sync_telegram_export.py <result.json> --since 2026-05-01
    python3 sync_telegram_export.py <result.json> --limit 30
    python3 sync_telegram_export.py <result.json> --vault /path/to/vault

Environment variables:
    OBSIDIAN_VAULT     Path to your Obsidian vault (required)
    OBSIDIAN_ARTICLES  Subdirectory for archived articles (default: "Articles")
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ARCHIVE_SCRIPT = Path(__file__).parent / "archive_x.py"

X_URL_RE = re.compile(
    r"https?://(?:mobile\.)?(?:x|twitter|fxtwitter)\.com/[^/\s?]+/status/(\d+)",
    re.IGNORECASE,
)


def resolve_vault(cli_vault: str | None) -> Path:
    if cli_vault:
        p = Path(cli_vault).expanduser().resolve()
    else:
        env = os.environ.get("OBSIDIAN_VAULT")
        if not env:
            print("❌ No vault path. Set OBSIDIAN_VAULT env or pass --vault <path>", file=sys.stderr)
            sys.exit(1)
        p = Path(env).expanduser().resolve()
    if not p.exists():
        print(f"❌ Vault path does not exist: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def resolve_article_root(vault: Path) -> Path:
    sub = os.environ.get("OBSIDIAN_ARTICLES", "Articles")
    return vault / sub


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


def extract_x_urls(json_path: Path) -> list[dict]:
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") != "saved_messages":
        print(
            f"⚠️ Warning: top-level type='{data.get('type')}' is not saved_messages",
            file=sys.stderr,
        )

    msgs = data.get("messages", [])
    results = []
    seen = set()
    for m in msgs:
        if m.get("type") != "message":
            continue
        for ent in m.get("text_entities", []):
            etype = ent.get("type")
            if etype not in ("link", "text_link"):
                continue
            url = ent.get("href") if etype == "text_link" else ent.get("text", "")
            if not url:
                continue
            mx = X_URL_RE.search(url)
            if not mx:
                continue
            sid = mx.group(1)
            if sid in seen:
                continue
            seen.add(sid)
            # normalize
            url_clean = re.sub(r"\?.*$", "", url)
            url_clean = re.sub(
                r"^https?://(mobile\.)?(twitter|fxtwitter)\.com",
                "https://x.com",
                url_clean,
                flags=re.IGNORECASE,
            )
            url_clean = re.sub(
                r"^https?://mobile\.x\.com",
                "https://x.com",
                url_clean,
                flags=re.IGNORECASE,
            )
            results.append({
                "status_id": sid,
                "url": url_clean,
                "date": m.get("date", ""),
                "from": m.get("from", "?"),
                "msg_id": m.get("id"),
            })
    # sort: newest first
    results.sort(key=lambda x: x["date"], reverse=True)
    return results


def extract_status_id(url: str) -> str | None:
    m = re.search(r"/status/(\d+)", url)
    return m.group(1) if m else None


def call_archive(url: str, vault: Path, force: bool = False, timeout: int = 60) -> tuple[str, str]:
    args = ["python3", str(ARCHIVE_SCRIPT), url, "--vault", str(vault)]
    if force:
        args.append("--force")
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "failed", "timeout"
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        if "SKIP:" in out:
            return "skipped", "already archived"
        if "Archived" in out or "✓" in out:
            for line in out.split("\n"):
                if "Archived" in line:
                    return "archived", line.strip()
            return "archived", "OK"
    return "failed", out[-300:] if out else f"exit {proc.returncode}"


def main():
    ap = argparse.ArgumentParser(description="Sync X URLs from Telegram JSON export to Obsidian vault")
    ap.add_argument("json_path", help="Path to result.json from Telegram Desktop export")
    ap.add_argument("--dry-run", action="store_true", help="List only, don't archive")
    ap.add_argument("--since", type=str, default=None, help="Only process after YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=None, help="Max items (newest first)")
    ap.add_argument("--no-skip", action="store_true", help="Don't skip already archived (force re-archive)")
    ap.add_argument("--sleep", type=float, default=0.5, help="Sleep between requests (seconds)")
    ap.add_argument("--reverse", action="store_true", help="Oldest first instead of newest first")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT)")
    args = ap.parse_args()

    vault = resolve_vault(args.vault)
    article_root = resolve_article_root(vault)

    json_path = Path(args.json_path).expanduser()
    if not json_path.exists():
        print(f"❌ File not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    if not ARCHIVE_SCRIPT.exists():
        print(f"❌ archive_x.py not found: {ARCHIVE_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 Reading {json_path}", file=sys.stderr)
    x_urls = extract_x_urls(json_path)
    print(f"   Found {len(x_urls)} unique X URLs", file=sys.stderr)

    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since)
        except ValueError:
            print(f"❌ Invalid --since format, expected YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
        x_urls = [
            u
            for u in x_urls
            if u["date"]
            and datetime.fromisoformat(u["date"][:19]) >= since_dt
        ]
        print(f"   After --since {args.since}: {len(x_urls)}", file=sys.stderr)

    if args.reverse:
        x_urls.reverse()

    if args.limit:
        x_urls = x_urls[: args.limit]
        print(f"   Limited to first {args.limit}", file=sys.stderr)

    archived = find_archived_status_ids(article_root)
    print(f"   Already archived in vault: {len(archived)}", file=sys.stderr)

    if args.no_skip:
        to_run = x_urls
    else:
        to_run = [u for u in x_urls if u["status_id"] not in archived]
        already = len(x_urls) - len(to_run)
        print(f"   To archive: {len(to_run)} ({already} skipped)", file=sys.stderr)

    print(file=sys.stderr)

    if args.dry_run:
        print("🔍 Dry run — to archive:")
        for i, u in enumerate(to_run, 1):
            d = u["date"][:10]
            print(f"  {i:3d}. [{d}] {u['url']}")
        return

    if not to_run:
        print("✅ Nothing new to archive", file=sys.stderr)
        return

    print(
        f"🚀 Archiving {len(to_run)} (sleep {args.sleep}s between)",
        file=sys.stderr,
    )
    print(file=sys.stderr)

    ok, skip, fail = 0, 0, 0
    failures = []
    for i, u in enumerate(to_run, 1):
        d = u["date"][:10]
        print(f"[{i}/{len(to_run)}] [{d}] {u['url']}", file=sys.stderr)
        status, msg = call_archive(u["url"], vault, force=args.no_skip)
        if status == "archived":
            print(f"  ✓ {msg}", file=sys.stderr)
            ok += 1
        elif status == "skipped":
            print(f"  ⏭️  exists", file=sys.stderr)
            skip += 1
        else:
            print(f"  ❌ failed: {msg[:200]}", file=sys.stderr)
            fail += 1
            failures.append({"url": u["url"], "date": d, "error": msg[:200]})
        if i < len(to_run):
            time.sleep(args.sleep)

    print(file=sys.stderr)
    print(f"=== Done ===", file=sys.stderr)
    print(f"  ✓ New: {ok}", file=sys.stderr)
    print(f"  ⏭️  Skipped: {skip}", file=sys.stderr)
    print(f"  ❌ Failed: {fail}", file=sys.stderr)

    if failures:
        fail_log = Path.cwd() / "telegram_sync_failures.json"
        fail_log.write_text(
            json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nFailure log: {fail_log}", file=sys.stderr)


if __name__ == "__main__":
    main()
