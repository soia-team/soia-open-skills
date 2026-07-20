#!/usr/bin/env python3
# @created_by  openai/gpt-5
# @created_at  2026-07-11
# @modified_by  openai/gpt-5
# @modified_at  2026-07-11
# @version  0.1.2
# @description  Offline regression tests for one-article WeChat archiving.
# @changelog  Cover symlink containment, vault discovery, URL authority, and metadata sanitization.
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/archive_wechat.py"
SPEC = importlib.util.spec_from_file_location("archive_wechat", SCRIPT)
assert SPEC and SPEC.loader
archive_wechat = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = archive_wechat
SPEC.loader.exec_module(archive_wechat)


FULL_HTML = """
<!doctype html>
<html><head>
<meta charset="utf-8">
<meta property="og:title" content="Fallback title">
<meta property="og:url" content="https://mp.weixin.qq.com/s/test-article">
<meta name="author" content="署名作者">
<script>
var nickname = '测试公众号';
var createTime = '2026-07-08 00:16';
</script>
</head><body>
<h1 id="activity-name">高级模型提示词</h1>
<a id="js_name">测试公众号</a>
<em id="publish_time"></em>
<div id="js_content">
  <section>
    <h2>第一节</h2>
    <p>这是用于验证正文抽取的一段中文内容，需要足够长以通过质量门。</p>
    <p>高级模型不需要重复命令，但仍需要清晰目标、边界、验收和证据。</p>
    <ul><li>保留为什么</li><li>删除旧脚手架</li></ul>
    <blockquote><p>高级模型应获得目标，而不是僵硬操作剧本。</p></blockquote>
    <p><a href="https://example.com/source">证据链接</a></p>
    <img data-src="https://example.com/image.png">
    <p>第二段继续补充验证文字，确保可见字符数量超过两百。提示词应根据模型能力调整抽象层级，
    让模型自行决定低层步骤，同时要求重新计算数字、检查反例、说明未知，并把结果写成结构化 Markdown。
    这段 fixture 只用于离线测试，不包含真实文章内容。继续增加一些文字来确保阈值稳定通过，
    并验证嵌套 section、段落、列表、链接和图片都能被 stdlib HTMLParser 正确处理。</p>
  </section>
</div>
</body></html>
"""


