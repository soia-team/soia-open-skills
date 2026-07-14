#!/usr/bin/env python3
"""Mirror a Feishu wiki space to Markdown without writing back to Feishu."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

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
MIRROR_DIR = "10_飞书镜像"
METADATA_DIR = "90_同步元数据"
STATE_FILE = "sync-state.json"
MANIFEST_FILE = "manifest.json"
SIDEBAR_FILE = "sidebar.json"
MAX_PATH_COMPONENT_LENGTH = 48
DEFAULT_ASSET_DIR = "_assets"
DEFAULT_ASSET_TIMEOUT_SECONDS = 30
DEFAULT_MAX_ASSET_BYTES = 20 * 1024 * 1024
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
    r"(--(?:app-secret|secret|password|passwd|access-token|token|doc|node-token|obj-token|space-id|config|output|output-dir))\s+([^\s]+)",
    re.IGNORECASE,
)


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
    """Parse lark-cli's optional human preamble followed by JSON."""
    for marker in ("{", "["):
        position = stdout.find(marker)
        if position >= 0:
            try:
                value = json.loads(stdout[position:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
            return {"data": value}
    raise RuntimeError("lark-cli returned no JSON payload")


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
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=command_env(config),
        )
        if result.returncode == 0:
            return parse_cli_json(result.stdout)
        detail = (result.stderr or result.stdout).strip().replace("\n", " ")
        transient = any(
            marker in detail.lower()
            for marker in ("429", "rate limit", "rate_limit", "99991400", "frequency limit", "temporarily unavailable", "timeout")
        )
        if transient and attempt < 4:
            time.sleep(min(8, 2**attempt))
            continue
        raise RuntimeError(
            f"command failed ({result.returncode}) for lark-cli operation: "
            f"{redact_output(detail)[:500]}"
        )
    raise RuntimeError("command failed after retries for lark-cli operation")


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


def normalize_content(content: str, title: str, cite_links: dict[str, str] | None = None) -> str:
    value = content.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"^\s*<title>.*?</title>\s*", "", value, count=1, flags=re.IGNORECASE | re.DOTALL)
    value = value.replace("<wiki_recent_update></wiki_recent_update>", "")

    def replace_attachment_source(match: re.Match[str]) -> str:
        attrs = match.group(1)
        href_match = re.search(r'\bhref="([^"]+)"', attrs, flags=re.IGNORECASE)
        token_match = re.search(r'\btoken="([^"]+)"', attrs, flags=re.IGNORECASE)
        if href_match:
            return f"[飞书附件]({href_match.group(1)})"
        if token_match:
            return f"[飞书附件](feishu-media://{token_match.group(1)})"
        return "（飞书附件）"

    # Feishu exports custom figure/grid/source tags. VitePress' Vue parser
    # treats these as components and can reject otherwise valid Markdown; keep
    # the attachment URL while removing the non-standard wrapper tags.
    value = re.sub(r"<source\b([^>]*)/?>", replace_attachment_source, value, flags=re.IGNORECASE)
    value = re.sub(
        r"</?(?:figure|grid|column|callout|sub-page-list|sub-page|sheet|readonly-block)\b[^>]*>",
        "",
        value,
        flags=re.IGNORECASE,
    )

    def replace_feishu_image(match: re.Match[str]) -> str:
        attrs = match.group(1)
        href_match = re.search(r'\bhref="([^"]+)"', attrs, flags=re.IGNORECASE)
        src_match = re.search(r'\bsrc="([^"]+)"', attrs, flags=re.IGNORECASE)
        token_match = re.search(r'\btoken="([^"]+)"', attrs, flags=re.IGNORECASE)
        alt_match = re.search(r'\balt="([^"]*)"', attrs, flags=re.IGNORECASE)
        image_url = (
            href_match.group(1)
            if href_match
            else src_match.group(1)
            if src_match
            else f"feishu-media://{token_match.group(1)}"
            if token_match
            else ""
        )
        if not image_url:
            return "（飞书图片）"
        alt = (alt_match.group(1) if alt_match else "飞书图片").replace('"', "'")
        return f'<img src="{image_url}" alt="{alt}">'

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
        return f"[{label}]({target})" if target else label

    # Resolve citations before generic XML escaping; cite is a Feishu export
    # construct, not an HTML tag that should be shown literally.
    value = re.sub(r"<cite\s+([^>]*)></cite>", replace_cite, value, flags=re.IGNORECASE)
    value = re.sub(r"<cite\s+([^>]*)/>", replace_cite, value, flags=re.IGNORECASE)

    known_html_tags = {
        "a", "abbr", "b", "blockquote", "br", "caption", "code", "col", "colgroup",
        "del", "details", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i",
        "img", "li", "mark", "ol", "p", "pre", "s", "small", "strong", "sub", "sup",
        "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
    }

    def escape_unknown_html(match: re.Match[str]) -> str:
        tag_name = match.group(1).lower()
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


