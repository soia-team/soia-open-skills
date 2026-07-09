#!/usr/bin/env python3
"""
generate_telegram_session.py — One-time setup to generate a Telegram MTProto
                                session string for sync_telegram_saved.py.

Prerequisites:
  1. Visit https://my.telegram.org/auth and log in
  2. Go to "API development tools", create an app
  3. Copy api_id and api_hash

Usage:
    # Put TELEGRAM_API_ID and TELEGRAM_API_HASH in a private config.yml,
    # or pass SOIA_PKM_CLIP_X_CONFIG_FILE.
    python3 generate_telegram_session.py

The script will prompt for:
  - Your phone number (with country code, e.g. +86XXXXXXXXXXX)
  - Confirmation code (sent via Telegram app, NOT SMS)
  - 2FA credential (if enabled)

It prints a session_string. Save it to a private config.yml:

    ~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-x/config.yml

⚠️ Session string is equivalent to an account credential. Keep it private.
   Never commit to git. If compromised, revoke via Telegram → Settings →
   Devices → end the session.

Dependencies: pip install telethon
"""
import os
import sys

from soia_env import env_source_hint, load_private_env

try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("❌ telethon not installed. Run: pip3 install telethon", file=sys.stderr)
    sys.exit(1)

load_private_env()

api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")

if not api_id or not api_hash:
    print("❌ Missing TELEGRAM_API_ID or TELEGRAM_API_HASH", file=sys.stderr)
    print()
    print("Get them from https://my.telegram.org/auth, then put them in a private config.yml.")
    print(f"Supported sources: {env_source_hint()}")
    print("private config.yml should define these variable names:")
    print("  TELEGRAM_API_ID")
    print("  TELEGRAM_API_HASH")
    print("  python3 generate_telegram_session.py")
    sys.exit(1)

try:
    api_id = int(api_id)
except ValueError:
    print(f"❌ TELEGRAM_API_ID must be a number, got: {api_id}", file=sys.stderr)
    sys.exit(1)

print("=" * 60)
print("Telegram MTProto Session Generator")
print("=" * 60)
print()
print("You will be prompted for:")
print("  - Phone number (with country code)")
print("  - Confirmation code (sent via Telegram app, NOT SMS!)")
print("  - 2FA credential (if enabled)")
print()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    me = client.get_me()
    session_string = client.session.save()

    print()
    print("=" * 60)
    print(f"✅ Logged in as: {me.first_name} (@{me.username or 'no-username'})")
    print("=" * 60)
    print()
    print("Session string (KEEP PRIVATE):")
    print()
    print(session_string)
    print()
    print("Save to a private config.yml (do not commit; do not put it in the vault):")
    print()
    print("  mkdir -p ~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-x")
    print("  $EDITOR ~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-clip-x/config.yml")
    print()
    print("Add env.TELEGRAM_SESSION_STRING with the session string printed above.")
    print("Keep TELEGRAM_API_ID and TELEGRAM_API_HASH in the same private config.yml; they are not echoed here.")
    print()
    print("Then test:")
    print("  python3 sync_telegram_saved.py --dry-run")