class ArchiveWeChatTests(unittest.TestCase):
    def test_parse_metadata_body_and_create_time_fallback(self) -> None:
        article = archive_wechat.parse_page(
            FULL_HTML, "https://mp.weixin.qq.com/s/test-article"
        )
        self.assertEqual(article.title, "高级模型提示词")
        self.assertEqual(article.author, "署名作者")
        self.assertEqual(article.publisher, "测试公众号")
        self.assertEqual(article.published_at, "2026-07-08 00:16")
        self.assertTrue(article.content_complete)
        self.assertIn("## 第一节", article.body)
        self.assertIn("- 保留为什么", article.body)
        self.assertIn("[证据链接](https://example.com/source)", article.body)
        self.assertIn("> 高级模型应获得目标", article.body)
        self.assertEqual(article.image_count, 1)

    def test_prefers_clean_input_url_over_tracking_query(self) -> None:
        page = FULL_HTML.replace(
            "https://mp.weixin.qq.com/s/test-article",
            "https://mp.weixin.qq.com/s/test-article?nwr_flag=1",
        )
        article = archive_wechat.parse_page(
            page, "https://mp.weixin.qq.com/s/test-article"
        )
        self.assertEqual(article.url, "https://mp.weixin.qq.com/s/test-article")

    def test_rejects_non_wechat_and_path_escape(self) -> None:
        with self.assertRaises(ValueError):
            archive_wechat.validate_wechat_url("https://example.com/s/test")
        with self.assertRaises(ValueError):
            archive_wechat.validate_wechat_url(
                "https://user@mp.weixin.qq.com/s/test"
            )
        with self.assertRaises(ValueError):
            archive_wechat.validate_wechat_url(
                "https://mp.weixin.qq.com:444/s/test"
            )
        self.assertEqual(
            archive_wechat.validate_wechat_url(
                "https://mp.weixin.qq.com:443/s/test"
            ),
            "https://mp.weixin.qq.com:443/s/test",
        )
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            vault = Path(temp)
            (vault / ".obsidian").mkdir()
            with self.assertRaises(ValueError):
                archive_wechat.resolve_article_root(vault, "../outside")
            article = archive_wechat.parse_page(
                FULL_HTML, "https://mp.weixin.qq.com/s/test-article"
            )
            with self.assertRaisesRegex(ValueError, "Article directory must stay inside"):
                archive_wechat.archive(
                    article,
                    vault,
                    vault.parent / "outside",
                    dry_run=True,
                    allow_incomplete=False,
                )

    def test_vault_discovery_requires_obsidian_marker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            root = Path(temp)
            child = root / "project" / "nested"
            child.mkdir(parents=True)
            (root / "AGENTS.md").write_text("rules", encoding="utf-8")
            with mock.patch.object(Path, "cwd", return_value=child):
                self.assertIsNone(archive_wechat.discover_vault_from_cwd())
                (root / ".obsidian").mkdir()
                self.assertEqual(archive_wechat.discover_vault_from_cwd(), root.resolve())

    def test_archive_is_month_organized_and_idempotent(self) -> None:
        article = archive_wechat.parse_page(
            FULL_HTML, "https://mp.weixin.qq.com/s/test-article"
        )
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            vault = Path(temp)
            (vault / ".obsidian").mkdir()
            root = archive_wechat.resolve_article_root(vault, "Articles")
            first, path = archive_wechat.archive(
                article, vault, root, dry_run=False, allow_incomplete=False
            )
            self.assertEqual(first["status"], "archived")
            assert path
            self.assertEqual(path.parent, root / "2026/07")
            self.assertIn(
                'url: "https://mp.weixin.qq.com/s/test-article"',
                path.read_text(encoding="utf-8"),
            )
            second, second_path = archive_wechat.archive(
                article, vault, root, dry_run=False, allow_incomplete=False
            )
            self.assertEqual(second["status"], "skipped")
            self.assertEqual(second_path, path)
            self.assertEqual(len(list(root.rglob("*.md"))), 1)

    def test_dry_run_writes_nothing(self) -> None:
        article = archive_wechat.parse_page(
            FULL_HTML, "https://mp.weixin.qq.com/s/test-article"
        )
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            vault = Path(temp)
            (vault / ".obsidian").mkdir()
            root = archive_wechat.resolve_article_root(vault, "Articles")
            result, _ = archive_wechat.archive(
                article, vault, root, dry_run=True, allow_incomplete=False
            )
            self.assertEqual(result["status"], "dry_run")
            self.assertFalse(root.exists())

    def test_dedupe_scan_fails_closed_on_unreadable_note(self) -> None:
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            article_root = Path(temp)
            (article_root / "existing.md").write_text("placeholder", encoding="utf-8")
            with mock.patch.object(Path, "read_text", side_effect=OSError("denied")):
                with self.assertRaisesRegex(RuntimeError, "Cannot inspect existing archive"):
                    archive_wechat.find_existing_by_url(
                        article_root, "https://mp.weixin.qq.com/s/test-article"
                    )

    def test_archive_rejects_year_symlink_escape_before_write(self) -> None:
        article = archive_wechat.parse_page(
            FULL_HTML, "https://mp.weixin.qq.com/s/test-article"
        )
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            base = Path(temp)
            vault = base / "vault"
            outside = base / "outside"
            (vault / ".obsidian").mkdir(parents=True)
            article_root = vault / "Articles"
            article_root.mkdir()
            outside.mkdir()
            try:
                (article_root / "2026").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "Output path must stay inside"):
                archive_wechat.archive(
                    article,
                    vault,
                    article_root,
                    dry_run=False,
                    allow_incomplete=False,
                )
            self.assertEqual(list(outside.rglob("*.md")), [])

    def test_dedupe_rejects_note_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            base = Path(temp)
            article_root = base / "Articles"
            article_root.mkdir()
            outside = base / "outside.md"
            outside.write_text(
                'url: "https://mp.weixin.qq.com/s/test-article"\n',
                encoding="utf-8",
            )
            try:
                (article_root / "linked.md").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"file symlinks unavailable: {exc}")
            with self.assertRaisesRegex(RuntimeError, "Existing archive must stay inside"):
                archive_wechat.find_existing_by_url(
                    article_root, "https://mp.weixin.qq.com/s/test-article"
                )

    def test_yaml_escape_and_timestamp_validation(self) -> None:
        escaped = archive_wechat.yaml_escape('a\r\nb\u2028c\t"d\\e')
        self.assertNotRegex(escaped, "[\r\n\t\u2028]")
        self.assertEqual(escaped, r'a b c \"d\\e')
        self.assertEqual(
            archive_wechat._timestamp_to_cst("2026-07-08T00:16:00+00:00"),
            "2026-07-08 08:16",
        )
        self.assertEqual(archive_wechat._timestamp_to_cst("2026-99-99"), "")

    def test_incomplete_content_is_blocked_by_default(self) -> None:
        article = archive_wechat.parse_page(
            "<meta property='og:title' content='Blocked'>",
            "https://mp.weixin.qq.com/s/test-article",
        )
        with tempfile.TemporaryDirectory(prefix="clip-wechat-") as temp:
            vault = Path(temp)
            (vault / ".obsidian").mkdir()
            root = archive_wechat.resolve_article_root(vault, "Articles")
            with self.assertRaises(RuntimeError):
                archive_wechat.archive(
                    article, vault, root, dry_run=False, allow_incomplete=False
                )
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
