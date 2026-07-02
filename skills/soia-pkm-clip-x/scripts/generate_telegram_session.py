#!/usr/bin/env python3
"""
generate_telegram_session.py — One-time setup to generate a Telegram MTProto
                                session string for sync_telegram_saved.py.

Prerequisites:
  1. Visit https://my.telegram.org/auth and log in
  2. Go to "API development tools", create an app
  3. Copy api_id and api_hash

Usage:
    export TELEGRAM_API_ID=12345678
    export TELEGRAM_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    python3 generate_telegram_session.py

The script will prompt for:
  - Your phone number (with country code, e.g. +86XXXXXXXXXXX)
  - Confirmation code (sent via Telegram app, NOT SMS)
  - 2FA password (if enabled)

It prints a session_string. Save it to your shell rc:

    echo 'export TELEGRAM_SESSION_STRING="1ApGNxxx..."' >> ~/.zshrc
    source ~/.zshrc

⚠️ Session string is equivalent to your account password. Keep it private.
   Never commit to git. If compromised, revoke via Telegram → Settings →
   Devices → end the session.

Dependencies: pip install telethon
"""
import os
import sys

try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("❌ telethon not installed. Run: pip3 install telethon", file=sys.stderr)
    sys.exit(1)

api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")

if not api_id or not api_hash:
    print("❌ Missing TELEGRAM_API_ID or TELEGRAM_API_HASH", file=sys.stderr)
    print()
    print("Get them from https://my.telegram.org/auth then:")
    print("  export TELEGRAM_API_ID=<your_api_id>")
    print("  export TELEGRAM_API_HASH=<your_api_hash>")
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
print("  - 2FA password (if enabled)")
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
    print("Save to your shell rc:")
    print()
    print(f'  echo \'export TELEGRAM_SESSION_STRING="{session_string}"\' >> ~/.zshrc')
    print(f"  echo 'export TELEGRAM_API_ID={api_id}' >> ~/.zshrc")
    print(f"  echo 'export TELEGRAM_API_HASH={api_hash}' >> ~/.zshrc")
    print(f"  source ~/.zshrc")
    print()
    print("Then test:")
    print("  python3 sync_telegram_saved.py --dry-run")
