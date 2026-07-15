#!/usr/bin/env python3
"""Regression tests for ID-based Feishu knowledge-base sync."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sync = load_module(
    "feishu_doc_sync_under_test",
    "skills/soia-cwork-feishu-doc-git-sync/scripts/sync_feishu_wiki.py",
)


class FeishuDocSyncTests(unittest.TestCase):
    @staticmethod
    def sync_args(config: Path) -> Namespace:
        return Namespace(
            config=str(config),
            space_id=None,
            output_dir=None,
            cli_path=None,
            dry_run=False,
            skip_content=False,
            download_assets=False,
            refresh_asset_urls=False,
            skip_assets=False,
            retry_failed=False,
            retry_batch_size=None,
            rebuild_tree=False,
            rebuild_tree_only=False,
            refresh_tree_only=False,
            validate_only=False,
            incremental=True,
            full_content=False,
            probe_remote_metadata=True,
            changed_node_token=[],
            only_node_token=[],
            changed_obj_token=[],
            event_file=None,
            max_nodes=None,
        )

    def test_expandable_node_uses_same_name_index_without_sibling_file(self) -> None:
        used: set[str] = set()
        self.assertEqual(
            sync.unique_path("规范", Path("10_knowledge-base"), used, "node-1", True).as_posix(),
            "10_knowledge-base/规范/规范.md",
        )
        self.assertEqual(
            sync.unique_path("叶子", Path("10_knowledge-base/规范"), used, "node-2", False).as_posix(),
            "10_knowledge-base/规范/叶子.md",
        )

    def test_missing_generated_dir_reuses_the_single_existing_generated_root(self) -> None:
        previous_mirror_dir = sync.MIRROR_DIR
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "docs"
            (output / "10_existing-root").mkdir(parents=True)
            metadata = output / "90_同步元数据"
            metadata.mkdir(parents=True)
            config = root / "config.yml"
            config.write_text(
                "\n".join(
                    [
                        "version: 1",
                        "provider:",
                        "  cli: lark-cli",
                        "space:",
                        '  id: "space-1"',
                        '  source_url_template: "https://example.test/wiki/{node_token}"',
                        "paths:",
                        f'  output_dir: "{output}"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            try:
                with mock.patch.object(sync, "walk_nodes", return_value=[]):
                    result = sync.sync(self.sync_args(config))
            finally:
                sync.MIRROR_DIR = previous_mirror_dir

            sidebar = json.loads((metadata / "sidebar.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(sidebar[0]["text"], "existing-root")

    def test_event_file_maps_obj_token_and_tree_event(self) -> None:
        nodes = [
            {
                "node_token": "node-1",
                "obj_token": "obj-1",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            event_file = Path(temp) / "events.ndjson"
            event_file.write_text(
                json.dumps(
                    {
                        "header": {"event_type": "drive.file.title_updated_v1"},
                        "event": {"file_token": "obj-1"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            changed_nodes, changed_objects, tree_event, names = sync.load_event_targets(
                str(event_file), nodes
            )

        self.assertEqual(changed_nodes, set())
        self.assertEqual(changed_objects, {"obj-1"})
        self.assertTrue(tree_event)
        self.assertEqual(names, ["drive.file.title_updated_v1"])

    def test_fetch_doc_keeps_revision_id_for_baseline(self) -> None:
        payload = {
            "data": {
                "document": {
                    "content": "# 内容",
                    "revision_id": 42,
                }
            }
        }
        with mock.patch.object(sync, "run_cli", return_value=payload):
            self.assertEqual(sync.fetch_doc({}, "obj-1"), ("# 内容", "42"))

    def test_parse_cli_json_skips_human_preamble_with_brackets(self) -> None:
        payload = sync.parse_cli_json("notice [not-json-yet]\n{" + '"ok": true, "data": {}}')
        self.assertTrue(payload["ok"])

    def test_error_records_keep_only_safe_categories(self) -> None:
        detail = (
            "command failed for /Users/example/private.yml; "
            '{"ok": false, "error": {"subtype": "rate_limit", "code": "99991400"}}'
        )
        self.assertEqual(sync.safe_error_category(detail), "rate_limit")

    def test_validation_reports_failed_records_and_error_categories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "docs"
            mirror = output / "10_knowledge-base"
            metadata = output / "90_同步元数据"
            mirror.mkdir(parents=True)
            metadata.mkdir(parents=True)
            good_path = mirror / "可用文档.md"
            failed_path = mirror / "待重试.md"
            good_path.write_text(
                '---\nnode_token: "node-good"\nsync_status: "ok"\n---\n\n# 正文\n',
                encoding="utf-8",
            )
            failed_path.write_text(
                '---\nnode_token: "node-failed"\nsync_status: "failed"\nerror: "rate_limit"\n---\n\n'
                "同步正文失败（错误类别：rate_limit）。\n",
                encoding="utf-8",
            )
            nodes = [
                {
                    "node_token": "node-good",
                    "title": "可用文档",
                    "obj_type": "docx",
                    "sync_status": "ok",
                    "relative_path": "10_knowledge-base/可用文档.md",
                    "parent_node_token": "",
                },
                {
                    "node_token": "node-failed",
                    "title": "待重试",
                    "obj_type": "docx",
                    "sync_status": "failed",
                    "error": "rate_limit",
                    "relative_path": "10_knowledge-base/待重试.md",
                    "parent_node_token": "",
                },
            ]
            sidebar_file = metadata / "sidebar.json"
            sidebar_file.write_text(
                json.dumps(sync.build_sidebar(nodes), ensure_ascii=False),
                encoding="utf-8",
            )
            result = sync.validate_mirror(
                output,
                {"nodes": nodes},
                sidebar_file=sidebar_file,
            )

        self.assertFalse(result["ok"])
        self.assertIn("failed_records", result["errors"])
        self.assertEqual(result["error_categories"], {"rate_limit": 1})
        self.assertEqual(result["stats"]["failed_records"], 1)

    def test_failed_refresh_keeps_body_as_stale_and_is_retryable(self) -> None:
        nodes = [
            {
                "node_token": "node-stale",
                "obj_token": "obj-stale",
                "obj_type": "docx",
                "title": "暂时不可读",
                "parent_node_token": "",
                "depth": 0,
                "has_child": False,
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "docs"
            mirror = output / "10_knowledge-base"
            metadata = output / "90_同步元数据"
            mirror.mkdir(parents=True)
            metadata.mkdir(parents=True)
            local = mirror / "暂时不可读.md"
            local.write_text(
                '---\nnode_token: "node-stale"\nsync_status: "ok"\n---\n\n旧正文\n',
                encoding="utf-8",
            )
            old = {
                "node_token": "node-stale",
                "obj_token": "obj-stale",
                "relative_path": "10_knowledge-base/暂时不可读.md",
                "sync_status": "ok",
                "content_hash": "old",
                "obj_edit_time": "1",
                "remote_updated_at": "1970-01-01T00:00:01Z",
            }
            (metadata / "sync-state.json").write_text(
                json.dumps({"version": 1, "nodes": {"node-stale": old}}),
                encoding="utf-8",
            )
            (metadata / "manifest.json").write_text(
                json.dumps({"version": 1, "nodes": [old]}),
                encoding="utf-8",
            )
            config = root / "config.yml"
            config.write_text(
                "\n".join(
                    [
                        "version: 1",
                        "provider:",
                        "  cli: lark-cli",
                        "space:",
                        '  id: "space-1"',
                        '  source_url_template: "https://example.test/wiki/{node_token}"',
                        "paths:",
                        f'  output_dir: "{output}"',
                        '  generated_dir: "10_knowledge-base"',
                        "sync:",
                        "  mode: mirror",
                        "  workers: 1",
                        "  metadata_workers: 1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            def fake_run_cli(_config, *args):
                if args[:2] == ("wiki", "+node-get"):
                    return {"data": {"obj_edit_time": "2", "updated_at": "1970-01-01T00:00:02Z"}}
                if args[:2] == ("docs", "+fetch"):
                    raise sync.CliCommandError("rate limited", category="rate_limit", retryable=True)
                raise AssertionError(args)

            with mock.patch.object(sync, "walk_nodes", return_value=nodes), mock.patch.object(
                sync, "run_cli", side_effect=fake_run_cli
            ):
                result = sync.sync(self.sync_args(config))

            updated = json.loads((metadata / "manifest.json").read_text(encoding="utf-8"))
            record = updated["nodes"][0]
            body = local.read_text(encoding="utf-8")

        self.assertEqual(result, 2)
        self.assertEqual(record["sync_status"], "stale")
        self.assertEqual(record["error"], "rate_limit")
        self.assertTrue(record["retryable"])
        self.assertIn("旧正文", body)

    def test_frontmatter_contains_incremental_markers(self) -> None:
        output = sync.frontmatter(
            {
                "node_token": "node-1",
                "obj_token": "obj-1",
                "obj_edit_time": "1713249771",
                "remote_updated_at": "2024-08-14T05:56:48Z",
                "revision_id": "42",
                "has_children": True,
                "children_count": 2,
            },
            "2026-07-14T00:00:00+00:00",
            "hash",
        )
        self.assertIn('node_token: "node-1"', output)
        self.assertIn('obj_edit_time: "1713249771"', output)
        self.assertIn('remote_updated_at: "2024-08-14T05:56:48Z"', output)
        self.assertIn('revision_id: "42"', output)
        self.assertIn("has_children: true", output)

    def test_incremental_fetches_changed_node_and_reuses_unchanged_node(self) -> None:
        nodes = [
            {
                "node_token": "node-stable",
                "obj_token": "obj-stable",
                "obj_type": "docx",
                "title": "稳定文档",
                "parent_node_token": "",
                "depth": 0,
                "has_child": False,
            },
            {
                "node_token": "node-changed",
                "obj_token": "obj-changed",
                "obj_type": "docx",
                "title": "变动文档",
                "parent_node_token": "",
                "depth": 0,
                "has_child": False,
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "docs"
            mirror = output / "10_knowledge-base"
            metadata = output / "90_同步元数据"
            stable_path = mirror / "稳定文档.md"
            changed_path = mirror / "变动文档.md"
            stable_path.parent.mkdir(parents=True)
            metadata.mkdir(parents=True)
            stable_path.write_text("---\nnode_token: node-stable\n---\n\n旧正文\n", encoding="utf-8")
            changed_path.write_text("---\nnode_token: node-changed\n---\n\n旧正文\n", encoding="utf-8")
            old_records = {
                "node-stable": {
                    "node_token": "node-stable",
                    "obj_token": "obj-stable",
                    "relative_path": "10_knowledge-base/稳定文档.md",
                    "sync_status": "ok",
                    "content_hash": "old-stable",
                },
                "node-changed": {
                    "node_token": "node-changed",
                    "obj_token": "obj-changed",
                    "relative_path": "10_knowledge-base/变动文档.md",
                    "sync_status": "ok",
                    "obj_edit_time": "100",
                    "remote_updated_at": "1970-01-01T00:01:40Z",
                    "content_hash": "old-changed",
                },
            }
            state = {"version": 1, "nodes": old_records}
            manifest = {"version": 1, "nodes": list(old_records.values())}
            (metadata / "sync-state.json").write_text(json.dumps(state), encoding="utf-8")
            (metadata / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            config = root / "config.yml"
            config.write_text(
                "\n".join(
                    [
                        "version: 1",
                        "provider:",
                        "  cli: lark-cli",
                        "space:",
                        '  id: "space-1"',
                        '  source_url_template: "https://example.test/wiki/{node_token}"',
                        "paths:",
                        f'  output_dir: "{output}"',
                        '  generated_dir: "10_knowledge-base"',
                        "sync:",
                        "  mode: mirror",
                        "  workers: 1",
                        "  metadata_workers: 1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            def fake_run_cli(_config, *args):
                if args[:2] == ("wiki", "+node-get"):
                    token = args[args.index("--node-token") + 1]
                    return {
                        "data": {
                            "node_token": token,
                            "obj_edit_time": "100" if token == "node-stable" else "200",
                            "updated_at": "1970-01-01T00:03:20Z" if token == "node-changed" else "1970-01-01T00:01:40Z",
                        }
                    }
                if args[:2] == ("docs", "+fetch"):
                    return {
                        "data": {
                            "document": {
                                "content": "# 新正文",
                                "revision_id": 9,
                            }
                        }
                    }
                raise AssertionError(args)

            with mock.patch.object(sync, "walk_nodes", return_value=nodes), mock.patch.object(
                sync, "run_cli", side_effect=fake_run_cli
            ) as run:
                result = sync.sync(self.sync_args(config))

            self.assertEqual(result, 0)
            docs_calls = [call for call in run.call_args_list if call.args[1:3] == ("docs", "+fetch")]
            self.assertEqual(len(docs_calls), 1)
            self.assertIn("obj-changed", docs_calls[0].args)
            updated_manifest = json.loads((metadata / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(updated_manifest["stats"]["content_fetched"], 1)
            self.assertEqual(updated_manifest["stats"]["content_reused"], 1)
            by_token = {row["node_token"]: row for row in updated_manifest["nodes"]}
            self.assertEqual(by_token["node-stable"]["revision_id"], "")
            self.assertEqual(by_token["node-changed"]["revision_id"], "9")

    def test_sidebar_keeps_feishu_node_order(self) -> None:
        sync.MIRROR_DIR = "10_knowledge-base"
        nodes = [
            {
                "node_token": "node-z",
                "title": "知识库必读",
                "parent_node_token": "",
                "relative_path": "10_knowledge-base/知识库必读.md",
            },
            {
                "node_token": "node-a",
                "title": "新人入职-从这里启程",
                "parent_node_token": "",
                "relative_path": "10_knowledge-base/新人入职-从这里启程/新人入职-从这里启程.md",
            },
            {
                "node_token": "node-b",
                "title": "规范-需求开发",
                "parent_node_token": "",
                "relative_path": "10_knowledge-base/规范-需求开发/规范-需求开发.md",
            },
        ]

        sidebar = sync.build_sidebar(nodes)

        self.assertEqual(sidebar[0]["text"], "knowledge-base")
        self.assertEqual(
            [item["text"] for item in sidebar[0]["items"]],
            ["知识库必读", "新人入职-从这里启程", "规范-需求开发"],
        )

    def test_remote_image_urls_are_rewritten_to_relative_assets(self) -> None:
        first = "https://internal-api-drive-stream.feishu.cn/image/a"
        second = "https://internal-api-drive-stream.feishu.cn/image/b"
        content = f"![一]({first})\n<img src=\"{second}\">"
        self.assertEqual(sync.extract_image_urls(content), [first, second])

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mirror = root / "10_knowledge-base"
            target = mirror / "目录" / "文档.md"
            rewritten = sync.rewrite_asset_urls(
                content,
                target,
                mirror,
                {
                    first: "_assets/a.png",
                    second: "_assets/b.png",
                },
            )

        self.assertIn("../_assets/a.png", rewritten)
        self.assertIn("../_assets/b.png", rewritten)

    def test_media_tokens_survive_normalization_as_downloadable_references(self) -> None:
        content = '<source token="file-token-1" />\n<img token="img-token-2" />'
        normalized = sync.normalize_content(content, "带图片文档")
        self.assertIn("feishu-media://file-token-1", normalized)
        self.assertIn("feishu-media://img-token-2", normalized)
        self.assertEqual(
            sync.extract_media_tokens(normalized),
            ["file-token-1", "img-token-2"],
        )
        self.assertEqual(
            sync.extract_asset_references(normalized),
            ["feishu-media://file-token-1", "feishu-media://img-token-2"],
        )

    def test_normalization_escapes_html_in_image_alt_and_repairs_tables(self) -> None:
        content = (
            '![说明 <a href="bad">链接](https://example.test/image.png)\n\n'
            '&lt;table&gt;<tbody><tr><td><p>单元格</p></td></tr></tbody>&lt;/table&gt;'
        )
        normalized = sync.normalize_content(content, "HTML 清理")
        self.assertIn("&lt;a href=", normalized)
        self.assertIn("<table>", normalized)
        self.assertNotIn("<p>单元格</p>", normalized)

    def test_cite_normalization_uses_node_tokens_and_preserves_user_mentions(self) -> None:
        content = (
            '<cite doc-id="node-1" file-type="wiki" title="基础组件"></cite> '
            '<cite type="user" user-name="张志伟"></cite>'
        )
        normalized = sync.normalize_content(
            content,
            "引用测试",
            {"node-1": "https://example.test/wiki/node-1"},
        )
        self.assertIn("[基础组件](https://example.test/wiki/node-1)", normalized)
        self.assertIn("@张志伟", normalized)
        self.assertNotIn("`基础组件`", normalized)

    def test_export_policy_requires_explicit_confirmation_and_disables_auto_export(self) -> None:
        import yaml

        policy_path = (
            REPO_ROOT
            / "skills"
            / "soia-cwork-feishu-doc-git-sync"
            / "references"
            / "export-policy.yml"
        )
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        self.assertFalse(policy["defaults"]["automatic_tabular_export"])
        self.assertTrue(policy["defaults"]["dry_run_before_export"])
        self.assertTrue(policy["confirmation"]["required"])
        self.assertIn("source_titles_or_node_tokens", policy["confirmation"]["required_fields"])
        self.assertIn("lark-cli drive +export", policy["execution"]["allowed_after_confirmation"])
        self.assertEqual(policy["output"]["generated_mirror_dir_policy"], "deny_by_default")

    def test_user_visible_diagnostics_redact_paths_and_credentials(self) -> None:
        message = (
            "config=/Users/example/private.yml output=/tmp/mirror/report.md "
            "LARK_APP_SECRET=secret-value PASSWORD=pass-value --doc local-file.md report.json"
        )
        redacted = sync.redact_output(message)
        self.assertNotIn("/Users/example", redacted)
        self.assertNotIn("/tmp/mirror/report.md", redacted)
        self.assertNotIn("secret-value", redacted)
        self.assertNotIn("pass-value", redacted)
        self.assertNotIn("local-file.md", redacted)
        self.assertNotIn("report.json", redacted)
        self.assertIn("<private-location>", redacted)
        self.assertIn("<redacted>", redacted)


if __name__ == "__main__":
    unittest.main()
