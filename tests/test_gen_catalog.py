#!/usr/bin/env python3
"""Regression tests for the catalog renderer."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gen_catalog = load_module(
    "gen_catalog_under_test",
    "skills/soia-pkm-alipan-curator/scripts/gen_catalog.py",
)


def _split_parent_name(path: str) -> tuple[str, str]:
    """按 scan_drive.py 的真实约定拆成 (父目录路径, 自身名字)；所有路径统一视为从 / 出发的绝对路径，
    顶层根的父目录拆分为空串，与生产扫描数据保持一致，避免父子路径前导 / 不一致导致链路断裂。"""
    absolute = path if path.startswith("/") else "/" + path
    parent, name = absolute.rsplit("/", 1)
    return parent, name


def folder(path: str, file_id: str) -> dict:
    parent, name = _split_parent_name(path)
    return {"path": parent, "name": name, "id": file_id, "dir": True, "size": None}


def file_record(path: str, size: int = 10) -> dict:
    parent, name = _split_parent_name(path)
    return {
        "path": parent,
        "name": name,
        "id": None,
        "dir": False,
        "size": size,
    }


def partition_catalog(
    partitions: list[tuple[str, str, int, int]],
    *,
    title: str = "Catalog",
    total_dirs: int | None = None,
    total_files: int | None = None,
) -> str:
    if total_dirs is None:
        total_dirs = sum(part[2] for part in partitions)
    if total_files is None:
        total_files = sum(part[3] for part in partitions)
    rows = "\n".join(
        f"| 📁 **{name}** | [🔗](https://drive.test/{file_id}) | {dirs} | {files} | 1GB |"
        for name, file_id, dirs, files in partitions
    )
    sections = "\n".join(
        f"# 📁 [{name}](https://drive.test/{file_id})\n## [{name} 内容](https://drive.test/{file_id}/item)"
        for name, file_id, _, _ in partitions
    )
    return f"""# {title}
> Drive · 全盘 **{total_dirs} 目录 / {total_files} 文件 / 1GB**
> 分类逻辑见地图。

| 区 | 直达 | 目录 | 文件 | 体量 |
|---|---|---:|---:|---:|
{rows}

