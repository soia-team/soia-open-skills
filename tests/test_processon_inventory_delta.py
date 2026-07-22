from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "skills"
    / "soia-cwork-processon-diagrams"
    / "scripts"
    / "diff_processon_inventory.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("processon_inventory_delta", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def checkpoint(files: list[dict], *, complete: bool = True) -> dict:
    return {
        "schema_version": 1,
        "source": "processon",
        "source_url": "https://www.processon.com/org/teams/example",
        "root_path": "team",
        "discovered_paths": ["team"] if complete else ["team", "team/pending"],
        "visited_paths": ["team"],
        "blocked_paths": {},
        "directories": {"team": {"files": files}},
    }


class ProcessOnInventoryDeltaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_compare_reports_add_update_move_rename_and_removal_candidate(self) -> None:
        previous = checkpoint(
            [
                {"title": "old-name", "type": "flowchart", "remote_id": "one", "remote_updated_at": "t1"},
                {"title": "removed", "type": "mindmap", "remote_id": "two"},
                {"title": "fallback", "type": "flowchart", "owner": "a"},
            ]
        )
        current = checkpoint(
            [
                {"title": "new-name", "type": "flowchart", "remote_id": "one", "remote_updated_at": "t2"},
                {"title": "added", "type": "mindmap", "remote_id": "three"},
            ]
        )
        current["directories"] = {
            "team": {"files": current["directories"]["team"]["files"][1:]},
            "team/new-folder": {"files": [current["directories"]["team"]["files"][0]]},
        }
        current["discovered_paths"].append("team/new-folder")
        current["visited_paths"].append("team/new-folder")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous_path = root / "previous.json"
            current_path = root / "current.json"
            previous_path.write_text(json.dumps(previous), encoding="utf-8")
            current_path.write_text(json.dumps(current), encoding="utf-8")
            report = self.module.compare_checkpoints(
                previous_path,
                self.module.load_object(previous_path, "previous"),
                current_path,
                self.module.load_object(current_path, "current"),
            )

        self.assertEqual(report["counts"], {
            "previous_total": 3,
            "current_total": 2,
            "previous_tracked": 3,
            "current_tracked": 2,
            "previous_ambiguous": 0,
            "current_ambiguous": 0,
            "added": 1,
            "changed": 1,
            "moved": 1,
            "renamed": 1,
            "updated": 1,
            "removed_candidates": 2,
            "unchanged": 0,
        })
        self.assertEqual(report["changed"][0]["change_kinds"], ["moved", "renamed", "updated"])
        self.assertEqual({item["title"] for item in report["removed_candidates"]}, {"removed", "fallback"})

    def test_compare_refuses_incomplete_snapshot_before_reporting_removals(self) -> None:
        complete = checkpoint([{"title": "A", "type": "flowchart", "remote_id": "one"}])
        incomplete = checkpoint([], complete=False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous_path = root / "previous.json"
            current_path = root / "current.json"
            previous_path.write_text(json.dumps(complete), encoding="utf-8")
            current_path.write_text(json.dumps(incomplete), encoding="utf-8")
            with self.assertRaisesRegex(self.module.InventoryDeltaError, "current checkpoint is incomplete"):
                self.module.compare_checkpoints(
                    previous_path,
                    self.module.load_object(previous_path, "previous"),
                    current_path,
                    self.module.load_object(current_path, "current"),
                )

    def test_compare_refuses_duplicate_stable_remote_identity(self) -> None:
        duplicated = checkpoint(
            [
                {"title": "A", "type": "flowchart", "remote_id": "duplicate"},
                {"title": "B", "type": "mindmap", "remote_id": "duplicate"},
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous_path = root / "previous.json"
            current_path = root / "current.json"
            previous_path.write_text(json.dumps(duplicated), encoding="utf-8")
            current_path.write_text(json.dumps(duplicated), encoding="utf-8")
            with self.assertRaisesRegex(self.module.InventoryDeltaError, "duplicate stable remote identity"):
                self.module.compare_checkpoints(
                    previous_path,
                    self.module.load_object(previous_path, "previous"),
                    current_path,
                    self.module.load_object(current_path, "current"),
                )

    def test_compare_isolates_ambiguous_fallback_entries(self) -> None:
        duplicated = checkpoint(
            [
                {"title": "A", "type": "flowchart", "owner": "same"},
                {"title": "A", "type": "flowchart", "owner": "same"},
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous_path = root / "previous.json"
            current_path = root / "current.json"
            previous_path.write_text(json.dumps(duplicated), encoding="utf-8")
            current_path.write_text(json.dumps(duplicated), encoding="utf-8")
            report = self.module.compare_checkpoints(
                previous_path,
                self.module.load_object(previous_path, "previous"),
                current_path,
                self.module.load_object(current_path, "current"),
            )

        self.assertEqual(report["status"], "complete_with_ambiguous_entries")
        self.assertEqual(report["counts"]["previous_ambiguous"], 2)
        self.assertEqual(report["counts"]["current_ambiguous"], 2)
        self.assertEqual(report["counts"]["changed"], 0)


if __name__ == "__main__":
    unittest.main()