def extract_image_urls(content: str) -> list[str]:
    """Return remote image URLs from Markdown images and raw HTML img tags."""
    urls = set(
        re.findall(r"!\[[^\]]*\]\((https?://[^)\s]+)", content, flags=re.IGNORECASE)
    )
    urls.update(
        re.findall(r"<img\b[^>]*\bsrc=[\"'](https?://[^\"']+)", content, flags=re.IGNORECASE)
    )
    return sorted(urls)


def extract_attachment_urls(content: str) -> list[str]:
    """Return remote URLs currently used by normalized Feishu attachments."""
    return sorted(
        set(
            re.findall(
                r"\[飞书附件\]\((https?://[^)\s]+)",
                content,
                flags=re.IGNORECASE,
            )
        )
    )


def extract_media_tokens(content: str) -> list[str]:
    """Return media tokens carried through normalization for local download."""
    return sorted(set(re.findall(r"feishu-media://([A-Za-z0-9_-]+)", content)))


def extract_asset_references(content: str) -> list[str]:
    """Return image URLs, attachment URLs, and token-backed media references."""
    return sorted(
        set(extract_image_urls(content))
        | set(extract_attachment_urls(content))
        | {f"feishu-media://{token}" for token in extract_media_tokens(content)}
    )


def image_extension(content_type: str, data: bytes, url: str) -> str:
    """Infer a browser-renderable extension without trusting Feishu's URL path."""
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
    guessed = Path(urlparse(url).path).suffix.lower()
    return guessed if guessed in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"} else ".bin"


def download_one_asset(
    url: str,
    asset_root: Path,
    timeout_seconds: float,
    max_bytes: int,
    require_image: bool = True,
) -> tuple[str, str, str]:
    """Download one remote asset into a content-addressed local asset path."""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    existing = next(iter(sorted(asset_root.glob(f"{digest}.*"))), None)
    if existing and existing.is_file() and existing.stat().st_size:
        return url, existing.name, "reused"

    request = Request(url, headers={"User-Agent": "soia-cwork-feishu-doc-git-sync/1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError(f"asset exceeds max_asset_bytes={max_bytes}")
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
) -> tuple[str, str, str]:
    """Download a token-backed document media resource through lark-cli."""
    reference = f"feishu-media://{token}"
    digest = hashlib.sha256(reference.encode("utf-8")).hexdigest()[:24]
    asset_root = mirror_dir / asset_dir
    existing = next(iter(sorted(asset_root.glob(f"{digest}.*"))), None) if asset_root.is_dir() else None
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
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=mirror_dir,
        env=command_env(config),
    )
    if result.returncode != 0:
        raise RuntimeError(f"docs +media-download failed (exit={result.returncode})")
    candidates = sorted(asset_root.glob(f"{digest}.*"))
    if not candidates:
        raise RuntimeError("docs +media-download returned no local file")
    target = candidates[0]
    if target.stat().st_size > max_bytes:
        target.unlink()
        raise RuntimeError(f"asset exceeds max_asset_bytes={max_bytes}")
    return reference, target.name, "downloaded"


def materialize_assets(
    contents: list[str],
    mirror_dir: Path,
    config: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str], int, int]:
    """Download all remote images once and return URL->mirror-relative asset paths."""
    references = sorted({ref for content in contents for ref in extract_asset_references(content)})
    if not references:
        return {}, {}, 0, 0
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
        max_bytes = max(1024, int(nested(config, "sync", "max_asset_bytes", default=DEFAULT_MAX_ASSET_BYTES)))
    except (TypeError, ValueError):
        max_bytes = DEFAULT_MAX_ASSET_BYTES

    asset_map: dict[str, str] = {}
    errors: dict[str, str] = {}
    downloaded = 0
    reused = 0

    image_references = {url for content in contents for url in extract_image_urls(content)}

    def download(reference: str) -> tuple[str, str, str, str]:
        try:
            if reference.startswith("feishu-media://"):
                source, filename, status = download_one_media(
                    config,
                    reference.removeprefix("feishu-media://"),
                    mirror_dir,
                    asset_dir,
                    max_bytes,
                )
            else:
                source, filename, status = download_one_asset(
                    reference,
                    asset_root,
                    timeout_seconds,
                    max_bytes,
                    require_image=reference in image_references,
                )
            return source, filename, status, ""
        except Exception as exc:  # keep the original URL when one image fails
            return reference, "", "failed", str(exc)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(download, reference) for reference in references]
        for future in as_completed(futures):
            url, filename, status, error = future.result()
            if status == "failed":
                errors[url] = error
                continue
            asset_map[url] = (Path(asset_dir) / filename).as_posix()
            if status == "downloaded":
                downloaded += 1
            else:
                reused += 1
    return asset_map, errors, downloaded, reused