{sections}
"""


class CatalogRendererTests(unittest.TestCase):
    def run_catalog(self, records: list[dict], *extra_args: str) -> str:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scan_dir = root / "scan"
            scan_dir.mkdir()
            (scan_dir / "scan.jsonl").write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
                encoding="utf-8",
            )
            out = root / "catalog.md"
            old_argv = sys.argv
            sys.argv = [
                "gen_catalog.py",
                "--scan-dir",
                str(scan_dir),
                "--out",
                str(out),
                "--url-prefix",
                "https://example.test/f/",
                "--heading-pattern",
                r"^\d{2}[_.]",
                *extra_args,
            ]
            try:
                gen_catalog.main()
            finally:
                sys.argv = old_argv
            return out.read_text(encoding="utf-8")

    def run_catalog_with_search(
        self,
        records: list[dict],
        *extra_args: str,
        search_name: str = "10_孩子.md",
    ) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scan_dir = root / "scan"
            search_dir = root / "search"
            scan_dir.mkdir()
            (scan_dir / "scan.jsonl").write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
                encoding="utf-8",
            )
            out = root / "catalog.md"
            old_argv = sys.argv
            sys.argv = [
                "gen_catalog.py",
                "--scan-dir",
                str(scan_dir),
                "--out",
                str(out),
                "--search-dir",
                str(search_dir),
                "--url-prefix",
                "https://example.test/f/",
                "--heading-pattern",
                r"^\d{2}[_.]",
                *extra_args,
            ]
            try:
                gen_catalog.main()
            finally:
                sys.argv = old_argv
            search = (search_dir / search_name).read_text(encoding="utf-8")
            return out.read_text(encoding="utf-8"), search

    def test_only_numbered_directories_enter_outline(self) -> None:
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_视频", "video"),
            folder("10_孩子/10_视频/10_儿歌动画正片", "songs"),
            folder("10_孩子/10_视频/10_儿歌动画正片/01_正片", "songs-main"),
            file_record("10_孩子/10_视频/10_儿歌动画正片/01_正片/01.mp4"),
            folder("10_孩子/10_视频/贝瓦儿歌", "beva"),
            folder("10_孩子/10_视频/贝瓦儿歌/01_第一集", "beva-one"),
            file_record("10_孩子/10_视频/贝瓦儿歌/01_第一集/01.mp4"),
            folder("10_孩子/10_视频/assets", "assets"),
            folder("10_孩子/10_视频/assets/banner", "banner"),
            file_record("10_孩子/10_视频/assets/banner/cover.png"),
        ]

        output = self.run_catalog(records, "--url-prefix", "https://example.test/f/")

        self.assertIn("# 📁 [10_孩子](https://example.test/f/root)", output)
        self.assertIn("## [10_视频](https://example.test/f/video)", output)
        self.assertIn("### [10_儿歌动画正片](https://example.test/f/songs)", output)
        self.assertIn("### [01_第一集](https://example.test/f/beva-one)", output)
        self.assertIn("| [assets/banner 🔗](https://example.test/f/banner) |", output)
        self.assertIsNone(re.search(r"^#{1,6} .*贝瓦儿歌", output, re.MULTILINE))
        self.assertIsNone(re.search(r"^#{1,6} .*banner", output, re.MULTILINE))
        self.assertNotIn("&nbsp;", output)
        self.assertNotIn(".-", output)

    def test_depth_seven_stays_at_h6_without_html_indent(self) -> None:
        records = []
        parts = []
        for index, name in enumerate(
            ["10_孩子", "10_一", "10_二", "10_三", "10_四", "10_五", "10_六"]
        ):
            parts.append(name)
            records.append(folder("/".join(parts), f"dir-{index}"))
        leaf = "/".join(parts + ["01_内容"])
        records.extend([folder(leaf, "leaf"), file_record(leaf + "/item.mp4")])

        output = self.run_catalog(records)

        self.assertIsNone(re.search(r"^#{7,}(?:\s|$)", output, re.MULTILINE))
        self.assertIn("###### [10_六](https://example.test/f/dir-6)", output)
        self.assertIn("###### [01_内容](https://example.test/f/leaf)", output)
        self.assertNotIn("10.10.10.10", output)
        self.assertNotIn("&nbsp;", output)
        self.assertNotRegex(output, re.compile(r"^\*\*10\.", re.MULTILINE))

    def test_max_heading_depth_caps_markdown_heading_level(self) -> None:
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_视频", "video"),
            folder("10_孩子/10_视频/10_儿歌动画正片", "songs"),
            folder("10_孩子/10_视频/10_儿歌动画正片/01_正片", "songs-main"),
            file_record("10_孩子/10_视频/10_儿歌动画正片/01_正片/01.mp4"),
        ]

        output = self.run_catalog(records, "--max-heading-depth", "2")

        self.assertIn("## [10_视频](https://example.test/f/video)", output)
        self.assertIn("## [10_儿歌动画正片](https://example.test/f/songs)", output)
        self.assertIn("## [01_正片](https://example.test/f/songs-main)", output)
        self.assertNotIn("10.10.10", output)
        self.assertNotIn("&nbsp;", output)
        self.assertNotRegex(output, re.compile(r"^\*\*10\.", re.MULTILINE))

    def test_technical_subtree_collapses_into_numbered_parent_row(self) -> None:
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_视频", "video"),
            folder("10_孩子/10_视频/20_官网离线资料", "website"),
            folder("10_孩子/10_视频/20_官网离线资料/images", "images"),
            folder("10_孩子/10_视频/20_官网离线资料/images/banner", "banner"),
            file_record("10_孩子/10_视频/20_官网离线资料/index.html"),
            file_record("10_孩子/10_视频/20_官网离线资料/images/banner/header.png"),
        ]

        output = self.run_catalog(records, "--url-prefix", "https://example.test/f/")

        self.assertIn("### [20_官网离线资料](https://example.test/f/website)", output)
        self.assertIn("| [20_官网离线资料 🔗](https://example.test/f/website) |", output)
        self.assertNotIn("| [images", output)
        self.assertNotRegex(output, re.compile(r"^#{1,6} .*\b(?:images|banner)\b", re.MULTILINE))

    def test_search_index_does_not_treat_a_file_as_a_resource_folder(self) -> None:
        records = [
            folder("/10_孩子", "root"),
            folder("/10_孩子/10_视频", "video"),
            folder("/10_孩子/10_视频/10_课程", "course"),
            file_record("/10_孩子/10_视频/10_课程/lesson.mp4"),
        ]

        _, search = self.run_catalog_with_search(records)

        self.assertIn(
            "## 10_视频/10_课程 [🔗打开文件夹](https://example.test/f/course)",
            search,
        )
        self.assertNotIn("## 10_视频/10_课程/lesson.mp4", search)
        self.assertIn("| lesson.mp4 | 10B |", search)

    def test_merge_partition_updates_only_target_section_and_totals(self) -> None:
        existing = """---
