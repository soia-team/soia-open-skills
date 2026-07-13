#!/usr/bin/env python3
"""Regression tests for the catalog renderer."""

from __future__ import annotations

import importlib.util
import json
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

        self.assertIn("# 👶 10_孩子 [🔗打开](https://example.test/f/root)", output)
        self.assertIn("## 10_视频 [🔗](https://example.test/f/video)", output)
        self.assertIn("### 10_儿歌动画正片 [🔗](https://example.test/f/songs)", output)
        self.assertIn("### 01_第一集 [🔗](https://example.test/f/beva-one)", output)
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
        self.assertIn("###### 10_六 [🔗]", output)
        self.assertIn("###### 01_内容 [🔗]", output)
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

        self.assertIn("## 10_视频", output)
        self.assertIn("## 10_儿歌动画正片 [🔗]", output)
        self.assertIn("## 01_正片 [🔗]", output)
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

        self.assertIn("### 20_官网离线资料 [🔗](https://example.test/f/website)", output)
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


if __name__ == "__main__":
    unittest.main()
