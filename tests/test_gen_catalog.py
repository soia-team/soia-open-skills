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

    def test_number_chain_and_unprefixed_placeholder(self) -> None:
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_视频", "video"),
            folder("10_孩子/10_视频/10_儿歌动画正片", "songs"),
            folder("10_孩子/10_视频/10_儿歌动画正片/01_正片", "songs-main"),
            file_record("10_孩子/10_视频/10_儿歌动画正片/01_正片/01.mp4"),
            folder("10_孩子/10_视频/贝瓦儿歌", "beva"),
            folder("10_孩子/10_视频/贝瓦儿歌/01_第一集", "beva-one"),
            file_record("10_孩子/10_视频/贝瓦儿歌/01_第一集/01.mp4"),
        ]

        output = self.run_catalog(records, "--url-prefix", "https://example.test/f/")

        self.assertIn("# 👶 10 孩子 [🔗打开](https://example.test/f/root)", output)
        self.assertIn("## 10.10 视频 [🔗](https://example.test/f/video)", output)
        self.assertIn("### 10.10.10 儿歌动画正片 [🔗](https://example.test/f/songs)", output)
        self.assertIn("### 10.10.- 贝瓦儿歌 [🔗](https://example.test/f/beva)", output)

    def test_depth_seven_uses_indented_bold_line(self) -> None:
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
        self.assertRegex(
            output,
            re.compile(r"^\*\*10\.10\.10\.10\.10\.10\.10 六\b\*\* \[🔗\]\(", re.MULTILINE),
            msg=output,
        )

    def test_max_heading_depth_degrades_earlier(self) -> None:
        records = [
            folder("10_孩子", "root"),
            folder("10_孩子/10_视频", "video"),
            folder("10_孩子/10_视频/10_儿歌动画正片", "songs"),
            folder("10_孩子/10_视频/10_儿歌动画正片/01_正片", "songs-main"),
            file_record("10_孩子/10_视频/10_儿歌动画正片/01_正片/01.mp4"),
        ]

        output = self.run_catalog(records, "--max-heading-depth", "2")

        self.assertIn("## 10.10 视频", output)
        self.assertRegex(
            output,
            re.compile(r"^\*\*10\.10\.10 儿歌动画正片\b\*\* \[🔗\]\(", re.MULTILINE),
        )


if __name__ == "__main__":
    unittest.main()
