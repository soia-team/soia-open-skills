#!/usr/bin/env python3
"""Tests for the incremental Excel catalog cache and parser."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_xlsx.cache import (  # noqa: E402
    aggregate,
    commit_manifest,
    load_json,
    parse_catalog,
    parse_search_markdown,
    prepare_incremental,
)
from gen_catalog_xlsx import (  # noqa: E402
    cleanup_inspection_sidecars,
    cleanup_stale_partition_outputs,
)


def search_markdown(partition: str, folder: str, rows: list[tuple[str, str]]) -> str:
    table = "\n".join(f"| {name} | {size} |" for name, size in rows)
    return (
        f"# {partition}\n\n"
        f"> 仅供检索（共 {len(rows):,} 个）\n\n"
        f"## {folder} [🔗打开文件夹](https://example.test/{partition})\n\n"
        "| 文件 | 大小 |\n"
        "|---|---|\n"
        f"{table}\n"
    )


def catalog_markdown() -> str:
    return """# 馆藏总览

> 备份盘 · 全盘 **5 目录 / 3 文件 / 2GB**

| 分区 | 直达 | 目录 | 文件 | 体量 |
|---|---|---:|---:|---:|
| 👶 **10_孩子** | [🔗](https://example.test/child) | 3 | 2 | 1GB |
| 📚 **20_阅读** | [🔗](https://example.test/read) | 2 | 1 | 1GB |

# 👶 [10_孩子](https://example.test/child)

## [10_英语](https://example.test/english)

### [10_课程](https://example.test/course)
"""


class IncrementalCatalogTests(unittest.TestCase):
    def test_cleanup_inspection_sidecars_keeps_workbooks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workbook = Path(temporary) / "catalog.xlsx"
            sidecar = Path(f"{workbook}.inspect.ndjson")
            workbook.write_bytes(b"xlsx")
            sidecar.write_text("debug", encoding="utf-8")
            cleanup_inspection_sidecars([workbook])
            self.assertTrue(workbook.exists())
            self.assertFalse(sidecar.exists())

    def test_parser_checks_declared_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "10_孩子.md"
            source.write_text(search_markdown("10_孩子", "10_孩子/10_英语", [("a.mp4", "1MB")]), encoding="utf-8")
            parsed = parse_search_markdown(source)
            self.assertEqual(parsed["declared"], 1)
            self.assertEqual(parsed["files"][0]["type"], "视频")
            source.write_text(source.read_text(encoding="utf-8").replace("共 1 个", "共 2 个"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "与头部声明"):
                parse_search_markdown(source)

    def test_parser_preserves_all_classification_levels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "Library.md"
            source.write_text(
                search_markdown(
                    "Library",
                    "Library/Domain/Topic/Stage/Series",
                    [("a.pdf", "1MB")],
                ),
                encoding="utf-8",
            )

            row = parse_search_markdown(source)["files"][0]

            self.assertEqual(row["categories"], ["Domain", "Topic", "Stage", "Series"])
            self.assertEqual(row["categoryPath"], "Domain/Topic/Stage/Series")
            self.assertEqual(row["categoryDepth"], 4)

    def test_catalog_heading_link_fills_course_parent_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog_path = root / "00_馆藏总览.md"
            catalog_path.write_text(catalog_markdown(), encoding="utf-8")
            search_path = root / "10_孩子.md"
            search_path.write_text(
                search_markdown(
                    "10_孩子",
                    "10_孩子/10_英语/10_课程/01_第一课",
                    [("a.mp4", "1MB"), ("b.pdf", "2MB")],
                ),
                encoding="utf-8",
            )
            catalog = parse_catalog(catalog_path)
            result = aggregate(catalog, [parse_search_markdown(search_path)])
            english = next(row for row in result["directories"] if row["path"] == "10_孩子/10_英语")
            course = next(row for row in result["directories"] if row["path"] == "10_孩子/10_英语/10_课程")
            self.assertEqual(english["url"], "https://example.test/english")
            self.assertEqual(course["url"], "https://example.test/course")

    def test_only_changed_partition_is_rebuilt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            search_dir = root / "search"
            search_dir.mkdir()
            catalog = root / "00_馆藏总览.md"
            catalog.write_text(catalog_markdown(), encoding="utf-8")
            child = search_dir / "10_孩子.md"
            reading = search_dir / "20_阅读.md"
            child.write_text(
                search_markdown("10_孩子", "10_孩子/10_英语", [("a.mp4", "1MB"), ("b.pdf", "2MB")]),
                encoding="utf-8",
            )
            reading.write_text(
                search_markdown("20_阅读", "20_阅读/10_书籍", [("c.epub", "3MB")]),
                encoding="utf-8",
            )
            output = root / "00_阿里云盘馆藏总索引.xlsx"
            cache_dir = root / "cache"

            first = prepare_incremental(
                catalog_path=catalog,
                search_dir=search_dir,
                output_path=output,
                cache_dir=cache_dir,
            )
            self.assertEqual(first["changedPartitions"], ["10_孩子", "20_阅读"])
            aggregate = load_json(Path(first["aggregatePath"]))
            self.assertEqual(aggregate["indexedFiles"], 3)
            self.assertEqual(sum(row["count"] for row in aggregate["typeStats"]), 3)
            output.touch()
            for item in first["partitions"]:
                Path(item["output"]).parent.mkdir(parents=True, exist_ok=True)
                Path(item["output"]).touch()
            commit_manifest(first)

            second = prepare_incremental(
                catalog_path=catalog,
                search_dir=search_dir,
                output_path=output,
                cache_dir=cache_dir,
            )
            self.assertFalse(second["buildMaster"])
            self.assertEqual(second["changedPartitions"], [])

            child.write_text(
                search_markdown("10_孩子", "10_孩子/10_英语", [("a2.mp4", "1MB"), ("b.pdf", "2MB")]),
                encoding="utf-8",
            )
            third = prepare_incremental(
                catalog_path=catalog,
                search_dir=search_dir,
                output_path=output,
                cache_dir=cache_dir,
            )
            self.assertTrue(third["buildMaster"])
            self.assertEqual(third["changedPartitions"], ["10_孩子"])
            self.assertEqual(
                [item["partition"] for item in third["partitions"] if not item["changed"]],
                ["20_阅读"],
            )

    def test_removed_partition_rebuilds_master_and_cleans_stale_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            search_dir = root / "search"
            search_dir.mkdir()
            catalog = root / "00_馆藏总览.md"
            catalog.write_text(catalog_markdown(), encoding="utf-8")
            child = search_dir / "10_孩子.md"
            reading = search_dir / "20_阅读.md"
            child.write_text(
                search_markdown("10_孩子", "10_孩子/10_英语", [("a.mp4", "1MB")]),
                encoding="utf-8",
            )
            reading.write_text(
                search_markdown("20_阅读", "20_阅读/10_书籍", [("b.pdf", "2MB")]),
                encoding="utf-8",
            )
            output = root / "00_阿里云盘馆藏总索引.xlsx"
            cache_dir = root / "cache"
            first = prepare_incremental(
                catalog_path=catalog,
                search_dir=search_dir,
                output_path=output,
                cache_dir=cache_dir,
            )
            output.touch()
            for item in first["partitions"]:
                Path(item["output"]).parent.mkdir(parents=True, exist_ok=True)
                Path(item["output"]).touch()
            commit_manifest(first)

            reading.unlink()
            second = prepare_incremental(
                catalog_path=catalog,
                search_dir=search_dir,
                output_path=output,
                cache_dir=cache_dir,
            )
            self.assertTrue(second["buildMaster"])
            self.assertEqual(
                [item["partition"] for item in second["stalePartitions"]],
                ["20_阅读"],
            )
            stale_output = Path(second["stalePartitions"][0]["output"])
            self.assertTrue(stale_output.exists())
            unmanaged_output = stale_output.parent / "旧分区.xlsx"
            unmanaged_output.touch()
            removed = cleanup_stale_partition_outputs(second)
            self.assertEqual(
                removed,
                sorted([str(stale_output.resolve()), str(unmanaged_output.resolve())]),
            )
            self.assertFalse(stale_output.exists())
            self.assertFalse(unmanaged_output.exists())
            self.assertTrue((stale_output.parent / "10_孩子.xlsx").exists())


if __name__ == "__main__":
    unittest.main()
