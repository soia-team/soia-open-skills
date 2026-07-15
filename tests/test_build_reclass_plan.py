#!/usr/bin/env python3
"""Tests for deterministic TSV-to-plan generation."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts" / "build_reclass_plan.py"
SPEC = importlib.util.spec_from_file_location("build_reclass_plan", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
planner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


class BuildReclassPlanTests(unittest.TestCase):
    def args(self, root: Path) -> Namespace:
        return Namespace(
            input=root / "map.tsv",
            output=root / "plan.jsonl",
            inventory=root / "scan.jsonl",
            source_base="/old",
            source_from_inventory=False,
            target_base="/new",
            include_target_prefix=[],
            source_path_column="source_path",
            source_name_column="source_name",
            source_group_column="source_group",
            target_column="target",
            name_column="final_name",
            id_column="file_id",
            skip_target_regex=r"^<",
            action_prefix="T10",
            no_mkdir=False,
        )

    def test_builds_mkdir_move_and_rename_with_inventory_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "map.tsv").write_text(
                "file_id\tsource_name\tsource_group\ttarget\tfinal_name\n"
                "id-1\tCourse A\tGroup\tCategory\t010_Course A\n",
                encoding="utf-8",
            )
            (root / "scan.jsonl").write_text(
                json.dumps({"path": "/old/Group", "name": "Course A", "id": "id-1"}) + "\n",
                encoding="utf-8",
            )
            actions, summary = planner.build_plan(self.args(root))

        self.assertEqual([item["op"] for item in actions], ["mkdir", "mv", "rename"])
        self.assertEqual(actions[0]["to"], "/new/Category")
        self.assertEqual(actions[1]["from"], "/old/Group/Course A")
        self.assertEqual(actions[2]["to"], "/new/Category/010_Course A")
        self.assertEqual(summary["selected_items"], 1)

    def test_no_mkdir_keeps_move_and_rename_actions_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "map.tsv").write_text(
                "file_id\tsource_name\tsource_group\ttarget\tfinal_name\n"
                "id-1\tCourse A\tGroup\tCategory\t010_Course A\n",
                encoding="utf-8",
            )
            (root / "scan.jsonl").write_text(
                json.dumps({"path": "/old/Group", "name": "Course A", "id": "id-1"}) + "\n",
                encoding="utf-8",
            )
            args = self.args(root)
            default_actions, _ = planner.build_plan(args)
            args.no_mkdir = True
            actions, summary = planner.build_plan(args)

        self.assertEqual([item["op"] for item in actions], ["mv", "rename"])
        self.assertEqual(
            actions,
            [item for item in default_actions if item["op"] in {"mv", "rename"}],
        )
        self.assertEqual(summary["mkdir_actions"], 0)
        self.assertEqual(summary["move_actions"], 1)
        self.assertEqual(summary["rename_actions"], 1)

    def test_skips_split_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "map.tsv").write_text(
                "file_id\tsource_name\tsource_group\ttarget\tfinal_name\n"
                "id-1\tShell\t\t<split-by-child>\tShell\n",
                encoding="utf-8",
            )
            args = self.args(root)
            args.inventory = None
            actions, summary = planner.build_plan(args)

        self.assertEqual(actions, [])
        self.assertEqual(summary["selected_items"], 0)

    def test_rejects_inventory_source_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "map.tsv").write_text(
                "file_id\tsource_name\tsource_group\ttarget\tfinal_name\n"
                "id-1\tCourse A\tGroup\tCategory\tCourse A\n",
                encoding="utf-8",
            )
            (root / "scan.jsonl").write_text(
                json.dumps({"path": "/elsewhere", "name": "Course A", "id": "id-1"}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source mismatch"):
                planner.build_plan(self.args(root))

    def test_can_derive_source_path_from_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "map.tsv").write_text(
                "file_id\tsource_name\ttarget\tfinal_name\n"
                "id-1\tCourse A\tCategory\t010_Course A\n",
                encoding="utf-8",
            )
            (root / "scan.jsonl").write_text(
                json.dumps({"path": "/old/unknown-branch", "name": "Course A", "id": "id-1"}) + "\n",
                encoding="utf-8",
            )
            args = self.args(root)
            args.source_from_inventory = True
            actions, _ = planner.build_plan(args)

        self.assertEqual(actions[1]["from"], "/old/unknown-branch/Course A")

    def test_can_filter_target_partition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "map.tsv").write_text(
                "file_id\tsource_name\ttarget\tfinal_name\n"
                "id-1\tCourse A\t/keep/category\tCourse A\n"
                "id-2\tCourse B\t/skip/category\tCourse B\n",
                encoding="utf-8",
            )
            args = self.args(root)
            args.inventory = None
            args.source_from_inventory = False
            args.include_target_prefix = ["/keep"]
            actions, summary = planner.build_plan(args)

        self.assertEqual(summary["selected_items"], 1)
        self.assertTrue(all("/skip" not in json.dumps(action) for action in actions))


if __name__ == "__main__":
    unittest.main()
