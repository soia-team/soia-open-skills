#!/usr/bin/env python3
"""Host-agnostic, non-interfering ProcessOn browser runner.

The runner owns a dedicated persistent browser profile. It never attaches to a
user's default Chrome profile and never reads cookies, passwords, local storage,
or browser credential files. Any AI host that can invoke Python can use it.

Commands:
    login       open a dedicated headed window for one-time manual login
    status      verify that a target URL is reachable from the dedicated profile
    snapshot    return bounded visible text and interactive element metadata
    run         execute a declarative click/download action file

The action language intentionally has no fill, evaluate, cookie, storage, or
network-interception operations. A scoped ``popup`` action always closes the
child page in ``finally``. The whole dedicated browser context is also closed in
``finally`` on success, timeout, validation failure, Ctrl-C, and SIGTERM.

Dependency: ``pip install playwright && python -m playwright install chromium``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import urlparse


SKILL_NAME = "soia-cwork-processon-diagrams"
PROFILE_MARKER = ".soia-processon-browser-profile.json"
PROFILE_SCHEMA = 1
MAX_STEPS = 100
MAX_NESTING = 3
MAX_VISIBLE_TEXT = 20_000
MAX_INTERACTIVE = 250
ALLOWED_ACTIONS = {
    "goto",
    "click",
    "hover",
    "download",
    "popup",
    "back",
    "press",
    "scroll",
    "wait_text",
    "snapshot",
    "inspect_text",
    "row_menu",
}
SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|cookie|token|local[_-]?storage|session[_-]?storage|credential)",
    re.IGNORECASE,
)
REMOTE_MUTATION_LABEL = re.compile(
    r"^\s*(?:删除|重命名|移动|分享|公开分享|发布|邀请|上传|新建|创建|编辑|保存|锁定|解锁|复制|delete|rename|move|share|publish|invite|upload|create|edit|save|lock)(?:\.{3}|…)?\s*$",
    re.IGNORECASE,
)


class BrowserRunnerError(RuntimeError):
    """Safe, customer-readable runner failure."""


class ManagedBrowserFailure(BrowserRunnerError):
    """Browser failure carrying the post-cleanup lifecycle receipt."""

    def __init__(self, original: BaseException, receipt: dict[str, Any]) -> None:
        if isinstance(original, KeyboardInterrupt):
            message = "interrupted; dedicated browser context was closed"
        elif isinstance(original, BrowserRunnerError):
            message = str(original)
        else:
            message = f"browser operation failed: {type(original).__name__}: {original}"
        super().__init__(message)
        self.receipt = receipt
        self.original_type = type(original).__name__


def config_root(home: Path | None = None, environ: dict[str, str] | None = None) -> Path:
    home = home or Path.home()
    environ = environ or os.environ
    if os.name == "nt":
        return Path(environ.get("APPDATA", home / "AppData" / "Roaming"))
    return Path(environ.get("XDG_CONFIG_HOME", home / ".config"))


def default_profile_dir(
    home: Path | None = None, environ: dict[str, str] | None = None
) -> Path:
    environ = environ or os.environ
    explicit = environ.get("SOIA_CWORK_PROCESSON_BROWSER_PROFILE_DIR")
    if explicit:
        return Path(explicit).expanduser()
    return (
        config_root(home, environ)
        / "soia-skills"
        / "soia-open-skills"
        / "cwork"
        / SKILL_NAME
        / "browser-profile"
    )


def default_browser_profile_roots(
    home: Path | None = None, environ: dict[str, str] | None = None
) -> list[Path]:
    """Return known user-owned browser roots that must never be automated."""

    home = home or Path.home()
    environ = environ or os.environ
    roots = [
        home / "Library" / "Application Support" / "Google" / "Chrome",
        home / "Library" / "Application Support" / "Chromium",
        home / ".config" / "google-chrome",
        home / ".config" / "chromium",
    ]
    local_app_data = environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
        roots.extend(
            [
                base / "Google" / "Chrome" / "User Data",
                base / "Chromium" / "User Data",
            ]
        )
    return [path.resolve(strict=False) for path in roots]


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_profile_dir(
    profile_dir: Path,
    *,
    home: Path | None = None,
    environ: dict[str, str] | None = None,
) -> Path:
    profile = profile_dir.expanduser().resolve(strict=False)
    if profile.is_symlink():
        raise BrowserRunnerError("browser profile must not be a symbolic link")
    for root in default_browser_profile_roots(home, environ):
        if profile == root or is_relative_to(profile, root):
            raise BrowserRunnerError(
                "refusing to automate a normal Chrome/Chromium profile; use the skill's dedicated profile"
            )
    return profile


def ensure_dedicated_profile(profile_dir: Path) -> Path:
    profile = validate_profile_dir(profile_dir)
    if profile.exists() and not profile.is_dir():
        raise BrowserRunnerError("browser profile path exists but is not a directory")
    profile.mkdir(parents=True, exist_ok=True)
    marker = profile / PROFILE_MARKER
    existing = [path for path in profile.iterdir() if path.name != PROFILE_MARKER]
    if not marker.exists() and existing:
        raise BrowserRunnerError(
            "refusing to claim a non-empty unmarked browser profile directory"
        )
    if marker.exists():
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BrowserRunnerError("invalid dedicated browser profile marker") from exc
        if payload.get("schema_version") != PROFILE_SCHEMA or payload.get("skill") != SKILL_NAME:
            raise BrowserRunnerError("browser profile marker does not belong to this skill")
    else:
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "schema_version": PROFILE_SCHEMA,
                    "skill": SKILL_NAME,
                    "purpose": "dedicated ProcessOn browser profile; contains provider-owned login state",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(marker)
    return profile


def validate_processon_url(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "processon.com" or host.endswith(".processon.com")):
        raise BrowserRunnerError("only HTTPS ProcessOn URLs are allowed")
    return value


def target_reached(current_url: str, target_url: str) -> bool:
    current = urlparse(current_url)
    target = urlparse(target_url)
    current_path = current.path.rstrip("/") or "/"
    target_path = target.path.rstrip("/") or "/"
    login_tokens = ("login", "signin", "sign-in", "passport")
    if any(token in current_path.lower() for token in login_tokens):
        return False
    return current.hostname == target.hostname and (
        target_path == "/" or current_path.startswith(target_path)
    )


def page_requires_login(page: Any) -> bool:
    """Detect visible login controls without reading their values or auth state."""

    selectors = (
        "input[type='password']",
        "input[autocomplete='current-password']",
        "input[placeholder*='手机号']",
        "input[placeholder*='邮箱']",
        "form[action*='login']",
    )
    for selector in selectors:
        try:
            locator = page.locator(selector)
            if locator.count() and locator.first.is_visible():
                return True
        except Exception:
            continue
    return False


def target_accessible(page: Any, target_url: str) -> bool:
    return target_reached(page.url, target_url) and not page_requires_login(page)


def require_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserRunnerError(
            "missing Playwright: pip install playwright && python -m playwright install chromium"
        ) from exc
    return sync_playwright


def launch_context(playwright: Any, profile_dir: Path, *, headless: bool) -> Any:
    kwargs = {
        "headless": headless,
        "accept_downloads": True,
        "viewport": {"width": 1440, "height": 1000},
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir), channel="chrome", **kwargs
        )
    except Exception:
        return playwright.chromium.launch_persistent_context(str(profile_dir), **kwargs)


@dataclass
class SessionReceipt:
    pages_seen_at_start: int = 0
    stale_pages_closed: int = 0
    scoped_pages_opened: int = 0
    scoped_pages_closed: int = 0
    pages_closed_at_exit: int = 0
    downloaded_files: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pages_seen_at_start": self.pages_seen_at_start,
            "stale_pages_closed": self.stale_pages_closed,
            "scoped_pages_opened": self.scoped_pages_opened,
            "scoped_pages_closed": self.scoped_pages_closed,
            "pages_closed_at_exit": self.pages_closed_at_exit,
            "downloaded_files": self.downloaded_files,
        }


def safe_close_page(page: Any) -> bool:
    try:
        if not page.is_closed():
            page.close(run_before_unload=False)
        return True
    except Exception:
        return False


@contextmanager
def managed_context(
    profile_dir: Path,
    *,
    headless: bool,
    launcher: Callable[[Path, bool], Any] | None = None,
) -> Iterator[tuple[Any, Any, SessionReceipt]]:
    """Yield one managed page and close every dedicated page in ``finally``."""

    profile = ensure_dedicated_profile(profile_dir)
    receipt = SessionReceipt()
    playwright_manager = None
    context = None
    if launcher is None:
        sync_playwright = require_playwright()
        playwright_manager = sync_playwright()
        playwright = playwright_manager.__enter__()
        context = launch_context(playwright, profile, headless=headless)
    else:
        context = launcher(profile, headless)

    failure: BaseException | None = None
    try:
        pages = list(context.pages)
        receipt.pages_seen_at_start = len(pages)
        page = pages[0] if pages else context.new_page()
        for stale in pages[1:]:
            if safe_close_page(stale):
                receipt.stale_pages_closed += 1
        yield context, page, receipt
    except BaseException as exc:
        failure = exc
    finally:
        if context is not None:
            remaining = list(context.pages)
            for page in remaining:
                if safe_close_page(page):
                    receipt.pages_closed_at_exit += 1
            try:
                context.close()
            except Exception:
                pass
        if playwright_manager is not None:
            try:
                playwright_manager.__exit__(None, None, None)
            except Exception:
                pass
    if failure is not None:
        raise ManagedBrowserFailure(failure, receipt.as_dict()) from failure


def bounded_snapshot(page: Any) -> dict[str, Any]:
    body = page.locator("body")
    try:
        visible_text = body.inner_text(timeout=5_000)[:MAX_VISIBLE_TEXT]
    except Exception:
        visible_text = ""
    items: list[dict[str, str]] = []
    locator = page.locator(
        "a,button,[role='button'],[role='menuitem'],[role='link'],input,textarea,"
        "[contenteditable='true'],[title],[aria-label],[data-title],[data-tooltip]"
    )
    try:
        count = min(locator.count(), MAX_INTERACTIVE)
    except Exception:
        count = 0
    for index in range(count):
        item = locator.nth(index)
        try:
            if not item.is_visible():
                continue
            label = (
                item.get_attribute("aria-label")
                or item.get_attribute("title")
                or item.get_attribute("data-title")
                or item.get_attribute("data-tooltip")
                or item.inner_text(timeout=1_000)
                or ""
            ).strip()[:500]
            role = (item.get_attribute("role") or "").strip()
            href = (item.get_attribute("href") or "").strip()
            items.append({"index": str(index), "role": role, "name": label, "href": href})
        except Exception:
            continue
    return {
        "url": page.url,
        "title": page.title(),
        "visible_text": visible_text,
        "interactive": items,
        "truncated": len(visible_text) >= MAX_VISIBLE_TEXT or len(items) >= MAX_INTERACTIVE,
    }


def inspect_text_structure(page: Any, step: dict[str, Any], timeout: int) -> dict[str, Any]:
    """Return a bounded, fixed DOM summary around visible text.

    The caller supplies only text/nth. The JavaScript is fixed by the skill and
    cannot be replaced through the action file.
    """

    text = str(step.get("text", ""))
    if not text:
        raise BrowserRunnerError("inspect_text requires text")
    locator = page.get_by_text(text, exact=bool(step.get("exact", True))).nth(
        int(step.get("nth", 0))
    )
    locator.wait_for(state="visible", timeout=timeout)
    return locator.evaluate(
        """
        (target) => {
          const keep = (element) => {
            const attrs = {};
            for (const attr of Array.from(element.attributes || [])) {
              if (attr.name === 'class' || attr.name === 'role' || attr.name === 'title' ||
                  attr.name === 'aria-label' || attr.name.startsWith('data-')) {
                attrs[attr.name] = String(attr.value).slice(0, 300);
              }
            }
            const children = Array.from(element.children || []).slice(0, 30).map((child) => ({
              tag: child.tagName.toLowerCase(),
              class: String(child.className || '').slice(0, 200),
              title: String(child.getAttribute('title') || '').slice(0, 200),
              aria_label: String(child.getAttribute('aria-label') || '').slice(0, 200),
              text: String(child.innerText || '').trim().slice(0, 200)
            }));
            return {
              tag: element.tagName.toLowerCase(),
              attrs,
              text: String(element.innerText || '').trim().slice(0, 500),
              children
            };
          };
          const ancestors = [];
          let node = target;
          for (let depth = 0; node && depth < 6; depth += 1, node = node.parentElement) {
            ancestors.push({depth, ...keep(node)});
          }
          return {ancestors};
        }
        """
    )


def reject_sensitive_keys(value: Any, path: str = "actions") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SENSITIVE_KEY.search(str(key)):
                raise BrowserRunnerError(f"sensitive field is forbidden in action files: {path}.{key}")
            reject_sensitive_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_keys(child, f"{path}[{index}]")


def validate_steps(steps: Any, *, depth: int = 0) -> list[dict[str, Any]]:
    if depth > MAX_NESTING:
        raise BrowserRunnerError("action nesting is too deep")
    if not isinstance(steps, list) or not steps:
        raise BrowserRunnerError("actions.steps must be a non-empty list")
    if len(steps) > MAX_STEPS:
        raise BrowserRunnerError(f"action file exceeds {MAX_STEPS} steps")
    validated: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise BrowserRunnerError(f"step {index} must be an object")
        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            raise BrowserRunnerError(f"step {index} uses unsupported action: {action!r}")
        if action == "popup":
            validate_steps(step.get("steps"), depth=depth + 1)
        validated.append(step)
    reject_sensitive_keys(validated)
    return validated


def load_action_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrowserRunnerError(f"cannot read action file: {path}") from exc
    if payload.get("schema_version") != 1:
        raise BrowserRunnerError("action file schema_version must be 1")
    validate_processon_url(str(payload.get("start_url", "")))
    validate_steps(payload.get("steps"))
    return payload


def step_locator(page: Any, step: dict[str, Any]) -> Any:
    selectors = [key for key in ("role", "text", "label") if step.get(key)]
    if len(selectors) != 1:
        raise BrowserRunnerError(
            "click/hover/download/popup step requires exactly one named semantic locator"
        )
    exact = bool(step.get("exact", True))
    if selectors[0] == "role":
        if not step.get("name"):
            raise BrowserRunnerError("role locators require a visible name")
        semantic_name = str(step["name"])
        locator = page.get_by_role(str(step["role"]), name=step.get("name"), exact=exact)
    elif selectors[0] == "text":
        semantic_name = str(step["text"])
        locator = page.get_by_text(str(step["text"]), exact=exact)
    else:
        semantic_name = str(step["label"])
        locator = page.get_by_label(str(step["label"]), exact=exact)
    if REMOTE_MUTATION_LABEL.search(semantic_name):
        raise BrowserRunnerError(
            f"remote mutation control is forbidden by this read/download runner: {semantic_name!r}"
        )
    if bool(step.get("visible", True)):
        locator = locator.filter(visible=True)
    nth = int(step.get("nth", 0))
    return locator.nth(nth)


def open_processon_row_menu(page: Any, step: dict[str, Any], timeout: int) -> None:
    """Open the provider's confirmed per-row "more" menu without arbitrary CSS input."""

    text = str(step.get("text", ""))
    if not text:
        raise BrowserRunnerError("row_menu requires a diagram title")
    title = page.get_by_text(text, exact=bool(step.get("exact", True))).filter(
        visible=True
    ).nth(int(step.get("nth", 0)))
    title.wait_for(state="visible", timeout=timeout)
    row = title.locator(
        "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' file_list_item ')][1]"
    )
    row.hover(timeout=timeout)
    trigger = row.locator("span.more.icons.icon-gengduo").filter(visible=True)
    if trigger.count() != 1:
        raise BrowserRunnerError(
            f"ProcessOn row menu trigger is ambiguous for {text!r}: {trigger.count()} visible matches"
        )
    trigger.click(timeout=timeout)


