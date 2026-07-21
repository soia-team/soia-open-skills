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
    / "processon_inventory_state.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("processon_inventory_state", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ProcessOnInventoryStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_batch_persists_discovered_visited_pending_and_files(self) -> None:
        state = self.module.new_state(
            root_path="解决方案后端组",
            source_url="https://www.processon.com/org/teams/example",
            now="2026-07-21T00:00:00+00:00",
        )
        self.module.apply_batch(
            state,
            {
                "directories": [
                    {
                        "path": "解决方案后端组",
                        "folders": ["01_系统架构", "04_移动互联"],
                        "files": [
                            {"title": "后端组汇总", "type": "mindmap"},
                            {"title": "柜面状态流转", "type": "flowchart"},
                        ],
                    },
                    {
                        "path": "解决方案后端组/01_系统架构",
                        "folders": ["规范"],
                        "files": [{"title": "部署图", "type": "flowchart"}],
                    },
                ]
            },
            now="2026-07-21T00:01:00+00:00",
        )

        summary = self.module.state_summary(state)
        self.assertEqual(summary["discovered_count"], 4)
        self.assertEqual(summary["visited_count"], 2)
        self.assertEqual(summary["pending_count"], 2)
        self.assertEqual(summary["file_entry_count"], 3)
        self.assertEqual(
            summary["pending_paths"],
            [
                "解决方案后端组/01_系统架构/规范",
                "解决方案后端组/04_移动互联",
            ],
        )

    def test_record_is_idempotent_and_resume_clears_pending(self) -> None:
        state = self.module.new_state(
            root_path="root", source_url="https://example.test", now="t0"
        )
        batch = {
            "directories": [
                {
                    "path": "root",
                    "folders": ["child"],
                    "files": [{"title": "A"}, {"title": "A"}],
                }
            ]
        }
        self.module.apply_batch(state, batch, now="t1")
        self.module.apply_batch(state, batch, now="t2")
        self.assertEqual(self.module.state_summary(state)["file_entry_count"], 1)
        self.module.apply_batch(
            state,
            {"directories": [{"path": "root/child", "folders": [], "files": []}]},
            now="t3",
        )
        self.assertEqual(self.module.state_summary(state)["pending_count"], 0)

    def test_blocked_path_is_not_returned_as_actionable_pending(self) -> None:
        state = self.module.new_state(
            root_path="root", source_url="https://example.test", now="t0"
        )
        self.module.apply_batch(
            state,
            {
                "directories": [{"path": "root", "folders": ["restricted"]}],
                "blocked": [
                    {"path": "root/restricted", "reason": "permission_denied"}
                ],
            },
            now="t1",
        )
        summary = self.module.state_summary(state)
        self.assertEqual(summary["pending_count"], 0)
        self.assertEqual(summary["blocked_count"], 1)

    def test_atomic_round_trip_and_symlink_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_file = root / "inventory.json"
            state = self.module.new_state(
                root_path="root", source_url="https://example.test", now="t0"
            )
            self.module.atomic_write_json(state_file, state)
            self.assertEqual(self.module.load_state(state_file), state)
            self.assertEqual(state_file.stat().st_mode & 0o777, 0o600)

            target = root / "target.json"
            target.write_text(json.dumps(state), encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(target)
            with self.assertRaises(self.module.InventoryStateError):
                self.module.load_state(link)
            with self.assertRaises(self.module.InventoryStateError):
                self.module.atomic_write_json(link, state)

    def test_run_bundle_archives_batches_and_resumes_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "runs" / "processon-test"
            state, run = self.module.initialize_run_bundle(
                run_dir,
                root_path="解决方案后端组",
                source_url="https://www.processon.com/org/teams/example",
                now="2026-07-21T00:00:00+00:00",
            )
            self.assertEqual(run["status"], "inventory_running")
            self.assertEqual((run_dir / "inventory").stat().st_mode & 0o777, 0o700)
            self.assertTrue((run_dir / "handoff").is_dir())
            self.assertTrue((run_dir / "verification").is_dir())
            batch = {
                "directories": [
                    {
                        "path": "解决方案后端组",
                        "folders": ["01_系统架构"],
                        "files": [{"title": "总览", "type": "mindmap"}],
                    }
                ]
            }
            state, already_applied, archived = self.module.record_run_batch(
                run_dir, batch, now="2026-07-21T00:01:00+00:00"
            )
            self.assertFalse(already_applied)
            self.assertTrue(archived.is_file())
            self.assertEqual(self.module.state_summary(state)["applied_batch_count"], 1)

            state, already_applied, archived_again = self.module.record_run_batch(
                run_dir, batch, now="2026-07-21T00:02:00+00:00"
            )
            self.assertTrue(already_applied)
            self.assertEqual(archived_again, archived)
            self.assertEqual(self.module.state_summary(state)["applied_batch_count"], 1)
            recorded_run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(recorded_run["counts"]["pending_count"], 1)
            self.assertEqual(len(recorded_run["batches"]), 1)
            self.assertEqual(
                recorded_run["batches"][0]["path"],
                str(archived.relative_to(run_dir)),
            )
            self.assertEqual(recorded_run["files"]["progress"], "handoff/progress.md")
            self.assertEqual(recorded_run["files"]["receipt"], "handoff/receipt.md")

            recorded_run["files"].pop("progress")
            recorded_run["files"].pop("receipt")
            recorded_run.pop("execution_chain")
            self.module.atomic_write_json(run_dir / "run.json", recorded_run)
            migrated = self.module.update_run_metadata(run_dir, state)
            self.assertEqual(migrated["files"]["progress"], "handoff/progress.md")
            self.assertEqual(migrated["files"]["receipt"], "handoff/receipt.md")
            self.assertEqual(migrated["execution_chain"][0], "inventory-init")

    def test_default_state_root_follows_xdg(self) -> None:
        root = self.module.default_state_root(
            environ={"XDG_STATE_HOME": "/tmp/custom-state"}, home=Path("/unused")
        )
        self.assertEqual(
            root,
            Path("/tmp/custom-state/soia-cwork-processon-diagrams").resolve(
                strict=False
            ),
        )

    def test_progress_and_final_audit_create_completion_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "runs" / "complete-test"
            self.module.initialize_run_bundle(
                run_dir,
                root_path="root",
                source_url="https://example.test",
                now="2026-07-21T00:00:00+00:00",
            )
            progress = run_dir / "handoff" / "progress.md"
            self.assertTrue(progress.is_file())
            self.assertIn("pending: 1", progress.read_text(encoding="utf-8"))

            self.module.record_run_batch(
                run_dir,
                {
                    "directories": [
                        {"path": "root", "folders": [], "files": [{"title": "A"}]}
                    ]
                },
                now="2026-07-21T00:01:00+00:00",
            )
            before_audit = json.loads(
                (run_dir / "run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(before_audit["status"], "inventory_ready_for_audit")
            self.assertFalse((run_dir / "handoff" / "receipt.md").exists())

            report, completed_run = self.module.audit_run_bundle(
                run_dir, now="2026-07-21T00:02:00+00:00"
            )
            self.assertEqual(report["status"], "passed")
            self.assertTrue(report["complete_eligible"])
            self.assertIsNotNone(completed_run)
            self.assertEqual(completed_run["status"], "completed")
            self.assertTrue((run_dir / "handoff" / "receipt.md").is_file())
            self.assertTrue(
                (run_dir / completed_run["files"]["inventory_audit"]).is_file()
            )

    def test_midrun_audit_passes_without_claiming_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "runs" / "partial-test"
            self.module.initialize_run_bundle(
                run_dir,
                root_path="root",
                source_url="https://example.test",
                now="2026-07-21T00:00:00+00:00",
            )
            self.module.record_run_batch(
                run_dir,
                {"directories": [{"path": "root", "folders": ["child"]}]},
                now="2026-07-21T00:01:00+00:00",
            )
            report, audited_run = self.module.audit_run_bundle(
                run_dir, now="2026-07-21T00:02:00+00:00"
            )
            self.assertEqual(report["status"], "passed")
            self.assertFalse(report["complete_eligible"])
            self.assertEqual(audited_run["status"], "inventory_running")
            self.assertFalse((run_dir / "handoff" / "receipt.md").exists())

    def test_audit_detects_tampered_batch_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "runs" / "tamper-test"
            self.module.initialize_run_bundle(
                run_dir,
                root_path="root",
                source_url="https://example.test",
                now="2026-07-21T00:00:00+00:00",
            )
            _, _, archived = self.module.record_run_batch(
                run_dir,
                {"directories": [{"path": "root", "folders": []}]},
                now="2026-07-21T00:01:00+00:00",
            )
            tampered = json.loads(archived.read_text(encoding="utf-8"))
            tampered["directories"][0]["files"] = [{"title": "injected"}]
            archived.write_text(json.dumps(tampered), encoding="utf-8")

            report, audited_run = self.module.audit_run_bundle(
                run_dir, now="2026-07-21T00:02:00+00:00"
            )
            self.assertEqual(report["status"], "failed")
            self.assertFalse(report["complete_eligible"])
            self.assertTrue(
                any("SHA-256 mismatch" in item for item in report["violations"])
            )
            self.assertEqual(audited_run["status"], "inventory_audit_failed")
            self.assertFalse((run_dir / "handoff" / "receipt.md").exists())

    def test_audit_rejects_symlink_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "runs" / "symlink-test"
            self.module.initialize_run_bundle(
                run_dir,
                root_path="root",
                source_url="https://example.test",
                now="2026-07-21T00:00:00+00:00",
            )
            _, _, archived = self.module.record_run_batch(
                run_dir,
                {"directories": [{"path": "root", "folders": []}]},
                now="2026-07-21T00:01:00+00:00",
            )
            outside = Path(temporary) / "outside.json"
            outside.write_bytes(archived.read_bytes())
            archived.unlink()
            archived.symlink_to(outside)

            report, audited_run = self.module.audit_run_bundle(
                run_dir, now="2026-07-21T00:02:00+00:00"
            )
            self.assertEqual(report["status"], "failed")
            self.assertTrue(
                any("refusing symlink" in item for item in report["violations"])
            )
            self.assertEqual(audited_run["status"], "inventory_audit_failed")

    def test_audit_malformed_run_files_fails_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "runs" / "malformed-run-test"
            self.module.initialize_run_bundle(
                run_dir,
                root_path="root",
                source_url="https://example.test",
                now="2026-07-21T00:00:00+00:00",
            )
            run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            run["files"] = "invalid"
            self.module.atomic_write_json(run_dir / "run.json", run)

            report, audited_run = self.module.audit_run_bundle(
                run_dir, now="2026-07-21T00:01:00+00:00"
            )
            self.assertEqual(report["status"], "failed")
            self.assertIn("run.json files must be an object", report["violations"])
            self.assertEqual(audited_run["status"], "inventory_audit_failed")


if __name__ == "__main__":
    unittest.main()
