#!/usr/bin/env python3
"""Host-agnostic X post/thread filler for soia-pkm-publish-x-thread.

Runs its own Playwright Chromium with a persistent profile, so it works from
any agent host (Claude Code, Codex, Gemini CLI, opencode, plain shell) — no
host browser tools, no cookie export. Login state lives only in the local
profile directory; nothing is written to the repo or logs.

Subcommands:
    login                    open X in a headed window; finishes when you log in
    status                   report whether the profile is logged in
    draft  "t1" ["t2" ...]   fill the composer (thread via +) and SAVE AS DRAFT
    send   "t1" ["t2" ...] --yes   actually publish; refuses without --yes

Safety contract (mirrors SKILL.md):
- draft never touches the post button.
- send requires the explicit --yes flag; the calling agent may only pass it
  when the user gave the final text verbatim and explicitly asked to publish.

Profile dir precedence: --profile-dir > $SOIA_X_PROFILE_DIR >
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-publish-x-thread/x-profile

Dependencies: pip install playwright && python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

COMPOSE_URL = "https://x.com/compose/post"
HOME_URL = "https://x.com/home"
LOGGED_IN_SELECTOR = '[data-testid="SideNav_AccountSwitcher_Button"]'
TEXTAREA = '[data-testid="tweetTextarea_{n}"]'
ADD_BUTTON = '[data-testid="addButton"]'
POST_BUTTON = '[data-testid="tweetButton"]'
CLOSE_BUTTON = '[data-testid="app-bar-close"]'
CONFIRM_SHEET = '[data-testid="confirmationSheetConfirm"]'
TOAST = '[data-testid="toast"]'


def default_profile_dir() -> Path:
    if os.environ.get("SOIA_X_PROFILE_DIR"):
        return Path(os.environ["SOIA_X_PROFILE_DIR"]).expanduser()
    return (
        Path.home()
        / ".config"
        / "soia-skills"
        / "soia-open-skills"
        / "soia-pkm"
        / "soia-pkm-publish-x-thread"
        / "x-profile"
    )


def out(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def launch(profile_dir: Path, playwright):
    profile_dir.mkdir(parents=True, exist_ok=True)
    # Headed on purpose: X throttles headless fingerprints, and login is
    # interactive anyway.
    kwargs = dict(
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    # Prefer the system Chrome binary: familiar UI, and Google sign-in blocks
    # bundled Chromium more often. Chrome >=136 forbids automating the user's
    # DEFAULT profile, so a dedicated profile dir is mandatory either way —
    # the login there is a one-time cost, persisted forever after.
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir), channel="chrome", **kwargs
        )
    except Exception:
        return playwright.chromium.launch_persistent_context(str(profile_dir), **kwargs)


def is_logged_in(page, timeout_ms: int = 8000) -> bool:
    page.goto(HOME_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_selector(LOGGED_IN_SELECTOR, timeout=timeout_ms)
        return True
    except Exception:
        return False


def cmd_login(profile_dir: Path) -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = launch(profile_dir, p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(HOME_URL, wait_until="domcontentloaded")
        print("请在弹出的浏览器窗口中登录 X（最长等待 5 分钟）…", file=sys.stderr)
        try:
            page.wait_for_selector(LOGGED_IN_SELECTOR, timeout=300_000)
        except Exception:
            out({"ok": False, "action": "login", "error": "5 分钟内未检测到登录态"})
            ctx.close()
            return 1
        ctx.close()  # persists the profile
        out({"ok": True, "action": "login", "profile_dir": str(profile_dir)})
        return 0


def cmd_status(profile_dir: Path) -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = launch(profile_dir, p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        ok = is_logged_in(page)
        ctx.close()
        out({"ok": ok, "action": "status", "logged_in": ok, "profile_dir": str(profile_dir)})
        return 0 if ok else 1


def fill_composer(page, texts: list[str]) -> None:
    page.goto(COMPOSE_URL, wait_until="domcontentloaded")
    page.wait_for_selector(TEXTAREA.format(n=0), timeout=15_000)
    for i, text in enumerate(texts):
        if i > 0:
            page.click(ADD_BUTTON)
            page.wait_for_selector(TEXTAREA.format(n=i), timeout=10_000)
        page.click(TEXTAREA.format(n=i))
        page.keyboard.insert_text(text)


def cmd_draft(profile_dir: Path, texts: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = launch(profile_dir, p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not is_logged_in(page):
            out({"ok": False, "action": "draft", "error": "未登录：先运行 `x_post.py login`"})
            ctx.close()
            return 1
        fill_composer(page, texts)
        page.click(CLOSE_BUTTON)
        # X asks whether to save or discard; confirm = save to unsent posts.
        page.wait_for_selector(CONFIRM_SHEET, timeout=10_000)
        page.click(CONFIRM_SHEET)
        page.wait_for_timeout(1_000)
        ctx.close()
        out(
            {
                "ok": True,
                "action": "draft",
                "parts": len(texts),
                "where": "X 更多 > 未发送帖子（Unsent posts）",
            }
        )
        return 0


def cmd_send(profile_dir: Path, texts: list[str], yes: bool) -> int:
    if not yes:
        out(
            {
                "ok": False,
                "action": "send",
                "error": "缺少 --yes：只有用户逐字确认文案并明确要求发布时才可传入",
            }
        )
        return 1
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = launch(profile_dir, p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not is_logged_in(page):
            out({"ok": False, "action": "send", "error": "未登录：先运行 `x_post.py login`"})
            ctx.close()
            return 1
        fill_composer(page, texts)
        page.click(POST_BUTTON)
        url = None
        try:
            toast_link = page.wait_for_selector(f'{TOAST} a[href*="/status/"]', timeout=10_000)
            href = toast_link.get_attribute("href")
            url = href if href.startswith("http") else "https://x.com" + href
        except Exception:
            pass  # posted but URL not captured; report honestly
        page.wait_for_timeout(1_000)
        ctx.close()
        out({"ok": True, "action": "send", "parts": len(texts), "url": url})
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Host-agnostic X composer automation")
    parser.add_argument("--profile-dir", help="persistent browser profile directory")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    sub.add_parser("status")
    d = sub.add_parser("draft")
    d.add_argument("texts", nargs="+", help="post text; multiple args form a thread")
    s = sub.add_parser("send")
    s.add_argument("texts", nargs="+", help="post text; multiple args form a thread")
    s.add_argument("--yes", action="store_true", help="explicit publish authorization")
    args = parser.parse_args()

    try:
        import playwright  # noqa: F401
    except ImportError:
        out(
            {
                "ok": False,
                "error": "缺少 playwright：pip install playwright && python -m playwright install chromium",
            }
        )
        return 1

    profile_dir = Path(args.profile_dir).expanduser() if args.profile_dir else default_profile_dir()

    for text in getattr(args, "texts", []):
        if len(text) > 280:
            out({"ok": False, "error": f"单条超 280 字符（{len(text)}）：先用拆条规则重拆"})
            return 1

    if args.cmd == "login":
        return cmd_login(profile_dir)
    if args.cmd == "status":
        return cmd_status(profile_dir)
    if args.cmd == "draft":
        return cmd_draft(profile_dir, args.texts)
    return cmd_send(profile_dir, args.texts, args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
