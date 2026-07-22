import argparse
import importlib.util
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-transform-article-ppt" / "scripts" / "media_bundle.py"
SPEC = importlib.util.spec_from_file_location("article_ppt_media_bundle", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


EDITABLE_SLIDE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>
"""

IMAGE_SLIDE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:pic/></p:spTree></p:cSld>
</p:sld>
"""


def write_fake_pptx(path: Path, slides: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for index, slide in enumerate(slides, 1):
            archive.writestr(f"ppt/slides/slide{index}.xml", slide)


def write_png_header(path: Path, width: int = 1080, height: int = 720) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height))


class ArticlePptMediaBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.article = self.root / "example.md"
        self.article.write_text(
            """---
title: 示例文章
author: Example Author
url: https://example.com/article
published_at: 2026-07-22 09:37
---
# 示例文章
## 模型基础
**1. Token（词元）** 模型的工作单位。
## 工具扩展
**2. Agent（智能体）** 模型、规划和工具的组合。
""",
            encoding="utf-8",
        )
        self.out_dir = self.root / "out"

    def tearDown(self):
        self.temp.cleanup()

    def plan(self, **overrides):
        values = {
            "article": str(self.article),
            "out_dir": str(self.out_dir),
            "provider": "hybrid",
            "audience": "初学者",
            "style": "course_module",
            "slide_count": "2",
            "image_count": 1,
            "infographic": True,
            "main_verdict": "术语要放回系统链路理解",
        }
        values.update(overrides)
        manifest = MODULE.build_manifest(argparse.Namespace(**values))
        MODULE.write_json(self.out_dir / "media-manifest.json", manifest)
        return manifest

    def materialize_valid_bundle(self, placeholder: bool = False):
        manifest = self.plan()
        stem = self.article.stem
        local_text = "[ARTIFACT_ID_PLACEHOLDER]" if placeholder else "可编辑标题"
        write_fake_pptx(
            self.out_dir / f"{stem}-editable.pptx",
            [EDITABLE_SLIDE.format(text=local_text), EDITABLE_SLIDE.format(text="来源")],
        )
        write_fake_pptx(
            self.out_dir / f"{stem}-notebooklm.pptx",
            [IMAGE_SLIDE, IMAGE_SLIDE],
        )
        for preview_dir in ("previews/editable", "previews/notebooklm"):
            write_png_header(self.out_dir / preview_dir / "slide-1.png")
            write_png_header(self.out_dir / preview_dir / "slide-2.png")
        write_png_header(self.out_dir / "assets/imagegen/image-01.png", 1024, 1024)
        write_png_header(self.out_dir / f"{stem}-infographic.png", 1080, 1600)
        for entry in manifest["expected"]["prompts"]:
            path = self.out_dir / entry["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("prompt\n", encoding="utf-8")
        return manifest

    def test_plan_extracts_source_and_hybrid_contract(self):
        manifest = self.plan()
        self.assertEqual(manifest["source"]["title"], "示例文章")
        self.assertEqual(manifest["source"]["published_at"], "2026-07-22 09:37")
        self.assertIn("模型基础", manifest["source"]["sections"])
        self.assertIn("Token", manifest["source"]["concepts"])
        self.assertTrue(manifest["expected"]["editable_pptx"]["required"])
        self.assertTrue(manifest["expected"]["notebooklm_pptx"]["required"])
        self.assertNotIn("created_by", json.dumps(manifest, ensure_ascii=False))

    def test_strict_validation_passes_complete_hybrid_bundle(self):
        self.materialize_valid_bundle()
        args = argparse.Namespace(
            manifest=str(self.out_dir / "media-manifest.json"),
            visual_reviewed=True,
            source_facts_reviewed=True,
            strict=True,
        )
        report, exit_code = MODULE.validate_manifest(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(any(item["code"] == "notebooklm_deck_is_flattened" for item in report["warnings"]))

    def test_placeholder_in_editable_pptx_fails(self):
        self.materialize_valid_bundle(placeholder=True)
        args = argparse.Namespace(
            manifest=str(self.out_dir / "media-manifest.json"),
            visual_reviewed=True,
            source_facts_reviewed=True,
            strict=True,
        )
        report, exit_code = MODULE.validate_manifest(args)
        self.assertEqual(exit_code, 1)
        self.assertTrue(any(item["code"] == "runtime_metadata_editable_pptx" for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
