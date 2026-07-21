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
    / "build_processon_archive_plan.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("processon_archive_plan", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def checkpoint() -> dict:
    return {
        "schema_version": 1,
        "source": "processon",
        "source_url": "https://www.processon.com/org/teams/example",
        "root_path": "team",
        "discovered_paths": ["team", "team/architecture"],
        "visited_paths": ["team", "team/architecture"],
        "blocked_paths": {},
        "directories": {
            "team": {
                "files": [
                    {
                        "title": "overview",
                        "type": "mindmap",
                        "owner": "owner-a",
                        "remote_updated_at": "today",
                    },
                    {"title": "unknown-diagram", "type": "unknown"},
                ]
            },
            "team/architecture": {
                "files": [
                    {"title": "deployment", "type": "flowchart", "remote_id": "diagram-1"},
                    {"title": "duplicate", "type": "flowchart", "remote_id": "diagram-2"},
                    {"title": "duplicate", "type": "flowchart", "remote_id": "diagram-3"},
                ]
            },
        },
    }


class ProcessOnArchivePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_plan_separates_known_exports_from_unknown_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint_path = Path(temporary) / "checkpoint.json"
            checkpoint_path.write_text(json.dumps(checkpoint()), encoding="utf-8")

            plan = self.module.build_plan(
                checkpoint_path, self.module.load_object(checkpoint_path, "checkpoint")
            )

        self.assertEqual(plan["archive_status"], "known_ready_pending_confirmation")
        self.assertTrue(plan["ready_for_known_artifacts"])
        self.assertFalse(plan["ready_for_archive"])
        self.assertEqual(plan["counts"], {
            "total": 5,
            "flowchart": 3,
            "mindmap": 1,
            "unknown": 1,
            "pending_confirmation": 1,
        })
        self.assertEqual(plan["collision_risk_count"], 2)
        flowchart = next(item for item in plan["entries"] if item["title"] == "deployment")
        unknown = next(item for item in plan["entries"] if item["title"] == "unknown-diagram")
        self.assertEqual(flowchart["primary_format"], "vsdx")
        self.assertEqual(flowchart["fallback_formats"], ["pos"])
        self.assertEqual(unknown["status"], "pending_confirmation")
        self.assertIsNone(unknown["primary_format"])

    def test_verify_rejects_changed_checkpoint_or_plan_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint_path = root / "checkpoint.json"
            plan_path = root / "archive-plan.json"
            checkpoint_path.write_text(json.dumps(checkpoint()), encoding="utf-8")
            plan = self.module.build_plan(
                checkpoint_path, self.module.load_object(checkpoint_path, "checkpoint")
            )
            self.module.atomic_write_json(plan_path, plan)
            self.assertEqual(
                self.module.verify_plan(plan_path, checkpoint_path)["status"], "passed"
            )

            tampered_plan = json.loads(plan_path.read_text(encoding="utf-8"))
            tampered_plan["entries"][0]["primary_format"] = "png"
            self.module.atomic_write_json(plan_path, tampered_plan)
            plan_result = self.module.verify_plan(plan_path, checkpoint_path)
            self.assertEqual(plan_result["status"], "failed")
            self.assertFalse(plan_result["entry_content_match"])

            self.module.atomic_write_json(plan_path, plan)
            changed_checkpoint = checkpoint()
            changed_checkpoint["updated_at"] = "changed"
            checkpoint_path.write_text(json.dumps(changed_checkpoint), encoding="utf-8")
            checkpoint_result = self.module.verify_plan(plan_path, checkpoint_path)
            self.assertEqual(checkpoint_result["status"], "failed")
            self.assertNotEqual(
                checkpoint_result["plan_checkpoint_sha256"],
                checkpoint_result["current_checkpoint_sha256"],
            )

    def test_plan_rejects_unsafe_inventory_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint_path = Path(temporary) / "checkpoint.json"
            unsafe = checkpoint()
            unsafe["discovered_paths"].append("team/../outside")
            checkpoint_path.write_text(json.dumps(unsafe), encoding="utf-8")
            with self.assertRaises(self.module.PlanError):
                self.module.build_plan(
                    checkpoint_path,
                    self.module.load_object(checkpoint_path, "checkpoint"),
                )


if __name__ == "__main__":
    unittest.main()
