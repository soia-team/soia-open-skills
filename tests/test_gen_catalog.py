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


def folder(path: str, file_id: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "id": file_id, "dir": True, "size": None}


def file_record(path: str, size: int = 10) -> dict:
    return {
        "path": path,
        "name": path.rsplit("/", 1)[-1],
        "id": None,
        "dir": False,
        "size": size,
    }


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
                *extra_args,
            ]
            try:
                gen_catalog.main()
            finally:
                sys.argv = old_argv
            return out.read_text(encoding="utf-8")

    def run_catalog_with_search(self, records: list[dict]) -> tuple[str, str]:
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
            ]
            try:
                gen_catalog.main()
            finally:
                sys.argv = old_argv
            search = (search_dir / "10_孩子.md").read_text(encoding="utf-8")
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

        self.assertIn("# 👶 [10_孩子](https://example.test/f/root)", output)
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
| 👶 **10_孩子学习库** | [🔗](https://old/root) | 100 | 200 | 700GB |
| 📖 **20_个人阅读** | [🔗](https://old/books) | 50 | 100 | 300GB |

# 👶 [10_孩子学习库](https://old/root)
## [10_旧结构](https://old/child)

# 📖 [20_个人阅读](https://old/books)
## [10_保留](https://old/keep)
"""
        generated = """---
type: moc
---
# ☁️ 单分区
> 备份盘 · 全盘 **91 目录 / 181 文件 / 690GB** · 浏览

| 区 | 直达 | 目录 | 文件 | 体量 |
|---|---|---:|---:|---:|
| 👶 **10_孩子学习库** | [🔗](https://new/root) | 91 | 181 | 690GB |

# 👶 [10_孩子学习库](https://new/root)
## [10_新结构](https://new/child)
"""

        merged, partition, dirs, files = gen_catalog.merge_partition_catalog(
            existing, generated, "2026-07-14"
        )

        self.assertEqual(partition, "10_孩子学习库")
        self.assertEqual((dirs, files), (91, 181))
        self.assertIn("全盘 **141 目录 / 281 文件 / 1.0TB**", merged)
        self.assertIn("| 👶 **10_孩子学习库** | [🔗](https://new/root) | 91 | 181 | 690GB |", merged)
        self.assertIn("## [10_新结构](https://new/child)", merged)
        self.assertNotIn("10_旧结构", merged)
        self.assertIn("## [10_保留](https://old/keep)", merged)
        self.assertIn("`10_孩子学习库` 已于 2026-07-14 全区重扫", merged)
        self.assertNotIn("690GB |\n\n| 📖", merged)

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
        self.assertIn("| 👶 **10_孩子** |", output)
        self.assertIn("| 3 | 2 | 30B |", output)

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
