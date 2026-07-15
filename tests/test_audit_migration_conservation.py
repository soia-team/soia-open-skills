#!/usr/bin/env python3
"""Regression tests for cross-root migration conservation audits."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts" / "audit_migration_conservation.py"
SPEC = importlib.util.spec_from_file_location("migration_conservation", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


SHA1 = "a" * 40


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def write_bundle(root: Path, initial: list[dict], finals: list[list[dict]], plan: list[dict], ledger: list[dict]) -> None:
    write_jsonl(root / "inventory/initial.jsonl", initial)
    for index, rows in enumerate(finals, 1):
        write_jsonl(root / f"verification/final-{index}.jsonl", rows)
    write_jsonl(root / "actions/10.plan.jsonl", plan)
    write_jsonl(root / "actions/10.result.jsonl", ledger)
    write_json(root / "run.json", {
        "files": {
            "initial_scan": "inventory/initial.jsonl",
            "final_scans": [f"verification/final-{index}.jsonl" for index in range(1, len(finals) + 1)],
        },
        "batches": [{"plan": "actions/10.plan.jsonl", "result": "actions/10.result.jsonl"}],
    })


class MigrationConservationTests(unittest.TestCase):
    def test_directory_package_can_move_cross_root_while_descendant_file_conserves(self) -> None:
        initial = [
            {"path": "/business", "name": "course", "id": "dir-1", "dir": True},
            {"path": "/business/course", "name": "lesson.pdf", "id": "file-1", "dir": False, "size": 12, "sha1": SHA1},
        ]
        final_business = []
        final_archive = [
            {"path": "/archive", "name": "course", "id": "dir-1", "dir": True},
            {"path": "/archive/course", "name": "lesson.pdf", "id": "file-1", "dir": False, "size": 12, "sha1": SHA1.upper()},
        ]
        plan = [{"action_id": "MV-1", "op": "mv", "from": "/business/course", "to": "/archive", "file_id": "dir-1", "reason": "approved whole package move"}]
        ledger = [{**plan[0], "status": "verified"}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [final_business, final_archive], plan, ledger)
            report = audit.audit_run(root)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["checked"]["final_scans"], 2)

    def test_reports_changed_file_fingerprint_and_unmatched_planned_path(self) -> None:
        initial = [{"path": "/business", "name": "one.pdf", "id": "file-1", "dir": False, "size": 12, "sha1": SHA1}]
        final = [{"path": "/archive", "name": "wrong.pdf", "id": "file-1", "dir": False, "size": 13, "sha1": "b" * 40}]
        plan = [{"action_id": "MV-1", "op": "mv", "from": "/business/one.pdf", "to": "/archive", "file_id": "file-1", "reason": "move"}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [final], plan, [{**plan[0], "status": "verified"}])
            report = audit.audit_run(root)
        self.assertEqual(
            {item["kind"] for item in report["violations"]},
            {"file_size_mismatch", "file_sha1_mismatch", "planned_final_path_mismatch"},
        )

    def test_reports_aggregate_duplicate_and_unapproved_missing_rows(self) -> None:
        initial = [
            {"path": "/business", "name": "one.pdf", "id": "file-1", "dir": False, "size": 1, "sha1": SHA1},
            {"path": "/business", "name": "two.pdf", "id": "file-2", "dir": False, "size": 1, "sha1": SHA1},
        ]
        final = [
            {"path": "/archive", "name": "one.pdf", "id": "file-1", "dir": False, "size": 1, "sha1": SHA1},
            {"path": "/archive", "name": "one-copy.pdf", "id": "file-1", "dir": False, "size": 1, "sha1": SHA1},
            {"path": "/archive", "name": "large", "id": "dir-2", "dir": True, "agg_files": 300, "agg_size": 9},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [final], [], [])
            report = audit.audit_run(root)
        self.assertEqual(
            {item["kind"] for item in report["violations"]},
            {"duplicate_physical_row", "aggregate_scan_row", "initial_entity_missing"},
        )

    def test_explicit_verified_delete_is_the_only_missing_authorization(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        plan = [{"action_id": "DEL-1", "op": "trash", "file_id": "dir-1", "allow_missing": True, "reason": "approved empty-shell removal"}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [[]], plan, [{**plan[0], "status": "verified"}])
            report = audit.audit_run(root)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["checked"]["authorized_missing"], 1)

    def test_verified_ledger_must_match_complete_operation_identity(self) -> None:
        initial = [{"path": "/business", "name": "one.pdf", "id": "file-1", "dir": False, "size": 1, "sha1": SHA1}]
        final = [{"path": "/archive", "name": "one.pdf", "id": "file-1", "dir": False, "size": 1, "sha1": SHA1}]
        plan = [{"action_id": "MV-1", "op": "mv", "from": "/business/one.pdf", "to": "/archive", "file_id": "file-1", "reason": "move"}]
        forged_result = {**plan[0], "file_id": "replacement-file-id", "status": "verified"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [final], plan, [forged_result])
            report = audit.audit_run(root)

        mismatches = [
            item for item in report["violations"]
            if item["kind"] == "verified_ledger_operation_identity_mismatch"
        ]
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["mismatches"], {
            "file_id": {"expected": "file-1", "actual": "replacement-file-id"},
        })

    def test_final_cli_returns_nonzero_for_violation_but_preview_does_not(self) -> None:
        initial = [{"path": "/business", "name": "one.pdf", "id": "file-1", "dir": False, "size": 1, "sha1": SHA1}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [[]], [], [])
            preview = subprocess.run([sys.executable, str(SCRIPT), "--run-dir", str(root)], capture_output=True, text=True)
            final = subprocess.run([sys.executable, str(SCRIPT), "--run-dir", str(root), "--final"], capture_output=True, text=True)
        self.assertEqual(preview.returncode, 0)
        self.assertEqual(final.returncode, 1)
        self.assertEqual(json.loads(final.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
