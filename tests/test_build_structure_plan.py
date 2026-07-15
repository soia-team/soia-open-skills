#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/soia-pkm-alipan-curator/scripts/build_structure_plan.py"
SPEC = importlib.util.spec_from_file_location("build_structure_plan", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class BuildStructurePlanTests(unittest.TestCase):
    def test_contract_and_batch_targets_are_depth_ordered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "actions").mkdir()
            (root / "actions/10.jsonl").write_text(
                json.dumps({"action_id": "A", "op": "mv", "from": "/old/a", "to": "/30_tech/20_backend"}) + "\n"
                + json.dumps({"action_id": "B", "op": "rename", "from": "/x/a", "to": "/60_digital/10_office/010_course"}) + "\n",
                encoding="utf-8",
            )
            contract = {
                "required_guides": [{"parent": "/30_tech", "guide_name": "01_start"}],
                "review_root": "/90_archive/10_review",
            }
            manifest = {"batches": [{"plan": "actions/10.jsonl"}]}
            actions = module.build_plan(contract, root, manifest, "S")

        paths = [action["to"] for action in actions]
        self.assertLess(paths.index("/30_tech"), paths.index("/30_tech/20_backend"))
        self.assertIn("/30_tech/01_start", paths)
        self.assertIn("/60_digital/10_office", paths)
        self.assertIn("/90_archive/10_review", paths)
        self.assertEqual(len({action["action_id"] for action in actions}), len(actions))
        self.assertTrue(module.within("/30_tech/a", "/30_tech"))
        self.assertFalse(module.within("/30_technology", "/30_tech"))

    def test_structure_batches_do_not_feed_stale_paths_back_into_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "actions").mkdir()
            (root / "actions/old-structure.jsonl").write_text(
                json.dumps({"action_id": "OLD", "op": "mkdir", "to": "/50_books/CHILD_stale"}) + "\n",
                encoding="utf-8",
            )
            (root / "actions/reclass.jsonl").write_text(
                json.dumps({"action_id": "NEW", "op": "mv", "from": "/old/a", "to": "/10_children/20_books"}) + "\n",
                encoding="utf-8",
            )
            manifest = {
                "batches": [
                    {"name": "structure-books", "kind": "structure", "plan": "actions/old-structure.jsonl"},
                    {"name": "books-to-children", "plan": "actions/reclass.jsonl"},
                ]
            }
            actions = module.build_plan({}, root, manifest, "S")

        paths = {action["to"] for action in actions}
        self.assertNotIn("/50_books/CHILD_stale", paths)
        self.assertIn("/10_children/20_books", paths)


if __name__ == "__main__":
    unittest.main()
