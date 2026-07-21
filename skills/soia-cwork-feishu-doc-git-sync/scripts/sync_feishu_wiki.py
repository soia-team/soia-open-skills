#!/usr/bin/env python3
"""Mirror a Feishu wiki space to Markdown without writing back to Feishu."""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
from html import escape as html_escape
import io
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised in dependency checks
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


DEFAULT_CONFIG = (
    Path.home()
    / ".config"
    / "soia-skills"
    / "soia-open-skills"
    / "cwork"
    / "soia-cwork-feishu-doc-git-sync"
    / "config.yml"
)
DEFAULT_MIRROR_DIR = "10_knowledge-base"
MIRROR_DIR = DEFAULT_MIRROR_DIR
METADATA_DIR = "90_同步元数据"
STATE_FILE = "sync-state.json"
MANIFEST_FILE = "manifest.json"
SIDEBAR_FILE = "sidebar.json"
MAX_PATH_COMPONENT_LENGTH = 48
DEFAULT_ASSET_DIR = "_assets"
DEFAULT_ASSET_TIMEOUT_SECONDS = 30
DEFAULT_ASSET_DOWNLOAD_ATTEMPTS = 3
DEFAULT_MAX_ASSET_BYTES = 50 * 1024 * 1024
PRIVATE_PATH_PATTERN = re.compile(
    r"(?:/(?:Users|home|private|var/folders|tmp)/[^\s'\";]+|[A-Za-z]:[\\/][^\s'\";]+)"
)
PRIVATE_FILENAME_PATTERN = re.compile(
    r"(?<![\w/])(?:[\w\u4e00-\u9fff.-]+/)*[\w\u4e00-\u9fff.-]+\.(?:md|markdown|yml|yaml|json|xlsx|xls|csv|ndjson|png|jpg|jpeg|gif|pdf|docx|pptx|base)\b",
    re.IGNORECASE,
)
SENSITIVE_ENV_PATTERN = re.compile(
    r"\b(?:LARK_APP_SECRET|APP_SECRET|PASSWORD|PASSWD|ACCESS_TOKEN|TOKEN)\s*=\s*[^\s,;]+",
    re.IGNORECASE,
)
SENSITIVE_FLAG_PATTERN = re.compile(
    r"(--(?:app-secret|secret|password|passwd|access-token|token|doc|node-token|parent-node-token|obj-token|file-token|folder-token|space-id|config|output|output-dir))\s+([^\s]+)",
    re.IGNORECASE,
)
SUB_PAGE_LIST_PATTERN = re.compile(r"<sub-page-list\b[^>]*>.*?</sub-page-list>", re.IGNORECASE | re.DOTALL)
SUB_PAGE_PATTERN = re.compile(r"<sub-page(?!-list)\b([^>]*)/?>", re.IGNORECASE | re.DOTALL)
HTML_ATTRIBUTE_PATTERN = re.compile(r"([\w:-]+)=([\"'])(.*?)\2", re.DOTALL)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\((\s*https?://[^)\s]+\s*)\)")
BARE_FEISHU_DOCUMENT_URL_PATTERN = re.compile(
    r"https?://[^\s)\]]*(?:feishu|larksuite)[^\s)\]]*/(?:wiki|docx|doc)/[^\s?#/)]+[^\s)]*",
    re.IGNORECASE,
)
DEFAULT_CHANGE_LEDGER_DIR = "change-reports"
DEFAULT_CHANGE_LEDGER_MAX_DIFF_LINES = 400
DEFAULT_SHEET_MAX_CELLS = 10_000
DEFAULT_SHEET_MAX_CHARS = 100_000
DEFAULT_EMBEDDED_SHEET_MAX_ROWS = 200
DEFAULT_EMBEDDED_SHEET_MAX_COLUMNS = 50
DEFAULT_EMBEDDED_SHEET_MAX_PER_DOCUMENT = 100
DEFAULT_SHEET_SNAPSHOT_DIR = "_snapshots"
DEFAULT_BITABLE_MAX_RECORDS = 1_000
DEFAULT_RESOURCE_EXPORT_DIR = "_exports"
DEFAULT_RESOURCE_BATCH_SIZE = 10
DEFAULT_RESOURCE_TIMEOUT_SECONDS = 120
SHEET_RANGE_PATTERN = re.compile(r"^([A-Z]+)([1-9][0-9]*):([A-Z]+)([1-9][0-9]*)$")
SHEET_MIRROR_MARKER = "<!-- soia:sheet-mirror -->"
SHEET_TAB_RENDER_MARKER = "<!-- soia:sheet-tab -->"
SHEET_BITABLE_TAB_RENDER_MARKER = "<!-- soia:sheet-bitable-tab -->"
SHEET_BITABLE_UNMIRRORED_MARKER = "<!-- soia:unmirrored-sheet-bitable-tab -->"
EMBEDDED_SHEET_SCAN_MARKER = "<!-- soia:embedded-sheet-scan -->"
EMBEDDED_SHEET_RENDER_MARKER = "<!-- soia:embedded-sheet -->"
EMBEDDED_SHEET_UNMIRRORED_MARKER = "<!-- soia:unmirrored-embedded-sheet -->"
EMBEDDED_SHEET_UNMIRRORED_BLOCK = (
    EMBEDDED_SHEET_UNMIRRORED_MARKER
    + "\n> 此处包含尚未归档的飞书嵌入式表格；请启用有界的 embedded_sheets 同步。"
)
EMBEDDED_SHEET_MIRRORED_POINTER = "> 嵌入式飞书表格已归档，见本文末尾“嵌入式表格”快照。"
ERROR_PLACEHOLDER_PATTERN = re.compile(
    r"同步正文(?:失败|未返回结果)|"
    r"该知识库节点类型为\s*`[^`]+`，当前同步器只读取文档正文。"
)


class CliCommandError(RuntimeError):
    """A classified lark-cli failure safe to carry into the sync manifest."""

    def __init__(
        self,
        message: str,
        *,
        category: str = "cli_error",
        code: str = "",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.code = code
        self.retryable = retryable


class AssetSizeLimitError(RuntimeError):
    """A downloaded resource exceeded the configured local safety limit."""

    def __init__(self) -> None:
        super().__init__("asset exceeds configured size limit")


class ExportPending(CliCommandError):
    """A successfully created async export task that is not ready to download."""

    def __init__(self, ticket: str, source_file_token: str) -> None:
        super().__init__(
            "lark-cli export task is still processing",
            category="export_pending",
            retryable=True,
        )
        self.ticket = ticket
        self.source_file_token = source_file_token


class RequestLimiter:
    """Coordinate request starts across worker threads and backoff all workers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._interval = 0.0
        self._next_slot = 0.0
        self._cooldown_until = 0.0

    def configure(self, interval_seconds: float) -> None:
        with self._lock:
            self._interval = max(0.0, interval_seconds)
            self._next_slot = 0.0
            self._cooldown_until = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot, self._cooldown_until)
            self._next_slot = slot + self._interval
        delay = slot - now
        if delay > 0:
            time.sleep(delay)

    def cooldown(self, seconds: float) -> None:
        with self._lock:
            self._cooldown_until = max(self._cooldown_until, time.monotonic() + max(0.0, seconds))


REQUEST_LIMITER = RequestLimiter()


def acquire_sync_lock(output_dir: Path):
    """Prevent a cancelled/slow run from racing a later run over one manifest."""
    lock_root = Path(tempfile.gettempdir()) / "soia-cwork-feishu-doc-git-sync-locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(str(output_dir).encode("utf-8")).hexdigest()[:24]
    handle = (lock_root / f"{digest}.lock").open("a+", encoding="utf-8")
    if fcntl is None:
        return handle
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise SystemExit("another sync is already running for this output") from exc
    return handle


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read a Feishu wiki space through lark-cli and mirror it to Markdown."
    )
    parser.add_argument("--config", help="private YAML config path")
    parser.add_argument("--space-id", help="override space.id")
    parser.add_argument("--output-dir", help="override paths.output_dir")
    parser.add_argument("--cli-path", help="override provider.cli")
    parser.add_argument("--dry-run", action="store_true", help="list and fetch metadata without writing files")
    parser.add_argument("--skip-content", action="store_true", help="only enumerate nodes and build no content")
    parser.add_argument(
        "--download-assets",
        action="store_true",
        help="download remote Feishu images into the local mirror and rewrite Markdown links",
    )
    parser.add_argument(
        "--sync-sheets",
        action="store_true",
        help="mirror explicitly configured Feishu Sheet ranges as Markdown tables",
    )
    parser.add_argument(
        "--sync-embedded-sheets",
        action="store_true",
        help="mirror explicitly authorised Sheet blocks embedded inside Feishu documents",
    )
    parser.add_argument(
        "--sync-bitables",
        action="store_true",
        help="mirror explicitly configured Feishu Base tables as bounded Markdown snapshots",
    )
    parser.add_argument(
        "--refresh-asset-urls",
        action="store_true",
        help="re-fetch documents containing remote images before downloading signed image URLs",
    )
    parser.add_argument(
        "--skip-assets",
        action="store_true",
        help="do not download or refresh media assets during a content-only repair",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="reuse successful content from sync-state.json and retry only failed document reads",
    )
    parser.add_argument(
        "--retry-batch-size",
        type=int,
        help="limit one --retry-failed run to this many candidates; repeat until validation passes",
    )
    parser.add_argument(
        "--rebuild-tree",
        action="store_true",
        help="rebuild generated paths as parent-directory/child.md and remove stale generated flat files",
    )
    parser.add_argument(
        "--rebuild-tree-only",
        action="store_true",
        help="rebuild paths from the existing manifest/files without making Feishu content requests",
    )
    parser.add_argument(
        "--refresh-tree-only",
        action="store_true",
        help="read the current Feishu node tree/order, rebuild paths/sidebar, and reuse existing local content",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate the existing local mirror, manifest, generated files, and sidebar without contacting Feishu",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="reuse unchanged content by node ID and remote edit metadata; first run creates a baseline",
    )
    parser.add_argument(
        "--full-content",
        action="store_true",
        help="force content fetch for every readable document; still reconciles the Feishu tree",
    )
    parser.add_argument(
        "--probe-remote-metadata",
        action="store_true",
        help="probe wiki node metadata to detect changed documents when no event targets are supplied",
    )
    parser.add_argument(
        "--changed-node-token",
        action="append",
        default=[],
        help="refresh one changed wiki node; repeat for multiple IDs",
    )
    parser.add_argument(
        "--only-node-token",
        action="append",
        default=[],
        help="fetch only these wiki nodes; repeat for multiple IDs and reuse all other local content",
    )
    parser.add_argument(
        "--pilot-node-token",
        action="append",
        default=[],
        help="write an isolated pilot mirror containing only these nodes; repeat for multiple IDs",
    )
    parser.add_argument(
        "--changed-obj-token",
        action="append",
        default=[],
        help="refresh the wiki node owning one changed document token; repeat for multiple IDs",
    )
    parser.add_argument(
        "--event-file",
        help="NDJSON/JSON file produced by an external Feishu event subscription; extracts node/file IDs",
    )
    parser.add_argument("--max-nodes", type=int, help="stop after this many nodes; useful for a smoke test")
    return parser.parse_args()


def load_config(path_arg: str | None) -> tuple[dict[str, Any], Path]:
    raw_path = path_arg or os.environ.get(
        "SOIA_CWORK_FEISHU_DOC_GIT_SYNC_CONFIG_FILE", str(DEFAULT_CONFIG)
    )
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(
            "private config not found; set --config or "
            "SOIA_CWORK_FEISHU_DOC_GIT_SYNC_CONFIG_FILE"
        )
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if not isinstance(config, dict):
        raise SystemExit("private config must be a YAML mapping")
    return config, path


def nested(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    value: Any = config
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def command_env(config: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    profile = nested(config, "provider", "profile")
    brand = nested(config, "provider", "brand")
    if profile and not str(profile).startswith("<"):
        env["LARK_PROFILE"] = str(profile)
    if brand and not str(brand).startswith("<"):
        env["LARK_BRAND"] = str(brand)
    return env


def cli_command(config: dict[str, Any], *args: str) -> list[str]:
    cli = str(nested(config, "provider", "cli", default="lark-cli"))
    return [cli, *args]


def parse_cli_json(stdout: str) -> dict[str, Any]:
    """Parse a JSON envelope even when lark-cli prepends human-readable text."""
    decoder = json.JSONDecoder()
    for position, marker in enumerate(stdout):
        if marker not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(stdout[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
        return {"data": value}
    raise RuntimeError("lark-cli returned no JSON payload")


def cli_error_info(detail: str) -> dict[str, Any]:
    """Classify an lark-cli error without retaining its private command text."""
    payload: dict[str, Any] = {}
    for candidate in (detail,):
        try:
            parsed = parse_cli_json(candidate)
        except RuntimeError:
            continue
        if isinstance(parsed, dict):
            payload = parsed
            break
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    if not isinstance(error, dict):
        error = {}
    code = str(error.get("code", "") or "")
    subtype = str(error.get("subtype", "") or "").lower()
    message = str(error.get("message", "") or "")
    lower = " ".join((detail, subtype, message)).lower()
    if (
        code == "99991400"
        or subtype in {"rate_limit", "frequency_limit"}
        or any(marker in lower for marker in ("rate limit", "rate_limit", "frequency limit", "too many requests", "429"))
    ):
        category = "rate_limit"
    elif code in {"403", "99991679", "99991672"} or any(
        marker in lower for marker in ("permission denied", "permission_denied", "forbidden", "missing scope", "not authorized")
    ):
        category = "permission_denied"
    elif code == "404" or any(marker in lower for marker in ("not found", "not_found", "node not found")):
        category = "not_found"
    elif any(marker in lower for marker in ("timeout", "timed out", "temporarily unavailable", "connection reset", "connection refused")):
        category = "temporary_network"
    elif payload.get("ok") is False or detail:
        category = "cli_error"
    else:
        category = "invalid_response"
    retryable = bool(error.get("retryable") is True) or category in {"rate_limit", "temporary_network"}
    return {"category": category, "code": code, "retryable": retryable}


def redact_output(value: Any) -> str:
    """Remove local locations and credentials from user-visible diagnostics."""
    text = str(value)
    text = SENSITIVE_ENV_PATTERN.sub(
        lambda match: match.group(0).split("=", 1)[0] + "=<redacted>",
        text,
    )
    text = SENSITIVE_FLAG_PATTERN.sub(r"\1 <redacted>", text)
    text = PRIVATE_PATH_PATTERN.sub("<private-location>", text)
    return PRIVATE_FILENAME_PATTERN.sub("<private-file>", text)


def run_cli(config: dict[str, Any], *args: str) -> dict[str, Any]:
    command = cli_command(config, *args)
    for attempt in range(5):
        REQUEST_LIMITER.acquire()
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=command_env(config),
        )
        if result.returncode == 0:
            try:
                payload = parse_cli_json(result.stdout)
            except RuntimeError as exc:
                raise CliCommandError("lark-cli returned invalid JSON", category="invalid_response") from exc
            if payload.get("ok") is not False:
                return payload
        detail = " ".join(part.strip() for part in (result.stderr, result.stdout) if part.strip())
        info = cli_error_info(detail)
        if info["retryable"] and attempt < 4:
            backoff = min(30, 2**attempt)
            REQUEST_LIMITER.cooldown(backoff)
            time.sleep(backoff)
            continue
        code_suffix = f" code={info['code']}" if info["code"] else ""
        raise CliCommandError(
            f"lark-cli request failed category={info['category']}{code_suffix}",
            category=str(info["category"]),
            code=str(info["code"]),
            retryable=bool(info["retryable"]),
        )
    raise CliCommandError("lark-cli request failed after retries", category="rate_limit", retryable=True)


def error_info(exc: Exception | str) -> dict[str, Any]:
    """Return a small, safe error record for manifests and validation."""
    if isinstance(exc, CliCommandError):
        return {"category": exc.category, "code": exc.code, "retryable": exc.retryable}
    if isinstance(exc, AssetSizeLimitError):
        return {"category": "asset_too_large", "code": "", "retryable": False}
    return cli_error_info(str(exc))


def safe_error_category(value: Exception | str) -> str:
    """Keep only the stable public error category in generated artifacts."""
    return str(error_info(value).get("category", "cli_error"))


def node_list(config: dict[str, Any], space_id: str, parent: str | None = None) -> list[dict[str, Any]]:
    args = ["wiki", "+node-list", "--as", "bot", "--space-id", space_id, "--page-all", "--format", "json"]
    if parent:
        args.extend(["--parent-node-token", parent])
    payload = run_cli(config, *args)
    nodes = nested(payload, "data", "nodes", default=[])
    if not isinstance(nodes, list):
        raise RuntimeError("node-list payload has no data.nodes list")
    return [item for item in nodes if isinstance(item, dict)]


def node_get(config: dict[str, Any], node_token: str, space_id: str) -> dict[str, Any]:
    payload = run_cli(
        config,
        "wiki",
        "+node-get",
        "--as",
        "bot",
        "--node-token",
        node_token,
        "--space-id",
        space_id,
        "--format",
        "json",
    )
    data = nested(payload, "data", default={})
    if not isinstance(data, dict):
        raise RuntimeError("wiki +node-get payload has no data object")
    return data


def walk_nodes(config: dict[str, Any], space_id: str, max_nodes: int | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    frontier: list[tuple[str | None, int]] = [(None, 0)]
    seen: set[str] = set()
    workers_value = nested(config, "sync", "structure_workers", default=2)
    try:
        workers = max(1, min(int(workers_value), 8))
    except (TypeError, ValueError):
        workers = 4
    while frontier:
        next_frontier: list[tuple[str | None, int]] = []
        current_depth = frontier[0][1]
        print(f"structure depth={current_depth} parents={len(frontier)}", flush=True)

        def list_one(item: tuple[str | None, int]) -> tuple[str | None, int, list[dict[str, Any]]]:
            parent, depth = item
            return parent, depth, node_list(config, space_id, parent)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(list_one, item) for item in frontier]
            listed = [future.result() for future in futures]
        for parent, depth, raw_nodes in listed:
            for raw in raw_nodes:
                token = str(raw.get("node_token", "")).strip()
                if not token or token in seen:
                    continue
                seen.add(token)
                node = dict(raw)
                node["depth"] = depth
                node["parent_node_token"] = raw.get("parent_node_token") or parent
                result.append(node)
                if max_nodes and len(result) >= max_nodes:
                    return result
                if raw.get("has_child"):
                    next_frontier.append((token, depth + 1))
        print(f"structure depth={current_depth} nodes_total={len(result)} next_parents={len(next_frontier)}", flush=True)
        frontier = next_frontier
    return result


def fetch_doc(config: dict[str, Any], obj_token: str) -> tuple[str, str]:
    payload = run_cli(
        config,
        "docs",
        "+fetch",
        "--as",
        "bot",
        "--doc",
        obj_token,
        "--scope",
        "full",
        "--doc-format",
        "markdown",
        "--format",
        "json",
    )
    document = nested(payload, "data", "document", default={})
    if not isinstance(document, dict):
        raise RuntimeError("docs +fetch payload has no data.document object")
    content = document.get("content")
    if not isinstance(content, str):
        raise RuntimeError("docs +fetch payload has no data.document.content string")
    revision_id = document.get("revision_id", "")
    return content, str(revision_id) if revision_id is not None else ""


def fetch_doc_xml(config: dict[str, Any], obj_token: str) -> str:
    """Read a document's XML only when an opted-in feature needs block metadata."""
    payload = run_cli(
        config,
        "docs",
        "+fetch",
        "--as",
        "bot",
        "--doc",
        obj_token,
        "--scope",
        "full",
        "--doc-format",
        "xml",
        "--format",
        "json",
    )
    document = nested(payload, "data", "document", default={})
    if not isinstance(document, dict):
        raise RuntimeError("docs +fetch XML payload has no data.document object")
    content = document.get("content")
    if not isinstance(content, str):
        raise RuntimeError("docs +fetch XML payload has no data.document.content string")
    return content


def a1_column_number(label: str) -> int:
    """Return the one-based number for an A1 column label."""
    value = 0
    for character in label.upper():
        if not "A" <= character <= "Z":
            raise ValueError("invalid A1 column")
        value = value * 26 + ord(character) - ord("A") + 1
    return value


def a1_column_label(value: int) -> str:
    """Return the A1 column label for a positive, one-based column number."""
    if value < 1:
        raise ValueError("A1 column number must be positive")
    letters: list[str] = []
    while value:
        value, remainder = divmod(value - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


def sheet_preservation_options(settings: dict[str, Any]) -> tuple[bool, dict[str, bool]]:
    """Read one bounded preservation policy shared by standalone and embedded Sheets."""
    preserve = settings.get("preserve", {})
    if preserve is True:
        preserve = {"enabled": True}
    if not isinstance(preserve, dict):
        raise SystemExit("Sheet preserve must be a mapping when provided")
    preserve_enabled = bool(preserve.get("enabled", False))
    return preserve_enabled, {
        "formulas": bool(preserve.get("formulas", True)),
        "styles": bool(preserve.get("styles", True)),
        "comments": bool(preserve.get("comments", True)),
        "layout": bool(preserve.get("layout", True)),
        "charts": bool(preserve.get("charts", True)),
        "floating_images": bool(preserve.get("floating_images", True)),
        # Report-oriented metadata remains opt-in even when the existing
        # preservation bundle is enabled, so current mirrors do not gain
        # extra API calls unexpectedly.
        "pivots": bool(preserve.get("pivots", False)),
        "filters": bool(preserve.get("filters", False)),
        "conditional_formats": bool(preserve.get("conditional_formats", False)),
        "sparklines": bool(preserve.get("sparklines", False)),
    }


def configured_sheet_selections(config: dict[str, Any], enabled: bool) -> dict[str, list[dict[str, Any]]]:
    """Return explicitly authorised, bounded Sheet ranges grouped by Wiki node token."""
    if not enabled:
        return {}
    settings = nested(config, "sync", "sheets", default={})
    if not isinstance(settings, dict):
        raise SystemExit("sync.sheets must be a mapping")
    raw_selections = settings.get("selections", [])
    if not isinstance(raw_selections, list):
        raise SystemExit("sync.sheets.selections must be a list")
    if not raw_selections and not bool(settings.get("all_nodes", False)):
        raise SystemExit(
            "sync.sheets requires all_nodes=true or at least one explicit selections entry"
        )
    try:
        max_cells = max(1, min(int(settings.get("max_cells", DEFAULT_SHEET_MAX_CELLS)), 100_000))
    except (TypeError, ValueError):
        max_cells = DEFAULT_SHEET_MAX_CELLS
    try:
        max_chars = max(1_024, min(int(settings.get("max_chars", DEFAULT_SHEET_MAX_CHARS)), 500_000))
    except (TypeError, ValueError):
        max_chars = DEFAULT_SHEET_MAX_CHARS
    skip_hidden = bool(settings.get("skip_hidden", False))
    preserve_enabled, preserve_options = sheet_preservation_options(settings)
    selections: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for raw in raw_selections:
        if not isinstance(raw, dict):
            raise SystemExit("each sync.sheets.selections item must be a mapping")
        node_token = str(raw.get("node_token", "")).strip()
        sheet_id = str(raw.get("sheet_id", "")).strip()
        cell_range = str(raw.get("range", "")).strip().upper()
        if not node_token or not sheet_id or not cell_range:
            raise SystemExit("each Sheet selection requires node_token, sheet_id, and range")
        match = SHEET_RANGE_PATTERN.fullmatch(cell_range)
        if not match:
            raise SystemExit("each Sheet selection range must use a bounded A1 range such as A1:F200")
        start_column, start_row, end_column, end_row = match.groups()
        width = a1_column_number(end_column) - a1_column_number(start_column) + 1
        height = int(end_row) - int(start_row) + 1
        if width <= 0 or height <= 0 or width * height > max_cells:
            raise SystemExit(f"Sheet selection range exceeds sync.sheets.max_cells={max_cells}")
        key = (node_token, sheet_id, cell_range)
        if key in seen:
            raise SystemExit("sync.sheets.selections contains a duplicate node_token, sheet_id, and range")
        seen.add(key)
        selections.setdefault(node_token, []).append(
            {
                "sheet_id": sheet_id,
                "range": cell_range,
                "max_chars": max_chars,
                "skip_hidden": skip_hidden,
                "preserve": bool(raw.get("preserve", preserve_enabled)),
                "preserve_options": preserve_options,
            }
        )
    return selections


def configured_all_sheet_settings(config: dict[str, Any], enabled: bool) -> dict[str, Any] | None:
    """Return bounded automatic discovery settings for every standalone Wiki Sheet node."""
    if not enabled:
        return None
    settings = nested(config, "sync", "sheets", default={})
    if not isinstance(settings, dict):
        raise SystemExit("sync.sheets must be a mapping")
    if not bool(settings.get("all_nodes", False)):
        return None

    def bounded_int(name: str, default: int, hard_limit: int) -> int:
        try:
            value = int(settings.get(name, default))
        except (TypeError, ValueError):
            value = default
        return max(1, min(value, hard_limit))

    max_cells = bounded_int("max_cells", DEFAULT_SHEET_MAX_CELLS, 100_000)
    max_rows = bounded_int("max_rows", DEFAULT_EMBEDDED_SHEET_MAX_ROWS, 100_000)
    max_columns = bounded_int("max_columns", DEFAULT_EMBEDDED_SHEET_MAX_COLUMNS, 702)
    if max_rows * max_columns > max_cells:
        raise SystemExit("sync.sheets.max_rows * max_columns exceeds max_cells")
    preserve_enabled, preserve_options = sheet_preservation_options(settings)
    return {
        "max_cells": max_cells,
        "max_rows": max_rows,
        "max_columns": max_columns,
        "max_chars": bounded_int("max_chars", DEFAULT_SHEET_MAX_CHARS, 500_000),
        "max_sheets_per_workbook": bounded_int("max_sheets_per_workbook", 500, 500),
        "skip_hidden": bool(settings.get("skip_hidden", False)),
        "include_bitable_tabs": bool(settings.get("include_bitable_tabs", False)),
        "max_bitable_records": bounded_int(
            "max_bitable_records", DEFAULT_BITABLE_MAX_RECORDS, 5_000
        ),
        "download_bitable_attachments": bool(
            settings.get("download_bitable_attachments", False)
        ),
        "preserve": preserve_enabled,
        "preserve_options": preserve_options,
    }


def configured_embedded_sheet_settings(config: dict[str, Any], enabled: bool) -> dict[str, Any] | None:
    """Return an explicit, bounded policy for Sheet blocks embedded in documents."""
    if not enabled:
        return None
    settings = nested(config, "sync", "embedded_sheets", default={})
    if not isinstance(settings, dict):
        raise SystemExit("sync.embedded_sheets must be a mapping")
    all_docx = bool(settings.get("all_docx", False))
    raw_node_tokens = settings.get("node_tokens", [])
    if not isinstance(raw_node_tokens, list) or any(not isinstance(item, str) for item in raw_node_tokens):
        raise SystemExit("sync.embedded_sheets.node_tokens must be a list of node tokens")
    node_tokens = {item.strip() for item in raw_node_tokens if item.strip()}
    if not all_docx and not node_tokens:
        raise SystemExit(
            "sync.embedded_sheets requires all_docx=true or at least one explicit node_tokens entry"
        )

    def bounded_int(name: str, default: int, hard_limit: int) -> int:
        try:
            value = int(settings.get(name, default))
        except (TypeError, ValueError):
            value = default
        return max(1, min(value, hard_limit))

    max_cells = bounded_int("max_cells", DEFAULT_SHEET_MAX_CELLS, 100_000)
    max_rows = bounded_int("max_rows", DEFAULT_EMBEDDED_SHEET_MAX_ROWS, 100_000)
    max_columns = bounded_int("max_columns", DEFAULT_EMBEDDED_SHEET_MAX_COLUMNS, 702)
    if max_rows * max_columns > max_cells:
        raise SystemExit("sync.embedded_sheets.max_rows * max_columns exceeds max_cells")
    max_chars = bounded_int("max_chars", DEFAULT_SHEET_MAX_CHARS, 500_000)
    max_sheets = bounded_int("max_sheets_per_document", DEFAULT_EMBEDDED_SHEET_MAX_PER_DOCUMENT, 500)
    preserve_enabled, preserve_options = sheet_preservation_options(settings)
    return {
        "all_docx": all_docx,
        "node_tokens": node_tokens,
        "max_cells": max_cells,
        "max_rows": max_rows,
        "max_columns": max_columns,
        "max_chars": max_chars,
        "max_sheets_per_document": max_sheets,
        "skip_hidden": bool(settings.get("skip_hidden", False)),
        "preserve": preserve_enabled,
        "preserve_options": preserve_options,
    }


def embedded_sheet_references(content: str, *, max_count: int) -> list[dict[str, str]]:
    """Extract unique workbook and worksheet identifiers from document XML."""
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in re.finditer(r"<sheet\b([^>]*)/?>", content, flags=re.IGNORECASE):
        attrs = html_attributes(match.group(1))
        workbook_token = attrs.get("token", "").strip()
        sheet_id = attrs.get("sheet-id", "").strip()
        if not workbook_token or not sheet_id:
            raise RuntimeError("embedded Sheet tag is missing a workbook token or sheet id")
        key = (workbook_token, sheet_id)
        if key in seen:
            continue
        seen.add(key)
        references.append({"workbook_token": workbook_token, "sheet_id": sheet_id})
        if len(references) > max_count:
            raise RuntimeError("embedded Sheet reference count exceeds the configured document limit")
    return references


def embedded_sheet_selection(settings: dict[str, Any], sheet: dict[str, Any]) -> dict[str, Any]:
    """Constrain one embedded worksheet to an A1 range before reading its values."""
    try:
        source_rows = max(1, int(sheet.get("row_count") or settings["max_rows"]))
    except (TypeError, ValueError):
        source_rows = int(settings["max_rows"])
    try:
        source_columns = max(1, int(sheet.get("column_count") or settings["max_columns"]))
    except (TypeError, ValueError):
        source_columns = int(settings["max_columns"])
    width = min(source_columns, int(settings["max_columns"]))
    height = min(source_rows, int(settings["max_rows"]), int(settings["max_cells"]) // width)
    if height < 1:
        raise RuntimeError("embedded Sheet bounds leave no readable cells")
    return {
        "sheet_id": str(sheet["sheet_id"]),
        "range": f"A1:{a1_column_label(width)}{height}",
        "max_chars": int(settings["max_chars"]),
        "skip_hidden": bool(settings["skip_hidden"]),
        "preserve": bool(settings["preserve"]),
        "preserve_options": dict(settings["preserve_options"]),
    }


def automatic_sheet_selections(
    settings: dict[str, Any], workbook_sheets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build bounded selections for every grid worksheet discovered in one workbook."""
    if len(workbook_sheets) > int(settings["max_sheets_per_workbook"]):
        raise RuntimeError("Sheet workbook tab count exceeds the configured workbook limit")
    selections = [
        embedded_sheet_selection(settings, item)
        for item in workbook_sheets
        if isinstance(item, dict)
        and item.get("sheet_id")
        and str(item.get("resource_type", "sheet")) == "sheet"
        and not (bool(settings["skip_hidden"]) and bool(item.get("is_hidden", False)))
    ]
    return selections


def automatic_sheet_bitable_selections(
    settings: dict[str, Any], workbook_sheets: list[dict[str, Any]]
) -> list[tuple[str, dict[str, Any]]]:
    """Route embedded Base tabs in a Sheet workbook through bounded Base reads."""
    bitable_tabs = [
        item
        for item in workbook_sheets
        if isinstance(item, dict) and str(item.get("resource_type", "")) == "bitable"
    ]
    if bitable_tabs and not bool(settings["include_bitable_tabs"]):
        raise RuntimeError(
            "Sheet workbook contains a Base tab; enable bounded include_bitable_tabs mirroring"
        )
    selections: list[tuple[str, dict[str, Any]]] = []
    for item in bitable_tabs:
        base_token = str(item.get("bitable_app_token", "")).strip()
        table_id = str(item.get("bitable_table_id", "")).strip()
        if not base_token or not table_id:
            raise RuntimeError("Sheet workbook Base tab is missing its app token or table id")
        selections.append(
            (
                base_token,
                {
                    "table_id": table_id,
                    "view_id": "",
                    "max_records": int(settings["max_bitable_records"]),
                    "include_views": False,
                    "include_dashboards": False,
                    "download_attachments": bool(settings["download_bitable_attachments"]),
                },
            )
        )
    unsupported = [
        item
        for item in workbook_sheets
        if isinstance(item, dict)
        and str(item.get("resource_type", "sheet")) not in {"sheet", "bitable"}
    ]
    if unsupported:
        raise RuntimeError("Sheet workbook contains an unsupported non-grid tab")
    return selections


def embedded_sheet_sync_applies(node: dict[str, Any], settings: dict[str, Any] | None) -> bool:
    """Limit XML reads to the document nodes explicitly authorised in private config."""
    if settings is None or str(node.get("obj_type", "")) not in {"docx", "doc"}:
        return False
    return bool(settings["all_docx"] or str(node.get("node_token", "")) in settings["node_tokens"])


def trim_sheet_rows(rows: list[list[str]]) -> list[list[str]]:
    """Keep meaningful Sheet cells while preserving internal blank rows and columns."""
    normalized = [[str(value) for value in row] for row in rows]
    while normalized and not any(cell.strip() for cell in normalized[-1]):
        normalized.pop()
    if not normalized:
        return []
    width = max(len(row) for row in normalized)
    for row in normalized:
        row.extend("" for _ in range(width - len(row)))
    while width and not any(row[width - 1].strip() for row in normalized):
        width -= 1
    return [row[:width] for row in normalized]


def markdown_table_from_csv(value: str) -> str:
    """Convert a bounded CSV value snapshot into portable Markdown table syntax."""
    rows = trim_sheet_rows(list(csv.reader(io.StringIO(value))))
    if not rows or not rows[0]:
        return "（所选工作表范围没有可同步的单元格。）"
    header = [cell.strip() or f"列 {index}" for index, cell in enumerate(rows[0], start=1)]

    def cell(value: str) -> str:
        return value.replace("\\r\\n", "<br>").replace("\\n", "<br>").replace("\\r", "<br>").replace("|", "\\\\|")

    lines = [
        "| " + " | ".join(cell(value) for value in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows[1:])
    return "\n".join(lines)


def fetch_sheet_csv(config: dict[str, Any], obj_token: str, selection: dict[str, Any]) -> str:
    """Read a bounded Sheet range, continuing by row when max_chars truncates a response."""
    requested = str(selection["range"]).upper()
    match = SHEET_RANGE_PATTERN.fullmatch(requested)
    if not match:
        raise RuntimeError("configured Sheet selection is not a bounded A1 range")
    start_column, start_row_value, end_column, end_row_value = match.groups()
    next_row = int(start_row_value)
    end_row = int(end_row_value)
    chunks: list[str] = []
    for _chunk in range(end_row - next_row + 2):
        current_range = f"{start_column}{next_row}:{end_column}{end_row}"
        payload = run_cli(
            config,
            "sheets",
            "+csv-get",
            "--as",
            "bot",
            "--spreadsheet-token",
            obj_token,
            "--sheet-id",
            str(selection["sheet_id"]),
            "--range",
            current_range,
            "--include-row-prefix=false",
            "--skip-hidden=true" if selection["skip_hidden"] else "--skip-hidden=false",
            "--max-chars",
            str(selection["max_chars"]),
            "--format",
            "json",
        )
        data = nested(payload, "data", default={})
        if not isinstance(data, dict):
            raise RuntimeError("sheets +csv-get payload has no data object")
        csv_value = data.get("annotated_csv", data.get("csv", ""))
        if not isinstance(csv_value, str):
            raise RuntimeError("sheets +csv-get payload has no CSV value")
        if csv_value:
            chunks.append(csv_value.rstrip("\n") + "\n")
        if not data.get("has_more"):
            return "".join(chunks)
        actual_range = str(data.get("actual_range", "")).rsplit("!", 1)[-1].replace("$", "").upper()
        actual_match = SHEET_RANGE_PATTERN.fullmatch(actual_range)
        if not actual_match:
            raise RuntimeError("truncated Sheet response has no usable actual_range")
        actual_end_row = int(actual_match.group(4))
        if actual_end_row < next_row or actual_end_row >= end_row:
            raise RuntimeError("truncated Sheet response made no forward row progress")
        next_row = actual_end_row + 1
    raise RuntimeError("Sheet CSV pagination exceeded the bounded row count")


def fetch_sheet_markdown(
    config: dict[str, Any],
    obj_token: str,
    title: str,
    selections: list[dict[str, Any]],
    *,
    snapshot_root: Path | None = None,
    node_token: str = "",
    workbook_sheets: list[dict[str, Any]] | None = None,
    include_document_heading: bool = True,
    section_heading_level: int = 2,
) -> tuple[str, str]:
    """Read explicitly selected Sheet ranges through lark-cli and render Markdown tables."""
    if workbook_sheets is None:
        workbook_payload = run_cli(
            config,
            "sheets",
            "+workbook-info",
            "--as",
            "bot",
            "--spreadsheet-token",
            obj_token,
            "--format",
            "json",
        )
        workbook_sheets = nested(workbook_payload, "data", "sheets", default=[])
    if not isinstance(workbook_sheets, list):
        raise RuntimeError("sheets +workbook-info payload has no data.sheets list")
    sheets_by_id = {
        str(item.get("sheet_id", "")): item
        for item in workbook_sheets
        if isinstance(item, dict) and item.get("sheet_id")
    }
    sections = (
        [f"# {title}", "", SHEET_MIRROR_MARKER, "", "> 已按私有配置读取飞书电子表格。"]
        if include_document_heading
        else []
    )
    heading = "#" * max(1, min(section_heading_level, 6))
    for selection in selections:
        sheet_id = str(selection["sheet_id"])
        sheet = sheets_by_id.get(sheet_id)
        if sheet is None:
            raise RuntimeError("configured Sheet selection was not found in workbook metadata")
        if str(sheet.get("resource_type", "sheet")) != "sheet":
            raise RuntimeError("configured Sheet selection is not a grid worksheet")
        csv_value = fetch_sheet_csv(config, obj_token, selection)
        sheet_title = str(sheet.get("title") or sheet.get("sheet_name") or sheet_id).strip()
        preservation_note = ""
        if selection.get("preserve"):
            if snapshot_root is None:
                raise RuntimeError("Sheet preservation requires a local snapshot directory")
            options = selection.get("preserve_options", {})
            if not isinstance(options, dict):
                raise RuntimeError("Sheet preservation options must be a mapping")
            cells_payload = run_cli(
                config,
                "sheets",
                "+cells-get",
                "--as",
                "bot",
                "--spreadsheet-token",
                obj_token,
                "--sheet-id",
                sheet_id,
                "--range",
                str(selection["range"]),
                "--include",
                ",".join(
                    item
                    for item, enabled in (
                        ("value", True),
                        ("formula", bool(options.get("formulas"))),
                        ("style", bool(options.get("styles"))),
                        ("comment", bool(options.get("comments"))),
                    )
                    if enabled
                ),
                "--skip-hidden=true" if selection["skip_hidden"] else "--skip-hidden=false",
                "--max-chars",
                str(selection["max_chars"]),
                "--format",
                "json",
            )
            cells_data = nested(cells_payload, "data", default={})
            if not isinstance(cells_data, dict) or cells_data.get("has_more") or cells_data.get("truncated"):
                raise RuntimeError("configured Sheet preservation range was truncated")
            snapshot: dict[str, Any] = {
                "schema_version": 1,
                "kind": "feishu_sheet_snapshot",
                "sheet_id": sheet_id,
                "sheet_title": sheet_title,
                "range": selection["range"],
                "cells": cells_data,
            }
            if options.get("layout"):
                snapshot["layout"] = nested(
                    run_cli(config, "sheets", "+sheet-info", "--as", "bot", "--spreadsheet-token", obj_token,
                            "--sheet-id", sheet_id, "--range", str(selection["range"]),
                            "--include", "merges,row_heights,col_widths,hidden_rows,hidden_cols,groups,frozen",
                            "--format", "json"),
                    "data", default={},
                )
            if options.get("charts"):
                snapshot["charts"] = nested(
                    run_cli(config, "sheets", "+chart-list", "--as", "bot", "--spreadsheet-token", obj_token,
                            "--sheet-id", sheet_id, "--format", "json"),
                    "data", default={},
                )
            if options.get("floating_images"):
                snapshot["floating_images"] = nested(
                    run_cli(config, "sheets", "+float-image-list", "--as", "bot", "--spreadsheet-token", obj_token,
                            "--sheet-id", sheet_id, "--format", "json"),
                    "data", default={},
                )
            report_queries = (
                ("pivots", "+pivot-list", "pivot_tables"),
                ("filters", "+filter-list", "filters"),
                ("conditional_formats", "+cond-format-list", "conditional_formats"),
                ("sparklines", "+sparkline-list", "sparklines"),
            )
            for option, command, field in report_queries:
                if options.get(option):
                    snapshot[field] = nested(
                        run_cli(
                            config, "sheets", command, "--as", "bot",
                            "--spreadsheet-token", obj_token, "--sheet-id", sheet_id,
                            "--format", "json",
                        ),
                        "data", default={},
                    )
            snapshot_root.mkdir(parents=True, exist_ok=True)
            filename = f"{(node_token or obj_token)[:16]}--{sheet_id[:16]}.sheet.json"
            write_text(snapshot_root / filename, json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
            labels = {
                "formulas": "公式",
                "styles": "样式",
                "comments": "批注",
                "layout": "布局",
                "charts": "图表",
                "floating_images": "浮动图片",
                "pivots": "透视表",
                "filters": "筛选器",
                "conditional_formats": "条件格式",
                "sparklines": "迷你图",
            }
            preserved = "、".join(label for key, label in labels.items() if options.get(key))
            preservation_note = f"已保存{preserved or '单元格'}的本地保真快照。"
        sections.extend(
            [
                "",
                SHEET_TAB_RENDER_MARKER,
                "",
                f"{heading} {sheet_title}",
                "",
                f"范围：`{selection['range']}`",
                *(["", preservation_note] if preservation_note else []),
                "",
                markdown_table_from_csv(csv_value),
            ]
        )
    return "\n".join(sections).rstrip() + "\n", ""


def fetch_embedded_sheet_markdown(
    config: dict[str, Any],
    document_xml: str,
    settings: dict[str, Any],
    *,
    snapshot_root: Path | None,
    node_token: str,
) -> tuple[str, int]:
    """Render opted-in Sheet blocks found in one document XML as bounded local tables."""
    references = embedded_sheet_references(
        document_xml,
        max_count=int(settings["max_sheets_per_document"]),
    )
    if not references:
        return "", 0
    workbook_cache: dict[str, list[dict[str, Any]]] = {}
    sections: list[str] = []
    for reference in references:
        workbook_token = reference["workbook_token"]
        workbook_sheets = workbook_cache.get(workbook_token)
        if workbook_sheets is None:
            payload = run_cli(
                config,
                "sheets",
                "+workbook-info",
                "--as",
                "bot",
                "--spreadsheet-token",
                workbook_token,
                "--format",
                "json",
            )
            workbook_sheets = nested(payload, "data", "sheets", default=[])
            if not isinstance(workbook_sheets, list):
                raise RuntimeError("embedded Sheet workbook metadata has no data.sheets list")
            workbook_cache[workbook_token] = workbook_sheets
        sheet = next(
            (
                item
                for item in workbook_sheets
                if isinstance(item, dict) and str(item.get("sheet_id", "")) == reference["sheet_id"]
            ),
            None,
        )
        if sheet is None:
            raise RuntimeError("embedded Sheet reference was not found in workbook metadata")
        if str(sheet.get("resource_type", "sheet")) != "sheet":
            raise RuntimeError("embedded Sheet reference is not a grid worksheet")
        selection = embedded_sheet_selection(settings, sheet)
        rendered, _ = fetch_sheet_markdown(
            config,
            workbook_token,
            "嵌入式表格",
            [selection],
            snapshot_root=snapshot_root,
            node_token=node_token,
            workbook_sheets=workbook_sheets,
            include_document_heading=False,
            section_heading_level=3,
        )
        sections.extend([EMBEDDED_SHEET_RENDER_MARKER, rendered.rstrip()])
    return "\n\n".join(sections).rstrip(), len(references)


def configured_bitable_selections(config: dict[str, Any], enabled: bool) -> dict[str, list[dict[str, Any]]]:
    """Return explicitly authorised, record-bounded Base table selections."""
    if not enabled:
        return {}
    settings = nested(config, "sync", "bitables", default={})
    if not isinstance(settings, dict):
        raise SystemExit("sync.bitables must be a mapping")
    raw_selections = settings.get("selections", [])
    if not isinstance(raw_selections, list) or not raw_selections:
        raise SystemExit("sync.bitables.selections is required when Base mirroring is enabled")
    try:
        default_max_records = max(1, min(int(settings.get("max_records", DEFAULT_BITABLE_MAX_RECORDS)), 5_000))
    except (TypeError, ValueError):
        default_max_records = DEFAULT_BITABLE_MAX_RECORDS
    download_attachments = bool(settings.get("download_attachments", False))
    selections: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()
    for raw in raw_selections:
        if not isinstance(raw, dict):
            raise SystemExit("each sync.bitables.selections item must be a mapping")
        node_token = str(raw.get("node_token", "")).strip()
        table_id = str(raw.get("table_id", "")).strip()
        if not node_token or not table_id:
            raise SystemExit("each Base selection requires node_token and table_id")
        try:
            max_records = max(1, min(int(raw.get("max_records", default_max_records)), 5_000))
        except (TypeError, ValueError):
            raise SystemExit("each Base selection max_records must be an integer")
        key = (node_token, table_id)
        if key in seen:
            raise SystemExit("sync.bitables.selections contains a duplicate node_token and table_id")
        seen.add(key)
        selections.setdefault(node_token, []).append(
            {
                "table_id": table_id,
                "view_id": str(raw.get("view_id", "")).strip(),
                "max_records": max_records,
                "include_views": bool(raw.get("include_views", False)),
                "include_dashboards": bool(raw.get("include_dashboards", False)),
                "download_attachments": bool(raw.get("download_attachments", download_attachments)),
            }
        )
    return selections


def markdown_table_from_rows(rows: list[list[Any]]) -> str:
    stream = io.StringIO()
    csv.writer(stream).writerows([["" if value is None else str(value) for value in row] for row in rows])
    return markdown_table_from_csv(stream.getvalue())


def bitable_cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        names = [str(item.get("name", "")) for item in value if isinstance(item, dict) and item.get("name")]
        if names:
            return ", ".join(names)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def bitable_attachment_tokens(value: Any) -> list[str]:
    """Find Base attachment file tokens without exposing them in rendered Markdown."""
    tokens: list[str] = []
    if isinstance(value, dict):
        token = value.get("file_token")
        if isinstance(token, str) and token:
            tokens.append(token)
        for child in value.values():
            tokens.extend(bitable_attachment_tokens(child))
    elif isinstance(value, list):
        for child in value:
            tokens.extend(bitable_attachment_tokens(child))
    return list(dict.fromkeys(tokens))


def download_bitable_record_attachments(
    config: dict[str, Any],
    *,
    base_token: str,
    table_id: str,
    record_id: str,
    file_tokens: list[str],
    mirror_dir: Path,
) -> list[str]:
    """Download explicitly selected Base attachments into a hashed local asset folder."""
    asset_dir = str(nested(config, "sync", "asset_dir", default=DEFAULT_ASSET_DIR)).strip("/\\")
    if not asset_dir or Path(asset_dir).is_absolute() or ".." in Path(asset_dir).parts:
        raise SystemExit("sync.asset_dir must be a relative directory without '..'")
    try:
        max_bytes = max(1, int(nested(config, "sync", "max_asset_bytes", default=DEFAULT_MAX_ASSET_BYTES)))
    except (TypeError, ValueError):
        max_bytes = DEFAULT_MAX_ASSET_BYTES
    bucket = hashlib.sha256(f"{base_token}\0{table_id}\0{record_id}".encode("utf-8")).hexdigest()[:24]
    relative_dir = Path(asset_dir) / "bitables" / bucket
    destination = mirror_dir / relative_dir
    destination.mkdir(parents=True, exist_ok=True)
    for token in file_tokens:
        command = cli_command(
            config,
            "base",
            "+record-download-attachment",
            "--as",
            "bot",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--record-id",
            record_id,
            "--file-token",
            token,
            "--output",
            relative_dir.as_posix(),
            "--format",
            "json",
        )
        REQUEST_LIMITER.acquire()
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=mirror_dir,
            env=command_env(config),
        )
        if result.returncode != 0:
            detail = " ".join(part.strip() for part in (result.stderr, result.stdout) if part.strip())
            info = cli_error_info(detail)
            raise CliCommandError(
                f"lark-cli Base attachment request failed category={info['category']}",
                category=str(info["category"]),
                code=str(info["code"]),
                retryable=bool(info["retryable"]),
            )
    files: list[str] = []
    for candidate in sorted(destination.rglob("*")):
        if not candidate.is_file():
            continue
        if candidate.stat().st_size > max_bytes:
            candidate.unlink()
            raise RuntimeError(f"Base attachment exceeds max_asset_bytes={max_bytes}")
        files.append(candidate.relative_to(mirror_dir).as_posix())
    if file_tokens and not files:
        raise RuntimeError("base +record-download-attachment returned no local file")
    return files


def paged_base_items(config: dict[str, Any], *args: str) -> list[dict[str, Any]]:
    """Read a bounded Base paginated list without silently dropping reports."""
    page_token = ""
    items: list[dict[str, Any]] = []
    for _page in range(100):
        command = [*args, "--page-size", "100"]
        if page_token:
            command.extend(["--page-token", page_token])
        payload = run_cli(config, *command)
        data = nested(payload, "data", default={})
        if not isinstance(data, dict):
            raise RuntimeError("Base paginated payload has no data object")
        page_items = data.get("items", [])
        if not isinstance(page_items, list):
            raise RuntimeError("Base paginated payload has no items list")
        items.extend(item for item in page_items if isinstance(item, dict))
        page_token = str(data.get("page_token") or "")
        if not data.get("has_more"):
            return items
        if not page_token:
            raise RuntimeError("Base paginated payload reports has_more without page_token")
    raise RuntimeError("Base paginated list exceeded 100 pages")


def fetch_bitable_dashboards(config: dict[str, Any], base_token: str) -> list[dict[str, Any]]:
    """Capture Base dashboard definitions and their report blocks as JSON metadata."""
    dashboards = paged_base_items(
        config, "base", "+dashboard-list", "--as", "bot", "--base-token", base_token, "--format", "json"
    )
    result: list[dict[str, Any]] = []
    for dashboard in dashboards:
        dashboard_id = str(dashboard.get("dashboard_id", "")).strip()
        entry = dict(dashboard)
        if dashboard_id:
            entry["blocks"] = paged_base_items(
                config, "base", "+dashboard-block-list", "--as", "bot", "--base-token", base_token,
                "--dashboard-id", dashboard_id, "--format", "json",
            )
        result.append(entry)
    return result


def fetch_bitable_markdown(
    config: dict[str, Any],
    obj_token: str,
    title: str,
    selections: list[dict[str, Any]],
    *,
    snapshot_root: Path,
    node_token: str,
    mirror_dir: Path | None = None,
    include_document_heading: bool = True,
    section_heading_level: int = 2,
) -> tuple[str, str]:
    """Mirror selected Base tables, schemas, records and optional view metadata."""
    sections = [f"# {title}", "", "> 已按私有配置读取指定多维表格。"] if include_document_heading else []
    heading = "#" * max(1, min(section_heading_level, 6))
    snapshot_root.mkdir(parents=True, exist_ok=True)
    for selection in selections:
        table_id = str(selection["table_id"])
        fields_payload = run_cli(
            config, "base", "+field-list", "--as", "bot", "--base-token", obj_token,
            "--table-id", table_id, "--limit", "200", "--format", "json",
        )
        fields_data = nested(fields_payload, "data", default={})
        fields = fields_data.get("items", fields_data.get("fields", [])) if isinstance(fields_data, dict) else []
        if not isinstance(fields, list):
            raise RuntimeError("base +field-list payload has no fields list")
        name_by_id = {
            str(field.get("field_id", "")): str(field.get("field_name") or field.get("name") or field.get("field_id"))
            for field in fields if isinstance(field, dict) and field.get("field_id")
        }
        rows: list[dict[str, Any]] = []
        offset = 0
        while len(rows) < int(selection["max_records"]):
            limit = min(200, int(selection["max_records"]) - len(rows))
            command = [
                "base", "+record-list", "--as", "bot", "--base-token", obj_token,
                "--table-id", table_id, "--limit", str(limit), "--offset", str(offset), "--format", "json",
            ]
            if selection.get("view_id"):
                command.extend(["--view-id", str(selection["view_id"])])
            payload = run_cli(config, *command)
            data = nested(payload, "data", default={})
            items = data.get("items", data.get("records", [])) if isinstance(data, dict) else []
            if not isinstance(items, list):
                raise RuntimeError("base +record-list payload has no records list")
            rows.extend(item for item in items if isinstance(item, dict))
            if not items or not isinstance(data, dict) or not data.get("has_more"):
                break
            offset += len(items)
        columns = [name_by_id.get(str(field.get("field_id", "")), "字段") for field in fields if isinstance(field, dict)]
        rendered_rows = [columns]
        for record in rows:
            values = record.get("fields", {})
            values = values if isinstance(values, dict) else {}
            rendered_rows.append([
                bitable_cell_text(values.get(field_id, values.get(name, "")))
                for field_id, name in name_by_id.items()
            ])
        snapshot: dict[str, Any] = {
            "schema_version": 1,
            "kind": "feishu_bitable_snapshot",
            "base_token": obj_token,
            "table_id": table_id,
            "fields": fields,
            "records": rows,
        }
        attachment_errors: dict[str, str] = {}
        attachment_files: dict[str, list[str]] = {}
        if selection.get("download_attachments"):
            if mirror_dir is None:
                raise RuntimeError("Base attachment download requires the local mirror directory")
            for record in rows:
                record_id = str(record.get("record_id", "")).strip()
                fields_value = record.get("fields", {})
                tokens = bitable_attachment_tokens(fields_value)
                if not record_id or not tokens:
                    continue
                try:
                    attachment_files[record_id] = download_bitable_record_attachments(
                        config,
                        base_token=obj_token,
                        table_id=table_id,
                        record_id=record_id,
                        file_tokens=tokens,
                        mirror_dir=mirror_dir,
                    )
                except Exception as exc:
                    attachment_errors[record_id] = safe_error_category(exc)
        if attachment_files:
            snapshot["local_attachment_paths"] = attachment_files
        if attachment_errors:
            snapshot["attachment_errors"] = attachment_errors
        if selection.get("include_views"):
            snapshot["views"] = nested(
                run_cli(config, "base", "+view-list", "--as", "bot", "--base-token", obj_token,
                        "--table-id", table_id, "--limit", "200", "--format", "json"),
                "data", default={},
            )
        if selection.get("include_dashboards"):
            snapshot["dashboards"] = fetch_bitable_dashboards(config, obj_token)
        write_text(snapshot_root / f"{node_token[:16]}--{table_id[:16]}.bitable.json", json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
        attachment_note = ""
        if attachment_files:
            attachment_note = "已按显式配置下载该表记录中的附件；本地路径写入保真快照。"
        elif attachment_errors:
            attachment_note = "部分附件未能下载；失败类别已写入保真快照。"
        sections.extend(
            ["", f"{heading} {table_id}", *(["", attachment_note] if attachment_note else []), "", markdown_table_from_rows(rendered_rows)]
        )
    return "\n".join(sections).rstrip() + "\n", ""


def relative_safe_directory(value: Any, *, setting: str) -> Path:
    """Validate a generated-resource directory before passing it to lark-cli."""
    directory = str(value or "").strip("/\\")
    path = Path(directory)
    if not directory or path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"{setting} must be a relative directory without '..'")
    return path


def resource_initialization_settings(
    config: dict[str, Any],
    *,
    section: str,
    key: str,
) -> dict[str, Any] | None:
    """Return an explicit whole-resource initialization policy, or None.

    A plain ``enabled`` switch is deliberately insufficient here: these routes
    download complete workbooks, Bases, or Drive files.  Requiring both flags
    records the user's whole-resource approval in the private config.
    """
    settings = nested(config, "sync", section, key, default={})
    if not isinstance(settings, dict):
        raise SystemExit(f"sync.{section}.{key} must be a mapping")
    if not bool(settings.get("enabled", False)):
        return None
    if not bool(settings.get("all_nodes", False)):
        raise SystemExit(
            f"sync.{section}.{key}.all_nodes=true is required for complete resource initialization"
        )
    directory = relative_safe_directory(
        settings.get("output_dir", f"{DEFAULT_RESOURCE_EXPORT_DIR}/{section}"),
        setting=f"sync.{section}.{key}.output_dir",
    )
    try:
        batch_size = max(1, min(int(settings.get("batch_size", DEFAULT_RESOURCE_BATCH_SIZE)), 100))
    except (TypeError, ValueError):
        raise SystemExit(f"sync.{section}.{key}.batch_size must be an integer from 1 to 100")
    try:
        timeout_seconds = max(10, min(int(settings.get("timeout_seconds", DEFAULT_RESOURCE_TIMEOUT_SECONDS)), 900))
    except (TypeError, ValueError):
        raise SystemExit(f"sync.{section}.{key}.timeout_seconds must be an integer from 10 to 900")
    return {
        "output_dir": directory,
        "batch_size": batch_size,
        "timeout_seconds": timeout_seconds,
    }


def safe_file_extension(title: Any, fallback: str = ".bin") -> str:
    """Keep a harmless filename suffix so opaque binary assets stay identifiable."""
    suffix = Path(str(title or "")).suffix.lower()
    if re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
        return suffix
    return fallback


def resource_export_path(node: dict[str, Any], output_dir: Path, suffix: str) -> Path:
    """Return a stable local resource target without exposing remote tokens in names."""
    seed = f"{node.get('obj_token', '')}\0{node.get('node_token', '')}"
    name = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24] + suffix
    return output_dir / name


def export_file_token(payload: Any) -> str:
    """Find the file token returned by a completed/pending export task."""
    if isinstance(payload, dict):
        token = payload.get("file_token")
        if isinstance(token, str) and token.strip():
            return token.strip()
        for value in payload.values():
            token = export_file_token(value)
            if token:
                return token
    elif isinstance(payload, list):
        for value in payload:
            token = export_file_token(value)
            if token:
                return token
    return ""


def export_task_reference(stdout: str) -> tuple[str, str] | None:
    """Return an async export ticket and its source file token, when present."""
    try:
        payload = parse_cli_json(stdout)
    except RuntimeError:
        return None
    data = nested(payload, "data", default={})
    if not isinstance(data, dict):
        return None
    ticket = str(data.get("ticket") or "").strip()
    source_file_token = str(data.get("token") or "").strip()
    return (ticket, source_file_token) if ticket and source_file_token else None


def download_export_file(
    config: dict[str, Any],
    mirror_dir: Path,
    target: Path,
    timeout_seconds: int,
    file_token: str,
) -> subprocess.CompletedProcess[str]:
    """Download a completed Drive export through its dedicated endpoint."""
    REQUEST_LIMITER.acquire()
    return subprocess.run(
        cli_command(
            config,
            "drive", "+export-download", "--as", "bot", "--file-token", file_token,
            "--output-dir", target.parent.relative_to(mirror_dir).as_posix(),
            "--file-name", target.name, "--overwrite", "--format", "json",
        ),
        check=False,
        capture_output=True,
        text=True,
        cwd=mirror_dir,
        env=command_env(config),
        timeout=timeout_seconds,
    )


def resume_export_download(
    config: dict[str, Any],
    mirror_dir: Path,
    target: Path,
    timeout_seconds: int,
    stdout: str,
) -> subprocess.CompletedProcess[str] | None:
    """Download a ready export file when the async exporter returned its token."""
    try:
        token = export_file_token(parse_cli_json(stdout))
    except RuntimeError:
        return None
    if not token:
        return None
    return download_export_file(config, mirror_dir, target, timeout_seconds, token)


def poll_sheet_export_task(
    config: dict[str, Any],
    mirror_dir: Path,
    target: Path,
    timeout_seconds: int,
    *,
    ticket: str,
    source_file_token: str,
) -> bool:
    """Poll one saved Sheet export task once, downloading it only when ready."""
    REQUEST_LIMITER.acquire()
    result = subprocess.run(
        cli_command(
            config,
            "drive", "+task_result", "--as", "bot", "--scenario", "export",
            "--ticket", ticket, "--file-token", source_file_token, "--format", "json",
        ),
        check=False,
        capture_output=True,
        text=True,
        cwd=mirror_dir,
        env=command_env(config),
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        detail = " ".join(part.strip() for part in (result.stderr, result.stdout) if part.strip())
        info = cli_error_info(detail)
        raise CliCommandError(
            f"lark-cli export task poll failed category={info['category']}",
            category=str(info["category"]),
            code=str(info["code"]),
            retryable=bool(info["retryable"]),
        )
    payload = parse_cli_json(result.stdout)
    data = nested(payload, "data", default={})
    if not isinstance(data, dict):
        raise CliCommandError("lark-cli export task returned no data", category="invalid_response")
    if data.get("failed") is True:
        raise CliCommandError("lark-cli export task reported failure", category="cli_error")
    if not data.get("ready"):
        return False
    file_token = export_file_token(data)
    if not file_token:
        raise CliCommandError("ready export task returned no exported file token", category="invalid_response")
    download = download_export_file(config, mirror_dir, target, timeout_seconds, file_token)
    if download.returncode == 0 and target.is_file() and target.stat().st_size > 0:
        return True
    detail = " ".join(part.strip() for part in (download.stderr, download.stdout) if part.strip())
    info = cli_error_info(detail)
    raise CliCommandError(
        f"lark-cli export download failed category={info['category']}",
        category=str(info["category"]),
        code=str(info["code"]),
        retryable=bool(info["retryable"]),
    )


def run_cli_to_local_path(
    config: dict[str, Any],
    mirror_dir: Path,
    target: Path,
    timeout_seconds: int,
    *args: str,
) -> None:
    """Run a read-only CLI download/export and require the requested local file."""
    command = cli_command(config, *args)
    for attempt in range(5):
        REQUEST_LIMITER.acquire()
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=mirror_dir,
                env=command_env(config),
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            if attempt < 4:
                REQUEST_LIMITER.cooldown(min(30, 2**attempt))
                continue
            raise CliCommandError(
                "lark-cli resource export timed out",
                category="temporary_network",
                retryable=True,
            ) from exc
        if result.returncode == 0:
            if target.is_file() and target.stat().st_size > 0:
                return
            # A pending export response may contain the source document's
            # file token.  Persist its ticket before attempting any generic
            # file-token download, otherwise that source token can be
            # mistaken for a completed export artifact.
            reference = export_task_reference(result.stdout)
            if reference is not None:
                raise ExportPending(*reference)
            try:
                resumed = resume_export_download(
                    config, mirror_dir, target, timeout_seconds, result.stdout
                )
            except subprocess.TimeoutExpired:
                resumed = None
            if resumed is not None:
                result = resumed
                if result.returncode == 0 and target.is_file() and target.stat().st_size > 0:
                    return
        detail = " ".join(part.strip() for part in (result.stderr, result.stdout) if part.strip())
        # `sheets +workbook-export` can successfully create/poll an async
        # task yet return before its requested local file is available.  Its
        # JSON status is not an API error, so classify every zero-exit/missing
        # target case as retryable rather than leaking it as `cli_error`.
        info = (
            {"category": "export_incomplete", "code": "", "retryable": True}
            if result.returncode == 0
            else cli_error_info(detail)
        )
        if info["retryable"] and attempt < 4:
            REQUEST_LIMITER.cooldown(min(30, 2**attempt))
            continue
        code_suffix = f" code={info['code']}" if info["code"] else ""
        raise CliCommandError(
            f"lark-cli resource export failed category={info['category']}{code_suffix}",
            category=str(info["category"]),
            code=str(info["code"]),
            retryable=bool(info["retryable"]),
        )


def initialize_complete_resources(
    config: dict[str, Any],
    nodes: list[dict[str, Any]],
    mirror_dir: Path,
    *,
    obj_type: str,
    section: str,
    key: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    """Export/download a bounded batch of whole resources with explicit approval.

    The returned paths are relative to the generated mirror so caller-created
    Markdown can link to the offline original without leaking tokens.
    """
    settings = resource_initialization_settings(config, section=section, key=key)
    stats = {"downloaded": 0, "reused": 0, "failed": 0, "pending": 0, "deferred": 0}
    if settings is None:
        return {}, {}, stats
    candidates = [node for node in nodes if str(node.get("obj_type", "")) == obj_type]
    target_dir = mirror_dir / settings["output_dir"]
    ready: dict[str, str] = {}
    pending: list[tuple[dict[str, Any], Path]] = []
    task_state_path = mirror_dir / DEFAULT_SHEET_SNAPSHOT_DIR / "sheet-export-tasks.json"
    task_state = load_json(task_state_path, {"version": 1, "tasks": {}}) if obj_type == "sheet" else {}
    tasks = task_state.get("tasks", {}) if isinstance(task_state, dict) else {}
    tasks = dict(tasks) if isinstance(tasks, dict) else {}
    for node in candidates:
        suffix = (
            ".xlsx" if obj_type == "sheet" else ".base" if obj_type == "bitable" else safe_file_extension(node.get("title"))
        )
        target = resource_export_path(node, target_dir, suffix)
        token = str(node.get("node_token", ""))
        if target.is_file() and target.stat().st_size > 0:
            ready[token] = target.relative_to(mirror_dir).as_posix()
            stats["reused"] += 1
            tasks.pop(token, None)
        else:
            pending.append((node, target))
    selected, deferred = pending[: settings["batch_size"]], pending[settings["batch_size"] :]
    stats["deferred"] = len(deferred)
    errors: dict[str, str] = {}
    for node, target in selected:
        token = str(node.get("node_token", ""))
        relative_target = target.relative_to(mirror_dir).as_posix()
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if obj_type == "sheet":
                saved_task = tasks.get(token)
                if isinstance(saved_task, dict):
                    ticket = str(saved_task.get("ticket") or "").strip()
                    source_file_token = str(saved_task.get("source_file_token") or "").strip()
                    if ticket and source_file_token:
                        if not poll_sheet_export_task(
                            config, mirror_dir, target, settings["timeout_seconds"],
                            ticket=ticket, source_file_token=source_file_token,
                        ):
                            errors[token] = "export_pending"
                            stats["pending"] += 1
                            continue
                    else:
                        tasks.pop(token, None)
                if not target.is_file() or target.stat().st_size == 0:
                    run_cli_to_local_path(
                        config, mirror_dir, target, settings["timeout_seconds"],
                        "drive", "+export", "--as", "bot", "--doc-type", "sheet",
                        "--token", str(node.get("obj_token", "")), "--file-extension", "xlsx",
                        "--output-dir", settings["output_dir"].as_posix(), "--file-name", target.name,
                        "--overwrite", "--format", "json",
                    )
            elif obj_type == "bitable":
                run_cli_to_local_path(
                    config, mirror_dir, target, settings["timeout_seconds"],
                    "drive", "+export", "--as", "bot", "--doc-type", "bitable",
                    "--token", str(node.get("obj_token", "")), "--file-extension", "base",
                    "--output-dir", settings["output_dir"].as_posix(), "--file-name", target.name,
                    "--overwrite", "--format", "json",
                )
            else:
                run_cli_to_local_path(
                    config, mirror_dir, target, settings["timeout_seconds"],
                    "drive", "+download", "--as", "bot", "--file-token", str(node.get("obj_token", "")),
                    "--output", relative_target, "--overwrite", "--format", "json",
                )
            ready[token] = relative_target
            stats["downloaded"] += 1
            tasks.pop(token, None)
        except ExportPending as exc:
            tasks[token] = {
                "ticket": exc.ticket,
                "source_file_token": exc.source_file_token,
                "created_at": utc_now(),
            }
            errors[token] = "export_pending"
            stats["pending"] += 1
        except Exception as exc:
            errors[token] = safe_error_category(exc)
            stats["failed"] += 1
    if obj_type == "sheet":
        write_text(task_state_path, json.dumps({"version": 1, "tasks": tasks}, ensure_ascii=False, indent=2) + "\n")
    return ready, errors, stats


def clean_title(title: Any, fallback: str) -> str:
    value = str(title or fallback).strip()
    value = re.sub(r"[\\/:*?\"<>|]", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value or fallback


def path_component(title: str, token: str, marker: str = "") -> str:
    """Keep local names readable while bounding VitePress/Rollup route length."""
    suffix = f"{marker}{token[:8]}" if marker else ""
    if len(title) + len(suffix) <= MAX_PATH_COMPONENT_LENGTH:
        return f"{title}{suffix}"
    if not marker:
        suffix = f"--{token[:8]}"
    keep = max(1, MAX_PATH_COMPONENT_LENGTH - len(suffix))
    return f"{title[:keep]}{suffix}"


def unique_path(
    title: str,
    parent_rel: Path,
    used: set[str],
    token: str,
    has_children: bool,
    directory_name: str | None = None,
    file_stem: str | None = None,
) -> Path:
    directory = directory_name or title
    stem = file_stem or title
    if has_children:
        base = parent_rel / directory / f"{stem}.md"
    else:
        base = parent_rel / f"{stem}.md"
    if str(base) not in used:
        used.add(str(base))
        return base
    if has_children:
        candidate = parent_rel / directory / f"{stem}--{token[:8]}.md"
    else:
        candidate = parent_rel / f"{stem}--{token[:8]}.md"
    counter = 2
    while str(candidate) in used:
        candidate = parent_rel / f"{stem}--{token[:8]}-{counter}.md"
        counter += 1
    used.add(str(candidate))
    return candidate


def html_attributes(value: str) -> dict[str, str]:
    """Parse the small quoted-attribute subset emitted by Feishu Markdown exports."""
    return {key.lower(): item for key, _quote, item in HTML_ATTRIBUTE_PATTERN.findall(value)}


def markdown_link(label: str, target: str) -> str:
    """Render a portable Markdown link while preserving local paths with spaces."""
    visible = (label or target).replace("[", "\\[").replace("]", "\\]")
    if not target:
        return visible
    if target.startswith(("http://", "https://", "feishu-media://")):
        return f"[{visible}]({target})"
    return f"[{visible}](<{target}>)"


def document_target_for_url(url: str, document_links: dict[str, str]) -> str:
    """Resolve a Feishu Wiki/doc URL to a configured local or remote document target."""
    lowered = url.lower()
    if "feishu" not in lowered and "larksuite" not in lowered:
        return ""
    for identifier in sorted(document_links, key=len, reverse=True):
        if identifier and identifier in url:
            return document_links[identifier]
    return ""


def rewrite_feishu_document_urls(content: str, document_links: dict[str, str]) -> str:
    """Replace known Feishu document URLs without touching media or unrelated web links."""
    def replace_markdown_link(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2).strip()
        target = document_target_for_url(url, document_links)
        return markdown_link(label or url, target) if target else match.group(0)

    value = MARKDOWN_LINK_PATTERN.sub(replace_markdown_link, content)

    def replace_bare_url(match: re.Match[str]) -> str:
        url = match.group(0)
        target = document_target_for_url(url, document_links)
        return markdown_link(url, target) if target else url

    return BARE_FEISHU_DOCUMENT_URL_PATTERN.sub(replace_bare_url, value)


def normalize_content(
    content: str,
    title: str,
    cite_links: dict[str, str] | None = None,
    *,
    render_sub_page_navigation: bool = False,
    localize_document_links: bool = False,
) -> str:
    value = content.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"^\s*<title>.*?</title>\s*", "", value, count=1, flags=re.IGNORECASE | re.DOTALL)
    value = value.replace("<wiki_recent_update></wiki_recent_update>", "")

    def replace_attachment_source(match: re.Match[str]) -> str:
        attrs = html_attributes(match.group(1))
        href = attrs.get("href", "")
        token = attrs.get("token", "")
        mime = attrs.get("mime", "")
        if mime.lower().startswith("image/"):
            source = href or (f"feishu-media://{token}" if token else "")
            if source:
                token_attr = f' data-feishu-token="{html_escape(token, quote=True)}"' if token else ""
                return f'<img src="{html_escape(source, quote=True)}" alt="飞书图片"{token_attr}>'
        if href and token:
            return (
                f'<a href="{html_escape(href, quote=True)}" data-feishu-attachment="true" '
                f'data-feishu-token="{html_escape(token, quote=True)}" '
                f'data-feishu-mime="{html_escape(mime, quote=True)}">飞书附件</a>'
            )
        if href:
            return f"[飞书附件]({href})"
        if token:
            return f"[飞书附件](feishu-media://{token})"
        return "（飞书附件）"

    # Feishu exports custom figure/grid/source tags. VitePress' Vue parser
    # treats these as components and can reject otherwise valid Markdown; keep
    # the attachment URL while removing the non-standard wrapper tags.
    value = re.sub(r"<source\b([^>]*)/?>", replace_attachment_source, value, flags=re.IGNORECASE)

    if render_sub_page_navigation:
        def render_sub_page_list(match: re.Match[str]) -> str:
            pages: list[str] = []
            for page in SUB_PAGE_PATTERN.finditer(match.group(0)):
                attrs = html_attributes(page.group(1))
                page_title = attrs.get("title", "").strip() or "未命名子页面"
                identifier = (
                    attrs.get("doc-id", "").strip()
                    or attrs.get("wiki-token", "").strip()
                    or attrs.get("node-token", "").strip()
                )
                target = cite_links.get(identifier, "") if identifier and cite_links else ""
                pages.append(f"- {markdown_link(page_title, target)}")
            if not pages:
                return ""
            return "## 子页面导航\n\n" + "\n".join(pages)

        value = SUB_PAGE_LIST_PATTERN.sub(render_sub_page_list, value)

    # Current lark-cli Markdown can expose an embedded worksheet as a bare
    # <sheet> tag.  Older normalisation removed that tag together with wrapper
    # markup, which silently turned a non-empty source block into blank local
    # content.  Keep a deterministic incompleteness marker unless the opted-in
    # XML + Sheets route replaces it with a bounded snapshot below.
    value = re.sub(
        r"<sheet\b[^>]*?/?>\s*(?:</sheet\s*>)?",
        "\n\n" + EMBEDDED_SHEET_UNMIRRORED_BLOCK + "\n\n",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"</?(?:figure|grid|column|callout|sub-page-list|sub-page|readonly-block)\b[^>]*>",
        "",
        value,
        flags=re.IGNORECASE,
    )

    def replace_feishu_image(match: re.Match[str]) -> str:
        attrs = html_attributes(match.group(1))
        href = attrs.get("href", "")
        src = attrs.get("src", "")
        token = attrs.get("token", "")
        alt_value = attrs.get("alt", "")
        image_url = (
            href
            if href
            else src
            if src
            else f"feishu-media://{token}"
            if token
            else ""
        )
        if not image_url:
            return "（飞书图片）"
        alt = (alt_value or "飞书图片").replace('"', "'")
        token_attr = f' data-feishu-token="{html_escape(token, quote=True)}"' if token else ""
        return f'<img src="{html_escape(image_url, quote=True)}" alt="{html_escape(alt, quote=True)}"{token_attr}>'

    # The Feishu exporter sometimes puts an opaque media token in img[src] and
    # the authenticated URL in img[href]. VitePress would treat the token as a
    # local module import, so prefer href as the rendered image source.
    value = re.sub(r"<img\b([^>]*)/?>", replace_feishu_image, value, flags=re.IGNORECASE)

    def replace_cite(match: re.Match[str]) -> str:
        attrs = match.group(1)
        doc_match = re.search(r'doc-id="([^"]+)"', attrs)
        title_match = re.search(r'title="([^"]*)"', attrs)
        user_name_match = re.search(r'user-name="([^"]*)"', attrs)
        user_id_match = re.search(r'user-id="([^"]*)"', attrs)
        if user_name_match or user_id_match or re.search(r'\btype="user"', attrs, flags=re.IGNORECASE):
            user_label = (
                user_name_match.group(1)
                if user_name_match
                else user_id_match.group(1)
                if user_id_match
                else "飞书用户"
            ).strip()
            return f"@{user_label}" if user_label else "@飞书用户"
        label = (title_match.group(1) if title_match else "飞书文档").strip() or "飞书文档"
        target = cite_links.get(doc_match.group(1), "") if doc_match and cite_links else ""
        return markdown_link(label, target) if target else label

    # Resolve citations before generic XML escaping; cite is a Feishu export
    # construct, not an HTML tag that should be shown literally.
    value = re.sub(r"<cite\s+([^>]*)></cite>", replace_cite, value, flags=re.IGNORECASE)
    value = re.sub(r"<cite\s+([^>]*)/>", replace_cite, value, flags=re.IGNORECASE)
    if localize_document_links and cite_links:
        value = rewrite_feishu_document_urls(value, cite_links)

    # Feishu occasionally exports a very long image description as a Markdown
    # image label.  Markdown renderers disagree on those labels (especially
    # when they contain copied punctuation), and some degrade them into a
    # visible hyperlink instead of an image.  Use one portable HTML form for
    # every ordinary image, with a compact escaped alt value.  Asset discovery
    # and local URL rewriting both support this form.
    def render_markdown_image(match: re.Match[str]) -> str:
        alt = re.sub(r"\s+", " ", match.group(1)).strip() or "飞书图片"
        source = match.group(2).strip()
        if source.startswith("<") and source.endswith(">"):
            source = source[1:-1].strip()
        if not source:
            return "（飞书图片）"
        return f'<img src="{html_escape(source, quote=True)}" alt="{html_escape(alt, quote=True)}">'

    value = re.sub(r"!\[([^\]\n]*)\]\(\s*(<[^>\n]+>|[^)\n]+)\s*\)", render_markdown_image, value)

    # A few exports escape only the opening/closing table tags while keeping
    # the inner HTML. Restore the block boundary and remove paragraph wrappers
    # inside tables so Markdown-it does not emit the invalid `<p>...</table>`.
    value = re.sub(r"&lt;(/?)table&gt;", r"<\1table>", value, flags=re.IGNORECASE)

    def normalize_table_markup(match: re.Match[str]) -> str:
        return re.sub(r"</?p\b[^>]*>", "", match.group(0), flags=re.IGNORECASE)

    value = re.sub(
        r"<table\b[^>]*>.*?</table>",
        normalize_table_markup,
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    known_html_tags = {
        "a", "abbr", "b", "blockquote", "br", "caption", "code", "col", "colgroup",
        "del", "details", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i",
        "img", "li", "mark", "ol", "p", "pre", "s", "small", "strong", "sub", "sup",
        "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
    }

    def escape_unknown_html(match: re.Match[str]) -> str:
        tag_name = match.group(1).lower()
        if match.string[max(0, match.start() - 2) : match.start()] == "](":
            # Markdown permits angle-wrapped local destinations so paths with
            # spaces, parentheses, or non-ASCII characters remain portable.
            return match.group(0)
        return match.group(0) if tag_name in known_html_tags else match.group(0).replace("<", "&lt;").replace(">", "&gt;")

    # Raw XML/code snippets such as #include <iostream> and Maven XML are
    # common in exported docs but are not Markdown HTML. Escape unknown tags so
    # VitePress/Vue does not parse them as components.
    value = re.sub(r"<\/?\s*([A-Za-z][\w:-]*)\b[^>]*>", escape_unknown_html, value)

    # markdown-it-attrs treats braces at the end of headings as attribute
    # syntax. Error-message headings from Feishu often contain JSON-like braces;
    # preserve their visible text as entities instead of generating invalid Vue.
    def escape_heading_braces(match: re.Match[str]) -> str:
        return match.group(1).replace("{", "&#123;").replace("}", "&#125;")

    value = re.sub(r"(?m)^(#{1,6}\s+.*)$", escape_heading_braces, value)

    value = value.strip()
    return value or f"# {title}\n\n（飞书文档当前没有可转换的正文内容。）"


def render_document_content(
    config: dict[str, Any],
    obj_token: str,
    title: str,
    cite_links: dict[str, str] | None,
    *,
    render_sub_page_navigation: bool,
    localize_document_links: bool,
    embedded_sheet_settings: dict[str, Any] | None = None,
    snapshot_root: Path | None = None,
    node_token: str = "",
) -> tuple[str, str]:
    """Fetch Markdown and, when explicitly enabled, append bounded embedded Sheet snapshots."""
    raw_content, revision_id = fetch_doc(config, obj_token)
    content = normalize_content(
        raw_content,
        title,
        cite_links,
        render_sub_page_navigation=render_sub_page_navigation,
        localize_document_links=localize_document_links,
    )
    if embedded_sheet_settings is None:
        return content, revision_id
    document_xml = fetch_doc_xml(config, obj_token)
    embedded_content, embedded_count = fetch_embedded_sheet_markdown(
        config,
        document_xml,
        embedded_sheet_settings,
        snapshot_root=snapshot_root,
        node_token=node_token,
    )
    if EMBEDDED_SHEET_UNMIRRORED_MARKER in content and embedded_count == 0:
        raise RuntimeError("document Markdown contains an embedded Sheet that XML discovery did not resolve")
    if embedded_count:
        content = content.replace(
            EMBEDDED_SHEET_UNMIRRORED_BLOCK,
            EMBEDDED_SHEET_MIRRORED_POINTER,
        )
    appendix = [EMBEDDED_SHEET_SCAN_MARKER]
    if embedded_content:
        appendix.extend(["", "## 嵌入式表格", "", embedded_content])
    return content.rstrip() + "\n\n" + "\n".join(appendix), revision_id


def extract_image_urls(content: str) -> list[str]:
    """Return remote image URLs from Markdown images and raw HTML img tags.

    Feishu's Markdown exporter may wrap a URL destination in ``<...>``.  That
    is valid CommonMark (and protects signed query strings), but it used to
    bypass the asset queue because the older matcher expected ``(https://``
    directly.  Accept both forms so a valid image never becomes an accidental
    offline placeholder merely because of its Markdown delimiter.
    """
    urls = set(
        re.findall(
            r"!\[[^\]]*\]\(\s*<?(https?://[^)\s>]+)>?",
            content,
            flags=re.IGNORECASE,
        )
    )
    urls.update(
        re.findall(r"<img\b[^>]*\bsrc=[\"'](https?://[^\"']+)", content, flags=re.IGNORECASE)
    )
    return sorted(urls)


def extract_attachment_urls(content: str) -> list[str]:
    """Return remote URLs from both legacy Markdown and normalized attachment links."""
    urls = set(
        re.findall(
            r"\[飞书附件\]\(\s*<?(https?://[^)\s>]+)>?",
            content,
            flags=re.IGNORECASE,
        )
    )
    for match in re.finditer(r"<a\b([^>]*)>", content, flags=re.IGNORECASE):
        attrs = html_attributes(match.group(1))
        href = attrs.get("href", "").strip()
        if attrs.get("data-feishu-attachment", "").lower() == "true" and href.startswith(("http://", "https://")):
            urls.add(href)
    return sorted(urls)


def extract_media_tokens(content: str) -> list[str]:
    """Return media tokens carried through normalization for local download."""
    return sorted(set(re.findall(r"feishu-media://([A-Za-z0-9_-]+)", content)))


def asset_identities(content: str) -> dict[str, str]:
    """Prefer stable Feishu media tokens over short-lived signed URLs for deduplication."""
    identities: dict[str, str] = {}
    for match in re.finditer(r"<(?:img|a)\b([^>]*)>", content, flags=re.IGNORECASE):
        attrs = html_attributes(match.group(1))
        token = attrs.get("data-feishu-token", "").strip()
        reference = attrs.get("src", "").strip()
        if not reference and attrs.get("data-feishu-attachment", "").lower() == "true":
            reference = attrs.get("href", "").strip()
        if reference and token:
            identities[reference] = f"feishu-token:{token}"
    for token in extract_media_tokens(content):
        identities[f"feishu-media://{token}"] = f"feishu-token:{token}"
    return identities


def extract_asset_references(content: str) -> list[str]:
    """Return image URLs, attachment URLs, and token-backed media references."""
    return sorted(
        set(extract_image_urls(content))
        | set(extract_attachment_urls(content))
        | {f"feishu-media://{token}" for token in extract_media_tokens(content)}
    )


def asset_contents_for_sync(
    fetched: dict[str, tuple[str, str, str, str]],
    fresh_tokens: set[str],
    *,
    targeted: bool,
) -> list[str]:
    """Keep event and pilot asset downloads within the documents fetched in this run."""
    tokens = fresh_tokens if targeted else set(fetched)
    return [
        fetched[token][1]
        for token in sorted(tokens)
        if token in fetched and isinstance(fetched[token], tuple) and len(fetched[token]) > 1
    ]


def image_extension(content_type: str, data: bytes, url: str) -> str:
    """Infer a browser-renderable extension from bytes before response metadata."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    if data.lstrip().startswith(b"<svg") or b"<svg" in data[:512]:
        return ".svg"
    header = (content_type or "").split(";", 1)[0].lower().strip()
    by_type = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/bmp": ".bmp",
    }
    if header in by_type:
        return by_type[header]
    guessed = Path(urlparse(url).path).suffix.lower()
    return guessed if guessed in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"} else ".bin"


def repair_cached_image_extension(existing: Path, url: str) -> Path:
    """Correct a legacy image suffix when server headers disagreed with file bytes."""
    try:
        detected = image_extension("", existing.read_bytes()[:512], url)
    except OSError:
        return existing
    if detected == ".bin" or existing.suffix.lower() == detected:
        return existing
    corrected = existing.with_suffix(detected)
    if corrected.exists():
        return corrected if corrected.is_file() and corrected.stat().st_size else existing
    existing.rename(corrected)
    return corrected


def download_one_asset(
    url: str,
    asset_root: Path,
    timeout_seconds: float,
    max_bytes: int,
    require_image: bool = True,
    identity: str | None = None,
) -> tuple[str, str, str]:
    """Download one remote asset into a content-addressed local asset path."""
    digest = hashlib.sha256((identity or url).encode("utf-8")).hexdigest()[:24]
    existing = next(iter(sorted(asset_root.glob(f"{digest}.*"))), None)
    if existing and existing.is_file() and existing.stat().st_size:
        if require_image:
            existing = repair_cached_image_extension(existing, url)
        return url, existing.name, "reused"

    request = Request(url, headers={"User-Agent": "soia-cwork-feishu-doc-git-sync/1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise AssetSizeLimitError()
    extension = image_extension(content_type, data, url)
    if extension == ".bin" and require_image:
        raise RuntimeError(f"remote response is not a recognized image: {content_type or 'unknown content type'}")
    if extension == ".bin":
        extension = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip())
        if not extension:
            extension = Path(urlparse(url).path).suffix.lower() or ".bin"
    asset_root.mkdir(parents=True, exist_ok=True)
    target = asset_root / f"{digest}{extension}"
    target.write_bytes(data)
    return url, target.name, "downloaded"


def download_one_media(
    config: dict[str, Any],
    token: str,
    mirror_dir: Path,
    asset_dir: str,
    max_bytes: int,
    timeout_seconds: float,
    *,
    attempts: int = DEFAULT_ASSET_DOWNLOAD_ATTEMPTS,
) -> tuple[str, str, str]:
    """Download token-backed media with bounded retries for transient CLI failures."""
    reference = f"feishu-media://{token}"
    digest = hashlib.sha256(reference.encode("utf-8")).hexdigest()[:24]
    asset_root = mirror_dir / asset_dir
    existing = (
        next(
            (
                candidate
                for candidate in sorted(asset_root.glob(f"{digest}.*"))
                if candidate.is_file() and candidate.stat().st_size > 0
            ),
            None,
        )
        if asset_root.is_dir()
        else None
    )
    if existing and existing.is_file() and existing.stat().st_size:
        return reference, existing.name, "reused"
    asset_root.mkdir(parents=True, exist_ok=True)
    output_relative = (Path(asset_dir) / digest).as_posix()
    command = cli_command(
        config,
        "docs",
        "+media-download",
        "--as",
        "bot",
        "--token",
        token,
        "--output",
        output_relative,
        "--overwrite",
        "--format",
        "json",
    )
    attempts = max(1, min(int(attempts), 5))
    for attempt in range(attempts):
        REQUEST_LIMITER.acquire()
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=mirror_dir,
                env=command_env(config),
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            info = {"category": "temporary_network", "code": "", "retryable": True}
            failure: Exception | None = exc
        else:
            failure = None
            if result.returncode == 0:
                target = next(
                    (
                        candidate
                        for candidate in sorted(asset_root.glob(f"{digest}.*"))
                        if candidate.is_file() and candidate.stat().st_size > 0
                    ),
                    None,
                )
                if target is not None:
                    if target.stat().st_size > max_bytes:
                        target.unlink()
                        raise AssetSizeLimitError()
                    return reference, target.name, "downloaded"
                info = {"category": "invalid_response", "code": "", "retryable": True}
            else:
                detail = " ".join(part.strip() for part in (result.stderr, result.stdout) if part.strip())
                info = cli_error_info(detail)

        # Some Feishu media calls fail once with an unclassified CLI response
        # even though the same stable token is immediately downloadable.  Retry
        # that bounded case, but never retry a confirmed permission or not-found
        # response that requires user action instead.
        retryable = bool(info["retryable"]) or str(info["category"]) in {"cli_error", "invalid_response"}
        if retryable and attempt < attempts - 1:
            REQUEST_LIMITER.cooldown(min(30, 2**attempt))
            continue
        code_suffix = f" code={info['code']}" if info["code"] else ""
        raise CliCommandError(
            f"lark-cli media request failed category={info['category']}{code_suffix}",
            category=str(info["category"]),
            code=str(info["code"]),
            retryable=retryable,
        ) from failure

    raise AssertionError("unreachable media download retry state")


def cached_asset_filename(identity: str, asset_root: Path) -> str:
    """Return the content-addressed asset filename already present for an identity."""
    cache_key = (
        f"feishu-media://{identity.removeprefix('feishu-token:')}"
        if identity.startswith("feishu-token:")
        else identity
    )
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:24]
    existing = next(iter(sorted(asset_root.glob(f"{digest}.*"))), None) if asset_root.is_dir() else None
    return existing.name if existing and existing.is_file() and existing.stat().st_size else ""


def is_short_lived_feishu_asset_url(reference: str) -> bool:
    """Identify Feishu drive/stream URLs that should be refreshed before download."""
    parsed = urlparse(reference)
    host = (parsed.hostname or "").lower()
    return host.endswith(".feishu.cn") and ("drive" in host or "stream" in host)


def materialize_assets(
    contents: list[str],
    mirror_dir: Path,
    config: dict[str, Any],
    *,
    refresh_short_lived_urls: bool = False,
    batch_size_override: int | None = None,
) -> tuple[dict[str, str], dict[str, str], int, int, int]:
    """Download assets once per stable media token or URL and return local paths."""
    references = sorted({ref for content in contents for ref in extract_asset_references(content)})
    if not references:
        return {}, {}, 0, 0, 0
    asset_dir = str(nested(config, "sync", "asset_dir", default=DEFAULT_ASSET_DIR)).strip("/\\")
    if not asset_dir or Path(asset_dir).is_absolute() or ".." in Path(asset_dir).parts:
        raise SystemExit("sync.asset_dir must be a relative directory without '..'")
    asset_root = mirror_dir / asset_dir
    try:
        workers = max(1, min(int(nested(config, "sync", "asset_workers", default=4)), 8))
    except (TypeError, ValueError):
        workers = 4
    try:
        timeout_seconds = max(
            1.0,
            float(nested(config, "sync", "asset_timeout_seconds", default=DEFAULT_ASSET_TIMEOUT_SECONDS)),
        )
    except (TypeError, ValueError):
        timeout_seconds = DEFAULT_ASSET_TIMEOUT_SECONDS
    try:
        media_attempts = max(
            1,
            min(
                int(
                    nested(
                        config,
                        "sync",
                        "asset_download_attempts",
                        default=DEFAULT_ASSET_DOWNLOAD_ATTEMPTS,
                    )
                ),
                5,
            ),
        )
    except (TypeError, ValueError):
        media_attempts = DEFAULT_ASSET_DOWNLOAD_ATTEMPTS
    try:
        max_bytes = max(1024, int(nested(config, "sync", "max_asset_bytes", default=DEFAULT_MAX_ASSET_BYTES)))
    except (TypeError, ValueError):
        max_bytes = DEFAULT_MAX_ASSET_BYTES
    try:
        batch_size = max(0, int(nested(config, "sync", "asset_batch_size", default=0)))
    except (TypeError, ValueError):
        batch_size = 0
    if batch_size_override is not None:
        batch_size = max(0, batch_size_override)

    identity_by_reference: dict[str, str] = {}
    for content in contents:
        identity_by_reference.update(asset_identities(content))
    grouped_references: dict[str, list[str]] = {}
    for reference in references:
        identity = identity_by_reference.get(reference, reference)
        grouped_references.setdefault(identity, []).append(reference)

    asset_map: dict[str, str] = {}
    errors: dict[str, str] = {}
    downloaded = 0
    reused = 0

    image_references = {url for content in contents for url in extract_image_urls(content)}

    def download(identity: str, candidates: list[str]) -> tuple[list[str], str, str, str]:
        last_error = ""
        media_token = identity.removeprefix("feishu-token:") if identity.startswith("feishu-token:") else ""
        if media_token:
            try:
                _source, filename, status = download_one_media(
                    config,
                    media_token,
                    mirror_dir,
                    asset_dir,
                    max_bytes,
                    timeout_seconds,
                    attempts=media_attempts,
                )
                return candidates, filename, status, ""
            except Exception as exc:  # Signed URLs are a best-effort fallback for token download failures.
                last_error = f"asset download failed category={safe_error_category(exc)}"
        for reference in candidates:
            # The stable-token attempt above already covered this exact source.
            if reference == f"feishu-media://{media_token}":
                continue
            try:
                if reference.startswith("feishu-media://"):
                    _source, filename, status = download_one_media(
                        config,
                        reference.removeprefix("feishu-media://"),
                        mirror_dir,
                        asset_dir,
                        max_bytes,
                        timeout_seconds,
                        attempts=media_attempts,
                    )
                else:
                    _source, filename, status = download_one_asset(
                        reference,
                        asset_root,
                        timeout_seconds,
                        max_bytes,
                        require_image=reference in image_references,
                        identity=identity,
                    )
                return candidates, filename, status, ""
            except Exception as exc:  # try a refreshed signed URL for the same media token
                last_error = f"asset download failed category={safe_error_category(exc)}"
        return candidates, "", "failed", last_error

    pending_groups: list[tuple[str, list[str]]] = []
    for identity, candidates in grouped_references.items():
        filename = cached_asset_filename(identity, asset_root)
        if filename:
            for source in candidates:
                asset_map[source] = (Path(asset_dir) / filename).as_posix()
            reused += 1
        else:
            pending_groups.append((identity, candidates))
    deferred = max(0, len(pending_groups) - batch_size) if batch_size else 0
    if batch_size:
        pending_groups = pending_groups[:batch_size]
    download_groups: list[tuple[str, list[str]]] = []
    for identity, candidates in pending_groups:
        if (
            refresh_short_lived_urls
            and not identity.startswith("feishu-token:")
            and any(is_short_lived_feishu_asset_url(reference) for reference in candidates)
        ):
            for source in candidates:
                errors[source] = "refresh_required"
            continue
        download_groups.append((identity, candidates))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(download, identity, candidates)
            for identity, candidates in download_groups
        ]
        for future in as_completed(futures):
            sources, filename, status, error = future.result()
            if status == "failed":
                for source in sources:
                    errors[source] = error
                continue
            for source in sources:
                asset_map[source] = (Path(asset_dir) / filename).as_posix()
            if status == "downloaded":
                downloaded += 1
            else:
                reused += 1
    return asset_map, errors, downloaded, reused, deferred


def rewrite_asset_urls(
    content: str,
    target: Path,
    mirror_dir: Path,
    asset_map: dict[str, str],
) -> str:
    """Rewrite downloaded media URLs to portable links relative to the Markdown."""
    for url, mirror_relative in asset_map.items():
        local_path = mirror_dir / mirror_relative
        relative = Path(os.path.relpath(local_path, target.parent)).as_posix()
        content = content.replace(url, relative)

    def rewrite_local_attachment_card(match: re.Match[str]) -> str:
        attrs = html_attributes(match.group(1))
        href = attrs.get("href", "").strip()
        if (
            attrs.get("data-feishu-attachment", "").lower() != "true"
            or not href
            or href.startswith(("http://", "https://", "feishu-media://"))
        ):
            return match.group(0)
        # Obsidian reliably intercepts Markdown links inside a vault, while a
        # relative raw HTML anchor can be delegated to the renderer's app URL
        # and appear unclickable.  Once an attachment is local there is no
        # need to retain its Feishu-only card attributes.
        label = re.sub(r"<[^>]+>", "", match.group(2)).strip() or "飞书附件"
        return markdown_link(label, href)

    content = re.sub(
        r"<a\b([^>]*)>(.*?)</a>",
        rewrite_local_attachment_card,
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Markdown is not parsed inside an HTML block by Obsidian.  Feishu often
    # wraps a source card in a paragraph, so remove only a paragraph whose
    # complete content is a now-local attachment link.  Do not touch normal
    # prose paragraphs or HTML table cells.
    return re.sub(
        r"<p\b[^>]*>\s*(\[飞书附件\]\(<[^>]+>\))\s*</p>",
        r"\1",
        content,
        flags=re.IGNORECASE,
    )


def merge_asset_results(
    previous_map: dict[str, str],
    previous_errors: dict[str, str],
    refreshed_map: dict[str, str],
    refreshed_errors: dict[str, str],
    final_contents: list[str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Keep successful first-pass mappings when only some documents refresh."""
    merged_map = {**previous_map, **refreshed_map}
    all_errors = {**previous_errors, **refreshed_errors}
    retained_errors = {
        reference: error
        for reference, error in all_errors.items()
        if any(reference in content for content in final_contents)
    }
    return merged_map, retained_errors


def summarize_asset_errors(errors: dict[str, str]) -> dict[str, int]:
    """Count only safe asset failure categories, never signed URLs or messages."""
    categories: dict[str, int] = {}
    for detail in errors.values():
        marker = re.search(
            r"\bcategory=(asset_too_large|rate_limit|permission_denied|not_found|temporary_network|invalid_response|cli_error)\b",
            detail,
        )
        category = (
            "refresh_required"
            if detail == "refresh_required"
            else marker.group(1)
            if marker
            else safe_error_category(detail)
        )
        categories[category] = categories.get(category, 0) + 1
    return dict(sorted(categories.items()))


def nodes_requiring_asset_refresh(
    nodes: list[dict[str, Any]],
    fetched: dict[str, tuple[str, str, str, str]],
    asset_errors: dict[str, str],
) -> list[dict[str, Any]]:
    """Refresh only documents that still carry a failed resource reference."""
    failed_references = set(asset_errors)
    return [
        node
        for node in nodes
        if str(node.get("obj_type", "")) in {"docx", "doc"}
        and str(node.get("node_token")) in fetched
        and any(reference in fetched[str(node["node_token"])][1] for reference in failed_references)
    ]


def source_url(config: dict[str, Any], node_token: str) -> str:
    template = str(nested(config, "space", "source_url_template", default=""))
    if not template or template.startswith("<"):
        return ""
    return template.format(node_token=node_token)


def frontmatter(metadata: dict[str, Any], synced_at: str, content_hash: str) -> str:
    lines = ["---"]
    for key in (
        "source",
        "sync_mode",
        "title",
        "source_url",
        "space_id",
        "node_token",
        "obj_token",
        "obj_type",
        "parent_node_token",
        "depth",
        "has_children",
        "children_count",
        "obj_edit_time",
        "remote_updated_at",
        "revision_id",
        "sync_status",
        "error",
        "retryable",
        "synced_at",
        "content_hash",
    ):
        value = metadata.get(key, "")
        if isinstance(value, str):
            value = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def load_event_targets(
    path: str | None,
    nodes: list[dict[str, Any]],
) -> tuple[set[str], set[str], bool, list[str]]:
    """Read externally delivered event payloads without depending on SDK shape.

    The official event payload has changed between v1/v2 envelopes and webhook/
    long-connection adapters. We intentionally inspect only identifier fields and
    event names here. Unknown structural events trigger a tree reconciliation.
    """
    if not path:
        return set(), set(), False, []
    event_path = Path(path).expanduser().resolve()
    if not event_path.is_file():
        raise SystemExit(f"event file not found: {event_path}")
    raw = event_path.read_text(encoding="utf-8")
    if not raw.strip():
        return set(), set(), False, []
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        parsed = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid event NDJSON in {event_path}: {exc}") from exc
    events = parsed if isinstance(parsed, list) else [parsed]
    node_tokens = {str(node.get("node_token")) for node in nodes if node.get("node_token")}
    obj_tokens = {str(node.get("obj_token")) for node in nodes if node.get("obj_token")}
    changed_nodes: set[str] = set()
    changed_objects: set[str] = set()
    event_names: list[str] = []
    tree_event = False
    tree_markers = ("created_in_folder", "trashed", "deleted", "title_updated", "move", "parent")

    def walk(value: Any) -> None:
        nonlocal tree_event
        if isinstance(value, dict):
            for key, child in value.items():
                key_name = str(key).lower()
                if key_name in {"event_type", "type", "event_name"} and isinstance(child, str):
                    event_names.append(child)
                    if any(marker in child.lower() for marker in tree_markers):
                        tree_event = True
                if isinstance(child, str):
                    if key_name in {"node_token", "wiki_token", "wiki_node_token"} and child in node_tokens:
                        changed_nodes.add(child)
                    elif key_name in {"obj_token", "file_token", "document_token"} and child in obj_tokens:
                        changed_objects.add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for event in events:
        walk(event)
    if events and not event_names:
        tree_event = True
    return changed_nodes, changed_objects, tree_event, event_names


def sidebar_path(path: str) -> str:
    route_parts = []
    for part in Path(path).with_suffix("").parts:
        route_parts.append(quote(part, safe="-._~!$&'()*+,;=:@"))
    return "/feishu-knowledge/" + "/".join(route_parts)


def build_sidebar(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_parent: dict[str | None, list[dict[str, Any]]] = {}
    node_tokens = {str(node.get("node_token")) for node in nodes if node.get("node_token")}
    for node in nodes:
        parent = node.get("parent_node_token")
        by_parent.setdefault(parent if parent in node_tokens else None, []).append(node)

    def build(parent: str | None) -> list[dict[str, Any]]:
        entries = []
        candidates = by_parent.get(parent, [])
        if parent is None and "" in by_parent:
            candidates += by_parent.get("", [])
        for node in candidates:
            item: dict[str, Any] = {
                "text": node["title"],
                "link": sidebar_path(node["relative_path"]),
            }
            children = build(node["node_token"])
            if children:
                item["collapsible"] = True
                item["collapsed"] = True
                item["items"] = children
            entries.append(item)
        return entries

    generated_name = Path(MIRROR_DIR).name
    if generated_name.startswith("10_"):
        generated_name = generated_name[3:]
    return [
        {"text": generated_name or "knowledge-base", "link": "/feishu-knowledge/00_同步说明", "items": build(None)}
    ]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def document_body(raw: str) -> str:
    """Exclude generated frontmatter from change details so diffs show document content."""
    if raw.startswith("---\n"):
        end = raw.find("\n---", 4)
        if end >= 0:
            return raw[end + 4 :].lstrip("\n")
    return raw


def relative_markdown_link(from_path: Path, target: Path, label: str) -> str:
    relative = Path(os.path.relpath(target, from_path.parent)).as_posix()
    return markdown_link(label, relative)


def classify_changes(
    old_nodes: dict[str, Any],
    records: list[dict[str, Any]],
    deleted: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Classify the current run without treating unchanged files as report entries."""
    changes = {"added": [], "modified": [], "moved": [], "deleted": list(deleted)}
    for record in records:
        token = str(record.get("node_token", ""))
        old = old_nodes.get(token, {}) if isinstance(old_nodes.get(token), dict) else {}
        if not old:
            changes["added"].append(record)
            continue
        moved = old.get("relative_path") != record.get("relative_path")
        content_changed = (
            old.get("content_hash") != record.get("content_hash")
            or old.get("sync_status") != record.get("sync_status")
        )
        if moved:
            changes["moved"].append(dict(record, previous_relative_path=old.get("relative_path", ""), content_changed=content_changed))
        elif content_changed:
            changes["modified"].append(record)
    return changes


def write_change_ledger(
    output_dir: Path,
    metadata_dir: Path,
    ledger_dir: str,
    changes: dict[str, list[dict[str, Any]]],
    previous_bodies: dict[str, str],
    sync_started: str,
    max_diff_lines: int,
) -> Path:
    """Write a private run ledger and bounded Markdown diffs without changing the mirror tree."""
    run_date = sync_started[:10] or "unknown-date"
    run_time = re.sub(r"[^0-9]", "", sync_started[11:19]) or "run"
    base = metadata_dir / ledger_dir / run_date
    report_dir = base / run_time
    suffix = 2
    while report_dir.exists():
        report_dir = base / f"{run_time}-{suffix}"
        suffix += 1
    details_dir = report_dir / "details"
    summary_path = report_dir / "summary.md"
    lines = [
        "# Feishu mirror change ledger",
        "",
        f"- Synced at: {sync_started}",
        f"- Added: **{len(changes['added'])}**",
        f"- Modified: **{len(changes['modified'])}**",
        f"- Moved or renamed: **{len(changes['moved'])}**",
        f"- Deleted remotely: **{len(changes['deleted'])}**",
        "",
    ]

    def entry_link(record: dict[str, Any]) -> str:
        target = output_dir / str(record.get("relative_path", ""))
        title = str(record.get("title", "document"))
        return relative_markdown_link(summary_path, target, title) if target.is_file() else title

    def append_entries(heading: str, entries: list[dict[str, Any]]) -> None:
        if not entries:
            return
        lines.extend([f"## {heading}", ""])
        for record in entries:
            lines.append(f"- {entry_link(record)}")
        lines.append("")

    append_entries("Added", changes["added"])
    if changes["modified"]:
        lines.extend(["## Modified", ""])
        for index, record in enumerate(changes["modified"], start=1):
            token = str(record.get("node_token", ""))
            before = previous_bodies.get(token, "")
            target = output_dir / str(record.get("relative_path", ""))
            after = document_body(target.read_text(encoding="utf-8")) if target.is_file() else ""
            detail_link = ""
            if before and after:
                diff = list(
                    difflib.unified_diff(
                        document_body(before).splitlines(),
                        after.splitlines(),
                        fromfile="before",
                        tofile="after",
                        lineterm="",
                        n=3,
                    )
                )
                if diff:
                    if len(diff) > max_diff_lines:
                        diff = diff[:max_diff_lines] + ["... diff truncated ..."]
                    detail_path = details_dir / f"change-{index:03d}.md"
                    write_text(
                        detail_path,
                        "\n".join(
                            [
                                "# Document change detail",
                                "",
                                f"- Document: {record.get('title', 'document')}",
                                "",
                                "```diff",
                                *diff,
                                "```",
                                "",
                            ]
                        ),
                    )
                    detail_link = " · " + relative_markdown_link(summary_path, detail_path, "diff")
            lines.append(f"- {entry_link(record)}{detail_link}")
        lines.append("")
    if changes["moved"]:
        lines.extend(["## Moved or renamed", ""])
        for record in changes["moved"]:
            content_note = " (content also changed)" if record.get("content_changed") else ""
            lines.append(f"- {entry_link(record)}{content_note}")
        lines.append("")
    if changes["deleted"]:
        lines.extend(["## Deleted remotely", ""])
        for record in changes["deleted"]:
            lines.append(f"- {record.get('title', 'document')} (preserved locally; marked deleted in the manifest)")
        lines.append("")
    write_text(summary_path, "\n".join(lines))
    return summary_path


def frontmatter_fields(raw: str) -> dict[str, str]:
    """Read the small generated frontmatter contract without a YAML dependency."""
    if not raw.startswith("---\n"):
        return {}
    end = raw.find("\n---", 4)
    if end < 0:
        return {}
    fields: dict[str, str] = {}
    for line in raw[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
        fields[match.group(1)] = value
    return fields


def sidebar_links(value: Any) -> set[str]:
    """Collect generated VitePress links without exposing their local names."""
    links: set[str] = set()
    if isinstance(value, dict):
        link = value.get("link")
        if isinstance(link, str):
            links.add(link)
        for child in value.values():
            links.update(sidebar_links(child))
    elif isinstance(value, list):
        for child in value:
            links.update(sidebar_links(child))
    return links


def has_error_placeholder(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return True
    body = raw.split("---", 2)[2] if raw.count("---") >= 2 else raw
    return bool(ERROR_PLACEHOLDER_PATTERN.search(body))


def validate_mirror(
    output_dir: Path,
    manifest: dict[str, Any] | None = None,
    sidebar_file: Path | None = None,
    require_local_assets: bool = False,
    require_embedded_sheet_scan: bool = False,
    require_all_sheet_nodes: bool = False,
) -> dict[str, Any]:
    """Validate the generated mirror as a separate, deterministic acceptance gate."""
    manifest = manifest if isinstance(manifest, dict) else load_json(output_dir / METADATA_DIR / MANIFEST_FILE, {})
    records = manifest.get("nodes", []) if isinstance(manifest, dict) else []
    if not isinstance(records, list):
        records = []
    root = output_dir.resolve()
    errors: list[str] = []
    seen_tokens: set[str] = set()
    seen_paths: set[str] = set()
    expected_sidebar_links: set[str] = set()
    checked_files = 0
    missing_files = 0
    frontmatter_errors = 0
    placeholder_errors = 0
    unresolved_embedded_sheets = 0
    unscanned_embedded_sheet_documents = 0
    unmirrored_sheet_nodes = 0
    unresolved_sheet_bitable_tabs = 0
    unresolved_assets = 0
    failed_records = 0
    stale_records = 0
    categories: dict[str, int] = {}

    for record in records:
        if not isinstance(record, dict):
            errors.append("invalid_record")
            continue
        token = str(record.get("node_token", ""))
        if not token or token in seen_tokens:
            errors.append("duplicate_or_missing_node_token")
        seen_tokens.add(token)
        relative = record.get("relative_path")
        if not isinstance(relative, str) or not relative:
            errors.append("missing_relative_path")
            continue
        candidate = (output_dir / relative).resolve()
        if not candidate.is_relative_to(root):
            errors.append("path_outside_output_dir")
            continue
        if relative in seen_paths:
            errors.append("duplicate_relative_path")
        seen_paths.add(relative)
        expected_sidebar_links.add(sidebar_path(relative))
        status = str(record.get("sync_status", ""))
        if status == "failed":
            failed_records += 1
        elif status == "stale":
            stale_records += 1
        raw_category = str(record.get("error", "") or "")
        if raw_category:
            known_categories = {
                "asset_too_large",
                "rate_limit",
                "permission_denied",
                "not_found",
                "temporary_network",
                "invalid_response",
                "cli_error",
            }
            category = raw_category if raw_category in known_categories else str(error_info(raw_category)["category"])
            categories[category] = categories.get(category, 0) + 1
        if not candidate.is_file():
            missing_files += 1
            continue
        checked_files += 1
        raw = candidate.read_text(encoding="utf-8")
        fields = frontmatter_fields(raw)
        if fields.get("node_token") != token or fields.get("sync_status") != status:
            frontmatter_errors += 1
        body = raw.split("---", 2)[2] if raw.count("---") >= 2 else raw
        if status in {"ok", "stale"} and ERROR_PLACEHOLDER_PATTERN.search(body):
            placeholder_errors += 1
        unresolved_embedded_sheets += body.count(EMBEDDED_SHEET_UNMIRRORED_MARKER)
        unresolved_sheet_bitable_tabs += body.count(SHEET_BITABLE_UNMIRRORED_MARKER)
        if (
            require_all_sheet_nodes
            and str(record.get("obj_type", "")) == "sheet"
            and (status != "ok" or SHEET_MIRROR_MARKER not in body)
        ):
            unmirrored_sheet_nodes += 1
        if (
            require_embedded_sheet_scan
            and str(record.get("obj_type", "")) in {"doc", "docx"}
            and status in {"ok", "stale"}
            and EMBEDDED_SHEET_SCAN_MARKER not in body
        ):
            unscanned_embedded_sheet_documents += 1
        if status == "ok":
            unresolved_assets += len(extract_asset_references(body))

    if missing_files:
        errors.append("missing_generated_files")
    if frontmatter_errors:
        errors.append("invalid_frontmatter")
    if placeholder_errors:
        errors.append("error_placeholder_in_successful_document")
    if unresolved_embedded_sheets:
        errors.append("unresolved_embedded_sheets")
    if unscanned_embedded_sheet_documents:
        errors.append("unscanned_embedded_sheet_documents")
    if unmirrored_sheet_nodes:
        errors.append("unmirrored_sheet_nodes")
    if unresolved_sheet_bitable_tabs:
        errors.append("unresolved_sheet_bitable_tabs")
    if failed_records:
        errors.append("failed_records")
    if stale_records:
        errors.append("stale_records")
    if require_local_assets and unresolved_assets:
        errors.append("unresolved_assets")

    sidebar_file = sidebar_file or output_dir / METADATA_DIR / SIDEBAR_FILE
    sidebar_value = load_json(sidebar_file, None)
    actual_sidebar_links = sidebar_links(sidebar_value)
    sidebar_missing_links = len(expected_sidebar_links - actual_sidebar_links)
    if sidebar_value is None:
        errors.append("missing_sidebar")
        sidebar_missing_links = len(expected_sidebar_links)
    elif sidebar_missing_links:
        errors.append("sidebar_missing_nodes")

    stats = {
        "records": len(records),
        "files_checked": checked_files,
        "missing_files": missing_files,
        "frontmatter_errors": frontmatter_errors,
        "placeholder_errors": placeholder_errors,
        "unresolved_embedded_sheets": unresolved_embedded_sheets,
        "unscanned_embedded_sheet_documents": unscanned_embedded_sheet_documents,
        "unmirrored_sheet_nodes": unmirrored_sheet_nodes,
        "unresolved_sheet_bitable_tabs": unresolved_sheet_bitable_tabs,
        "failed_records": failed_records,
        "stale_records": stale_records,
        "unresolved_assets": unresolved_assets,
        "sidebar_missing_links": sidebar_missing_links,
    }
    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "error_categories": dict(sorted(categories.items())),
        "stats": stats,
    }


def print_validation(result: dict[str, Any]) -> None:
    stats = result.get("stats", {}) if isinstance(result, dict) else {}
    print(
        "validation "
        f"passed={str(bool(result.get('ok'))).lower()} "
        f"records={stats.get('records', 0)} files_checked={stats.get('files_checked', 0)} "
        f"missing_files={stats.get('missing_files', 0)} frontmatter_errors={stats.get('frontmatter_errors', 0)} "
        f"placeholder_errors={stats.get('placeholder_errors', 0)} failed_records={stats.get('failed_records', 0)} "
        f"unresolved_embedded_sheets={stats.get('unresolved_embedded_sheets', 0)} "
        f"unscanned_embedded_sheet_documents={stats.get('unscanned_embedded_sheet_documents', 0)} "
        f"unmirrored_sheet_nodes={stats.get('unmirrored_sheet_nodes', 0)} "
        f"unresolved_sheet_bitable_tabs={stats.get('unresolved_sheet_bitable_tabs', 0)} "
        f"stale_records={stats.get('stale_records', 0)} unresolved_assets={stats.get('unresolved_assets', 0)} "
        f"sidebar_missing_links={stats.get('sidebar_missing_links', 0)}"
    )
    categories = result.get("error_categories", {}) if isinstance(result, dict) else {}
    if categories:
        print(f"validation error_categories={json.dumps(categories, ensure_ascii=False, sort_keys=True)}")


def sync(args: argparse.Namespace) -> int:
    config, config_path = load_config(args.config)
    if args.rebuild_tree_only and not args.rebuild_tree:
        raise SystemExit("--rebuild-tree-only requires --rebuild-tree")
    if args.refresh_tree_only and not args.rebuild_tree:
        raise SystemExit("--refresh-tree-only requires --rebuild-tree")
    space_id = args.space_id or str(nested(config, "space", "id", default=""))
    if not space_id or space_id.startswith("<"):
        raise SystemExit("space.id is required")
    output_dir = Path(args.output_dir or str(nested(config, "paths", "output_dir", default=""))).expanduser().resolve()
    if not str(output_dir) or str(output_dir) == ".":
        raise SystemExit("paths.output_dir is required")
    lock_handle = acquire_sync_lock(output_dir)
    cli = args.cli_path or str(nested(config, "provider", "cli", default="lark-cli"))
    config = json.loads(json.dumps(config))
    config.setdefault("provider", {})["cli"] = cli
    global MIRROR_DIR
    configured_value = nested(config, "paths", "generated_dir", default="")
    configured_mirror_dir = str(configured_value or "").strip()
    if not configured_mirror_dir:
        existing_generated_dirs = sorted(
            path.name
            for path in output_dir.glob("10_*")
            if path.is_dir()
        )
        if len(existing_generated_dirs) == 1:
            configured_mirror_dir = existing_generated_dirs[0]
        elif len(existing_generated_dirs) > 1:
            raise SystemExit(
                "paths.generated_dir is required when multiple generated directories exist"
            )
        else:
            configured_mirror_dir = DEFAULT_MIRROR_DIR
    if (
        not configured_mirror_dir
        or configured_mirror_dir.startswith("<")
        or Path(configured_mirror_dir).is_absolute()
        or Path(configured_mirror_dir).name != configured_mirror_dir
        or configured_mirror_dir in {".", ".."}
    ):
        raise SystemExit("paths.generated_dir must be one relative directory name")
    MIRROR_DIR = configured_mirror_dir
    try:
        request_delay = max(0.0, float(nested(config, "sync", "request_delay_seconds", default=0.0)))
    except (TypeError, ValueError):
        request_delay = 0.0
    try:
        min_request_interval = max(
            0.0,
            float(nested(config, "sync", "min_request_interval_seconds", default=0.5)),
        )
    except (TypeError, ValueError):
        min_request_interval = 0.5
    REQUEST_LIMITER.configure(max(request_delay, min_request_interval))
    sidebar_path_file = output_dir / METADATA_DIR / str(
        nested(config, "vitepress", "sidebar_file", default=SIDEBAR_FILE)
    ).split("/")[-1]
    if getattr(args, "validate_only", False):
        validation = validate_mirror(
            output_dir,
            sidebar_file=sidebar_path_file,
            require_local_assets=bool(
                nested(config, "sync", "download_assets", default=False) and not args.skip_assets
            ),
            require_embedded_sheet_scan=bool(
                nested(config, "sync", "embedded_sheets", "enabled", default=False)
                and nested(config, "sync", "embedded_sheets", "all_docx", default=False)
            ),
            require_all_sheet_nodes=bool(
                nested(config, "sync", "sheets", "enabled", default=False)
                and nested(config, "sync", "sheets", "all_nodes", default=False)
            ),
        )
        print_validation(validation)
        result = 0 if validation["ok"] else 2
        lock_handle.close()
        return result
    sync_started = utc_now()
    print("started space_id=<configured-space> identity=bot config=<private-config> output=<private-location>")
    previous_manifest = load_json(output_dir / METADATA_DIR / MANIFEST_FILE, {})
    pilot_node_tokens = {str(token).strip() for token in args.pilot_node_token if str(token).strip()}
    if pilot_node_tokens:
        if args.retry_failed or args.rebuild_tree_only or args.refresh_tree_only:
            raise SystemExit("--pilot-node-token cannot be combined with retry or tree-rebuild modes")
        nodes = []
        for token in sorted(pilot_node_tokens):
            node = node_get(config, token, space_id)
            node["node_token"] = str(node.get("node_token") or token)
            node.setdefault("parent_node_token", "")
            node.setdefault("depth", 0)
            node.setdefault("has_child", False)
            nodes.append(node)
        print(f"pilot_scope selected_nodes={len(nodes)} source=wiki_node_get", flush=True)
    elif (args.retry_failed or args.rebuild_tree_only) and isinstance(previous_manifest, dict) and isinstance(previous_manifest.get("nodes"), list):
        nodes = [node for node in previous_manifest["nodes"] if isinstance(node, dict)]
        mode = "retry_failed" if args.retry_failed else "tree_rebuild"
        print(f"structure source=previous_manifest mode={mode}", flush=True)
    else:
        nodes = walk_nodes(config, space_id, args.max_nodes)
    print(f"processed nodes_discovered={len(nodes)}")
    if args.dry_run:
        for node in nodes[:10]:
            print(
                f"node title={clean_title(node.get('title'), node['node_token'])} "
                f"type={str(node.get('obj_type', 'unknown'))}"
            )
        if len(nodes) > 10:
            print(f"node ... and {len(nodes) - 10} more")
        print("completed dry_run=true files_written=0")
        lock_handle.close()
        return 0

    mirror_dir = output_dir / MIRROR_DIR
    metadata_dir = output_dir / METADATA_DIR
    state_path = metadata_dir / STATE_FILE
    manifest_path = metadata_dir / MANIFEST_FILE
    sidebar_path_file = metadata_dir / str(nested(config, "vitepress", "sidebar_file", default=SIDEBAR_FILE)).split("/")[-1]
    old_state = load_json(state_path, {"version": 1, "nodes": {}})
    old_nodes = old_state.get("nodes", {}) if isinstance(old_state, dict) else {}
    if not isinstance(old_nodes, dict) or not old_nodes:
        old_nodes = {
            str(node.get("node_token")): node
            for node in (previous_manifest.get("nodes", []) if isinstance(previous_manifest, dict) else [])
            if isinstance(node, dict) and node.get("node_token")
        }
    incremental = bool(
        not args.full_content
        and (
            args.incremental
            or args.refresh_tree_only
            or nested(config, "sync", "incremental", default=False)
        )
    )
    explicit_node_targets = {str(token).strip() for token in args.changed_node_token if str(token).strip()}
    only_node_tokens = {str(token).strip() for token in args.only_node_token if str(token).strip()}
    explicit_obj_targets = {str(token).strip() for token in args.changed_obj_token if str(token).strip()}
    event_file = args.event_file or nested(config, "sync", "event_file")
    if isinstance(event_file, str) and event_file.startswith("<"):
        event_file = None
    event_nodes, event_objects, tree_event, event_names = load_event_targets(event_file, nodes)
    changed_node_tokens = explicit_node_targets | event_nodes
    changed_node_tokens.update(only_node_tokens)
    changed_obj_tokens = explicit_obj_targets | event_objects
    node_by_obj = {
        str(node.get("obj_token")): str(node.get("node_token"))
        for node in nodes
        if node.get("obj_token") and node.get("node_token")
    }
    changed_node_tokens.update(node_by_obj[obj] for obj in changed_obj_tokens if obj in node_by_obj)
    event_driven = bool(
        event_file or explicit_node_targets or explicit_obj_targets or only_node_tokens or pilot_node_tokens
    )
    probe_remote_metadata = bool(
        incremental
        and not args.rebuild_tree_only
        and not args.refresh_tree_only
        and not args.retry_failed
        and not args.skip_content
        and not event_driven
        and (args.probe_remote_metadata or nested(config, "sync", "probe_remote_metadata", default=True))
    )
    if incremental:
        if event_driven:
            detection = "event_targets"
        elif probe_remote_metadata:
            detection = "wiki_node_get_metadata"
        else:
            detection = "baseline_only"
        print(
            f"content_mode=incremental detection={detection} "
            f"changed_nodes={len(changed_node_tokens)} changed_objects={len(changed_obj_tokens)} "
            f"tree_event={tree_event}",
            flush=True,
        )
    # Keep the remote node order stable while planning local paths and links.
    ordered = list(nodes)
    used_paths: set[str] = set()
    path_by_token: dict[str, Path] = {}
    children_by_parent: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        parent = str(node.get("parent_node_token") or "")
        if parent:
            children_by_parent.setdefault(parent, []).append(node)
    sibling_by_parent_title: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for node in nodes:
        key = (str(node.get("parent_node_token") or ""), clean_title(node.get("title"), str(node["node_token"])))
        sibling_by_parent_title.setdefault(key, []).append(node)
    expandable_directory_by_token: dict[str, str] = {}
    expandable_titles_by_parent: dict[str, set[str]] = {}
    for (parent, title), siblings in sibling_by_parent_title.items():
        expandable = sorted(
            (node for node in siblings if children_by_parent.get(str(node["node_token"]))),
            key=lambda node: str(node["node_token"]),
        )
        if not expandable:
            continue
        used_directory_names: set[str] = set()
        expandable_titles_by_parent.setdefault(parent, set()).add(title)
        for node in expandable:
            token = str(node["node_token"])
            directory = path_component(title, token)
            if directory in used_directory_names:
                directory = path_component(title, token, "--node--")
                counter = 2
                while directory in used_directory_names:
                    directory = path_component(title, token, f"--node--{counter}-")
                    counter += 1
            used_directory_names.add(directory)
            expandable_directory_by_token[token] = directory
    def path_for(node: dict[str, Any]) -> Path:
        node_key = node["node_token"]
        old = old_nodes.get(node_key, {}) if isinstance(old_nodes, dict) else {}
        old_path = old.get("relative_path") if isinstance(old, dict) else None
        parent = node.get("parent_node_token")
        has_children = bool(children_by_parent.get(node_key))
        title = clean_title(node.get("title"), node_key)
        parent_path = path_by_token.get(parent)
        parent_rel = (
            parent_path.parent
            if parent_path and parent and children_by_parent.get(str(parent))
            else parent_path.with_suffix("")
            if parent_path and parent
            else Path()
        )
        directory_name = expandable_directory_by_token.get(node_key, title)
        if has_children and str(parent_rel / f"{directory_name}.md") in used_paths:
            directory_name = path_component(title, node_key, "--node--")
            counter = 2
            index_stem = path_component(title, node_key)
            while str(parent_rel / directory_name / f"{index_stem}.md") in used_paths:
                directory_name = path_component(title, node_key, f"--node--{counter}-")
                counter += 1
            expandable_directory_by_token[node_key] = directory_name
        file_stem = title
        if not has_children and title in expandable_titles_by_parent.get(str(parent or ""), set()):
            file_stem = path_component(title, node_key, "--leaf--")
        if not args.rebuild_tree and isinstance(old_path, str) and old_path.startswith(f"{MIRROR_DIR}/"):
            expected_dir = (
                parent_rel / directory_name
                if has_children
                else parent_rel
            )
            try:
                candidate_path = Path(old_path).relative_to(MIRROR_DIR)
                can_reuse = candidate_path.parent == expected_dir and candidate_path.name == f"{file_stem}.md"
            except ValueError:
                can_reuse = False
            if can_reuse:
                candidate = Path(old_path).relative_to(MIRROR_DIR)
                if str(candidate) not in used_paths:
                    used_paths.add(str(candidate))
                    return candidate
        return unique_path(
            path_component(title, node_key),
            parent_rel,
            used_paths,
            node_key,
            has_children,
            directory_name=directory_name,
            file_stem=file_stem,
        )

    planned_paths: dict[str, Path] = {}
    for node in ordered:
        token = str(node["node_token"])
        planned_paths[token] = path_for(node)
        path_by_token[token] = planned_paths[token]

    sheet_sync_enabled = bool(
        getattr(args, "sync_sheets", False)
        or nested(config, "sync", "sheets", "enabled", default=False)
    )
    sheet_selections = configured_sheet_selections(config, sheet_sync_enabled)
    all_sheet_settings = configured_all_sheet_settings(config, sheet_sync_enabled)
    embedded_sheet_sync_enabled = bool(
        getattr(args, "sync_embedded_sheets", False)
        or nested(config, "sync", "embedded_sheets", "enabled", default=False)
    )
    embedded_sheet_settings = configured_embedded_sheet_settings(
        config,
        embedded_sheet_sync_enabled,
    )
    bitable_sync_enabled = bool(
        getattr(args, "sync_bitables", False)
        or nested(config, "sync", "bitables", "enabled", default=False)
    )
    bitable_selections = configured_bitable_selections(config, bitable_sync_enabled)
    configured_sheet_nodes = set(sheet_selections)
    available_sheet_nodes = {
        str(node.get("node_token"))
        for node in ordered
        if str(node.get("obj_type", "")) == "sheet"
    }
    missing_sheet_nodes = configured_sheet_nodes - available_sheet_nodes
    if missing_sheet_nodes:
        raise SystemExit("sync.sheets.selections references a node that is not a Sheet in this Wiki")
    available_bitable_nodes = {
        str(node.get("node_token")) for node in ordered if str(node.get("obj_type", "")) == "bitable"
    }
    if set(bitable_selections) - available_bitable_nodes:
        raise SystemExit("sync.bitables.selections references a node that is not a Base in this Wiki")

    def reads_sync_content(node: dict[str, Any]) -> bool:
        obj_type = str(node.get("obj_type", ""))
        return obj_type in {"docx", "doc"} or (
            obj_type == "sheet"
            and (
                str(node.get("node_token")) in sheet_selections
                or all_sheet_settings is not None
            )
        ) or (obj_type == "bitable" and str(node.get("node_token")) in bitable_selections)

    content_nodes = [node for node in ordered if reads_sync_content(node)]

    localize_document_links = bool(
        nested(config, "sync", "localize_internal_links", default=False)
    )
    render_sub_page_navigation = bool(
        nested(config, "sync", "render_sub_page_navigation", default=False)
    )
    change_ledger_enabled = bool(nested(config, "sync", "change_ledger", default=False))
    change_ledger_dir = str(
        nested(config, "sync", "change_ledger_dir", default=DEFAULT_CHANGE_LEDGER_DIR)
    ).strip("/\\")
    if (
        not change_ledger_dir
        or Path(change_ledger_dir).is_absolute()
        or ".." in Path(change_ledger_dir).parts
    ):
        raise SystemExit("sync.change_ledger_dir must be a relative directory without '..'")
    try:
        change_ledger_max_diff_lines = max(
            20,
            int(
                nested(
                    config,
                    "sync",
                    "change_ledger_max_diff_lines",
                    default=DEFAULT_CHANGE_LEDGER_MAX_DIFF_LINES,
                )
            ),
        )
    except (TypeError, ValueError):
        change_ledger_max_diff_lines = DEFAULT_CHANGE_LEDGER_MAX_DIFF_LINES

    def document_links_for(node_token: str) -> dict[str, str]:
        links: dict[str, str] = {}
        current_path = mirror_dir / planned_paths[node_token]
        for candidate in ordered:
            candidate_token = str(candidate["node_token"])
            if localize_document_links:
                target = Path(
                    os.path.relpath(
                        mirror_dir / planned_paths[candidate_token],
                        current_path.parent,
                    )
                ).as_posix()
            else:
                target = source_url(config, candidate_token)
            for identifier in (candidate.get("node_token"), candidate.get("obj_token")):
                if identifier:
                    links[str(identifier)] = target
        return links

    def has_embedded_sheet_scan(node: dict[str, Any], old: dict[str, Any]) -> bool:
        if not embedded_sheet_sync_applies(node, embedded_sheet_settings):
            return True
        old_path = old.get("relative_path") if isinstance(old, dict) else None
        if not isinstance(old_path, str):
            return False
        existing = output_dir / old_path
        if not existing.is_file():
            return False
        try:
            return EMBEDDED_SHEET_SCAN_MARKER in existing.read_text(encoding="utf-8")
        except OSError:
            return False

    def has_standalone_sheet_mirror(node: dict[str, Any], old: dict[str, Any]) -> bool:
        if all_sheet_settings is None or str(node.get("obj_type", "")) != "sheet":
            return True
        old_path = old.get("relative_path") if isinstance(old, dict) else None
        if not isinstance(old_path, str) or str(old.get("sync_status", "")) != "ok":
            return False
        existing = output_dir / old_path
        if not existing.is_file():
            return False
        try:
            return SHEET_MIRROR_MARKER in existing.read_text(encoding="utf-8")
        except OSError:
            return False

    records: list[dict[str, Any]] = []
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "failed": 0,
        "stale": 0,
        "stub": 0,
        "remote_images": 0,
        "assets_downloaded": 0,
        "assets_reused": 0,
        "assets_failed": 0,
        "assets_deferred": 0,
        "asset_error_categories": {},
        "asset_content_refreshed": 0,
        "asset_content_refresh_failed": 0,
        "moved_deleted": 0,
        "content_fetched": 0,
        "content_reused": 0,
        "sheets_mirrored": 0,
        "sheet_tabs_mirrored": 0,
        "embedded_sheet_documents_scanned": 0,
        "embedded_sheets_mirrored": 0,
        "bitables_mirrored": 0,
        "bitable_tables_mirrored": 0,
        "sheet_workbooks_downloaded": 0,
        "sheet_workbooks_reused": 0,
        "sheet_workbooks_failed": 0,
        "sheet_workbooks_deferred": 0,
        "bitable_exports_downloaded": 0,
        "bitable_exports_reused": 0,
        "bitable_exports_failed": 0,
        "bitable_exports_deferred": 0,
        "wiki_files_downloaded": 0,
        "wiki_files_reused": 0,
        "wiki_files_failed": 0,
        "wiki_files_deferred": 0,
        "error_categories": {},
    }
    fetched: dict[str, tuple[str, str, str, str]] = {}
    fresh_content_tokens: set[str] = set()
    previous_bodies: dict[str, str] = {}
    remote_metadata: dict[str, dict[str, Any]] = {}
    metadata_probe_errors: dict[str, str] = {}
    if probe_remote_metadata:
        metadata_nodes = content_nodes
        metadata_workers_value = nested(
            config,
            "sync",
            "metadata_workers",
            default=nested(config, "sync", "structure_workers", default=2),
        )
        try:
            metadata_workers = max(1, min(int(metadata_workers_value), 4))
        except (TypeError, ValueError):
            metadata_workers = 2

        def probe_one(node: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str]:
            token = str(node["node_token"])
            try:
                delay_value = nested(config, "sync", "metadata_request_delay_seconds", default=0.0)
                try:
                    delay = max(0.0, float(delay_value))
                except (TypeError, ValueError):
                    delay = 0.0
                if delay:
                    time.sleep(delay)
                return token, node_get(config, token, space_id), ""
            except Exception as exc:
                return token, None, str(exc)

        with ThreadPoolExecutor(max_workers=metadata_workers) as executor:
            futures = [executor.submit(probe_one, node) for node in metadata_nodes]
            for completed, future in enumerate(as_completed(futures), start=1):
                token, metadata, error = future.result()
                if metadata is not None:
                    remote_metadata[token] = metadata
                else:
                    metadata_probe_errors[token] = error
                if completed == 1 or completed % 100 == 0 or completed == len(futures):
                    print(f"metadata_probe progress={completed}/{len(futures)}", flush=True)
        print(
            f"metadata_probe completed={len(remote_metadata)} failed={len(metadata_probe_errors)} "
            f"workers={metadata_workers}",
            flush=True,
        )

    if not args.skip_content and not args.refresh_tree_only and (
        not args.rebuild_tree_only or only_node_tokens
    ):
        all_content_nodes = content_nodes
        if only_node_tokens:
            missing_only_nodes = only_node_tokens - {str(node["node_token"]) for node in all_content_nodes}
            if missing_only_nodes:
                raise SystemExit(
                    "--only-node-token not found in the current manifest/tree: "
                    + ",".join(sorted(missing_only_nodes))
                )
            content_nodes_to_fetch = [
                node for node in all_content_nodes if str(node["node_token"]) in only_node_tokens
            ]
        elif args.retry_failed:
            retry_candidates = [
                node
                for node in all_content_nodes
                if (
                    not isinstance(old_nodes.get(str(node["node_token"])), dict)
                    or old_nodes[str(node["node_token"])].get("sync_status") != "ok"
                    or has_error_placeholder(
                        output_dir / str(old_nodes[str(node["node_token"])].get("relative_path", ""))
                    )
                    or not has_embedded_sheet_scan(
                        node, old_nodes.get(str(node["node_token"]), {})
                    )
                    or not has_standalone_sheet_mirror(
                        node, old_nodes.get(str(node["node_token"]), {})
                    )
                )
            ]
            retry_candidates.sort(
                key=lambda node: (
                    0
                    if has_error_placeholder(
                        output_dir
                        / str(old_nodes.get(str(node["node_token"]), {}).get("relative_path", ""))
                    )
                    else 1
                    if (
                        str(node.get("obj_type", "")) == "sheet"
                        and str(
                            old_nodes.get(str(node["node_token"]), {}).get("sync_status", "")
                        )
                        != "failed"
                    )
                    else 2
                    if not has_embedded_sheet_scan(
                        node, old_nodes.get(str(node["node_token"]), {})
                    )
                    else 3
                )
            )
            if args.retry_batch_size is not None:
                if args.retry_batch_size <= 0:
                    raise SystemExit("--retry-batch-size must be greater than zero")
                content_nodes_to_fetch = retry_candidates[: args.retry_batch_size]
                print(
                    f"retry_batch selected={len(content_nodes_to_fetch)} candidates={len(retry_candidates)}",
                    flush=True,
                )
            else:
                content_nodes_to_fetch = retry_candidates
        elif args.full_content or not incremental:
            content_nodes_to_fetch = all_content_nodes
        else:
            content_nodes_to_fetch = []
            for node in all_content_nodes:
                token = str(node["node_token"])
                old = old_nodes.get(token, {}) if isinstance(old_nodes, dict) else {}
                old_status = str(old.get("sync_status", "")) if isinstance(old, dict) else ""
                old_marker = str(
                    old.get("obj_edit_time") or old.get("remote_updated_at") or old.get("updated_at") or ""
                ) if isinstance(old, dict) else ""
                current = remote_metadata.get(token, {})
                current_marker = str(current.get("obj_edit_time") or current.get("updated_at") or "")
                changed_remotely = bool(old_marker and current_marker and current_marker != old_marker)
                old_path = old.get("relative_path") if isinstance(old, dict) else None
                has_local_success = bool(
                    isinstance(old, dict)
                    and old_status == "ok"
                    and old.get("content_hash")
                    and isinstance(old_path, str)
                    and (output_dir / old_path).is_file()
                    and not has_error_placeholder(output_dir / old_path)
                )
                missing_baseline = not old_marker and not has_local_success
                probe_failed = token in metadata_probe_errors
                needs_embedded_sheet_scan = not has_embedded_sheet_scan(node, old)
                if (
                    token in changed_node_tokens
                    or not isinstance(old, dict)
                    or old_status != "ok"
                    or changed_remotely
                    or missing_baseline
                    or probe_failed
                    or needs_embedded_sheet_scan
                ):
                    content_nodes_to_fetch.append(node)
            print(
                f"incremental_selection candidates={len(all_content_nodes)} fetch={len(content_nodes_to_fetch)} "
                f"reuse={len(all_content_nodes) - len(content_nodes_to_fetch)}",
                flush=True,
            )
        workers_value = nested(
            config,
            "sync",
            "retry_workers" if args.retry_failed else "workers",
            default=1 if args.retry_failed else 4,
        )
        try:
            workers = max(1, min(int(workers_value), 8))
        except (TypeError, ValueError):
            workers = 4

        def previous_success_content(node: dict[str, Any]) -> tuple[str, str] | None:
            token = str(node["node_token"])
            old = old_nodes.get(token, {}) if isinstance(old_nodes, dict) else {}
            old_path = old.get("relative_path") if isinstance(old, dict) else None
            if (
                not isinstance(old, dict)
                or old.get("sync_status") not in {"ok", "stale"}
                or not isinstance(old_path, str)
            ):
                return None
            existing = output_dir / old_path
            if not existing.is_file():
                return None
            raw = existing.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            body = parts[2].lstrip("\n") if len(parts) == 3 else raw
            if str(node.get("obj_type", "")) in {"sheet", "bitable"}:
                return body.rstrip("\n"), str(old.get("revision_id", ""))
            return (
                normalize_content(
                    body.rstrip("\n"),
                    clean_title(node.get("title"), token),
                    document_links_for(token),
                    render_sub_page_navigation=render_sub_page_navigation,
                    localize_document_links=localize_document_links,
                ),
                str(old.get("revision_id", "")),
            )

        def fetch_one(node: dict[str, Any]) -> tuple[str, str, str, str, str]:
            token = str(node["node_token"])
            title = clean_title(node.get("title"), token)
            try:
                delay_value = nested(config, "sync", "request_delay_seconds", default=0.0)
                try:
                    delay = max(0.0, float(delay_value))
                except (TypeError, ValueError):
                    delay = 0.0
                if delay:
                    time.sleep(delay)
                if str(node.get("obj_type", "")) == "sheet":
                    selections = sheet_selections.get(token)
                    workbook_sheets = None
                    if not selections:
                        if all_sheet_settings is None:
                            raise RuntimeError("Sheet node is outside the configured mirror scope")
                        workbook_payload = run_cli(
                            config,
                            "sheets",
                            "+workbook-info",
                            "--as",
                            "bot",
                            "--spreadsheet-token",
                            str(node.get("obj_token", "")),
                            "--format",
                            "json",
                        )
                        workbook_sheets = nested(workbook_payload, "data", "sheets", default=[])
                        if not isinstance(workbook_sheets, list):
                            raise RuntimeError("sheets +workbook-info payload has no data.sheets list")
                        selections = automatic_sheet_selections(all_sheet_settings, workbook_sheets)
                    bitable_tabs = (
                        automatic_sheet_bitable_selections(all_sheet_settings, workbook_sheets)
                        if all_sheet_settings is not None and workbook_sheets is not None
                        else []
                    )
                    if not selections and not bitable_tabs:
                        raise RuntimeError("Sheet workbook has no readable grid or Base tab")
                    content, revision_id = fetch_sheet_markdown(
                        config,
                        str(node.get("obj_token", "")),
                        title,
                        selections,
                        snapshot_root=mirror_dir / DEFAULT_SHEET_SNAPSHOT_DIR,
                        node_token=token,
                        workbook_sheets=workbook_sheets,
                    )
                    mixed_bitable_error = ""
                    for base_token, base_selection in bitable_tabs:
                        try:
                            rendered_base, _ = fetch_bitable_markdown(
                                config,
                                base_token,
                                "内嵌多维表格",
                                [base_selection],
                                snapshot_root=mirror_dir / DEFAULT_SHEET_SNAPSHOT_DIR,
                                node_token=token,
                                mirror_dir=mirror_dir,
                                include_document_heading=False,
                                section_heading_level=2,
                            )
                            content = (
                                content.rstrip()
                                + "\n\n"
                                + SHEET_BITABLE_TAB_RENDER_MARKER
                                + "\n\n"
                                + rendered_base.lstrip()
                            )
                        except Exception as exc:
                            category = safe_error_category(exc)
                            mixed_bitable_error = mixed_bitable_error or category
                            content = (
                                content.rstrip()
                                + "\n\n"
                                + SHEET_BITABLE_UNMIRRORED_MARKER
                                + "\n\n> 此工作簿中的多维表格子表尚未归档；"
                                + f"错误类别：`{category}`。普通 Sheet 子表已保留。\n"
                            )
                    if mixed_bitable_error:
                        return token, "failed", content, mixed_bitable_error, revision_id
                elif str(node.get("obj_type", "")) == "bitable":
                    content, revision_id = fetch_bitable_markdown(
                        config,
                        str(node.get("obj_token", "")),
                        title,
                        bitable_selections[token],
                        snapshot_root=mirror_dir / DEFAULT_SHEET_SNAPSHOT_DIR,
                        node_token=token,
                        mirror_dir=mirror_dir,
                    )
                else:
                    content, revision_id = render_document_content(
                        config,
                        str(node.get("obj_token", "")),
                        title,
                        document_links_for(token),
                        render_sub_page_navigation=render_sub_page_navigation,
                        localize_document_links=localize_document_links,
                        embedded_sheet_settings=(
                            embedded_sheet_settings
                            if embedded_sheet_sync_applies(node, embedded_sheet_settings)
                            else None
                        ),
                        snapshot_root=mirror_dir / DEFAULT_SHEET_SNAPSHOT_DIR,
                        node_token=token,
                    )
                return token, "ok", content, "", revision_id
            except Exception as exc:  # keep inventory even when one document is unavailable
                details = error_info(exc)
                category = str(details["category"])
                previous = previous_success_content(node)
                if previous is not None:
                    # Keep the last good body, but mark it stale so validation
                    # and the next incremental run cannot mistake it for fresh.
                    return token, "stale", previous[0], category, previous[1]
                retryable = "是" if details["retryable"] else "否"
                content = (
                    f"# {title}\n\n"
                    f"同步正文失败（错误类别：{category}，可重试：{retryable}）。\n\n"
                    f"来源：{source_url(config, token)}"
                )
                return token, "failed", content, category, ""

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_one, node) for node in content_nodes_to_fetch]
            for completed, future in enumerate(as_completed(futures), start=1):
                token, status, content, error, revision_id = future.result()
                fetched[token] = (status, content, error, revision_id)
                if completed == 1 or completed % 100 == 0 or completed == len(futures):
                    print(f"content_fetch progress={completed}/{len(futures)}", flush=True)
        counts["content_fetched"] = len(content_nodes_to_fetch)
        fresh_content_tokens.update(fetched)
        print(
            f"content_fetch completed={len(fetched)} fetched_now={len(content_nodes_to_fetch)} workers={workers}"
        )

    def reuse_existing(node: dict[str, Any]) -> bool:
        token = str(node["node_token"])
        old = old_nodes.get(token, {}) if isinstance(old_nodes, dict) else {}
        old_path = old.get("relative_path") if isinstance(old, dict) else None
        if not isinstance(old_path, str):
            return False
        existing = output_dir / old_path
        if not existing.is_file():
            return False
        raw = existing.read_text(encoding="utf-8")
        parts = raw.split("---", 2)
        body = parts[2].lstrip("\n") if len(parts) == 3 else raw
        if str(node.get("obj_type", "")) not in {"sheet", "bitable"}:
            body = normalize_content(
                body.rstrip("\n"),
                clean_title(node.get("title"), token),
                document_links_for(token),
                render_sub_page_navigation=render_sub_page_navigation,
                localize_document_links=localize_document_links,
            )
        fetched[token] = (
            str(old.get("sync_status", "ok")),
            body.rstrip("\n"),
            safe_error_category(str(old.get("error", ""))) if old.get("error") else "",
            str(old.get("revision_id", "")),
        )
        return True

    if incremental or args.retry_failed or args.refresh_tree_only:
        for node in content_nodes:
            token = str(node["node_token"])
            if token in fetched:
                continue
            if reuse_existing(node):
                counts["content_reused"] += 1
    if args.rebuild_tree_only:
        for node in ordered:
            if str(node["node_token"]) not in fetched:
                reuse_existing(node)
        print(f"tree_rebuild reuse_files={len(fetched)}", flush=True)

    download_assets_enabled = bool(
        not args.skip_content
        and not args.skip_assets
        and (args.download_assets or nested(config, "sync", "download_assets", default=False))
    )
    refresh_asset_urls_enabled = bool(
        download_assets_enabled
        and (args.refresh_asset_urls or nested(config, "sync", "refresh_asset_urls", default=True))
    )
    asset_map: dict[str, str] = {}
    asset_errors: dict[str, str] = {}
    if download_assets_enabled:
        asset_contents = asset_contents_for_sync(
            fetched,
            fresh_content_tokens,
            targeted=event_driven,
        )
        asset_map, asset_errors, assets_downloaded, assets_reused, assets_deferred = materialize_assets(
            asset_contents,
            mirror_dir,
            config,
            refresh_short_lived_urls=refresh_asset_urls_enabled,
        )
        counts["assets_downloaded"] = assets_downloaded
        counts["assets_reused"] = assets_reused
        counts["assets_failed"] = len(asset_errors)
        counts["asset_error_categories"] = summarize_asset_errors(asset_errors)
        counts["assets_deferred"] = assets_deferred
        print(
            f"asset_download completed={len(asset_map)} downloaded={assets_downloaded} "
            f"reused={assets_reused} failed={len(asset_errors)} deferred={assets_deferred}",
            flush=True,
        )

    # Markdown exports contain short-lived signed image URLs, and XML-derived
    # media blocks may carry only a file token. Reusing an old local document
    # is correct for正文增量, but its asset reference may have expired or be
    # unusable offline. When asset localization is enabled, refresh only
    # documents that still contain unresolved assets, then download fresh URLs
    # or token-backed media through the official CLI.
    if download_assets_enabled and asset_errors and refresh_asset_urls_enabled:
        asset_nodes = nodes_requiring_asset_refresh(ordered, fetched, asset_errors)
        refresh_workers_value = nested(
            config,
            "sync",
            "asset_refresh_workers",
            default=nested(config, "sync", "workers", default=4),
        )
        try:
            refresh_workers = max(1, min(int(refresh_workers_value), 8))
        except (TypeError, ValueError):
            refresh_workers = 4

        def refresh_one_asset_doc(node: dict[str, Any]) -> tuple[str, str, str, str, str]:
            token = str(node["node_token"])
            title = clean_title(node.get("title"), token)
            try:
                delay_value = nested(config, "sync", "request_delay_seconds", default=0.0)
                try:
                    delay = max(0.0, float(delay_value))
                except (TypeError, ValueError):
                    delay = 0.0
                if delay:
                    time.sleep(delay)
                content, revision_id = render_document_content(
                    config,
                    str(node.get("obj_token", "")),
                    title,
                    document_links_for(token),
                    render_sub_page_navigation=render_sub_page_navigation,
                    localize_document_links=localize_document_links,
                    embedded_sheet_settings=(
                        embedded_sheet_settings
                        if embedded_sheet_sync_applies(node, embedded_sheet_settings)
                        else None
                    ),
                    snapshot_root=mirror_dir / DEFAULT_SHEET_SNAPSHOT_DIR,
                    node_token=token,
                )
                return (
                    token,
                    "ok",
                    content,
                    "",
                    revision_id,
                )
            except Exception as exc:
                return token, "failed", "", str(exc), ""

        refreshed_contents: list[str] = []
        with ThreadPoolExecutor(max_workers=refresh_workers) as executor:
            futures = [executor.submit(refresh_one_asset_doc, node) for node in asset_nodes]
            for future in as_completed(futures):
                token, status, content, error, revision_id = future.result()
                if status == "ok":
                    fetched[token] = (status, content, error, revision_id)
                    refreshed_contents.append(content)
                    counts["asset_content_refreshed"] += 1
                else:
                    counts["asset_content_refresh_failed"] += 1
        print(
            f"asset_content_refresh completed={len(asset_nodes)} "
            f"succeeded={counts['asset_content_refreshed']} "
            f"failed={counts['asset_content_refresh_failed']} workers={refresh_workers}",
            flush=True,
        )
        if refreshed_contents:
            try:
                refreshed_batch_size = max(
                    0,
                    int(nested(config, "sync", "asset_refreshed_batch_size", default=0)),
                )
            except (TypeError, ValueError):
                refreshed_batch_size = 0
            refreshed_map, refreshed_errors, assets_downloaded, assets_reused, assets_deferred = materialize_assets(
                refreshed_contents,
                mirror_dir,
                config,
                batch_size_override=refreshed_batch_size,
            )
            final_contents = asset_contents_for_sync(
                fetched,
                fresh_content_tokens,
                targeted=event_driven,
            )
            asset_map, asset_errors = merge_asset_results(
                asset_map,
                asset_errors,
                refreshed_map,
                refreshed_errors,
                final_contents,
            )
            counts["assets_downloaded"] += assets_downloaded
            counts["assets_reused"] += assets_reused
            counts["assets_failed"] = len(asset_errors)
            counts["asset_error_categories"] = summarize_asset_errors(asset_errors)
            counts["assets_deferred"] += assets_deferred
            print(
                f"asset_download refreshed={len(asset_map)} downloaded={assets_downloaded} "
                f"reused={assets_reused} failed={len(asset_errors)} deferred={assets_deferred}",
                flush=True,
            )
            if asset_errors:
                print(
                    "asset_download error_categories="
                    f"{json.dumps(counts['asset_error_categories'], ensure_ascii=False, sort_keys=True)}",
                    flush=True,
                )

    complete_sheet_exports: dict[str, str] = {}
    complete_bitable_exports: dict[str, str] = {}
    complete_file_downloads: dict[str, str] = {}
    resource_init_errors: dict[str, str] = {}
    if not args.skip_content:
        complete_sheet_exports, sheet_export_errors, sheet_export_stats = initialize_complete_resources(
            config, ordered, mirror_dir, obj_type="sheet", section="sheets", key="workbook_exports"
        )
        complete_bitable_exports, bitable_export_errors, bitable_export_stats = initialize_complete_resources(
            config, ordered, mirror_dir, obj_type="bitable", section="bitables", key="base_exports"
        )
        complete_file_downloads, file_download_errors, file_download_stats = initialize_complete_resources(
            config, ordered, mirror_dir, obj_type="file", section="files", key="downloads"
        )
        resource_init_errors = {
            **sheet_export_errors,
            **bitable_export_errors,
            **file_download_errors,
        }
        for prefix, stats in (
            ("sheet_workbooks", sheet_export_stats),
            ("bitable_exports", bitable_export_stats),
            ("wiki_files", file_download_stats),
        ):
            for name, value in stats.items():
                counts[f"{prefix}_{name}"] = value
        print(
            "resource_initialization "
            f"sheets_downloaded={sheet_export_stats['downloaded']} sheets_deferred={sheet_export_stats['deferred']} "
            f"bitables_downloaded={bitable_export_stats['downloaded']} bitables_deferred={bitable_export_stats['deferred']} "
            f"files_downloaded={file_download_stats['downloaded']} files_deferred={file_download_stats['deferred']}",
            flush=True,
        )

    for node in ordered:
        token = str(node["node_token"])
        relative = planned_paths[token]
        target = output_dir / MIRROR_DIR / relative
        title = clean_title(node.get("title"), token)
        obj_type = str(node.get("obj_type", ""))
        status = "ok"
        error = ""
        content = ""
        revision_id = ""
        if args.skip_content:
            status = "metadata_only"
            content = f"# {title}\n\n（本次运行使用了 --skip-content，未读取正文。）"
        elif reads_sync_content(node):
            status, content, error, revision_id = fetched.get(
                token,
                (
                    "failed",
                    f"# {title}\n\n同步正文未返回结果。\n\n来源：{source_url(config, token)}",
                    "content fetch did not return a result",
                    "",
                ),
            )
            if status in {"failed", "stale"}:
                counts["failed"] += 1
                if status == "stale":
                    counts["stale"] += 1
                if error:
                    categories = counts["error_categories"]
                    categories[error] = categories.get(error, 0) + 1
                if obj_type == "sheet" and SHEET_MIRROR_MARKER in content:
                    counts["sheet_tabs_mirrored"] += content.count(SHEET_TAB_RENDER_MARKER)
                    counts["sheet_tabs_mirrored"] += content.count(
                        SHEET_BITABLE_TAB_RENDER_MARKER
                    )
            elif status == "metadata_stub":
                counts["stub"] += 1
            elif embedded_sheet_sync_applies(node, embedded_sheet_settings):
                if EMBEDDED_SHEET_SCAN_MARKER in content:
                    counts["embedded_sheet_documents_scanned"] += 1
                counts["embedded_sheets_mirrored"] += content.count(EMBEDDED_SHEET_RENDER_MARKER)
            elif obj_type == "sheet" and SHEET_MIRROR_MARKER in content:
                counts["sheets_mirrored"] += 1
                counts["sheet_tabs_mirrored"] += content.count(SHEET_TAB_RENDER_MARKER)
                counts["sheet_tabs_mirrored"] += content.count(SHEET_BITABLE_TAB_RENDER_MARKER)
            elif obj_type == "bitable":
                counts["bitables_mirrored"] += 1
                counts["bitable_tables_mirrored"] += len(bitable_selections.get(token, []))
        elif obj_type == "sheet" and token in complete_sheet_exports:
            status = "ok"
            content = (
                f"# {title}\n\n"
                "> 已初始化完整 Sheet 工作簿的本地保真副本；公式、样式、批注、图表、透视与单元格图片以 .xlsx 为准。\n"
            )
        elif obj_type == "bitable" and token in complete_bitable_exports:
            status = "ok"
            content = (
                f"# {title}\n\n"
                "> 已初始化完整多维表格的本地保真副本；表、视图、仪表盘/报表及附件关联以 .base 为准。\n"
            )
        elif obj_type == "file" and token in complete_file_downloads:
            status = "ok"
            content = (
                f"# {title}\n\n"
                "> 已下载知识库文件的原始二进制副本；文件仅保存，不会执行、挂载、解压或解析。\n"
            )
        else:
            status = "metadata_stub"
            counts["stub"] += 1
            content = (
                f"# {title}\n\n"
                f"该知识库节点类型为 `{obj_type or 'unknown'}`，当前同步器只读取文档正文。\n\n"
                f"如需转换该类型，请单独设计对应的导出策略。\n"
            )
        local_resource = (
            complete_sheet_exports.get(token)
            or complete_bitable_exports.get(token)
            or complete_file_downloads.get(token)
        )
        if local_resource:
            resource_target = mirror_dir / local_resource
            label = (
                "本地完整工作簿 (.xlsx)"
                if obj_type == "sheet"
                else "本地完整多维表格 (.base)"
                if obj_type == "bitable"
                else "本地原始附件（二进制）"
            )
            content = content.rstrip() + "\n\n" + relative_markdown_link(target, resource_target, label) + "\n"
        resource_error = resource_init_errors.get(token)
        if resource_error:
            if status not in {"failed", "stale"}:
                counts["failed"] += 1
                categories = counts["error_categories"]
                categories[resource_error] = categories.get(resource_error, 0) + 1
            status = "failed"
            error = resource_error
            content = content.rstrip() + "\n\n> 完整本地资源初始化未完成；可按同一私有配置重试。\n"
        counts["remote_images"] += len(extract_image_urls(content))
        if download_assets_enabled:
            content = rewrite_asset_urls(content, target, mirror_dir, asset_map)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        old_record = old_nodes.get(token, {}) if isinstance(old_nodes, dict) else {}
        current_remote = remote_metadata.get(token, {})
        if not isinstance(old_record, dict):
            old_record = {}
        current_relative_path = f"{MIRROR_DIR}/{relative.as_posix()}"
        obj_edit_time = str(
            current_remote.get("obj_edit_time")
            or node.get("obj_edit_time")
            or old_record.get("obj_edit_time")
            or ""
        )
        remote_updated_at = str(
            current_remote.get("updated_at")
            or node.get("updated_at")
            or old_record.get("remote_updated_at")
            or old_record.get("updated_at")
            or ""
        )
        revision_id = str(revision_id or old_record.get("revision_id", ""))
        metadata = {
            "source": "feishu",
            "sync_mode": str(nested(config, "sync", "mode", default="mirror")),
            "title": title,
            "source_url": source_url(config, token),
            "space_id": space_id,
            "node_token": token,
            "obj_token": str(node.get("obj_token", "")),
            "obj_type": obj_type,
            "parent_node_token": str(node.get("parent_node_token") or ""),
            "depth": int(node.get("depth", 0)),
            "has_children": bool(children_by_parent.get(token)),
            "children_count": len(children_by_parent.get(token, [])),
            "obj_edit_time": obj_edit_time,
            "remote_updated_at": remote_updated_at,
            "revision_id": revision_id,
            "sync_status": status,
            "error": safe_error_category(error) if error else "",
            "retryable": error_info(error)["retryable"] if error else False,
            "synced_at": sync_started,
            "content_hash": content_hash,
        }
        record = dict(metadata)
        record["relative_path"] = f"{MIRROR_DIR}/{relative.as_posix()}"
        if error:
            record["error"] = safe_error_category(error)
        records.append(record)
        before_exists = target.is_file()
        old_record = old_nodes.get(token, {}) if isinstance(old_nodes, dict) else {}
        unchanged = (
            before_exists
            and isinstance(old_record, dict)
            and old_record.get("relative_path") == current_relative_path
            and old_record.get("content_hash") == content_hash
            and old_record.get("sync_status") == status
        )
        if unchanged:
            counts.setdefault("unchanged", 0)
            counts["unchanged"] += 1
        else:
            if before_exists:
                previous_bodies[token] = target.read_text(encoding="utf-8")
            write_text(target, frontmatter(metadata, sync_started, content_hash) + content + "\n")
            counts["updated" if before_exists else "created"] += 1

    current_tokens = {node["node_token"] for node in nodes}
    deleted = []
    if isinstance(old_nodes, dict):
        deleted = [dict(value, deleted_at=sync_started) for key, value in old_nodes.items() if key not in current_tokens]
    for record in deleted:
        record["sync_status"] = "deleted"
    changes = classify_changes(old_nodes, records, deleted)
    change_stats = {name: len(entries) for name, entries in changes.items()}
    manifest = {
        "version": 2,
        "space_id": space_id,
        "synced_at": sync_started,
        "content_mode": "incremental" if incremental else "full",
        "tree_order": "feishu_node_list",
        "change_detection": (
            "event_targets"
            if event_driven
            else "wiki_node_get_metadata"
            if probe_remote_metadata
            else "baseline_only"
            if incremental
            else "full"
        ),
        "event_names": event_names,
        "source_url_template": nested(config, "space", "source_url_template", default=""),
        "stats": {**counts, "deleted": len(deleted), "total": len(records)},
        "changes": change_stats,
        "change_ledger": {"enabled": change_ledger_enabled},
        "nodes": records,
        "deleted_nodes": deleted,
    }
    state = {
        "version": 2,
        "space_id": space_id,
        "last_started_at": sync_started,
        "last_completed_at": utc_now(),
        "content_mode": "incremental" if incremental else "full",
        "tree_order": "feishu_node_list",
        "change_detection": (
            "event_targets"
            if event_driven
            else "wiki_node_get_metadata"
            if probe_remote_metadata
            else "baseline_only"
            if incremental
            else "full"
        ),
        "changed_node_tokens": sorted(changed_node_tokens),
        "changed_obj_tokens": sorted(changed_obj_tokens),
        "event_names": event_names,
        "nodes": {record["node_token"]: record for record in records},
    }
    sidebar = build_sidebar(records)
    if args.rebuild_tree:
        new_paths = {record["relative_path"] for record in records}
        # The old flat-layout migration may have left files that were never in
        # the previous manifest. The mirror directory is generator-owned, so a
        # rebuild can safely remove every stale generated Markdown path there.
        for stale in sorted(mirror_dir.rglob("*.md")):
            relative = f"{MIRROR_DIR}/{stale.relative_to(mirror_dir).as_posix()}"
            if stale.is_file() and stale.name != "README.md" and relative not in new_paths:
                stale.unlink()
                counts["moved_deleted"] += 1
        for directory in sorted(
            (path for path in mirror_dir.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
    manifest["stats"] = {**counts, "deleted": len(deleted), "total": len(records)}
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    write_text(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    write_text(sidebar_path_file, json.dumps(sidebar, ensure_ascii=False, indent=2) + "\n")
    if change_ledger_enabled:
        write_change_ledger(
            output_dir,
            metadata_dir,
            change_ledger_dir,
            changes,
            previous_bodies,
            sync_started,
            change_ledger_max_diff_lines,
        )
        print(
            "change_ledger "
            f"added={change_stats['added']} modified={change_stats['modified']} "
            f"moved={change_stats['moved']} deleted={change_stats['deleted']}",
            flush=True,
        )
    readme = output_dir / "00_同步说明.md"
    if not readme.exists():
        write_text(
            readme,
            "# feishu-knowledge 同步说明\n\n"
            "本目录由 `soia-cwork-feishu-doc-git-sync` 维护。\n\n"
            f"- `{MIRROR_DIR}/`：知识库生成内容，下一次同步可能覆盖。\n"
            "- `20_本地补录/`：本地手工补录，不会被同步任务覆盖。\n"
            "- `90_同步元数据/`：节点清单、路径映射和 VitePress 侧边栏。\n\n"
            "图片和附件是否能在本地直接展示，取决于飞书应用是否具备对应资源下载权限。\n",
        )
    validation = validate_mirror(
        output_dir,
        manifest=manifest,
        sidebar_file=sidebar_path_file,
        require_local_assets=download_assets_enabled,
        require_embedded_sheet_scan=bool(
            embedded_sheet_settings and embedded_sheet_settings["all_docx"]
        ),
        require_all_sheet_nodes=all_sheet_settings is not None,
    )
    if download_assets_enabled:
        # A refreshed document can replace one old signed URL with several
        # current URLs. Report the post-write validation count rather than
        # adding intermediate queue sizes from both passes.
        counts["assets_deferred"] = int(validation["stats"].get("unresolved_assets", 0))
        manifest["stats"] = {**counts, "deleted": len(deleted), "total": len(records)}
    manifest["validation"] = {
        "ok": validation["ok"],
        "errors": validation["errors"],
        "error_categories": validation["error_categories"],
        "stats": validation["stats"],
    }
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(
        "completed "
        f"created={counts['created']} updated={counts['updated']} failed={counts['failed']} "
        f"stale={counts['stale']} stubs={counts['stub']} unchanged={counts['unchanged']} moved_deleted={counts['moved_deleted']} "
        f"deleted_marked={len(deleted)} remote_images={counts['remote_images']} "
        f"sheets_mirrored={counts['sheets_mirrored']} sheet_tabs={counts['sheet_tabs_mirrored']} "
        f"bitables_mirrored={counts['bitables_mirrored']} bitable_tables={counts['bitable_tables_mirrored']}"
    )
    print_validation(validation)
    result = 0 if counts["failed"] == 0 and validation["ok"] else 2
    lock_handle.close()
    return result


def main() -> int:
    try:
        return sync(parse_args())
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"failed: {redact_output(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
