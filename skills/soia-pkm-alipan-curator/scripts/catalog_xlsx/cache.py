"""Parse catalog Markdown and maintain per-partition incremental caches."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


CACHE_VERSION = 3

TYPE_RULES = [
    ("视频", {"mp4", "mkv", "avi", "flv", "mov", "rmvb", "wmv", "m4v", "ts", "m2ts", "vob", "webm", "mpeg", "mpg"}),
    ("音频", {"mp3", "m4a", "aac", "wav", "flac", "ape", "ogg", "wma", "m4b", "amr"}),
    ("电子书", {"pdf", "epub", "mobi", "azw", "azw3", "djvu", "caj", "chm"}),
    ("Office文档", {"doc", "docx", "ppt", "pptx", "xls", "xlsx", "csv", "wps", "et", "dps"}),
    ("文本与网页", {"txt", "md", "rtf", "html", "htm", "xhtml", "xml", "json", "yaml", "yml", "url"}),
    ("图片", {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff", "svg", "heic", "ico"}),
    ("压缩包", {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso"}),
    ("字幕", {"srt", "ass", "ssa", "vtt", "sub"}),
    ("软件与安装包", {"exe", "dmg", "pkg", "msi", "app", "apk", "ipa", "deb", "rpm", "dll", "lnk", "swf"}),
    ("代码与数据", {"js", "ts", "jsx", "tsx", "py", "java", "go", "rs", "c", "cpp", "h", "hpp", "sql", "db", "sqlite", "ipynb", "sh", "bat", "ps1", "bin", "dat", "nfo"}),
]


def parse_size(text: str) -> int:
    raw = str(text or "").strip()
    match = re.fullmatch(r"([\d.]+)\s*(B|KB|MB|GB|TB)", raw, re.IGNORECASE)
    if not match:
        return 0
    factors = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return round(float(match.group(1)) * factors[match.group(2).upper()])


def extension_of(name: str) -> str:
    clean = str(name).strip().lower()
    index = clean.rfind(".")
    return clean[index + 1 :] if 0 < index < len(clean) - 1 else "(无扩展名)"


def classify(extension: str) -> str:
    for label, extensions in TYPE_RULES:
        if extension in extensions:
            return label
    return "其他"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_search_markdown(path: Path) -> dict[str, Any]:
    markdown = path.read_text(encoding="utf-8")
    partition = path.stem
    declared_match = re.search(r"共\s*([\d,]+)\s*个", markdown)
    if not declared_match:
        raise ValueError(f"{path.name}: 无法读取头部声明文件数")
    declared = int(declared_match.group(1).replace(",", ""))
    folder = ""
    folder_url = ""
    folder_links: dict[str, str] = {}
    files: list[dict[str, Any]] = []

    heading_pattern = re.compile(r"^## (.+?) \[🔗打开文件夹\]\((https?://[^)]+)\)$")
    linked_heading_pattern = re.compile(r"^## \[(.+?)\]\((https?://[^)]+)\)$")
    row_pattern = re.compile(r"^\| (.*) \| ([^|]+) \|$")

    for line in markdown.splitlines():
        heading_match = heading_pattern.match(line) or linked_heading_pattern.match(line)
        if heading_match:
            source_folder = heading_match.group(1).strip().lstrip("/")
            folder = (
                source_folder
                if source_folder == partition or source_folder.startswith(f"{partition}/")
                else f"{partition}/{source_folder}"
            )
            folder_url = heading_match.group(2)
            folder_links[folder] = folder_url
            continue
        if not folder or line == "| 文件 | 大小 |" or line.startswith("|---"):
            continue
        row_match = row_pattern.match(line)
        if not row_match:
            continue
        name = row_match.group(1).replace(r"\|", "|").strip()
        size_text = row_match.group(2).strip()
        extension = extension_of(name)
        parts = [part for part in folder.split("/") if part]
        categories = parts[1:] if parts and parts[0] == partition else parts
        files.append(
            {
                "partition": partition,
                "categories": categories,
                "categoryPath": "/".join(categories),
                "categoryDepth": len(categories),
                "type": classify(extension),
                "ext": extension,
                "name": name,
                "sizeText": size_text,
                "sizeBytes": parse_size(size_text),
                "folder": folder,
                "fullPath": f"{folder}/{name}",
                "folderUrl": folder_url,
                "source": path.name,
            }
        )

    if len(files) != declared:
        raise ValueError(f"{path.name}: 明细行 {len(files):,} 与头部声明 {declared:,} 不一致")

    return {
        "version": CACHE_VERSION,
        "partition": partition,
        "source": str(path.resolve()),
        "sourceName": path.name,
        "declared": declared,
        "folderLinks": folder_links,
        "files": files,
    }


def parse_catalog(path: Path) -> dict[str, Any]:
    markdown = path.read_text(encoding="utf-8")
    total_match = re.search(r"全盘 \*\*([\d,]+) 目录 / ([\d,]+) 文件 / ([^*]+)\*\*", markdown)
    if not total_match:
        raise ValueError(f"{path.name}: 无法解析全盘口径")
    partitions: list[dict[str, Any]] = []
    row_pattern = re.compile(
        r"^\|\s*[^|]*\*\*([^*]+)\*\*\s*\|\s*\[🔗\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([^|]+)\|"
    )
    for line in markdown.splitlines():
        match = row_pattern.match(line)
        if not match:
            continue
        partitions.append(
            {
                "partition": match.group(1).strip(),
                "url": match.group(2),
                "dirs": int(match.group(3).replace(",", "")),
                "files": int(match.group(4).replace(",", "")),
                "volume": match.group(5).strip(),
            }
        )
    if not partitions:
        raise ValueError(f"{path.name}: 未解析到分区统计")

    heading_links: list[dict[str, str]] = []
    current_partition = ""
    linked_heading_pattern = re.compile(
        r"^(#{1,6})\s+(?:\S+\s+)?\[([^]]+)\]\((https?://[^)]+)\)\s*$"
    )
    legacy_heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+?)\s+\[🔗(?:打开)?\]\((https?://[^)]+)\)\s*$"
    )
    for line in markdown.splitlines():
        linked_match = linked_heading_pattern.match(line)
        legacy_match = legacy_heading_pattern.match(line) if not linked_match else None
        if not linked_match and not legacy_match:
            continue
        match = linked_match or legacy_match
        assert match is not None
        level = len(match.group(1))
        raw_name = match.group(2).strip()
        numbered_name = re.search(r"(\d{2}[_.].*)$", raw_name)
        name = numbered_name.group(1) if numbered_name else raw_name
        url = match.group(3)
        if level == 1:
            current_partition = name
        if current_partition:
            heading_links.append({"partition": current_partition, "name": name, "url": url})
    total_files = int(total_match.group(2).replace(",", ""))
    if sum(row["files"] for row in partitions) != total_files:
        raise ValueError(f"{path.name}: 分区文件数之和与全盘文件数不一致")
    return {
        "source": str(path.resolve()),
        "sourceName": path.name,
        "totalDirs": int(total_match.group(1).replace(",", "")),
        "totalFiles": total_files,
        "totalSize": total_match.group(3).strip(),
        "partitions": partitions,
        "headingLinks": heading_links,
    }


def dominant_type(type_counts: Counter[str]) -> str:
    if not type_counts:
        return "空目录/未展开"
    return sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def aggregate(catalog: dict[str, Any], partition_caches: list[dict[str, Any]]) -> dict[str, Any]:
    folder_links: dict[str, str] = {}
    folder_sources: dict[str, str] = {}
    all_files: list[dict[str, Any]] = []

    for partition_cache in partition_caches:
        all_files.extend(partition_cache["files"])
        for folder, url in partition_cache["folderLinks"].items():
            folder_links[folder] = url
            folder_sources[folder] = partition_cache["sourceName"]
    for row in catalog["partitions"]:
        folder_links[row["partition"]] = row["url"]
        folder_sources[row["partition"]] = catalog["sourceName"]

    directory_map: dict[str, dict[str, Any]] = {}

    def ensure_dir(raw_path: str) -> dict[str, Any] | None:
        clean = raw_path.strip("/")
        if not clean:
            return None
        if clean not in directory_map:
            parts = clean.split("/")
            directory_map[clean] = {
                "path": clean,
                "partition": parts[0],
                "depth": len(parts),
                "name": parts[-1],
                "parent": "/".join(parts[:-1]),
                "directFiles": 0,
                "subtreeFiles": 0,
                "directBytes": 0,
                "subtreeBytes": 0,
                "childDirs": set(),
                "typeCounts": Counter(),
            }
        return directory_map[clean]

    for row in all_files:
        parts = [part for part in row["folder"].split("/") if part]
        for index in range(1, len(parts) + 1):
            current = ensure_dir("/".join(parts[:index]))
            assert current is not None
            current["subtreeFiles"] += 1
            current["subtreeBytes"] += row["sizeBytes"]
            current["typeCounts"][row["type"]] += 1
            if index < len(parts):
                current["childDirs"].add(parts[index])
        leaf = ensure_dir(row["folder"])
        assert leaf is not None
        leaf["directFiles"] += 1
        leaf["directBytes"] += row["sizeBytes"]

    for folder in folder_links:
        parts = [part for part in folder.split("/") if part]
        for index in range(1, len(parts) + 1):
            current = ensure_dir("/".join(parts[:index]))
            assert current is not None
            if index < len(parts):
                current["childDirs"].add(parts[index])

    paths_by_name: dict[tuple[str, str], list[str]] = {}
    for path_key, item in directory_map.items():
        paths_by_name.setdefault((item["partition"], item["name"]), []).append(path_key)
    for heading in catalog.get("headingLinks", []):
        candidates = paths_by_name.get((heading["partition"], heading["name"]), [])
        if len(candidates) != 1:
            continue
        resolved_path = candidates[0]
        if not folder_links.get(resolved_path):
            folder_links[resolved_path] = heading["url"]
            folder_sources[resolved_path] = catalog["sourceName"]

    directories = []
    for item in sorted(directory_map.values(), key=lambda row: row["path"]):
        directories.append(
            {
                "partition": item["partition"],
                "depth": item["depth"],
                "name": item["name"],
                "path": item["path"],
                "parent": item["parent"],
                "dominantType": dominant_type(item["typeCounts"]),
                "directFiles": item["directFiles"],
                "subtreeFiles": item["subtreeFiles"],
                "directBytes": item["directBytes"],
                "subtreeBytes": item["subtreeBytes"],
                "childDirCount": len(item["childDirs"]),
                "url": folder_links.get(item["path"], ""),
                "source": folder_sources.get(item["path"], "路径推导"),
            }
        )

    type_counts: Counter[str] = Counter()
    type_bytes: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    partition_counts: Counter[str] = Counter()
    partition_bytes: Counter[str] = Counter()
    for row in all_files:
        type_counts[row["type"]] += 1
        type_bytes[row["type"]] += row["sizeBytes"]
        extension_counts[row["ext"]] += 1
        extension_bytes[row["ext"]] += row["sizeBytes"]
        partition_counts[row["partition"]] += 1
        partition_bytes[row["partition"]] += row["sizeBytes"]

    type_stats = [
        {"type": label, "count": type_counts[label], "bytes": type_bytes[label]}
        for label in sorted(type_counts)
    ]
    extension_stats = [
        {"ext": extension, "type": classify(extension), "count": extension_counts[extension], "bytes": extension_bytes[extension]}
        for extension in sorted(extension_counts, key=lambda ext: (-extension_counts[ext], ext))
    ]
    partition_stats = []
    for row in catalog["partitions"]:
        partition = row["partition"]
        partition_stats.append(
            {
                **row,
                "indexedFiles": partition_counts[partition],
                "indexedBytes": partition_bytes[partition],
            }
        )

    return {
        "catalog": catalog,
        "indexedFiles": len(all_files),
        "indexedBytes": sum(row["sizeBytes"] for row in all_files),
        "directories": directories,
        "typeStats": type_stats,
        "extensionStats": extension_stats,
        "partitionStats": partition_stats,
    }


def default_cache_dir(catalog: Path, search_dir: Path) -> Path:
    identity = f"{catalog.resolve()}\n{search_dir.resolve()}".encode("utf-8")
    key = hashlib.sha256(identity).hexdigest()[:16]
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "soia-pkm-alipan-curator" / "catalog-xlsx" / key


def prepare_incremental(
    *,
    catalog_path: Path,
    search_dir: Path,
    output_path: Path,
    cache_dir: Path,
    force: bool = False,
    verify: bool = False,
) -> dict[str, Any]:
    catalog_path = catalog_path.resolve()
    search_dir = search_dir.resolve()
    output_path = output_path.resolve()
    detail_dir = output_path.parent / f"{output_path.stem}-分区明细"
    cache_dir.mkdir(parents=True, exist_ok=True)
    partition_cache_dir = cache_dir / "partitions"
    partition_cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "manifest.json"
    old_manifest = load_json(manifest_path, {}) or {}
    if old_manifest.get("version") != CACHE_VERSION:
        old_manifest = {}

    source_paths = sorted(search_dir.glob("*.md"), key=lambda item: item.name)
    if not source_paths:
        raise ValueError(f"{search_dir}: 没有可用的 Markdown 全文检索文件")

    old_partitions = old_manifest.get("partitions", {})
    partition_caches: list[dict[str, Any]] = []
    changed_partitions: list[str] = []
    next_partitions: dict[str, Any] = {}
    partition_plan: list[dict[str, Any]] = []

    for source_path in source_paths:
        source_hash = sha256_file(source_path)
        partition = source_path.stem
        cache_path = partition_cache_dir / f"{partition}.json"
        detail_output = detail_dir / f"{partition}.xlsx"
        old = old_partitions.get(partition, {})
        changed = (
            force
            or old.get("sha256") != source_hash
            or old.get("source") != str(source_path.resolve())
            or not cache_path.exists()
            or not detail_output.exists()
        )
        if changed:
            parsed = parse_search_markdown(source_path)
            parsed["sha256"] = source_hash
            atomic_write_json(cache_path, parsed)
            changed_partitions.append(partition)
        else:
            parsed = load_json(cache_path)
            if not parsed or parsed.get("version") != CACHE_VERSION:
                parsed = parse_search_markdown(source_path)
                parsed["sha256"] = source_hash
                atomic_write_json(cache_path, parsed)
                changed_partitions.append(partition)
        partition_caches.append(parsed)
        next_partitions[partition] = {
            "source": str(source_path.resolve()),
            "sha256": source_hash,
            "cache": str(cache_path),
            "output": str(detail_output),
            "files": parsed["declared"],
        }
        partition_plan.append(
            {
                "partition": partition,
                "source": str(source_path.resolve()),
                "cache": str(cache_path),
                "output": str(detail_output),
                "changed": partition in changed_partitions,
            }
        )

    stale_partitions = []
    for partition in sorted(set(old_partitions) - set(next_partitions)):
        old = old_partitions.get(partition, {})
        stale_partitions.append(
            {
                "partition": partition,
                "cache": old.get("cache", str(partition_cache_dir / f"{partition}.json")),
                "output": old.get("output", str(detail_dir / f"{partition}.xlsx")),
            }
        )

    catalog_hash = sha256_file(catalog_path)
    catalog = parse_catalog(catalog_path)
    aggregate_payload = aggregate(catalog, partition_caches)
    aggregate_path = cache_dir / "aggregate.json"
    atomic_write_json(aggregate_path, aggregate_payload)

    build_master = (
        force
        or bool(changed_partitions)
        or bool(stale_partitions)
        or old_manifest.get("catalogSha256") != catalog_hash
        or not output_path.exists()
    )
    next_manifest = {
        "version": CACHE_VERSION,
        "catalog": str(catalog_path),
        "catalogSha256": catalog_hash,
        "searchDir": str(search_dir),
        "output": str(output_path),
        "detailDir": str(detail_dir),
        "partitions": next_partitions,
    }
    plan = {
        "version": CACHE_VERSION,
        "catalogPath": str(catalog_path),
        "searchDir": str(search_dir),
        "outputPath": str(output_path),
        "detailDir": str(detail_dir),
        "cacheDir": str(cache_dir),
        "aggregatePath": str(aggregate_path),
        "buildMaster": build_master,
        "verify": verify,
        "partitions": partition_plan,
        "changedPartitions": changed_partitions,
        "stalePartitions": stale_partitions,
        "nextManifest": next_manifest,
        "manifestPath": str(manifest_path),
    }
    atomic_write_json(cache_dir / "build-plan.json", plan)
    return plan


def commit_manifest(plan: dict[str, Any]) -> None:
    atomic_write_json(Path(plan["manifestPath"]), plan["nextManifest"])
