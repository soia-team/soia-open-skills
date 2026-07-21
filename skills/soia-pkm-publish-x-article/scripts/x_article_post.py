#!/usr/bin/env python3
"""Host-agnostic X Articles draft filler for soia-pkm-publish-x-article.

Runs its own Playwright Chromium with a persistent profile, so it works from
any agent host (Claude Code, Codex, Gemini CLI, opencode, plain shell) — no
host browser tools required. This mirrors the pattern in the sibling skill
soia-pkm-publish-x-thread's scripts/x_post.py.

PROFILE SHARING (intentional, not a bug): this script's default profile
directory resolves to the EXACT SAME path as x_post.py's
default_profile_dir() — literally
~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-publish-x-thread/x-profile
(same $SOIA_X_PROFILE_DIR env var, same --profile-dir precedence). X's login
cookies are not scoped per-skill, so a user who already ran
`x_post.py login` once to post threads must NOT be asked to log in again
just to draft an Article. The path still says "publish-x-thread" on purpose
— that is where the profile was first created, and renaming the directory
would silently orphan any already-logged-in profile. Do not "fix" this by
pointing it at a new soia-pkm-publish-x-article directory; that would defeat
the sharing and force a redundant login.

Clipboard is handled WITHOUT any OS-specific shell-out (no osascript, no
sips) via Playwright's native clipboard permission grant plus the in-page
Clipboard API (navigator.clipboard.write). This is a deliberate, genuine
improvement over the sibling clipboard_x.py (which is macOS-only via
osascript and remains in place for the claude-in-chrome fallback path
documented in SKILL.md) — this script is meant to run unmodified on macOS,
Windows, and Linux. Paste is dispatched via Meta+V on macOS and Control+V
elsewhere, detected via sys.platform.

Subcommands:
    status              report whether the shared profile is logged in
    check               classify Articles access without changing anything:
                         state is one of not_logged_in / no_articles_access /
                         ok / unknown (see classify_articles_access())
    draft <json-path>   load parse_x_article.py's JSON output (a FILE PATH,
                         not inline JSON — the payload is large) and fill the
                         X Articles editor: cover, title, rich-text body,
                         content images (reverse block_index order),
                         dividers (reverse block_index order), then run a
                         mechanical verification pass.

Safety contract (mirrors SKILL.md's "任何情况下不点发布"):
- This script contains NO code path that clicks, searches for, or otherwise
  locates any publish/发布/Post button for the Articles flow. draft only
  ever produces a draft. There is no `send`/`publish` subcommand — unlike
  x_post.py's two-tier draft/send design, Articles publishing is entirely
  out of scope for automation here, by design, permanently.

Honesty contract for `check`/`draft` classification: the real X Articles
editor DOM has never been observed by anyone on this team with a working
Premium subscription. Every selector below is therefore a best-effort,
text/role-based Playwright locator (get_by_role / get_by_placeholder /
get_by_text), not an invented data-testid. When a locator cannot be found
with reasonable confidence, this script reports an honest "unknown" state
with a screenshot rather than silently misclassifying — see
classify_articles_access() and find_create_control().

Dependencies: pip install playwright && python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ARTICLES_URL = "https://x.com/compose/articles"
HOME_URL = "https://x.com/home"
LOGGED_IN_SELECTOR = '[data-testid="SideNav_AccountSwitcher_Button"]'

NO_PREMIUM_MESSAGE = (
    "当前账号未开通含「撰写文章」权益的 X Premium，请到 "
    "https://x.com/i/premium_sign_up 开通（2026-07 实测 US$4/月的 Premium 档即"
    "含此权益）后再试。"
)

CREATE_CONTROL_RE = re.compile(r"create|撰写|写文章|new article|新建文章", re.I)
TITLE_PLACEHOLDER_RE = re.compile(r"add title|添加标题", re.I)
BODY_EDITOR_NAME_RE = re.compile(
    r"article body|write your article|tell your story|正文|写文章|开始写作", re.I
)
APPLY_BUTTON_RE = re.compile(r"apply|应用", re.I)
UPLOADING_RE = re.compile(r"uploading|正在上传", re.I)
INSERT_MENU_RE = re.compile(r"insert|插入", re.I)
DIVIDER_ITEM_RE = re.compile(r"divider|分割线|horizontal rule", re.I)
SAVED_INDICATOR_RE = re.compile(r"已保存|saved|autosaved|draft saved", re.I)
NOT_FOUND_TEXT_MARKERS = ("页面不存在", "doesn't exist", "doesn’t exist", "This page doesn")
PREMIUM_UPSELL_MARKERS = (
    "premium_sign_up",
    "Subscribe to Premium",
    "订阅 Premium",
    "开通 Premium",
    "Premium 订阅",
)


# ---------------------------------------------------------------------------
# Profile / launch / login (mirrors x_post.py; duplicated on purpose — skills
# in this repo are independently installable and must not import a sibling
# skill's scripts/ directory)
# ---------------------------------------------------------------------------


def default_profile_dir() -> Path:
    """Same default path as x_post.py's default_profile_dir() — see the
    PROFILE SHARING note in the module docstring for why."""
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
    kwargs = dict(
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir), channel="chrome", **kwargs
        )
    except Exception:
        return playwright.chromium.launch_persistent_context(str(profile_dir), **kwargs)


def grant_clipboard_permissions(ctx) -> None:
    """Best-effort: some Playwright/Chromium combinations reject an explicit
    origin for a persistent context; fall back to no-origin, then give up
    quietly — clipboard_write_* will still raise its own honest error later
    if the permission was in fact required and missing."""
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://x.com")
        return
    except Exception:
        pass
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    except Exception:
        pass


def is_logged_in(page, timeout_ms: int = 8000) -> bool:
    page.goto(HOME_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_selector(LOGGED_IN_SELECTOR, timeout=timeout_ms)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Cross-platform clipboard via Playwright's native Clipboard API (no
# osascript / sips / any OS shell-out) — see module docstring requirement.
# ---------------------------------------------------------------------------


def paste_modifier() -> str:
    return "Meta+V" if sys.platform == "darwin" else "Control+V"


def clipboard_write_html(page, html: str) -> None:
    page.evaluate(
        """
        async (html) => {
            const blob = new Blob([html], { type: "text/html" });
            const item = new ClipboardItem({ "text/html": blob });
            await navigator.clipboard.write([item]);
        }
        """,
        html,
    )


def clipboard_write_image(page, image_path: Path) -> None:
    mime, _ = mimetypes.guess_type(str(image_path))
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    data_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    page.evaluate(
        """
        async ({ data, mime }) => {
            const bin = atob(data);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            const blob = new Blob([bytes], { type: mime });
            const item = new ClipboardItem({ [mime]: blob });
            await navigator.clipboard.write([item]);
        }
        """,
        {"data": data_b64, "mime": mime},
    )


def paste_html_into(page, locator, html: str) -> None:
    locator.click()
    clipboard_write_html(page, html)
    page.keyboard.press(paste_modifier())


def paste_image_into(page, locator, image_path: Path) -> None:
    locator.click()
    page.keyboard.press("End")  # avoid landing inside an inline link
    clipboard_write_image(page, image_path)
    page.keyboard.press(paste_modifier())


def wait_for_upload_to_finish(page, timeout_ms: int = 15_000) -> None:
    try:
        page.get_by_text(UPLOADING_RE).first.wait_for(state="hidden", timeout=timeout_ms)
    except Exception:
        # Either the indicator never appeared (fast upload) or it didn't
        # disappear in time. Don't block the whole draft on this signal
        # alone — the mechanical media-count check catches a truly failed
        # upload honestly instead of hanging here indefinitely.
        pass


def wait_for_autosave_signal(page, settle_ms: int = 1500, timeout_ms: int = 8000) -> bool:
    """Give the editor's (assumed) debounced autosave time to fire before the
    caller tears down the browser context, and try to observe a positive
    "已保存/Saved" signal.

    Why this exists: whether X Articles autosaves as you type — and how long
    it debounces — is an unverified assumption (see module docstring's
    Honesty contract; nobody on this team has observed the real editor with
    a working Premium account). Closing the context immediately after the
    last paste risked losing content that hadn't been persisted yet, while
    the caller still reported ok:true. This does not *guarantee* persistence
    (that would require live-DOM verification this session cannot do), but
    it converts a silent assumption into an honestly-reported signal: a
    generous settle wait first, then a bounded attempt to find the saved
    indicator. Returns False (not an exception) when the indicator can't be
    confirmed — callers must surface that as a warning, not swallow it."""
    try:
        page.wait_for_timeout(settle_ms)
    except Exception:
        pass
    try:
        page.get_by_text(SAVED_INDICATOR_RE).first.wait_for(state="visible", timeout=timeout_ms)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Screenshots / error safety net
# ---------------------------------------------------------------------------


def screenshot_path(prefix: str) -> Path:
    d = Path(tempfile.gettempdir()) / "soia-pkm-publish-x-article"
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return d / f"{prefix}-{ts}.png"


def safe_screenshot(page, prefix: str) -> str | None:
    if page is None:
        return None
    try:
        p = screenshot_path(prefix)
        page.screenshot(path=str(p))
        return str(p)
    except Exception:
        return None


def safe_url(page) -> str | None:
    try:
        return page.url
    except Exception:
        return None


def safe_title(page) -> str | None:
    try:
        return page.title()
    except Exception:
        return None


def run_subcommand(action: str, profile_dir: Path, fn):
    """Launch a Playwright session, hand (ctx, page) to fn, and turn ANY
    unexpected exception into a structured error (screenshot + page url/title
    + message) instead of a raw traceback or a silent wrong click. Normal,
    anticipated outcomes (not logged in, no access, divider failed, ...) are
    reported by fn itself via out() and are not exceptions."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = None
        page = None
        try:
            ctx = launch(profile_dir, p)
            grant_clipboard_permissions(ctx)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            return fn(ctx, page)
        except Exception as exc:
            out(
                {
                    "ok": False,
                    "action": action,
                    "error": str(exc),
                    "screenshot": safe_screenshot(page, action),
                    "url": safe_url(page),
                    "title": safe_title(page),
                }
            )
            return 1
        finally:
            if ctx is not None:
                try:
                    ctx.close()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Articles access classification (used by `check` and as `draft`'s step 1)
# ---------------------------------------------------------------------------


def find_create_control(page):
    """Best-effort, text/role-based locator for the 'create article' control
    on the Articles draft-list page. Returns a Playwright locator or None —
    never raises. See the module docstring's Honesty contract."""
    try:
        loc = page.get_by_role("button", name=CREATE_CONTROL_RE)
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first
    except Exception:
        pass
    try:
        loc = page.get_by_role("link", name=CREATE_CONTROL_RE)
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first
    except Exception:
        pass
    # Last-resort fallback: plain text match. Riskier (could match an upsell
    # paragraph rather than a real control) but explicitly allowed by the
    # task spec's locator guidance; is_visible() is the only guard available.
    try:
        loc = page.get_by_text(CREATE_CONTROL_RE)
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first
    except Exception:
        pass
    return None


def classify_articles_access(page) -> dict:
    """Navigate to ARTICLES_URL and classify into exactly one of:
    not_logged_in / no_articles_access / ok / unknown. Never raises for
    ordinary "couldn't find it" cases — those become "unknown"."""
    if not is_logged_in(page):
        return {"state": "not_logged_in", "url": safe_url(page), "title": safe_title(page)}

    page.goto(ARTICLES_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    url = safe_url(page)
    title = safe_title(page)

    if url and ("/login" in url or "/i/flow/login" in url or "/account/login" in url):
        return {"state": "not_logged_in", "url": url, "title": title}

    try:
        page_text = page.inner_text("body")
    except Exception:
        page_text = ""

    is_404 = (title is not None and "404" in title) or any(
        m in page_text for m in NOT_FOUND_TEXT_MARKERS
    )
    if is_404:
        return {
            "state": "no_articles_access",
            "message": NO_PREMIUM_MESSAGE,
            "url": url,
            "title": title,
        }

    if find_create_control(page) is not None:
        return {"state": "ok", "url": url, "title": title}

    # No create control found, but the page did load (not a 404). If the
    # page text itself carries a clear Premium-upsell signal, we're
    # reasonably confident this is "logged in, no Articles access" rather
    # than an unrecognized editor DOM — report that with the required
    # verbatim message. Otherwise this is genuinely ambiguous: report
    # "unknown" with a screenshot rather than guessing either way.
    if any(m in page_text for m in PREMIUM_UPSELL_MARKERS):
        return {
            "state": "no_articles_access",
            "message": NO_PREMIUM_MESSAGE,
            "url": url,
            "title": title,
        }

    return {
        "state": "unknown",
        "url": url,
        "title": title,
        "screenshot": safe_screenshot(page, "check-unknown"),
    }


# ---------------------------------------------------------------------------
# Editor interaction helpers used only by `draft`
# ---------------------------------------------------------------------------


def find_title_input(page):
    try:
        loc = page.get_by_placeholder(TITLE_PLACEHOLDER_RE)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    return None


def find_body_editor(page):
    """Best-effort locator for the Articles rich-text body editor. The real
    editor DOM has never been observed with a working Premium account (see
    module docstring), so this is a layered guess: prefer an explicitly
    labeled textbox, then fall back to the last contenteditable/textbox
    region on the page (the title field is typically single-line and earlier
    in the DOM than the multi-line body)."""
    try:
        loc = page.get_by_role("textbox", name=BODY_EDITOR_NAME_RE)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    try:
        loc = page.locator('[contenteditable="true"]')
        n = loc.count()
        if n >= 2:
            return loc.nth(n - 1)
        if n == 1:
            return loc.first
    except Exception:
        pass
    try:
        loc = page.get_by_role("textbox")
        n = loc.count()
        if n >= 2:
            return loc.nth(n - 1)
        if n == 1:
            return loc.first
    except Exception:
        pass
    return None


def find_paragraph_by_text(page, after_text: str):
    if not after_text:
        return None
    try:
        loc = page.get_by_text(after_text, exact=False)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    return None


def upload_cover(page, cover_path: str, warnings: list) -> bool:
    """Upload the cover via a real file input (far more reliable than any
    clipboard/drag trick for a file-upload widget). Returns True once
    set_input_files succeeded. The Apply/应用 confirm click is best-effort
    per the task spec: failing to find it is a warning, not a hard failure,
    since some editor versions may auto-apply."""
    file_input = page.locator('input[type="file"]').first
    try:
        file_input.wait_for(state="attached", timeout=10_000)
    except Exception:
        warnings.append("未找到封面上传的文件输入控件（input[type=file]），跳过封面上传")
        return False

    try:
        file_input.set_input_files(cover_path)
    except Exception as exc:
        warnings.append(f"封面文件上传失败（{cover_path}）：{exc}，跳过封面，继续正文/图片/分割线")
        return False

    try:
        apply_btn = page.get_by_role("button", name=APPLY_BUTTON_RE)
        if apply_btn.count() > 0:
            apply_btn.first.click(timeout=6_000)
    except Exception:
        warnings.append(
            "封面媒体编辑层未找到或未能点击「应用/Apply」按钮"
            "（部分编辑器版本可能自动应用，未强制阻断流程）"
        )
    return True


def insert_divider_at(page, anchor) -> None:
    """Raises on failure — callers must wrap this per-item and turn a
    failure into a warning rather than aborting the whole draft. `anchor` is
    pre-resolved by the caller (a paragraph locator, or body_editor as a
    deterministic fallback — mirrors the content-images loop) so a divider's
    placement is never left to whatever position the cursor happened to be
    at from a previous item; without this fallback, a divider whose
    block_index==0 (e.g. cover immediately followed by `---`, which yields
    an empty after_text — see parse_x_article.py's _tail_text([]) == "")
    would silently land wherever the last-processed item left the cursor."""
    anchor.click()
    page.keyboard.press("End")
    menu_btn = page.get_by_role("button", name=INSERT_MENU_RE)
    menu_btn.first.click(timeout=5_000)
    item = page.get_by_role("menuitem", name=DIVIDER_ITEM_RE)
    if item.count() == 0:
        item = page.get_by_text(DIVIDER_ITEM_RE)
    item.first.click(timeout=5_000)


def count_editor_images(page) -> int | None:
    """Best-effort SCOPED image count — restricted to the app's main content
    region (role=main) so nav-bar chrome (account avatar, etc.) isn't
    double-counted alongside the article's own images. An unscoped
    page.locator("img").count() over the whole page would produce
    near-guaranteed false negatives on a real X page (any chrome-level
    <img> inflates the count above the JSON-derived expectation). Falls back
    to the unscoped whole-page count only when no role="main" region exists
    at all on this page (meaning the scoping assumption itself doesn't hold
    here) — not when the scoped count is legitimately 0, since that's a
    real, trustworthy answer once the region has been confirmed to exist."""
    try:
        main_loc = page.locator('[role="main"]')
        if main_loc.count() > 0:
            return main_loc.first.locator("img").count()
    except Exception:
        pass
    try:
        return page.locator("img").count()
    except Exception:
        return None


def run_verification(
    page, data: dict, dividers_inserted: int, autosave_confirmed: bool
) -> dict:
    checks: dict = {}

    title_ok = False
    title_input = find_title_input(page)
    if title_input is not None:
        current = None
        try:
            current = title_input.input_value()
        except Exception:
            try:
                current = title_input.inner_text()
            except Exception:
                current = None
        title_ok = current is not None and current.strip() == data["title"].strip()
    checks["title_matches"] = title_ok

    try:
        body_text = page.inner_text("body")
    except Exception:
        body_text = ""
    visible_html_text = re.sub(r"<[^>]+>", " ", data.get("html", ""))
    visible_html_text = re.sub(r"\s+", " ", visible_html_text).strip()
    prefix = visible_html_text[:40]
    suffix = visible_html_text[-40:]
    checks["body_prefix_found"] = bool(prefix) and prefix in body_text
    checks["body_suffix_found"] = bool(suffix) and suffix in body_text

    img_count = count_editor_images(page)
    expected_img_count = (1 if data.get("cover_image") else 0) + len(
        data.get("content_images", [])
    )
    checks["media_count_expected"] = expected_img_count
    checks["media_count_found"] = img_count
    checks["media_count_matches"] = img_count == expected_img_count if img_count is not None else False

    checks["dividers_expected"] = len(data.get("dividers", []))
    checks["dividers_inserted"] = dividers_inserted
    # NOTE on what this check actually proves: dividers_inserted is the
    # insertion loop's OWN success bookkeeping (incremented whenever
    # insert_divider_at didn't raise), not an independent DOM re-scan. It
    # cannot detect a false-positive where the menu-item click succeeded
    # without exception but matched the wrong element (e.g. a same-named
    # unrelated menuitem) and no divider was actually produced. No reliable,
    # confirmed selector exists for detecting a rendered divider element in
    # the real editor DOM (see module docstring's Honesty contract) — rather
    # than invent one with false confidence, this check is left as an
    # honest "did the loop believe it succeeded" signal, not a proof.
    checks["dividers_count_matches"] = dividers_inserted == checks["dividers_expected"]

    checks["autosave_confirmed"] = autosave_confirmed

    draft_url = None
    current_url = safe_url(page)
    if current_url and "compose/articles" in current_url and current_url != ARTICLES_URL:
        draft_url = current_url
    checks["draft_url"] = draft_url  # None means not confidently available — not guessed

    return checks


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_status(profile_dir: Path) -> int:
    def fn(ctx, page):
        ok = is_logged_in(page)
        out({"ok": ok, "action": "status", "logged_in": ok, "profile_dir": str(profile_dir)})
        return 0 if ok else 1

    return run_subcommand("status", profile_dir, fn)


def cmd_check(profile_dir: Path) -> int:
    def fn(ctx, page):
        result = classify_articles_access(page)
        ok = result["state"] == "ok"
        out({"ok": ok, "action": "check", "profile_dir": str(profile_dir), **result})
        return 0 if ok else 1

    return run_subcommand("check", profile_dir, fn)


def cmd_draft(profile_dir: Path, json_path: Path) -> int:
    try:
        raw = json_path.read_text(encoding="utf-8")
    except Exception as exc:
        out({"ok": False, "action": "draft", "error": f"无法读取 JSON 文件：{exc}"})
        return 1
    try:
        data = json.loads(raw)
    except Exception as exc:
        out({"ok": False, "action": "draft", "error": f"JSON 解析失败：{exc}"})
        return 1

    for key in ("title", "html", "content_images", "dividers"):
        if key not in data:
            out({"ok": False, "action": "draft", "error": f"JSON 缺少字段：{key}"})
            return 1

    def fn(ctx, page):
        # a. Reuse `check` logic first; stop immediately on anything but ok.
        access = classify_articles_access(page)
        if access["state"] != "ok":
            out({"ok": False, "action": "draft", **access})
            return 1

        control = find_create_control(page)
        if control is None:
            # classify_articles_access just found it moments ago; losing it
            # now means the page changed under us — report honestly rather
            # than guessing a click.
            out(
                {
                    "ok": False,
                    "action": "draft",
                    "state": "unknown",
                    "error": "check 通过后未能重新定位创建按钮，页面可能已变化",
                    "screenshot": safe_screenshot(page, "draft-lost-create-control"),
                    "url": safe_url(page),
                }
            )
            return 1
        control.click()

        warnings: list = []

        # b. cover (skip entirely if null — caller already gated this)
        cover_image = data.get("cover_image")
        cover_uploaded = False
        if cover_image:
            cover_uploaded = upload_cover(page, cover_image, warnings)

        # c. title
        title_input = find_title_input(page)
        if title_input is None:
            warnings.append("未找到标题输入框（placeholder 匹配失败），标题未填写")
        else:
            title_input.click()
            title_input.fill(data["title"])

        # d. body — click editor, clipboard-paste rich HTML
        body_editor = find_body_editor(page)
        if body_editor is None:
            out(
                {
                    "ok": False,
                    "action": "draft",
                    "error": "未找到正文编辑区，停止（不猜测点击）",
                    "screenshot": safe_screenshot(page, "draft-no-body-editor"),
                    "url": safe_url(page),
                    "warnings": warnings,
                }
            )
            return 1
        paste_html_into(page, body_editor, data["html"])

        # e. content images, block_index DESCENDING (hard requirement)
        content_images = sorted(
            data.get("content_images", []), key=lambda i: i["block_index"], reverse=True
        )
        for item in content_images:
            after_text = item.get("after_text", "")
            anchor = find_paragraph_by_text(page, after_text) if after_text else None
            if anchor is None:
                # Either after_text is empty (this is the very first block —
                # there is no preceding anchor by definition) or the text
                # couldn't be located. Either way, fall back to the body
                # editor itself rather than crashing on an empty locator.
                if after_text:
                    warnings.append(
                        f"未找到图片锚点文字（block_index={item['block_index']}），"
                        "已改用正文编辑区作为落点"
                    )
                anchor = body_editor
            try:
                paste_image_into(page, anchor, Path(item["path"]))
                wait_for_upload_to_finish(page)
            except Exception as exc:
                warnings.append(f"插图失败（block_index={item['block_index']}）：{exc}")

        # f. dividers, block_index DESCENDING; a failure here must not abort
        # an otherwise-good draft. Anchor resolution mirrors the content-
        # images loop above (fallback to body_editor) — see
        # insert_divider_at's docstring for why this matters.
        dividers_inserted = 0
        for item in sorted(data.get("dividers", []), key=lambda d: d["block_index"], reverse=True):
            after_text = item.get("after_text", "")
            anchor = find_paragraph_by_text(page, after_text) if after_text else None
            if anchor is None:
                if after_text:
                    warnings.append(
                        f"未找到分割线锚点文字（block_index={item['block_index']}），"
                        "已改用正文编辑区作为落点"
                    )
                anchor = body_editor
            try:
                insert_divider_at(page, anchor)
                dividers_inserted += 1
            except Exception as exc:
                warnings.append(
                    {
                        "block_index": item["block_index"],
                        "after_text": after_text,
                        "error": f"分割线插入失败：{exc}",
                    }
                )

        # g. give the (assumed) debounced autosave time to fire and try to
        # observe a positive "已保存/Saved" signal BEFORE the context gets
        # torn down — closing immediately after the last paste, with no
        # wait and no save-confirmation, risked silently losing content
        # while still reporting ok:true (the editor's real autosave timing
        # has never been observed with a working Premium account).
        autosave_confirmed = wait_for_autosave_signal(page)
        if not autosave_confirmed:
            warnings.append(
                "未观测到「已保存/Saved」提示——草稿内容可能未完全持久化，"
                "请打开 checks.draft_url 人工确认后再依赖本次结果"
            )

        # h. mechanical verification
        checks = run_verification(page, data, dividers_inserted, autosave_confirmed)

        # i. There is no publish step. None. Ever. (see module docstring)
        out(
            {
                "ok": True,
                "action": "draft",
                "title": data["title"],
                "cover_image_present": bool(cover_image),
                "cover_uploaded": cover_uploaded,
                "content_image_count": len(content_images),
                "divider_count": len(data.get("dividers", [])),
                "dividers_inserted": dividers_inserted,
                "checks": checks,
                "warnings": warnings,
            }
        )
        return 0

    return run_subcommand("draft", profile_dir, fn)


def main() -> int:
    parser = argparse.ArgumentParser(description="Host-agnostic X Articles draft filler")
    parser.add_argument(
        "--profile-dir",
        help="persistent browser profile directory (shared default with x_post.py; see module docstring)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("check")
    d = sub.add_parser("draft")
    d.add_argument("json_path", help="path to a JSON FILE produced by parse_x_article.py")
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

    profile_dir = (
        Path(args.profile_dir).expanduser() if args.profile_dir else default_profile_dir()
    )

    if args.cmd == "status":
        return cmd_status(profile_dir)
    if args.cmd == "check":
        return cmd_check(profile_dir)
    return cmd_draft(profile_dir, Path(args.json_path).expanduser())


if __name__ == "__main__":
    raise SystemExit(main())
