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
            sync_sheets=False,
            sync_bitables=False,
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

    def test_sheet_sync_requires_an_explicit_bounded_selection(self) -> None:
        with self.assertRaises(SystemExit):
            sync.configured_sheet_selections({"sync": {"sheets": {}}}, True)
        with self.assertRaises(SystemExit):
            sync.configured_sheet_selections(
                {
                    "sync": {
                        "sheets": {
                            "selections": [
                                {"node_token": "node-sheet", "sheet_id": "sheet-1", "range": "A:A"}
                            ]
                        }
                    }
                },
                True,
            )
        selections = sync.configured_sheet_selections(
            {
                "sync": {
                    "sheets": {
                        "max_cells": 12,
                        "selections": [
                            {"node_token": "node-sheet", "sheet_id": "sheet-1", "range": "A1:C4"}
                        ],
                    }
                }
            },
            True,
        )
        self.assertEqual(selections["node-sheet"][0]["range"], "A1:C4")

    def test_bitable_sync_requires_explicit_tables_and_keeps_attachment_opt_in(self) -> None:
        with self.assertRaises(SystemExit):
            sync.configured_bitable_selections({"sync": {"bitables": {}}}, True)
        selections = sync.configured_bitable_selections(
            {
                "sync": {
                    "bitables": {
                        "max_records": 20,
                        "download_attachments": True,
                        "selections": [{"node_token": "node-base", "table_id": "tbl-1"}],
                    }
                }
            },
            True,
        )
        self.assertEqual(selections["node-base"][0]["max_records"], 20)
        self.assertTrue(selections["node-base"][0]["download_attachments"])

    def test_fetch_sheet_markdown_reads_only_the_selected_grid_range(self) -> None:
        calls = []

        def fake_run_cli(_config, *args):
            calls.append(args)
            if args[:2] == ("sheets", "+workbook-info"):
                return {
                    "data": {
                        "sheets": [
                            {"sheet_id": "sheet-1", "title": "人员", "resource_type": "sheet"}
                        ]
                    }
                }
            if args[:2] == ("sheets", "+csv-get"):
                return {"data": {"annotated_csv": "姓名,岗位\n张三,后端\n", "has_more": False}}
            raise AssertionError(args)

        with mock.patch.object(sync, "run_cli", side_effect=fake_run_cli):
            content, revision_id = sync.fetch_sheet_markdown(
                {},
                "spreadsheet-1",
                "九安人员名单",
                [{"sheet_id": "sheet-1", "range": "A1:B20", "max_chars": 2000, "skip_hidden": False}],
            )

        self.assertEqual(revision_id, "")
        self.assertIn("## 人员", content)
        self.assertIn("| 姓名 | 岗位 |", content)
        self.assertIn("| 张三 | 后端 |", content)
        csv_call = next(call for call in calls if call[:2] == ("sheets", "+csv-get"))
        self.assertIn("A1:B20", csv_call)
        self.assertIn("--sheet-id", csv_call)

    def test_sheet_preservation_writes_a_bounded_local_snapshot(self) -> None:
        def fake_run_cli(_config, *args):
            if args[:2] == ("sheets", "+workbook-info"):
                return {"data": {"sheets": [{"sheet_id": "sheet-1", "title": "人员", "resource_type": "sheet"}]}}
            if args[:2] == ("sheets", "+csv-get"):
                return {"data": {"annotated_csv": "姓名,岗位\n张三,后端\n", "has_more": False}}
            if args[:2] == ("sheets", "+cells-get"):
                return {"data": {"ranges": [{"cells": [[{"value": "张三", "formula": "", "comment": "备注"}]]}]}}
            if args[:2] == ("sheets", "+sheet-info"):
                return {"data": {"merged_cells": []}}
            if args[:2] in {("sheets", "+chart-list"), ("sheets", "+float-image-list")}:
                return {"data": {"items": []}}
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as temp, mock.patch.object(sync, "run_cli", side_effect=fake_run_cli):
            content, _ = sync.fetch_sheet_markdown(
                {}, "spreadsheet-1", "人员名单",
                [{"sheet_id": "sheet-1", "range": "A1:B20", "max_chars": 2000, "skip_hidden": False,
                  "preserve": True, "preserve_options": {"formulas": True, "styles": True, "comments": True,
                  "layout": True, "charts": True, "floating_images": True}}],
                snapshot_root=Path(temp), node_token="node-sheet",
            )
            snapshots = list(Path(temp).glob("*.sheet.json"))
            payload = json.loads(snapshots[0].read_text(encoding="utf-8"))

        self.assertIn("保真快照", content)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(payload["cells"]["ranges"][0]["cells"][0][0]["comment"], "备注")

    def test_bitable_snapshot_renders_schema_and_records(self) -> None:
        def fake_run_cli(_config, *args):
            if args[:2] == ("base", "+field-list"):
                return {"data": {"items": [{"field_id": "fld-name", "field_name": "姓名"}, {"field_id": "fld-file", "field_name": "附件"}]}}
            if args[:2] == ("base", "+record-list"):
                return {"data": {"items": [{"record_id": "rec-1", "fields": {"fld-name": "张三", "fld-file": [{"name": "证件.png", "file_token": "file-1"}]}}], "has_more": False}}
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as temp, mock.patch.object(sync, "run_cli", side_effect=fake_run_cli):
            content, _ = sync.fetch_bitable_markdown(
                {}, "base-1", "人员库", [{"table_id": "tbl-1", "view_id": "", "max_records": 10, "include_views": False}],
                snapshot_root=Path(temp), node_token="node-base",
            )
            snapshot = json.loads(next(Path(temp).glob("*.bitable.json")).read_text(encoding="utf-8"))

        self.assertIn("| 姓名 | 附件 |", content)
        self.assertIn("证件.png", content)
        self.assertEqual(snapshot["records"][0]["record_id"], "rec-1")

    def test_bitable_attachment_download_uses_a_hashed_local_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            mirror = Path(temp)

            def fake_run(command, **kwargs):
                self.assertIn("+record-download-attachment", command)
                output = Path(command[command.index("--output") + 1])
                (kwargs["cwd"] / output / "attachment.bin").write_bytes(b"fixture")
                return mock.Mock(returncode=0, stdout='{"ok": true}', stderr="")

            with mock.patch.object(sync.subprocess, "run", side_effect=fake_run):
                files = sync.download_bitable_record_attachments(
                    {"provider": {"cli": "lark-cli"}},
                    base_token="base-1",
                    table_id="tbl-1",
                    record_id="rec-1",
                    file_tokens=["file-1"],
                    mirror_dir=mirror,
                )

        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("_assets/bitables/"))

    def test_enabled_sheet_node_is_mirrored_as_a_markdown_table(self) -> None:
        nodes = [
            {
                "node_token": "node-sheet",
                "obj_token": "spreadsheet-1",
                "obj_type": "sheet",
                "title": "人员名单",
                "parent_node_token": "",
                "depth": 0,
                "has_child": False,
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "docs"
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
                        "  sheets:",
                        "    enabled: true",
                        "    selections:",
                        '      - node_token: "node-sheet"',
                        '        sheet_id: "sheet-1"',
                        '        range: "A1:B20"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            def fake_run_cli(_config, *args):
                if args[:2] == ("wiki", "+node-get"):
                    return {"data": {"obj_edit_time": "1", "updated_at": "1970-01-01T00:00:01Z"}}
                if args[:2] == ("sheets", "+workbook-info"):
                    return {"data": {"sheets": [{"sheet_id": "sheet-1", "title": "成员", "resource_type": "sheet"}]}}
                if args[:2] == ("sheets", "+csv-get"):
                    return {"data": {"annotated_csv": "姓名,岗位\n张三,后端\n", "has_more": False}}
                raise AssertionError(args)

            with mock.patch.object(sync, "walk_nodes", return_value=nodes), mock.patch.object(
                sync, "run_cli", side_effect=fake_run_cli
            ):
                result = sync.sync(self.sync_args(config))
            with mock.patch.object(sync, "walk_nodes", return_value=nodes), mock.patch.object(
                sync, "run_cli", side_effect=fake_run_cli
            ):
                incremental_result = sync.sync(self.sync_args(config))

            manifest = json.loads((output / "90_同步元数据" / "manifest.json").read_text(encoding="utf-8"))
            generated = (output / "10_knowledge-base" / "人员名单.md").read_text(encoding="utf-8")

        self.assertEqual(result, 0)
        self.assertEqual(incremental_result, 0)
        self.assertEqual(manifest["nodes"][0]["sync_status"], "ok")
        self.assertEqual(manifest["stats"]["sheets_mirrored"], 1)
        self.assertIn("| 姓名 | 岗位 |", generated)

    def test_enabled_bitable_node_is_mirrored_as_a_markdown_table(self) -> None:
        nodes = [
            {
                "node_token": "node-base",
                "obj_token": "base-1",
                "obj_type": "bitable",
                "title": "人员库",
                "parent_node_token": "",
                "depth": 0,
                "has_child": False,
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "docs"
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
                        "  bitables:",
                        "    enabled: true",
                        "    selections:",
                        '      - node_token: "node-base"',
                        '        table_id: "tbl-1"',
                        "        max_records: 20",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            def fake_run_cli(_config, *args):
                if args[:2] == ("wiki", "+node-get"):
                    return {"data": {"obj_edit_time": "1", "updated_at": "1970-01-01T00:00:01Z"}}
                if args[:2] == ("base", "+field-list"):
                    return {"data": {"items": [{"field_id": "fld-name", "field_name": "姓名"}]}}
                if args[:2] == ("base", "+record-list"):
                    return {"data": {"items": [{"record_id": "rec-1", "fields": {"fld-name": "张三"}}], "has_more": False}}
                raise AssertionError(args)

            with mock.patch.object(sync, "walk_nodes", return_value=nodes), mock.patch.object(
                sync, "run_cli", side_effect=fake_run_cli
            ):
                result = sync.sync(self.sync_args(config))
            with mock.patch.object(sync, "walk_nodes", return_value=nodes), mock.patch.object(
                sync, "run_cli", side_effect=fake_run_cli
            ):
                incremental_result = sync.sync(self.sync_args(config))

            manifest = json.loads((output / "90_同步元数据" / "manifest.json").read_text(encoding="utf-8"))
            generated = (output / "10_knowledge-base" / "人员库.md").read_text(encoding="utf-8")

        self.assertEqual(result, 0)
        self.assertEqual(incremental_result, 0)
        self.assertEqual(manifest["stats"]["bitables_mirrored"], 1)
        self.assertEqual(manifest["stats"]["bitable_tables_mirrored"], 1)
        self.assertIn("| 姓名 |", generated)

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

    def test_local_navigation_rewrites_document_links_and_sub_page_lists(self) -> None:
        content = (
            '<cite doc-id="node-child" title="子页面"></cite>\n\n'
            '[另一个页面](https://example.feishu.cn/wiki/node-other)\n\n'
            '<sub-page-list><sub-page doc-id="node-child" title="子页面"/>'
            '<sub-page wiki-token="node-other" title="另一个页面"/></sub-page-list>'
        )
        normalized = sync.normalize_content(
            content,
            "父页面",
            {"node-child": "child.md", "node-other": "../other.md"},
            render_sub_page_navigation=True,
            localize_document_links=True,
        )

        self.assertIn("[子页面](<child.md>)", normalized)
        self.assertIn("[另一个页面](<../other.md>)", normalized)
        self.assertIn("## 子页面导航", normalized)
        self.assertNotIn("<sub-page-list", normalized)

    def test_asset_identities_prefer_stable_media_tokens_over_signed_urls(self) -> None:
        first = "https://internal-api-drive-stream.feishu.cn/authcode?code=old"
        second = "https://internal-api-drive-stream.feishu.cn/authcode?code=new"
        content = (
            f'<img src="{first}" data-feishu-token="media-1">\n'
            f'<a href="{second}" data-feishu-attachment="true" data-feishu-token="media-1">飞书附件</a>'
        )

        identities = sync.asset_identities(content)

        self.assertEqual(identities[first], "feishu-token:media-1")
        self.assertEqual(identities[second], "feishu-token:media-1")

    def test_change_ledger_writes_bounded_diff_without_touching_the_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "docs"
            target = output / "10_knowledge-base" / "文档.md"
            target.parent.mkdir(parents=True)
            target.write_text("---\nnode_token: node-1\n---\n\n新正文\n", encoding="utf-8")
            changes = {
                "added": [],
                "modified": [
                    {
                        "node_token": "node-1",
                        "title": "文档",
                        "relative_path": "10_knowledge-base/文档.md",
                    }
                ],
                "moved": [],
                "deleted": [],
            }
            summary = sync.write_change_ledger(
                output,
                output / "90_同步元数据",
                "change-reports",
                changes,
                {"node-1": "---\nnode_token: node-1\n---\n\n旧正文\n"},
                "2026-07-17T13:47:33+00:00",
                20,
            )
            summary_text = summary.read_text(encoding="utf-8")
            detail_files = list(summary.parent.joinpath("details").glob("*.md"))
            detail_text = detail_files[0].read_text(encoding="utf-8")

        self.assertIn("Modified", summary_text)
        self.assertEqual(len(detail_files), 1)
        self.assertIn("-旧正文", detail_text)
        self.assertIn("+新正文", detail_text)

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