def click_locator(locator: Any, step: dict[str, Any], timeout: int) -> None:
    button = str(step.get("button", "left"))
    if button not in {"left", "right"}:
        raise BrowserRunnerError("click button must be left or right")
    click_count = int(step.get("click_count", 1))
    if click_count not in {1, 2}:
        raise BrowserRunnerError("click_count must be 1 or 2")
    locator.click(button=button, click_count=click_count, timeout=timeout)


def collision_safe_path(directory: Path, name: str) -> Path:
    safe_name = Path(name).name
    if safe_name in {"", ".", ".."}:
        raise BrowserRunnerError("download returned an invalid filename")
    candidate = directory / safe_name
    counter = 1
    while candidate.exists():
        candidate = directory / f"{Path(safe_name).stem} ({counter}){Path(safe_name).suffix}"
        counter += 1
    return candidate


def close_unexpected_pages(context: Any, expected: set[int], receipt: SessionReceipt) -> None:
    unexpected = [page for page in context.pages if id(page) not in expected]
    if not unexpected:
        return
    for page in unexpected:
        if safe_close_page(page):
            receipt.scoped_pages_closed += 1
    raise BrowserRunnerError(
        "an action opened an unexpected page; it was closed. Use a scoped popup action instead"
    )


def execute_steps(
    context: Any,
    page: Any,
    steps: list[dict[str, Any]],
    *,
    download_dir: Path,
    receipt: SessionReceipt,
    depth: int = 0,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        action = step["action"]
        timeout = int(step.get("timeout_ms", 15_000))
        if timeout < 250 or timeout > 300_000:
            raise BrowserRunnerError(f"step {index} timeout_ms is outside 250..300000")
        before = {id(candidate) for candidate in context.pages}
        result: dict[str, Any] = {"index": index, "action": action}

        if action == "goto":
            url = validate_processon_url(str(step.get("url", "")))
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_timeout(int(step.get("settle_ms", 750)))
        elif action == "click":
            click_locator(step_locator(page, step), step, timeout)
            page.wait_for_timeout(int(step.get("settle_ms", 250)))
            close_unexpected_pages(context, before, receipt)
        elif action == "hover":
            step_locator(page, step).hover(timeout=timeout)
            page.wait_for_timeout(int(step.get("settle_ms", 250)))
            close_unexpected_pages(context, before, receipt)
        elif action == "download":
            download_dir.mkdir(parents=True, exist_ok=True)
            with page.expect_download(timeout=timeout) as download_info:
                click_locator(step_locator(page, step), step, timeout)
            download = download_info.value
            destination = collision_safe_path(download_dir, download.suggested_filename)
            download.save_as(destination)
            size = destination.stat().st_size
            if size <= 0:
                raise BrowserRunnerError(f"downloaded file is empty: {destination}")
            item = {"path": str(destination), "bytes": size, "suggested_filename": download.suggested_filename}
            receipt.downloaded_files.append(item)
            result["download"] = item
            close_unexpected_pages(context, before, receipt)
        elif action == "popup":
            locator = step_locator(page, step)
            popup = None
            try:
                with context.expect_page(timeout=timeout) as popup_info:
                    click_locator(locator, step, timeout)
                popup = popup_info.value
                receipt.scoped_pages_opened += 1
                popup.wait_for_load_state("domcontentloaded", timeout=timeout)
                popup.wait_for_timeout(int(step.get("settle_ms", 1_000)))
                result["steps"] = execute_steps(
                    context,
                    popup,
                    validate_steps(step["steps"], depth=depth + 1),
                    download_dir=download_dir,
                    receipt=receipt,
                    depth=depth + 1,
                )
            finally:
                if popup is not None and safe_close_page(popup):
                    receipt.scoped_pages_closed += 1
            close_unexpected_pages(context, before, receipt)
        elif action == "back":
            page.go_back(wait_until="domcontentloaded", timeout=timeout)
        elif action == "press":
            key = str(step.get("key", ""))
            if key not in {"Escape", "ArrowDown", "ArrowUp", "Tab"}:
                raise BrowserRunnerError(f"step {index} uses a forbidden key")
            page.keyboard.press(key)
        elif action == "scroll":
            delta_y = int(step.get("delta_y", 0))
            if delta_y == 0 or abs(delta_y) > 10_000:
                raise BrowserRunnerError("scroll delta_y must be non-zero and within -10000..10000")
            page.mouse.wheel(0, delta_y)
            page.wait_for_timeout(int(step.get("settle_ms", 250)))
        elif action == "wait_text":
            text = str(step.get("text", ""))
            if not text:
                raise BrowserRunnerError(f"step {index} wait_text requires text")
            page.get_by_text(text, exact=bool(step.get("exact", False))).filter(
                visible=True
            ).nth(int(step.get("nth", 0))).wait_for(state="visible", timeout=timeout)
        elif action == "snapshot":
            result["snapshot"] = bounded_snapshot(page)
        elif action == "inspect_text":
            result["structure"] = inspect_text_structure(page, step, timeout)
        elif action == "row_menu":
            open_processon_row_menu(page, step, timeout)
            page.wait_for_timeout(int(step.get("settle_ms", 250)))
            close_unexpected_pages(context, before, receipt)

        result["url"] = page.url
        results.append(result)
    return results


def cmd_login(args: argparse.Namespace) -> dict[str, Any]:
    url = validate_processon_url(args.url)
    receipt = None
    reached_url = ""
    print(
        "请只在技能弹出的独立 ProcessOn 窗口中手动登录；无需向 Agent 提供密码或验证码。",
        file=sys.stderr,
    )
    with managed_context(args.profile_dir, headless=False) as (_context, page, receipt):
        page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        deadline = time.monotonic() + args.wait_seconds
        while time.monotonic() < deadline:
            if target_accessible(page, url):
                reached_url = page.url
                break
            page.wait_for_timeout(500)
        else:
            raise BrowserRunnerError(
                f"manual login did not reach the target within {args.wait_seconds} seconds"
            )
    assert receipt is not None
    return {
        "ok": True,
        "action": "login",
        "target_reached": True,
        "url": reached_url,
        "profile_dir": str(args.profile_dir),
        "receipt": receipt.as_dict(),
    }


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    url = validate_processon_url(args.url)
    receipt = None
    with managed_context(args.profile_dir, headless=not args.headed) as (_context, page, receipt):
        page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        page.wait_for_timeout(args.settle_ms)
        accessible = target_accessible(page, url)
        reached_url = page.url
        title = page.title()
    assert receipt is not None
    return {
        "ok": accessible,
        "action": "status",
        "target_reached": accessible,
        "url": reached_url,
        "title": title,
        "profile_dir": str(args.profile_dir),
        "receipt": receipt.as_dict(),
    }


def cmd_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    url = validate_processon_url(args.url)
    receipt = None
    with managed_context(args.profile_dir, headless=not args.headed) as (_context, page, receipt):
        page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        page.wait_for_timeout(args.settle_ms)
        accessible = target_accessible(page, url)
        snapshot = bounded_snapshot(page)
    assert receipt is not None
    return {
        "ok": accessible,
        "action": "snapshot",
        "snapshot": snapshot,
        "receipt": receipt.as_dict(),
    }


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_action_file(args.actions)
    receipt = None
    with managed_context(args.profile_dir, headless=not args.headed) as (context, page, receipt):
        page.goto(payload["start_url"], wait_until="domcontentloaded", timeout=args.timeout_ms)
        page.wait_for_timeout(args.settle_ms)
        if not target_accessible(page, payload["start_url"]):
            raise BrowserRunnerError("dedicated profile is not logged in for the requested ProcessOn URL")
        results = execute_steps(
            context,
            page,
            payload["steps"],
            download_dir=args.download_dir,
            receipt=receipt,
        )
    assert receipt is not None
    return {
        "ok": True,
        "action": "run",
        "results": results,
        "receipt": receipt.as_dict(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dir", type=Path, default=default_profile_dir())
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=2_000,
        help="wait after initial navigation for ProcessOn SPA rendering (default: 2000)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="one-time manual login in the dedicated profile")
    login.add_argument("--url", required=True)
    login.add_argument("--wait-seconds", type=int, default=600)
    login.set_defaults(func=cmd_login)

    status = sub.add_parser("status", help="verify access using the dedicated profile")
    status.add_argument("--url", required=True)
    status.add_argument("--headed", action="store_true")
    status.set_defaults(func=cmd_status)

    snapshot = sub.add_parser("snapshot", help="return a bounded semantic page snapshot")
    snapshot.add_argument("--url", required=True)
    snapshot.add_argument("--headed", action="store_true")
    snapshot.set_defaults(func=cmd_snapshot)

    run = sub.add_parser("run", help="execute a declarative ProcessOn action file")
    run.add_argument("--actions", type=Path, required=True)
    run.add_argument("--download-dir", type=Path, required=True)
    run.add_argument("--headed", action="store_true")
    run.set_defaults(func=cmd_run)
    return parser


def install_signal_guards() -> None:
    def interrupt(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)


def main(argv: list[str] | None = None) -> int:
    install_signal_guards()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.profile_dir = validate_profile_dir(args.profile_dir)
    if args.timeout_ms < 250 or args.timeout_ms > 300_000:
        print(json.dumps({"ok": False, "error": "timeout-ms must be 250..300000"}))
        return 2
    if args.settle_ms < 0 or args.settle_ms > 30_000:
        print(json.dumps({"ok": False, "error": "settle-ms must be 0..30000"}))
        return 2
    try:
        result = args.func(args)
    except ManagedBrowserFailure as exc:
        result = {
            "ok": False,
            "error": str(exc),
            "error_type": exc.original_type,
            "receipt": exc.receipt,
        }
    except KeyboardInterrupt:
        result = {"ok": False, "error": "interrupted; dedicated browser context was closed"}
    except BrowserRunnerError as exc:
        result = {"ok": False, "error": str(exc)}
    except Exception as exc:
        result = {"ok": False, "error": f"browser operation failed: {type(exc).__name__}: {exc}"}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