def rewrite_asset_urls(
    content: str,
    target: Path,
    mirror_dir: Path,
    asset_map: dict[str, str],
) -> str:
    """Rewrite downloaded image URLs to paths relative to the generated Markdown."""
    for url, mirror_relative in asset_map.items():
        local_path = mirror_dir / mirror_relative
        relative = Path(os.path.relpath(local_path, target.parent)).as_posix()
        content = content.replace(url, relative)
    return content


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
    for node in nodes:
        by_parent.setdefault(node.get("parent_node_token"), []).append(node)

    def build(parent: str | None) -> list[dict[str, Any]]:
        entries = []
        candidates = by_parent.get(parent, [])
        if parent is None:
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

    return [
        {"text": "飞书知识库镜像", "link": "/feishu-knowledge/00_同步说明", "items": build(None)}
    ]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
    cli = args.cli_path or str(nested(config, "provider", "cli", default="lark-cli"))
    config = json.loads(json.dumps(config))
    config.setdefault("provider", {})["cli"] = cli
    sync_started = utc_now()
    print("started space_id=<configured-space> identity=bot config=<private-config> output=<private-location>")
    previous_manifest = load_json(output_dir / METADATA_DIR / MANIFEST_FILE, {})
    if (args.retry_failed or args.rebuild_tree_only) and isinstance(previous_manifest, dict) and isinstance(previous_manifest.get("nodes"), list):
        nodes = [node for node in previous_manifest["nodes"] if isinstance(node, dict)]
        mode = "retry_failed" if args.retry_failed else "tree_rebuild"
        print(f"structure source=previous_manifest mode={mode}", flush=True)
    else:
        nodes = walk_nodes(config, space_id, args.max_nodes)
    print(f"processed nodes_discovered={len(nodes)}")
    if args.dry_run:
        for node in nodes[:10]:
            print(f"node title={clean_title(node.get('title'), node['node_token'])} token={node['node_token']}")
        if len(nodes) > 10:
            print(f"node ... and {len(nodes) - 10} more")
        print("completed dry_run=true files_written=0")
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
    event_driven = bool(event_file or explicit_node_targets or explicit_obj_targets or only_node_tokens)
    probe_remote_metadata = bool(
        incremental
        and not args.rebuild_tree_only
        and not args.refresh_tree_only
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
    cite_links: dict[str, str] = {}
    for node in nodes:
        target = source_url(config, str(node.get("node_token")))
        for identifier in (node.get("node_token"), node.get("obj_token")):
            if identifier:
                cite_links[str(identifier)] = target

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

    records: list[dict[str, Any]] = []
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "failed": 0,
        "stub": 0,
        "remote_images": 0,
        "assets_downloaded": 0,
        "assets_reused": 0,
        "assets_failed": 0,
        "asset_content_refreshed": 0,
        "asset_content_refresh_failed": 0,
        "moved_deleted": 0,
        "content_fetched": 0,
        "content_reused": 0,
    }
    # `wiki +node-list` returns siblings in the order configured in Feishu.
    # Keep that order all the way through records and sidebar generation.  A
    # title sort makes the local tree look tidy but silently changes the
    # knowledge owner's information architecture.
    ordered = list(nodes)

    fetched: dict[str, tuple[str, str, str, str]] = {}
    remote_metadata: dict[str, dict[str, Any]] = {}
    metadata_probe_errors: dict[str, str] = {}
    if probe_remote_metadata:
        metadata_nodes = [
            node for node in ordered if str(node.get("obj_type", "")) in {"docx", "doc"}
        ]
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
        all_doc_nodes = [node for node in ordered if str(node.get("obj_type", "")) in {"docx", "doc"}]
        if only_node_tokens:
            missing_only_nodes = only_node_tokens - {str(node["node_token"]) for node in all_doc_nodes}
            if missing_only_nodes:
                raise SystemExit(
                    "--only-node-token not found in the current manifest/tree: "
                    + ",".join(sorted(missing_only_nodes))
                )
            doc_nodes = [node for node in all_doc_nodes if str(node["node_token"]) in only_node_tokens]
        elif args.retry_failed:
            doc_nodes = [
                node
                for node in all_doc_nodes
                if not (
                    isinstance(old_nodes.get(str(node["node_token"])), dict)
                    and old_nodes[str(node["node_token"])].get("sync_status") == "ok"
                )
            ]
        elif args.full_content or not incremental:
            doc_nodes = all_doc_nodes
        else:
            doc_nodes = []
            for node in all_doc_nodes:
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
                )
                missing_baseline = not old_marker and not has_local_success
                probe_failed = token in metadata_probe_errors
                if (
                    token in changed_node_tokens
                    or not isinstance(old, dict)
                    or old_status != "ok"
                    or changed_remotely
                    or missing_baseline
                    or probe_failed
                ):
                    doc_nodes.append(node)
            print(
                f"incremental_selection candidates={len(all_doc_nodes)} fetch={len(doc_nodes)} "
                f"reuse={len(all_doc_nodes) - len(doc_nodes)}",
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
            if not isinstance(old, dict) or old.get("sync_status") != "ok" or not isinstance(old_path, str):
                return None
            existing = output_dir / old_path
            if not existing.is_file():
                return None
            raw = existing.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            body = parts[2].lstrip("\n") if len(parts) == 3 else raw
            return (
                normalize_content(body.rstrip("\n"), clean_title(node.get("title"), token), cite_links),
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
                raw_content, revision_id = fetch_doc(config, str(node.get("obj_token", "")))
                content = normalize_content(raw_content, title, cite_links)
                return token, "ok", content, "", revision_id
            except Exception as exc:  # keep inventory even when one document is unavailable
                previous = previous_success_content(node)
                if previous is not None:
                    # A transient rate limit or permission change must never
                    # replace a previously successful local mirror with an
                    # error page. Keep the old body and retry next run.
                    return token, "ok", previous[0], "", previous[1]
                error = str(exc)
                content = f"# {title}\n\n同步正文失败：`{error.replace('`', '')}`\n\n来源：{source_url(config, token)}"
                return token, "failed", content, error, ""

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_one, node) for node in doc_nodes]
            for completed, future in enumerate(as_completed(futures), start=1):
                token, status, content, error, revision_id = future.result()
                fetched[token] = (status, content, error, revision_id)
                if completed == 1 or completed % 100 == 0 or completed == len(futures):
                    print(f"content_fetch progress={completed}/{len(futures)}", flush=True)
        counts["content_fetched"] = len(doc_nodes)
        print(f"content_fetch completed={len(fetched)} fetched_now={len(doc_nodes)} workers={workers}")

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
        body = normalize_content(body.rstrip("\n"), clean_title(node.get("title"), token), cite_links)
        fetched[token] = (
            str(old.get("sync_status", "ok")),
            body.rstrip("\n"),
            str(old.get("error", "")),
            str(old.get("revision_id", "")),
        )
        return True

    if incremental or args.retry_failed or args.refresh_tree_only:
        doc_nodes_for_reuse = [
            node for node in ordered if str(node.get("obj_type", "")) in {"docx", "doc"}
        ]
        for node in doc_nodes_for_reuse:
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
        asset_map, asset_errors, assets_downloaded, assets_reused = materialize_assets(
            [value[1] for value in fetched.values() if isinstance(value, tuple) and len(value) > 1],
            mirror_dir,
            config,
        )
        counts["assets_downloaded"] = assets_downloaded
        counts["assets_reused"] = assets_reused
        counts["assets_failed"] = len(asset_errors)
        print(
            f"asset_download completed={len(asset_map)} downloaded={assets_downloaded} "
            f"reused={assets_reused} failed={len(asset_errors)}",
            flush=True,
        )

    # Markdown exports contain short-lived signed image URLs, and XML-derived
    # media blocks may carry only a file token. Reusing an old local document
    # is correct for正文增量, but its asset reference may have expired or be
    # unusable offline. When asset localization is enabled, refresh only
    # documents that still contain unresolved assets, then download fresh URLs
    # or token-backed media through the official CLI.
    if download_assets_enabled and asset_errors and refresh_asset_urls_enabled:
        asset_nodes = [
            node
            for node in ordered
            if str(node.get("obj_type", "")) in {"docx", "doc"}
            and str(node.get("node_token")) in fetched
            and extract_asset_references(fetched[str(node["node_token"])][1])
        ]
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
                raw_content, revision_id = fetch_doc(config, str(node.get("obj_token", "")))
                return token, "ok", normalize_content(raw_content, title, cite_links), "", revision_id
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
            asset_map, asset_errors, assets_downloaded, assets_reused = materialize_assets(
                refreshed_contents,
                mirror_dir,
                config,
            )
            counts["assets_downloaded"] = assets_downloaded
            counts["assets_reused"] = assets_reused
            counts["assets_failed"] = len(asset_errors)
            print(
                f"asset_download refreshed={len(asset_map)} downloaded={assets_downloaded} "
                f"reused={assets_reused} failed={len(asset_errors)}",
                flush=True,
            )

    for node in ordered:
        token = str(node["node_token"])
        relative = path_for(node)
        path_by_token[token] = relative
        title = clean_title(node.get("title"), token)
        obj_type = str(node.get("obj_type", ""))
        status = "ok"
        error = ""
        content = ""
        revision_id = ""
        if args.skip_content:
            status = "metadata_only"
            content = f"# {title}\n\n（本次运行使用了 --skip-content，未读取正文。）"
        elif obj_type in {"docx", "doc"}:
            status, content, error, revision_id = fetched.get(
                token,
                (
                    "failed",
                    f"# {title}\n\n同步正文未返回结果。\n\n来源：{source_url(config, token)}",
                    "content fetch did not return a result",
                    "",
                ),
            )
            if status == "failed":
                counts["failed"] += 1
        else:
            status = "metadata_stub"
            counts["stub"] += 1
            content = (
                f"# {title}\n\n"
                f"该知识库节点类型为 `{obj_type or 'unknown'}`，当前同步器只读取文档正文。\n\n"
                f"如需转换该类型，请单独设计对应的导出策略。\n"
            )
        target = output_dir / MIRROR_DIR / relative
        counts["remote_images"] += len(extract_image_urls(content))
        if download_assets_enabled:
            content = rewrite_asset_urls(content, target, mirror_dir, asset_map)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        old_record = old_nodes.get(token, {}) if isinstance(old_nodes, dict) else {}
        current_remote = remote_metadata.get(token, {})
        if not isinstance(old_record, dict):
            old_record = {}
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
            "synced_at": sync_started,
            "content_hash": content_hash,
        }
        record = dict(metadata)
        record["relative_path"] = f"{MIRROR_DIR}/{relative.as_posix()}"
        if error:
            record["error"] = error
        records.append(record)
        before_exists = target.is_file()
        old_record = old_nodes.get(token, {}) if isinstance(old_nodes, dict) else {}
        unchanged = (
            before_exists
            and isinstance(old_record, dict)
            and old_record.get("content_hash") == content_hash
            and old_record.get("sync_status") == status
        )
        if unchanged:
            counts.setdefault("unchanged", 0)
            counts["unchanged"] += 1
        else:
            write_text(target, frontmatter(metadata, sync_started, content_hash) + content + "\n")
            counts["updated" if before_exists else "created"] += 1

    current_tokens = {node["node_token"] for node in nodes}
    deleted = []
    if isinstance(old_nodes, dict):
        deleted = [dict(value, deleted_at=sync_started) for key, value in old_nodes.items() if key not in current_tokens]
    for record in deleted:
        record["sync_status"] = "deleted"
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
    readme = output_dir / "00_同步说明.md"
    if not readme.exists():
        write_text(
            readme,
            "# 飞书知识库同步说明\n\n"
            "本目录由 `soia-cwork-feishu-doc-git-sync` 维护。\n\n"
            "- `10_飞书镜像/`：飞书只读镜像，下一次同步可能覆盖。\n"
            "- `20_本地补录/`：本地手工补录，不会被镜像同步覆盖。\n"
            "- `90_同步元数据/`：节点清单、路径映射和 VitePress 侧边栏。\n\n"
            "图片和附件是否能在本地直接展示，取决于飞书应用是否具备对应资源下载权限。\n",
        )
    print(
        "completed "
        f"created={counts['created']} updated={counts['updated']} failed={counts['failed']} "
        f"stubs={counts['stub']} unchanged={counts['unchanged']} moved_deleted={counts['moved_deleted']} "
        f"deleted_marked={len(deleted)} remote_images={counts['remote_images']}"
    )
    return 0 if counts["failed"] == 0 else 2


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
