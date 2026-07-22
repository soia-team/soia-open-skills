#!/usr/bin/env python3
"""Download and archive a bounded ProcessOn batch with fixed headless workers.

The script uses one skill-owned persistent browser context and 1-3 fixed pages.
It never attaches to a user's normal Chrome. Every source popup closes in
``finally``; every worker page and the whole context close on every exit path.
Downloads may run concurrently, while finalization, metadata, source-link and
archive-progress writes are serialized by one writer in the parent process.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

from processon_browser_runner import (
    BrowserRunnerError,
    default_profile_dir,
    ensure_dedicated_profile,
    target_reached,
    validate_processon_url,
    validate_profile_dir,
)


SCRIPT_DIR = Path(__file__).resolve().parent
ARCHIVE_STATE = SCRIPT_DIR / "processon_archive_state.py"
FINALIZER = SCRIPT_DIR / "finalize_processon_download.py"
MAX_WORKERS = 3
MAX_BATCH = 60
READY_ATTEMPTS = 2
MAX_ZIP_ENTRIES = 10_000
MAX_ZIP_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ZIP_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
COMMON_TITLE_WORDS = (
    "生产环境",
    "测试环境",
    "新测试环境",
    "部署架构图",
    "部署图",
    "架构图",
    "流程图",
    "示意图",
    "系统",
    "未上生产",
)


class BatchError(RuntimeError):
    """Fail-closed batch error."""


@dataclass
class BrowserReceipt:
    pages_seen_at_start: int = 0
    stale_pages_closed: int = 0
    worker_pages_opened: int = 0
    worker_pages_closed: int = 0
    scoped_pages_opened: int = 0
    scoped_pages_closed: int = 0
    pages_closed_at_exit: int = 0
    downloaded_files: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pages_seen_at_start": self.pages_seen_at_start,
            "stale_pages_closed": self.stale_pages_closed,
            "worker_pages_opened": self.worker_pages_opened,
            "worker_pages_closed": self.worker_pages_closed,
            "scoped_pages_opened": self.scoped_pages_opened,
            "scoped_pages_closed": self.scoped_pages_closed,
            "pages_closed_at_exit": self.pages_closed_at_exit,
            "downloaded_files": self.downloaded_files,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BatchError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise BatchError(f"JSON root must be an object: {path}")
    return value


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = completed.stdout.strip() or completed.stderr.strip()
        raise BatchError(f"command failed ({completed.returncode}): {detail[:2000]}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BatchError(f"command returned non-JSON output: {completed.stdout[:1000]}") from exc
    if not isinstance(payload, dict):
        raise BatchError("command JSON result must be an object")
    return payload


def progress_done_ids(progress: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key in ("completed", "failed", "blocked"):
        values = progress.get(key, [])
        if not isinstance(values, list):
            raise BatchError(f"progress.{key} must be a list")
        for item in values:
            if isinstance(item, dict) and item.get("artifact_id"):
                result.add(str(item["artifact_id"]))
    return result


def validate_plan(plan: dict[str, Any], progress: dict[str, Any]) -> None:
    entries = plan.get("entries")
    if plan.get("schema_version") != 1 or not isinstance(entries, list):
        raise BatchError("archive plan must be schema 1 with entries")
    expected_sha = progress.get("plan", {}).get("sha256")
    if not expected_sha:
        raise BatchError("progress is missing plan.sha256")
    # The state CLI performs the authoritative plan fingerprint verification.


@contextmanager
def exclusive_lock(path: Path):
    """Hold one cross-platform writer lock for the full orchestrator run."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise BatchError(f"lock file must not be a symlink: {path}")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise BatchError(f"cannot safely open lock file: {path}") from exc
    handle = os.fdopen(descriptor, "r+b", buffering=0)
    locked = False
    try:
        descriptor_stat = os.fstat(handle.fileno())
        path_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(descriptor_stat.st_mode):
            raise BatchError(f"lock file is not a regular file: {path}")
        if descriptor_stat.st_nlink != 1:
            raise BatchError(f"lock file must have exactly one hard link: {path}")
        if (descriptor_stat.st_dev, descriptor_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
            raise BatchError(f"lock file changed while opening: {path}")
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            if handle.read(1) == b"":
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise BatchError(f"another archive orchestrator holds the lock: {path}") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise BatchError(f"another archive orchestrator holds the lock: {path}") from exc
        locked = True
        # The lock file is deliberately never written. This makes an unexpected
        # hard-link race non-destructive even after the preflight identity check.
        yield
    finally:
        if locked:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def validate_concurrency_proof(
    path: Path | None, *, workers: int, plan: dict[str, Any], progress: dict[str, Any]
) -> dict[str, Any] | None:
    if workers == 1:
        return None
    if path is None:
        raise BatchError("--concurrency-proof is required when --workers is greater than 1")
    proof = load_json(path)
    if proof.get("schema_version") != 1 or proof.get("status") != "passed":
        raise BatchError("concurrency proof is not a passed schema-1 proof")
    if int(proof.get("max_workers", 0)) < workers:
        raise BatchError(f"concurrency proof permits fewer than {workers} workers")
    if proof.get("plan_sha256") != progress.get("plan", {}).get("sha256"):
        raise BatchError("concurrency proof belongs to another archive plan")
    samples = proof.get("samples")
    if not isinstance(samples, list) or len(samples) < workers:
        raise BatchError("concurrency proof has too few independently verified samples")
    if any(sample.get("semantic_status") != "matched" for sample in samples):
        raise BatchError("concurrency proof contains a sample without semantic matching")
    for identity_key in ("artifact_id", "source_url", "sha256"):
        values = [str(sample.get(identity_key, "")) for sample in samples[:workers]]
        if any(not value for value in values) or len(set(values)) != workers:
            raise BatchError(
                f"concurrency proof samples must have {workers} distinct {identity_key} values"
            )
    plan_by_id = {
        str(entry.get("artifact_id", "")): entry
        for entry in plan.get("entries", [])
        if entry.get("artifact_id")
    }
    for sample in samples[:workers]:
        artifact_id = str(sample.get("artifact_id", ""))
        entry = plan_by_id.get(artifact_id)
        if entry is None:
            raise BatchError(f"concurrency proof sample is not in the current plan: {artifact_id}")
        if str(sample.get("title", "")) != str(entry.get("title", "")):
            raise BatchError(f"concurrency proof title differs from the plan: {artifact_id}")
        completed = next(
            (
                item
                for item in progress.get("completed", [])
                if str(item.get("artifact_id", "")) == artifact_id
            ),
            None,
        )
        if not completed:
            raise BatchError(
                f"concurrency proof sample has no completed archive evidence: {artifact_id}"
            )
        destination = Path(str(completed.get("archive_destination", "")))
        if not destination.is_file() or destination.is_symlink():
            raise BatchError(f"concurrency proof archive file is unavailable: {artifact_id}")
        actual_sha256 = sha256(destination)
        if (
            str(sample.get("sha256", "")) != actual_sha256
            or str(completed.get("sha256", "")) != actual_sha256
        ):
            raise BatchError(f"concurrency proof SHA-256 is not replayable: {artifact_id}")
        inspection = inspect_download(destination, entry)
        if inspection.get("semantic_status") != "matched":
            raise BatchError(f"concurrency proof semantic evidence did not replay: {artifact_id}")
        metadata_path = destination.parent / "metadata.yml"
        if not metadata_path.is_file() or metadata_path.is_symlink():
            raise BatchError(f"concurrency proof metadata is unavailable: {artifact_id}")
        metadata = read_top_level_metadata(metadata_path)
        if (
            str(metadata.get("artifact_id", "")) != artifact_id
            or str(metadata.get("sha256", "")) != actual_sha256
            or str(metadata.get("title", "")) != str(entry.get("title", ""))
        ):
            raise BatchError(f"concurrency proof metadata differs from the archive: {artifact_id}")
        sample_url = str(sample.get("source_url", ""))
        sample_remote_id = str(sample.get("remote_id", ""))
        observed_remote_id = verify_source_identity(
            {"source_url": sample_url, "remote_id": sample_remote_id}, sample_url
        )
        expected_url = str(metadata.get("source_url") or "").strip()
        expected_remote_id = str(metadata.get("remote_id") or "").strip()
        plan_url = str(entry.get("source_url") or "").strip()
        plan_remote_id = str(entry.get("remote_id") or "").strip()
        if plan_url and normalized_processon_source_url(plan_url) != normalized_processon_source_url(
            expected_url
        ):
            raise BatchError(f"plan source URL differs from archived evidence: {artifact_id}")
        if plan_remote_id and plan_remote_id != expected_remote_id:
            raise BatchError(f"plan remote id differs from archived evidence: {artifact_id}")
        if normalized_processon_source_url(sample_url) != normalized_processon_source_url(
            expected_url
        ) or observed_remote_id != expected_remote_id:
            raise BatchError(
                f"concurrency proof source identity differs from archived evidence: {artifact_id}"
            )
    lifecycle = proof.get("lifecycle", {})
    scoped_opened = int(lifecycle.get("scoped_pages_opened", 0))
    scoped_closed = int(lifecycle.get("scoped_pages_closed", 0))
    if scoped_opened != scoped_closed or scoped_opened < workers:
        raise BatchError("concurrency proof has unmatched popup lifecycle counts")
    worker_opened = int(lifecycle.get("worker_pages_opened", 0))
    worker_closed = int(lifecycle.get("worker_pages_closed", 0))
    if worker_opened != worker_closed or worker_opened < workers:
        raise BatchError("concurrency proof has unmatched worker-page lifecycle counts")
    if "pages_remaining" in lifecycle and int(lifecycle["pages_remaining"]) != 0:
        raise BatchError("concurrency proof left browser pages open")
    if "pages_closed_at_exit" in lifecycle and int(lifecycle["pages_closed_at_exit"]) != 0:
        raise BatchError("concurrency proof relied on context-exit cleanup for live pages")
    if "pages_remaining" not in lifecycle and "pages_closed_at_exit" not in lifecycle:
        raise BatchError("concurrency proof is missing final page lifecycle evidence")
    return proof


def safe_relative_parts(source_path: str) -> tuple[str, ...]:
    pure = PurePosixPath(source_path)
    if pure.is_absolute() or not pure.parts:
        raise BatchError(f"invalid source_path: {source_path!r}")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise BatchError(f"unsafe source_path: {source_path!r}")
    return pure.parts


def output_folder(output_root: Path, entry: dict[str, Any]) -> Path:
    parts = list(safe_relative_parts(str(entry["source_path"])))
    if entry.get("collision_risk") not in {None, "", "none_detected"}:
        parts[-1] = f"{parts[-1]}--{str(entry['artifact_id'])[:8]}"
    root = output_root.expanduser().resolve(strict=False)
    target = root.joinpath(*parts).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise BatchError(f"archive target escapes output root: {target}") from exc
    return target


def choose_entries(
    plan: dict[str, Any], progress: dict[str, Any], limit: int, *, workers: int
) -> list[dict[str, Any]]:
    done = progress_done_ids(progress)
    selected: list[dict[str, Any]] = []
    for entry in plan["entries"]:
        if entry.get("confirmation_required") or entry.get("type") == "unknown":
            continue
        artifact_id = str(entry.get("artifact_id", ""))
        if not artifact_id or artifact_id in done:
            continue
        if entry.get("collision_risk") not in {None, "", "none_detected"}:
            continue
        selected.append(entry)
        if len(selected) >= limit:
            break
    return selected


def deferred_collision_entries(
    plan: dict[str, Any], progress: dict[str, Any]
) -> list[dict[str, Any]]:
    done = progress_done_ids(progress)
    return [
        entry
        for entry in plan["entries"]
        if str(entry.get("artifact_id", "")) not in done
        and not entry.get("confirmation_required")
        and entry.get("type") != "unknown"
        and entry.get("collision_risk") not in {None, "", "none_detected"}
    ]


def legacy_flat_download_review(progress: dict[str, Any]) -> dict[str, Any]:
    downloads_root = (Path.home() / "Downloads").resolve(strict=False)
    flat: list[dict[str, Any]] = []
    numbered: list[dict[str, Any]] = []
    for item in progress.get("completed", []):
        if not isinstance(item, dict) or not item.get("download_source"):
            continue
        source = Path(str(item["download_source"])).expanduser().resolve(strict=False)
        if source.parent != downloads_root:
            continue
        summary = {
            "artifact_id": str(item.get("artifact_id", "")),
            "source_path": str(item.get("source_path", "")),
            "download_source": str(source),
            "archive_destination": str(item.get("archive_destination", "")),
        }
        flat.append(summary)
        if re.search(r" \(\d+\)$", source.stem):
            numbered.append(summary)
    return {
        "flat_downloads_completed_count": len(flat),
        "numbered_suffix_review_count": len(numbered),
        "numbered_suffix_items": numbered,
    }


def build_jobs(entries: list[dict[str, Any]], workers: int) -> list[tuple[str, list[dict[str, Any]]]]:
    by_directory: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for entry in entries:
        by_directory.setdefault(str(entry["source_directory"]), []).append(entry)
    jobs: list[tuple[str, list[dict[str, Any]]]] = []
    for directory, items in by_directory.items():
        shard_count = min(workers, len(items)) if len(items) >= workers else 1
        shards = [[] for _ in range(shard_count)]
        for index, item in enumerate(items):
            shards[index % shard_count].append(item)
        jobs.extend((directory, shard) for shard in shards if shard)
    return jobs


def directory_segments(root_path: str, source_directory: str) -> list[str]:
    root_parts = safe_relative_parts(root_path)
    directory_parts = safe_relative_parts(source_directory)
    if tuple(directory_parts[: len(root_parts)]) != root_parts:
        raise BatchError(f"directory is outside plan root: {source_directory}")
    return list(directory_parts[len(root_parts) :])


async def wait_visible_text(page: Any, text: str, timeout_ms: int) -> Any:
    locator = page.get_by_text(text, exact=True).filter(visible=True).nth(0)
    await locator.wait_for(state="visible", timeout=timeout_ms)
    return locator


async def wait_folder_row(page: Any, text: str, timeout_ms: int) -> Any:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        candidates = page.get_by_text(text, exact=True).filter(visible=True)
        count = await candidates.count()
        matches: list[Any] = []
        for index in range(count):
            candidate = candidates.nth(index)
            row = candidate.locator(
                "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' file_list_item ')][1]"
            )
            if await row.count():
                matches.append(candidate)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise BatchError(f"folder row is ambiguous: {text!r}")
        await page.wait_for_timeout(300)
    raise BatchError(f"folder row did not become visible: {text!r}")


async def reset_to_team_root(page: Any, root_label: str, timeout_ms: int) -> None:
    breadcrumb = page.locator("div.breadc").filter(visible=True).nth(0)
    await breadcrumb.wait_for(state="visible", timeout=timeout_ms)
    crumbs = breadcrumb.locator("div.wrap_bre")
    if await crumbs.count() < 1:
        raise BatchError("ProcessOn breadcrumb has no root item")
    first = crumbs.nth(0)
    if (await first.inner_text()).strip() != root_label:
        raise BatchError("ProcessOn breadcrumb root differs from archive plan root")
    if await crumbs.count() > 1:
        link = first.locator("div.wrap_link")
        await link.click(timeout=timeout_ms)
        await page.wait_for_timeout(1200)
    refreshed = page.locator("div.breadc").filter(visible=True).nth(0).locator("div.wrap_bre")
    if await refreshed.count() != 1 or (await refreshed.nth(0).inner_text()).strip() != root_label:
        raise BatchError("failed to reset ProcessOn breadcrumb to the team root")


async def async_target_accessible(page: Any, target_url: str) -> bool:
    if not target_reached(page.url, target_url):
        return False
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
            if await locator.count() and await locator.first.is_visible():
                return False
        except Exception:
            continue
    return True


async def async_safe_close_page(page: Any) -> bool:
    try:
        if not page.is_closed():
            await page.close(run_before_unload=False)
        return True
    except Exception:
        return False


async def navigate_directory(
    page: Any,
    *,
    team_url: str,
    root_path: str,
    source_directory: str,
    settle_ms: int,
    timeout_ms: int,
) -> None:
    root_label = safe_relative_parts(root_path)[-1]
    segments = directory_segments(root_path, source_directory)
    last_error: Exception | None = None
    for attempt in range(READY_ATTEMPTS):
        try:
            await page.goto(team_url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(settle_ms + attempt * 1000)
            if not await async_target_accessible(page, team_url):
                raise BatchError("dedicated ProcessOn profile is not logged in")
            await reset_to_team_root(page, root_label, min(timeout_ms, 20_000))
            for segment in segments:
                locator = await wait_folder_row(page, segment, min(timeout_ms, 20_000))
                await locator.click(click_count=2, timeout=timeout_ms)
                await page.wait_for_timeout(1200)
            return
        except Exception as exc:
            last_error = exc
            if attempt + 1 < READY_ATTEMPTS:
                continue
    raise BatchError(
        f"directory did not become ready after {READY_ATTEMPTS} attempts: "
        f"{source_directory}; {type(last_error).__name__}: {last_error}"
    )


async def find_title(page: Any, title: str, timeout_ms: int) -> Any:
    deadline = time.monotonic() + timeout_ms / 1000
    previous_marker: tuple[int, str] | None = None
    unchanged = 0
    while time.monotonic() < deadline:
        locator = page.get_by_text(title, exact=True).filter(visible=True).nth(0)
        try:
            if await locator.count() and await locator.is_visible():
                return locator
        except Exception:
            pass
        marker = (
            int(await page.evaluate("() => Math.round(window.scrollY || 0)")),
            (await page.locator("body").inner_text())[-500:],
        )
        unchanged = unchanged + 1 if marker == previous_marker else 0
        previous_marker = marker
        if unchanged >= 2:
            break
        await page.mouse.move(720, 850)
        await page.mouse.wheel(0, 900)
        await page.wait_for_timeout(350)
    raise BatchError(f"title is not visible after bounded virtual-list scroll: {title}")


def safe_download_path(download_dir: Path, artifact_id: str, suggested_filename: str) -> Path:
    name = Path(suggested_filename).name
    if name in {"", ".", ".."}:
        raise BatchError("ProcessOn returned an invalid filename")
    artifact_dir = download_dir / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    destination = artifact_dir / name
    if destination.exists():
        destination = artifact_dir / f"{Path(name).stem}--{time.time_ns()}{Path(name).suffix}"
    return destination


async def download_one(
    page: Any,
    entry: dict[str, Any],
    *,
    download_dir: Path,
    timeout_ms: int,
    receipt: BrowserReceipt,
) -> dict[str, Any]:
    artifact_id = str(entry["artifact_id"])
    title = str(entry["title"])
    popup = None
    result: dict[str, Any] = {
        "artifact_id": artifact_id,
        "source_path": entry["source_path"],
        "title": title,
        "requested_format": entry["primary_format"],
    }
    try:
        title_locator = await find_title(page, title, timeout_ms)
        # Bind the popup to the page that initiated the click. A context-wide
        # page listener can fulfill multiple concurrent waiters with the same
        # popup and silently cross-wire two artifacts.
        async with page.expect_popup(timeout=timeout_ms) as popup_info:
            await title_locator.click(timeout=timeout_ms)
        popup = await popup_info.value
        receipt.scoped_pages_opened += 1
        await popup.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        await popup.wait_for_timeout(900)
        source_url = validate_processon_url(popup.url)
        source_title = await popup.title()
        if not source_title_matches(title, source_title):
            raise BatchError(f"source popup title mismatch: expected {title!r}, got {source_title!r}")
        remote_id = verify_source_identity(entry, source_url)
        result["source_url"] = source_url
        result["source_title"] = source_title
        result["remote_id"] = remote_id
        await popup.close(run_before_unload=False)
        receipt.scoped_pages_closed += 1
        popup = None

        # Reacquire after opening/closing the editor; SPA may have replaced nodes.
        title_locator = await find_title(page, title, timeout_ms)
        await title_locator.hover(timeout=timeout_ms)
        row = title_locator.locator(
            "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' file_list_item ')][1]"
        )
        trigger = row.locator("span.more.icons.icon-gengduo").filter(visible=True)
        if await trigger.count() != 1:
            raise BatchError(f"ambiguous ProcessOn row menu for {title!r}")
        await trigger.click(timeout=timeout_ms)
        download_label = page.get_by_text("下载", exact=False).filter(visible=True).nth(0)
        await download_label.hover(timeout=timeout_ms)
        menu_label = str(entry["primary_menu"])
        menu = page.get_by_text(menu_label, exact=True).filter(visible=True).nth(0)
        await menu.wait_for(state="visible", timeout=timeout_ms)
        async with page.expect_download(timeout=max(timeout_ms, 60_000)) as download_info:
            await menu.click(timeout=timeout_ms)
        download = await download_info.value
        suggested = download.suggested_filename
        expected_suffix = f".{entry['primary_format'].lower()}"
        if Path(suggested).suffix.lower() != expected_suffix:
            raise BatchError(
                f"download suffix mismatch for {title!r}: expected {expected_suffix}, got {suggested!r}"
            )
        if Path(suggested).stem != title:
            raise BatchError(
                f"download title mismatch for {title!r}: suggested filename is {suggested!r}"
            )
        destination = safe_download_path(download_dir, artifact_id, suggested)
        await download.save_as(destination)
        size = destination.stat().st_size
        if size <= 0:
            raise BatchError(f"downloaded file is empty: {destination}")
        item = {
            "artifact_id": artifact_id,
            "path": str(destination),
            "bytes": size,
            "suggested_filename": suggested,
        }
        receipt.downloaded_files.append(item)
        result["download"] = item
        result["ok"] = True
        return result
    except Exception as exc:
        result.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return result
    finally:
        if popup is not None and not popup.is_closed():
            if await async_safe_close_page(popup):
                receipt.scoped_pages_closed += 1


async def worker_loop(
    worker_id: int,
    context: Any,
    queue: asyncio.Queue[tuple[str, list[dict[str, Any]]] | None],
    *,
    plan: dict[str, Any],
    team_url: str,
    download_dir: Path,
    settle_ms: int,
    timeout_ms: int,
    receipt: BrowserReceipt,
) -> list[dict[str, Any]]:
    page = await context.new_page()
    receipt.worker_pages_opened += 1
    results: list[dict[str, Any]] = []
    try:
        await asyncio.sleep(worker_id * 1.5)
        while True:
            job = await queue.get()
            if job is None:
                queue.task_done()
                break
            directory, entries = job
            try:
                await navigate_directory(
                    page,
                    team_url=team_url,
                    root_path=str(plan["root_path"]),
                    source_directory=directory,
                    settle_ms=settle_ms,
                    timeout_ms=timeout_ms,
                )
                for entry in entries:
                    results.append(
                        await download_one(
                            page,
                            entry,
                            download_dir=download_dir,
                            timeout_ms=timeout_ms,
                            receipt=receipt,
                        )
                    )
            except Exception as exc:
                for entry in entries:
                    results.append(
                        {
                            "ok": False,
                            "artifact_id": entry["artifact_id"],
                            "source_path": entry["source_path"],
                            "title": entry["title"],
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
            finally:
                queue.task_done()
        return results
    finally:
        if not page.is_closed():
            await page.close(run_before_unload=False)
            receipt.worker_pages_closed += 1


async def browser_download_batch(
    entries: list[dict[str, Any]],
    *,
    plan: dict[str, Any],
    team_url: str,
    profile_dir: Path,
    download_dir: Path,
    workers: int,
    settle_ms: int,
    timeout_ms: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise BatchError("missing Playwright; install playwright and Chromium") from exc

    profile = ensure_dedicated_profile(profile_dir)
    receipt = BrowserReceipt()
    results: list[dict[str, Any]] = []
    async with async_playwright() as playwright:
        kwargs = {
            "headless": True,
            "accept_downloads": True,
            "viewport": {"width": 1440, "height": 1000},
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        try:
            context = await playwright.chromium.launch_persistent_context(
                str(profile), channel="chrome", **kwargs
            )
        except Exception:
            context = await playwright.chromium.launch_persistent_context(str(profile), **kwargs)
        try:
            initial = list(context.pages)
            receipt.pages_seen_at_start = len(initial)
            for stale in initial:
                if await async_safe_close_page(stale):
                    receipt.stale_pages_closed += 1
            queue: asyncio.Queue[tuple[str, list[dict[str, Any]]] | None] = asyncio.Queue()
            for job in build_jobs(entries, workers):
                queue.put_nowait(job)
            actual_workers = min(workers, max(1, queue.qsize()))
            for _ in range(actual_workers):
                queue.put_nowait(None)
            tasks = [
                asyncio.create_task(
                    worker_loop(
                        worker_id,
                        context,
                        queue,
                        plan=plan,
                        team_url=team_url,
                        download_dir=download_dir,
                        settle_ms=settle_ms,
                        timeout_ms=timeout_ms,
                        receipt=receipt,
                    )
                )
                for worker_id in range(actual_workers)
            ]
            await queue.join()
            for worker_results in await asyncio.gather(*tasks):
                results.extend(worker_results)
        finally:
            for page in list(context.pages):
                if await async_safe_close_page(page):
                    receipt.pages_closed_at_exit += 1
            await context.close()
    return results, receipt.as_dict()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def source_title_matches(expected: str, observed: str) -> bool:
    return observed in {expected, f"{expected}-ProcessOn"}


def normalized_processon_source_url(value: str) -> str:
    validated = validate_processon_url(value)
    parsed = urlparse(validated)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def verify_source_identity(entry: dict[str, Any], observed_url: str) -> str:
    normalized_observed = normalized_processon_source_url(observed_url)
    parsed = urlparse(normalized_observed)
    remote_id = parsed.path.rstrip("/").split("/")[-1]
    if not remote_id:
        raise BatchError(f"source popup URL has no remote id: {observed_url}")
    expected_remote_id = str(entry.get("remote_id") or "").strip()
    if expected_remote_id and expected_remote_id != remote_id:
        raise BatchError(
            f"source popup remote id mismatch: expected {expected_remote_id!r}, got {remote_id!r}"
        )
    expected_url = str(entry.get("source_url") or "").strip()
    if expected_url:
        normalized_expected = normalized_processon_source_url(expected_url)
        if normalized_expected != normalized_observed:
            raise BatchError(
                f"source popup URL mismatch: expected {normalized_expected!r}, got {normalized_observed!r}"
            )
    return remote_id


def title_signals(title: str) -> list[str]:
    candidates: list[str] = []
    candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9_.-]{1,}", title))
    cleaned = title
    for word in COMMON_TITLE_WORDS:
        cleaned = cleaned.replace(word, "")
    for piece in re.split(r"[\s《》()（）\[\]【】,，、:：/&+_\-.]+", cleaned):
        piece = piece.strip()
        if len(piece) >= 2 and not piece.isdigit():
            candidates.append(piece)
    result: list[str] = []
    for candidate in candidates:
        value = normalized_text(candidate)
        if value and value not in result:
            result.append(value)
    return result


def validate_zip_archive(archive: zipfile.ZipFile) -> list[str]:
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise BatchError(f"ZIP contains too many entries: {len(infos)}")
    total = 0
    names: list[str] = []
    for info in infos:
        raw_name = info.filename
        normalized_name = raw_name.replace("\\", "/")
        pure = PurePosixPath(normalized_name)
        if (
            not raw_name
            or "\\" in raw_name
            or pure.is_absolute()
            or any(part in {"", ".", ".."} for part in pure.parts)
            or (pure.parts and re.fullmatch(r"[A-Za-z]:", pure.parts[0]))
        ):
            raise BatchError(f"ZIP contains an unsafe member path: {raw_name!r}")
        if info.file_size > MAX_ZIP_MEMBER_BYTES:
            raise BatchError(f"ZIP member is too large: {raw_name!r}")
        total += info.file_size
        if total > MAX_ZIP_UNCOMPRESSED_BYTES:
            raise BatchError("ZIP uncompressed size exceeds the safety limit")
        names.append(raw_name)
    return names


def inspect_vsdx(path: Path, title: str) -> dict[str, Any]:
    texts: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = validate_zip_archive(archive)
        if "visio/document.xml" not in names:
            raise BatchError("VSDX is missing visio/document.xml")
        page_parts = sorted(
            name
            for name in names
            if re.fullmatch(r"visio/pages/page\d+\.xml", name)
        )
        if not page_parts:
            raise BatchError("VSDX contains no page XML")
        for name in page_parts:
            root = ElementTree.fromstring(archive.read(name))
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] == "Text":
                    text = "".join(element.itertext()).strip()
                    if text:
                        texts.append(text)
    combined = normalized_text("\n".join(texts))
    signals = title_signals(title)
    if not signals:
        raise BatchError(f"VSDX title has no distinctive signal and cannot be verified: {title!r}")
    matched = [signal for signal in signals if signal in combined]
    if not matched:
        raise BatchError(
            f"VSDX semantic title check failed; no distinctive title signal was found: {signals[:8]}"
        )
    return {
        "kind": "visio-vsdx",
        "package_entries": len(names),
        "page_part_count": len(page_parts),
        "text_count": len(texts),
        "title_signals": signals,
        "matched_title_signals": matched,
        "semantic_status": "matched",
    }


def xmind_topic_title(topic: Any) -> str:
    if isinstance(topic, dict):
        title = topic.get("title")
        if isinstance(title, str):
            return title
    return ""


def inspect_xmind(path: Path, title: str) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = validate_zip_archive(archive)
        if "content.json" not in names:
            raise BatchError("XMind is missing content.json")
        content = json.loads(archive.read("content.json"))
    if not isinstance(content, list) or not content:
        raise BatchError("XMind content.json has no sheets")
    root_title = xmind_topic_title(content[0].get("rootTopic"))
    if root_title != title:
        raise BatchError(f"XMind root title mismatch: expected {title!r}, got {root_title!r}")
    return {
        "kind": "xmind",
        "package_source": "content.json",
        "root_title": root_title,
        "semantic_status": "matched",
    }


def inspect_download(path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    actual = str(entry["primary_format"]).lower()
    if actual == "vsdx":
        inspection = inspect_vsdx(path, str(entry["title"]))
    elif actual == "xmind":
        inspection = inspect_xmind(path, str(entry["title"]))
    else:
        raise BatchError(f"parallel batch does not support primary format: {actual}")
    inspection.update({"bytes": path.stat().st_size, "sha256": sha256(path)})
    return inspection


def yaml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def write_metadata(
    path: Path,
    *,
    entry: dict[str, Any],
    browser_result: dict[str, Any],
    finalized: dict[str, Any],
    inspection: dict[str, Any],
    team_url: str,
) -> None:
    if path.is_symlink():
        raise BatchError(f"metadata path must not be a symlink: {path}")
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if yaml_string(entry["artifact_id"]) not in existing:
            raise BatchError(f"metadata already belongs to another artifact: {path}")
        return
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "schema_version: 1",
        'index_role: "asset-folder-index"',
        f"artifact_id: {yaml_string(entry['artifact_id'])}",
        'source: "processon"',
        f"source_path: {yaml_string(entry['source_path'])}",
        f"source_url: {yaml_string(browser_result['source_url'])}",
        'source_url_status: "verified_from_dedicated_browser_popup"',
        f"remote_id: {yaml_string(browser_result['remote_id'])}",
        f"team_url: {yaml_string(team_url)}",
        f"title: {yaml_string(entry['title'])}",
        f"owner: {yaml_string(entry.get('owner', ''))}",
        f"remote_updated_at: {yaml_string(entry.get('remote_updated_at', ''))}",
        f"type: {yaml_string(entry['type'])}",
        f"type_evidence: {yaml_string('ProcessOn 盘点类型与官方下载菜单一致。')}",
        f"exported_at: {yaml_string(now)}",
        f"archived_at: {yaml_string(now)}",
        f"requested_format: {yaml_string(entry['primary_format'])}",
        f"actual_format: {yaml_string(entry['primary_format'])}",
        "fallback_used: false",
        f"file: {yaml_string(Path(finalized['destination']).name)}",
        f"bytes: {int(inspection['bytes'])}",
        f"sha256: {yaml_string(inspection['sha256'])}",
        f"finalizer_manifest: {yaml_string(finalized['manifest'])}",
        "inspection:",
    ]
    for key, value in inspection.items():
        if key in {"bytes", "sha256"}:
            continue
        if isinstance(value, list):
            lines.append(f"  {key}:")
            lines.extend(f"    - {yaml_string(item)}" for item in value)
        elif isinstance(value, int):
            lines.append(f"  {key}: {value}")
        else:
            lines.append(f"  {key}: {yaml_string(value)}")
    lines.extend(
        [
            f"verification: {yaml_string('浏览器弹页标题、源 URL、下载文件名、文件结构与文件内标题信号均已核对；归档 SHA-256 与下载文件一致。')}",
            'visibility: "internal"',
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_top_level_metadata(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        raw = raw.strip()
        if not raw:
            continue
        try:
            result[key] = json.loads(raw)
        except json.JSONDecodeError:
            result[key] = raw
    return result


def reconcile_existing(
    plan: dict[str, Any], progress: dict[str, Any], *, args: argparse.Namespace
) -> list[dict[str, Any]]:
    """Finish a prior half-commit when metadata and finalizer evidence agree."""

    done = progress_done_ids(progress)
    recovered: list[dict[str, Any]] = []
    for entry in plan["entries"]:
        artifact_id = str(entry.get("artifact_id", ""))
        if (
            not artifact_id
            or artifact_id in done
            or entry.get("confirmation_required")
            or entry.get("collision_risk") not in {None, "", "none_detected"}
        ):
            continue
        folder = output_folder(args.output_root, entry)
        metadata_path = folder / "metadata.yml"
        if not metadata_path.is_file() or metadata_path.is_symlink():
            continue
        metadata = read_top_level_metadata(metadata_path)
        if metadata.get("artifact_id") != artifact_id:
            raise BatchError(f"existing metadata artifact_id mismatch: {metadata_path}")
        required = ("file", "sha256", "actual_format", "finalizer_manifest", "source_url", "remote_id")
        missing = [key for key in required if not metadata.get(key)]
        if missing:
            raise BatchError(f"existing metadata cannot be reconciled; missing {missing}: {metadata_path}")
        destination = folder / str(metadata["file"])
        manifest_path = Path(str(metadata["finalizer_manifest"])).expanduser()
        manifest = load_json(manifest_path)
        source = Path(str(manifest.get("source", ""))).expanduser()
        if not destination.is_file() or sha256(destination) != str(metadata["sha256"]):
            raise BatchError(f"existing archive file does not match metadata: {destination}")
        if not source.is_file() and manifest.get("operation") != "move":
            raise BatchError(f"cannot reconcile after staging source was removed: {source}")
        browser_result = {
            "source_url": str(metadata["source_url"]),
            "remote_id": str(metadata["remote_id"]),
        }
        verified_remote_id = verify_source_identity(entry, browser_result["source_url"])
        if verified_remote_id != browser_result["remote_id"]:
            raise BatchError(f"existing metadata source identity mismatch: {metadata_path}")
        if args.source_links:
            append_source_link(args.source_links, entry, browser_result)
        recorded = run_json(
            [
                sys.executable,
                str(ARCHIVE_STATE),
                "record",
                "--plan",
                str(args.plan),
                "--progress",
                str(args.progress),
                "--artifact-id",
                artifact_id,
                "--download-source",
                str(source),
                "--destination",
                str(destination),
                "--manifest",
                str(manifest_path),
                "--requested-format",
                str(entry["primary_format"]),
                "--actual-format",
                str(metadata["actual_format"]),
                "--download-event",
                "observed",
            ]
        )
        recovered.append(
            {
                "artifact_id": artifact_id,
                "status": "reconciled",
                "destination": str(destination),
                "metadata": str(metadata_path),
                "manifest": str(manifest_path),
                "progress_counts": recorded.get("counts", {}),
            }
        )
        done.add(artifact_id)
    return recovered


def append_source_link(path: Path, entry: dict[str, Any], browser_result: dict[str, Any]) -> None:
    if path.is_symlink():
        raise BatchError(f"source-links path must not be a symlink: {path}")
    text = path.read_text(encoding="utf-8")
    artifact_id = str(entry["artifact_id"])
    if f'artifact_id: "{artifact_id}"' in text:
        pattern = re.compile(
            rf'(?ms)^  - artifact_id: "{re.escape(artifact_id)}"\n(?P<body>.*?)(?=^  - artifact_id:|\Z)'
        )
        match = pattern.search(text)
        existing_url = ""
        if match:
            url_match = re.search(r'^    source_url: "([^"]*)"$', match.group("body"), re.MULTILINE)
            existing_url = url_match.group(1) if url_match else ""
        if existing_url != str(browser_result["source_url"]):
            raise BatchError(
                f"source-links URL conflict for {artifact_id}: {existing_url!r} != {browser_result['source_url']!r}"
            )
        return
    if "\nentries:\n" not in text:
        raise BatchError("source-links YAML is missing entries")
    block = "\n".join(
        [
            f'  - artifact_id: "{artifact_id}"',
            f"    source_path: {yaml_string(entry['source_path'])}",
            f"    title: {yaml_string(entry['title'])}",
            f"    type: {yaml_string(entry['type'])}",
            f"    source_url: {yaml_string(browser_result['source_url'])}",
            f"    remote_id: {yaml_string(browser_result['remote_id'])}",
            '    status: "verified_from_dedicated_browser_popup"',
        ]
    )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    temporary.replace(path)


def write_progress_mirror(
    path: Path, *, plan: dict[str, Any], progress: dict[str, Any], run_id: str
) -> None:
    if path.is_symlink():
        raise BatchError(f"progress mirror must not be a symlink: {path}")
    counts = progress.get("counts", {})
    remaining_known = int(counts.get("remaining_known", 0))
    blocked = int(counts.get("blocked", 0))
    failed = int(counts.get("failed", 0))
    unknown = int(counts.get("unknown_pending_confirmation", 0))
    collision_pending = len(deferred_collision_entries(plan, progress))
    automatic_remaining = max(remaining_known - blocked - failed - collision_pending, 0)
    if remaining_known > 0:
        mirror_status = "asset_archive_running"
    elif unknown > 0:
        mirror_status = "known_artifacts_completed_pending_confirmation"
    else:
        mirror_status = "asset_archive_completed"
    lines = [
        "schema_version: 1",
        'source: "processon"',
        f"run_id: {yaml_string(run_id)}",
        f"updated_at: {yaml_string(datetime.now().astimezone().isoformat(timespec='seconds'))}",
        f"status: {yaml_string(mirror_status)}",
        "archive_plan:",
        f"  checkpoint_sha256: {yaml_string(plan.get('checkpoint_sha256', ''))}",
        f"  plan_sha256: {yaml_string(progress.get('plan', {}).get('sha256', ''))}",
        f"  archive_status: {yaml_string(plan.get('archive_status', ''))}",
        f"  ready_for_known_artifacts: {str(bool(plan.get('ready_for_known_artifacts'))).lower()}",
        f"  ready_for_archive: {str(bool(plan.get('ready_for_archive'))).lower()}",
        "counts:",
        f"  total_inventory_entries: {int(plan.get('counts', {}).get('total_entries', len(plan.get('entries', []))))}",
        f"  planned_known: {int(counts.get('planned_known', 0))}",
        f"  unknown_pending_confirmation: {unknown}",
        f"  completed: {int(counts.get('completed', 0))}",
        f"  failed: {failed}",
        f"  blocked: {blocked}",
        f"  remaining_known: {remaining_known}",
        f"  collision_identity_pending: {collision_pending}",
        f"  automatic_remaining: {automatic_remaining}",
        "completed:",
    ]
    for item in progress.get("completed", []):
        destination = Path(str(item.get("archive_destination", "")))
        metadata = destination.parent / "metadata.yml"
        lines.extend(
            [
                f"  - artifact_id: {yaml_string(item.get('artifact_id', ''))}",
                f"    source_path: {yaml_string(item.get('source_path', ''))}",
                f"    format: {yaml_string(item.get('actual_format', ''))}",
                f"    file: {yaml_string(os.path.relpath(destination, path.parent))}",
                f"    metadata: {yaml_string(os.path.relpath(metadata, path.parent))}",
            ]
        )
    lines.append("blocked:")
    for item in progress.get("blocked", []):
        lines.extend(
            [
                f"  - artifact_id: {yaml_string(item.get('artifact_id', ''))}",
                f"    source_path: {yaml_string(item.get('source_path', ''))}",
                f"    reason: {yaml_string(item.get('reason', ''))}",
            ]
        )
    lines.append(
        'next_action: "继续按机械队列下载已确认类型；并发项须通过语义交叉校验，未知类型须人工确认。"'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)


def finalize_result(
    browser_result: dict[str, Any],
    entry: dict[str, Any],
    *,
    args: argparse.Namespace,
) -> dict[str, Any]:
    source = Path(browser_result["download"]["path"])
    inspection = inspect_download(source, entry)
    destination_dir = output_folder(args.output_root, entry)
    base_command = [
        sys.executable,
        str(FINALIZER),
        "finalize",
        str(source),
        "--output-dir",
        str(destination_dir),
        "--manifest-dir",
        str(args.manifest_dir),
        "--collision",
        "fail",
    ]
    dry_run = run_json(base_command + ["--dry-run"])
    if dry_run.get("status") != "dry-run":
        raise BatchError("finalizer dry-run did not return dry-run status")
    finalized = run_json(base_command)
    if finalized.get("status") != "completed":
        raise BatchError("finalizer did not return completed status")
    destination = Path(finalized["destination"])
    if sha256(destination) != inspection["sha256"]:
        raise BatchError("archive destination hash differs from browser download")
    metadata_path = destination_dir / "metadata.yml"
    write_metadata(
        metadata_path,
        entry=entry,
        browser_result=browser_result,
        finalized=finalized,
        inspection=inspection,
        team_url=args.team_url,
    )
    if args.source_links:
        append_source_link(args.source_links, entry, browser_result)
    recorded = run_json(
        [
            sys.executable,
            str(ARCHIVE_STATE),
            "record",
            "--plan",
            str(args.plan),
            "--progress",
            str(args.progress),
            "--artifact-id",
            str(entry["artifact_id"]),
            "--download-source",
            str(source),
            "--destination",
            str(destination),
            "--manifest",
            str(finalized["manifest"]),
            "--requested-format",
            str(entry["primary_format"]),
            "--actual-format",
            str(entry["primary_format"]),
            "--download-event",
            "observed",
        ]
    )
    return {
        "artifact_id": entry["artifact_id"],
        "status": "completed",
        "source_url": browser_result["source_url"],
        "download": str(source),
        "destination": str(destination),
        "metadata": str(metadata_path),
        "manifest": finalized["manifest"],
        "sha256": inspection["sha256"],
        "inspection": inspection,
        "progress_counts": recorded.get("counts", {}),
    }


def write_receipt(receipt_dir: Path, payload: dict[str, Any]) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = receipt_dir / f"processon-archive-batch-{stamp}.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(target)
    return target


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan = load_json(args.plan)
    progress = load_json(args.progress)
    validate_plan(plan, progress)
    validate_processon_url(args.team_url)
    proof = validate_concurrency_proof(
        args.concurrency_proof, workers=args.workers, plan=plan, progress=progress
    )
    # Verify the current plan against the current progress/checkpoint before browsing.
    run_json(
        [
            sys.executable,
            str(ARCHIVE_STATE),
            "audit",
            "--plan",
            str(args.plan),
            "--progress",
            str(args.progress),
        ]
    )
    reconciled: list[dict[str, Any]] = []
    if not args.dry_run:
        reconciled = reconcile_existing(plan, progress, args=args)
        if reconciled:
            progress = load_json(args.progress)
    legacy_review = legacy_flat_download_review(progress)
    deferred_collisions = deferred_collision_entries(plan, progress)
    selected = choose_entries(plan, progress, args.limit, workers=args.workers)
    if not selected:
        refreshed_progress = load_json(args.progress)
        if args.progress_mirror and not args.dry_run:
            write_progress_mirror(
                args.progress_mirror,
                plan=plan,
                progress=refreshed_progress,
                run_id=args.progress.parent.parent.name,
            )
        payload = {
            "schema_version": 1,
            "status": "collision_confirmation_required" if deferred_collisions else "nothing_to_do",
            "selected": 0,
            "deferred_collision_count": len(deferred_collisions),
            "deferred_collision_artifact_ids": [
                str(item["artifact_id"]) for item in deferred_collisions
            ],
            "legacy_flat_download_review": legacy_review,
            "created_at": utc_now(),
            "reconciled": reconciled,
        }
        payload["receipt_file"] = str(write_receipt(args.receipt_dir, payload))
        return payload
    if args.dry_run:
        payload = {
            "schema_version": 1,
            "status": "dry-run",
            "workers": args.workers,
            "concurrency_proof": str(args.concurrency_proof) if proof else None,
            "selected": len(selected),
            "deferred_collision_count": len(deferred_collisions),
            "legacy_flat_download_review": legacy_review,
            "jobs": [
                {"source_directory": directory, "artifact_ids": [item["artifact_id"] for item in items]}
                for directory, items in build_jobs(selected, args.workers)
            ],
            "created_at": utc_now(),
        }
        payload["receipt_file"] = str(write_receipt(args.receipt_dir, payload))
        return payload

    results, browser_receipt = asyncio.run(
        browser_download_batch(
            selected,
            plan=plan,
            team_url=args.team_url,
            profile_dir=args.profile_dir,
            download_dir=args.download_dir,
            workers=args.workers,
            settle_ms=args.settle_ms,
            timeout_ms=args.timeout_ms,
        )
    )
    selected_by_id = {str(item["artifact_id"]): item for item in selected}
    completed: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    for result in results:
        if not result.get("ok"):
            pending.append(result)
            continue
        entry = selected_by_id[str(result["artifact_id"])]
        try:
            inspection = inspect_download(Path(result["download"]["path"]), entry)
            prior = seen_hashes.get(inspection["sha256"])
            if prior and prior != entry["artifact_id"]:
                raise BatchError(
                    f"same batch produced an identical SHA-256 for two artifacts: {prior}, {entry['artifact_id']}"
                )
            seen_hashes[inspection["sha256"]] = str(entry["artifact_id"])
            completed.append(finalize_result(result, entry, args=args))
        except Exception as exc:
            pending.append(
                {
                    **result,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "stage": "validate_or_archive",
                }
            )
    audit = run_json(
        [
            sys.executable,
            str(ARCHIVE_STATE),
            "audit",
            "--plan",
            str(args.plan),
            "--progress",
            str(args.progress),
        ]
    )
    refreshed_progress = load_json(args.progress)
    if args.progress_mirror:
        write_progress_mirror(
            args.progress_mirror,
            plan=plan,
            progress=refreshed_progress,
            run_id=args.progress.parent.parent.name,
        )
    lifecycle_ok = (
        browser_receipt["worker_pages_opened"] == browser_receipt["worker_pages_closed"]
        and browser_receipt["scoped_pages_opened"] == browser_receipt["scoped_pages_closed"]
        and browser_receipt["pages_closed_at_exit"] == 0
    )
    status = "completed" if not pending and lifecycle_ok else "partial"
    payload = {
        "schema_version": 1,
        "status": status,
        "selected": len(selected),
        "deferred_collision_count": len(deferred_collisions),
        "legacy_flat_download_review": legacy_review,
        "reconciled_count": len(reconciled),
        "reconciled": reconciled,
        "completed_count": len(completed),
        "pending_count": len(pending),
        "workers": args.workers,
        "concurrency_proof": str(args.concurrency_proof) if proof else None,
        "browser_receipt": browser_receipt,
        "completed": completed,
        "pending": pending,
        "audit": audit,
        "created_at": utc_now(),
    }
    payload["receipt_file"] = str(write_receipt(args.receipt_dir, payload))
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--team-url", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest-dir", type=Path, required=True)
    parser.add_argument("--source-links", type=Path)
    parser.add_argument("--progress-mirror", type=Path)
    parser.add_argument("--concurrency-proof", type=Path)
    parser.add_argument("--lock-file", type=Path)
    parser.add_argument("--receipt-dir", type=Path)
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--profile-dir", type=Path, default=default_profile_dir())
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--settle-ms", type=int, default=3_000)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= MAX_WORKERS:
        parser.error(f"--workers must be within 1..{MAX_WORKERS}")
    if not 1 <= args.limit <= MAX_BATCH:
        parser.error(f"--limit must be within 1..{MAX_BATCH}")
    if not 250 <= args.timeout_ms <= 300_000:
        parser.error("--timeout-ms must be within 250..300000")
    if not 0 <= args.settle_ms <= 30_000:
        parser.error("--settle-ms must be within 0..30000")
    args.profile_dir = validate_profile_dir(args.profile_dir)
    args.download_dir = (
        args.download_dir
        or Path(tempfile.gettempdir()) / "soia-cwork-processon-diagrams"
    ).expanduser().resolve(strict=False)
    args.receipt_dir = (
        args.receipt_dir
        or args.progress.expanduser().resolve(strict=False).parent / "batch-receipts"
    )
    args.lock_file = (
        args.lock_file
        or args.progress.expanduser().resolve(strict=False).parent / ".archive-orchestrator.lock"
    )
    try:
        with exclusive_lock(args.lock_file):
            payload = cmd_run(args)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["status"] in {
            "completed",
            "dry-run",
            "nothing_to_do",
            "collision_confirmation_required",
        } else 1
    except (BatchError, BrowserRunnerError, OSError, ValueError) as exc:
        payload = {
            "schema_version": 1,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "created_at": utc_now(),
        }
        try:
            payload["receipt_file"] = str(write_receipt(args.receipt_dir, payload))
        except Exception:
            pass
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