type: moc
---
# ☁️ 云盘馆藏总览
> 备份盘 · 全盘 **150 目录 / 300 文件 / 1.0TB** · 浏览
> 分类逻辑见地图。
> 增量状态：旧状态。

| 区 | 直达 | 目录 | 文件 | 体量 |
|---|---|---:|---:|---:|
| 📁 **10_学习资料** | [🔗](https://old/root) | 100 | 200 | 700GB |
| 📁 **20_参考资料** | [🔗](https://old/books) | 50 | 100 | 300GB |

# 📁 [10_学习资料](https://old/root)
## [10_旧结构](https://old/child)

# 📁 [20_参考资料](https://old/books)
## [10_保留](https://old/keep)
"""
        generated = """---
type: moc
---
# ☁️ 单分区
> 备份盘 · 全盘 **91 目录 / 181 文件 / 690GB** · 浏览

| 区 | 直达 | 目录 | 文件 | 体量 |
|---|---|---:|---:|---:|
| 📁 **10_学习资料** | [🔗](https://new/root) | 91 | 181 | 690GB |

# 📁 [10_学习资料](https://new/root)
## [10_新结构](https://new/child)
"""

        merged, partition, dirs, files = gen_catalog.merge_partition_catalog(
            existing, generated, "2026-07-14"
        )

        self.assertEqual(partition, "10_学习资料")
        self.assertEqual((dirs, files), (91, 181))
        self.assertIn("全盘 **141 目录 / 281 文件 / 1.0TB**", merged)
        self.assertIn("| 📁 **10_学习资料** | [🔗](https://new/root) | 91 | 181 | 690GB |", merged)
        self.assertIn("## [10_新结构](https://new/child)", merged)
        self.assertNotIn("10_旧结构", merged)
        self.assertIn("## [10_保留](https://old/keep)", merged)
        self.assertIn("`10_学习资料` 已于 2026-07-14 全区重扫", merged)
        self.assertNotIn("690GB |\n\n| 📁 **20_参考资料**", merged)

    def test_merge_partition_accepts_unnumbered_root(self) -> None:
        existing = """# Catalog
> Drive · 全盘 **3 目录 / 2 文件 / 1GB**

| 区 | 直达 | 目录 | 文件 | 体量 |
|---|---|---:|---:|---:|
| 📁 **Library** | [🔗](https://old/root) | 3 | 2 | 1GB |

# 📁 [Library](https://old/root)
## [Old](https://old/item)
"""
        generated = """# Partial
> Drive · 全盘 **4 目录 / 3 文件 / 1GB**

| 区 | 直达 | 目录 | 文件 | 体量 |
|---|---|---:|---:|---:|
| 📁 **Library** | [🔗](https://new/root) | 4 | 3 | 1GB |

# 📁 [Library](https://new/root)
## [New](https://new/item)
"""

        merged, partition, dirs, files = gen_catalog.merge_partition_catalog(existing, generated)

        self.assertEqual((partition, dirs, files), ("Library", 4, 3))
        self.assertIn("## [New](https://new/item)", merged)
        self.assertNotIn("## [Old]", merged)

    def test_merge_partition_inserts_new_partition_only_when_explicit(self) -> None:
        existing = partition_catalog(
            [("10_学习", "old-10", 10, 20), ("30_资料", "old-30", 30, 40)],
        )
        generated = partition_catalog(
            [("20_新增", "new-20", 5, 7)],
            title="Partial",
            total_dirs=5,
            total_files=7,
        )

        with self.assertRaises(ValueError):
            gen_catalog.merge_partition_catalog(existing, generated)

        merged, partition, dirs, files = gen_catalog.merge_partition_catalog(
            existing,
            generated,
            "2026-07-16",
            allow_new_partition=True,
        )

        self.assertEqual((partition, dirs, files), ("20_新增", 5, 7))
        self.assertEqual(
            [merged.index(f"**{name}**") for name in ("10_学习", "20_新增", "30_资料")],
            sorted(merged.index(f"**{name}**") for name in ("10_学习", "20_新增", "30_资料")),
        )
        self.assertEqual(
            [merged.index(f"# 📁 [{name}]") for name in ("10_学习", "20_新增", "30_资料")],
            sorted(merged.index(f"# 📁 [{name}]") for name in ("10_学习", "20_新增", "30_资料")),
        )
        self.assertIn("全盘 **45 目录 / 67 文件 / 1GB**", merged)
        self.assertIn("https://drive.test/old-10", merged)
        self.assertIn("https://drive.test/old-30", merged)
        self.assertIn("https://drive.test/new-20", merged)

    def test_merge_partition_uses_stable_natural_order(self) -> None:
        existing = partition_catalog(
            [("2_短", "old-2", 2, 2), ("10_长", "old-10", 10, 10)],
            total_dirs=12,
            total_files=12,
        )
        generated = partition_catalog(
            [("3_中", "new-3", 3, 3)],
            title="Partial",
            total_dirs=3,
            total_files=3,
        )

        merged, _, _, _ = gen_catalog.merge_partition_catalog(
            existing, generated, allow_new_partition=True
        )

        self.assertLess(merged.index("**2_短**"), merged.index("**3_中**"))
        self.assertLess(merged.index("**3_中**"), merged.index("**10_长**"))
        self.assertLess(merged.index("# 📁 [2_短]"), merged.index("# 📁 [3_中]"))
        self.assertLess(merged.index("# 📁 [3_中]"), merged.index("# 📁 [10_长]"))

    def test_merge_partition_rejects_duplicate_or_ambiguous_templates(self) -> None:
        duplicate = partition_catalog(
            [("10_重复", "one", 1, 1), ("10_重复", "two", 2, 2)],
        )
        generated = partition_catalog(
            [("20_新增", "new", 1, 1)],
            title="Partial",
            total_dirs=1,
            total_files=1,
        )
        with self.assertRaises(ValueError):
            gen_catalog.merge_partition_catalog(
                duplicate, generated, allow_new_partition=True
            )

        ambiguous = partition_catalog([("10_已有", "old", 1, 1)]) + "\n# Footer\n"
        with self.assertRaises(ValueError):
            gen_catalog.merge_partition_catalog(
                ambiguous, generated, allow_new_partition=True
            )

        with self.assertRaisesRegex(ValueError, "roots"):
            gen_catalog.merge_partition_catalog(
                partition_catalog([("10_已有", "old", 1, 1)]),
                generated,
                allow_new_partition=True,
                expected_partition="20_根",
            )

    def test_merge_partition_new_partition_is_idempotent(self) -> None:
        existing = partition_catalog([("10_已有", "old", 1, 1)])
        generated = partition_catalog(
            [("20_新增", "new", 2, 3)],
            title="Partial",
            total_dirs=2,
            total_files=3,
        )

        first, _, _, _ = gen_catalog.merge_partition_catalog(
            existing, generated, "2026-07-16", allow_new_partition=True
        )
        second, _, _, _ = gen_catalog.merge_partition_catalog(
            first, generated, "2026-07-16", allow_new_partition=True
        )

        self.assertEqual(first, second)
        self.assertEqual(first.count("**20_新增**"), 1)
        self.assertEqual(first.count("# 📁 [20_新增]"), 1)

    def test_search_index_uses_catalog_root_without_leading_slash(self) -> None:
        records = [
            folder("Library", "root"),
            folder("Library/Reading", "reading"),
            folder("Library/Reading/Course", "course"),
            file_record("Library/Reading/Course/a.pdf"),
        ]

        _, search = self.run_catalog_with_search(
            records,
            "--heading-pattern",
            r".*",
            search_name="Library.md",
        )

        self.assertIn("# 🔍 Library · 全文检索索引", search)
        self.assertIn("## Reading/Course [🔗打开文件夹]", search)

    def test_summary_counts_duplicate_logical_paths_as_physical_directories(self) -> None:
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_课程", "course-a"),
            folder("10_孩子/10_课程", "course-b"),
            file_record("10_孩子/10_课程/one.mp4", 10),
            file_record("10_孩子/10_课程/two.mp4", 20),
        ]

        output = self.run_catalog(records)

        self.assertIn("全盘 **3 目录 / 2 文件 / 30B**", output)
        self.assertIn("| 📁 **10_孩子** |", output)
        self.assertIn("| 3 | 2 | 30B |", output)

    def test_summary_collapses_exact_scan_double_listings(self) -> None:
        # Same path AND same file_id appearing twice is a scan double-listing
        # (e.g. --resume re-enqueues a directory, or a thread race relists it).
        # The cloud has one entity; the summary must count it once. Distinct
        # entities that merely share a path (different file_id) are still kept.
        # Records follow scan_drive.py's contract: path = parent dir, name = leaf
        # (folder()/file_record() split a full path into that shape; raw file dicts
        # below carry an explicit file_id, which file_record() cannot).
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_课程", "course"),
            folder("10_孩子/10_课程", "course"),  # exact duplicate scan row -> collapse
            {"path": "/10_孩子/10_课程", "name": "one.mp4", "id": "file-a", "dir": False, "size": 10},
            {"path": "/10_孩子/10_课程", "name": "one.mp4", "id": "file-a", "dir": False, "size": 10},  # dup
            {"path": "/10_孩子/10_课程", "name": "two.mp4", "id": "file-b", "dir": False, "size": 20},
        ]

        output = self.run_catalog(records)

        # 2 目录 (root + course, NOT 3) / 2 文件 (one + two, NOT 3)
        self.assertIn("全盘 **2 目录 / 2 文件 / 30B**", output)
        self.assertIn("| 2 | 2 | 30B |", output)

    def test_same_name_parent_child_directory_does_not_break_root_detection(self) -> None:
        """回归测试：当某个目录与其直接子目录同名时（常见于压缩包解压出的
        「文件夹/文件夹/真内容」结构），iter_scan_records 曾因误判「path 最后一段
        等于 name 即代表 path 已是完整路径」而漏拼一层，导致更深层内容与顶层分区
        断链、被 catalog_roots() 误判为独立的伪顶层区。"""
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/同名课程", "course"),
            folder("10_孩子/同名课程/同名课程", "course-inner"),
            folder("10_孩子/同名课程/同名课程/子目录", "grandchild"),
            file_record("10_孩子/同名课程/同名课程/子目录/深层文件.mp4", 10),
        ]

        output = self.run_catalog(records)

        self.assertIn("全盘 **4 目录 / 1 文件 / 10B**", output)
        self.assertIn("| 📁 **10_孩子** |", output)
        self.assertNotIn("**子目录**", output, "同名父子目录导致的断链不应把更深层子目录误判成独立顶层区")
        self.assertEqual(output.count("| 📁 **"), 1, "同名父子目录不应产生额外的伪顶层区")

    def test_custom_heading_pattern_and_section_icons_are_user_configurable(self) -> None:
        records = [
            folder("Library", "root"),
            folder("Library/Reading", "reading"),
            folder("Library/Reading/assets", "assets"),
            file_record("Library/Reading/assets/cover.png"),
        ]

        output = self.run_catalog(
            records,
            "--heading-pattern",
            r"^(Library|Reading)$",
            "--section-icons",
            '{"Library":"📚"}',
        )

        self.assertIn("# 📚 [Library](https://example.test/f/root)", output)
        self.assertIn("## [Reading](https://example.test/f/reading)", output)
        self.assertNotRegex(output, re.compile(r"^#{1,6} .*assets", re.MULTILINE))

    def test_explicit_roots_exclude_orphans_created_by_missing_parent_records(self) -> None:
        recs = {
            "/10_孩子": folder("/10_孩子", "root"),
            "/10_孩子/10_课程/孤儿叶": folder("/10_孩子/10_课程/孤儿叶", "orphan"),
        }
        with tempfile.TemporaryDirectory() as temp:
            roots_path = Path(temp) / "roots.json"
            roots_path.write_text(json.dumps({"/10_孩子": "root"}), encoding="utf-8")

            roots = gen_catalog.catalog_roots(recs, str(roots_path))

        self.assertEqual(roots, ["/10_孩子"])

    def test_release_metadata_is_written_to_catalog_and_search_indexes(self) -> None:
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_课程", "course"),
            file_record("10_孩子/10_课程/lesson.mp4"),
        ]
        metadata = json.dumps(
            {
                "catalog_release_id": "catalog-20260721.1",
                "index_updated_at": "2026-07-21T09:30:00+08:00",
                "snapshot_at": "2026-07-21T09:00:00+08:00",
                "catalog_schema_version": "2026-07",
                "source_fingerprint": "sha256:abc123",
            },
            ensure_ascii=False,
        )

        catalog, search = self.run_catalog_with_search(records, "--release-metadata", metadata)

        for markdown in (catalog, search):
            self.assertIn('catalog_release_id: "catalog-20260721.1"', markdown)
            self.assertIn('index_updated_at: "2026-07-21T09:30:00+08:00"', markdown)
            self.assertIn("## 发布元数据", markdown)
            self.assertIn("| source_fingerprint | sha256:abc123 |", markdown)

    def test_release_metadata_rejects_timezone_less_timestamps(self) -> None:
        records = [folder("10_孩子", "root")]
        metadata = json.dumps(
            {
                "catalog_release_id": "catalog-20260721.1",
                "index_updated_at": "2026-07-21T09:30:00",
                "snapshot_at": "2026-07-21T09:00:00+08:00",
                "catalog_schema_version": "2026-07",
                "source_fingerprint": "sha256:abc123",
            },
            ensure_ascii=False,
        )
        with self.assertRaises(SystemExit):
            self.run_catalog(records, "--release-metadata", metadata)

    def test_release_metadata_rejects_snapshot_after_publish_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "不能晚于"):
            gen_catalog.normalize_release_metadata({
                "catalog_release_id": "catalog-20260721.1",
                "index_updated_at": "2026-07-21T09:00:00+08:00",
                "snapshot_at": "2026-07-21T09:01:00+08:00",
                "catalog_schema_version": "2026-07",
                "source_fingerprint": "sha256:abc123",
            })

    def test_release_metadata_upsert_is_idempotent(self) -> None:
        metadata = gen_catalog.normalize_release_metadata(
            {
                "catalog_release_id": "catalog-20260721.1",
                "index_updated_at": "2026-07-21T09:30:00+08:00",
                "snapshot_at": "2026-07-21T09:00:00+08:00",
                "catalog_schema_version": "2026-07",
                "source_fingerprint": "sha256:abc123",
            }
        )
        source = "---\ntitle: Catalog\n---\n# Catalog\n\n正文\n"

        first = gen_catalog.apply_release_metadata(source, metadata)
        second = gen_catalog.apply_release_metadata(first, metadata)

        self.assertEqual(first, second)
        self.assertEqual(first.count("## 发布元数据"), 1)

    def test_url_prefix_must_be_explicit(self) -> None:
        old_argv = sys.argv
        old_env = os.environ.pop("SOIA_ALIPAN_URL_PREFIX", None)
        sys.argv = ["gen_catalog.py", "--scan-dir", "missing", "--out", "out.md"]
        try:
            with self.assertRaises(SystemExit):
                gen_catalog.main()
        finally:
            sys.argv = old_argv
            if old_env is not None:
                os.environ["SOIA_ALIPAN_URL_PREFIX"] = old_env


if __name__ == "__main__":
    unittest.main()
