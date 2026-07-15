#!/usr/bin/env python3
"""Tests for the curator large-run bundle audit."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts" / "audit_run_bundle.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("curator_run_bundle", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def refresh_preflight_report(root: Path) -> None:
    manifest = audit.read_json(root / "run.json")
    manifest.setdefault("files", {})["preflight_report"] = "verification/preflight-reclass-01.json"
    write_json(root / "run.json", manifest)
    hashes = {"run.json": audit.preflight_gate.sha256_file(root / "run.json")}
    for plan in audit.preflight_gate.registered_plan_paths(manifest):
        hashes[plan] = audit.preflight_gate.sha256_file(root / plan)
    write_json(root / manifest["files"]["preflight_report"], {
        "schema_version": 1,
        "status": "passed",
        "hashes": hashes,
    })


def refresh_migration_conservation_report(root: Path) -> None:
    manifest = audit.read_json(root / "run.json")
    report_member = manifest["files"]["migration_conservation"]
    write_json(
        root / report_member,
        audit.audit_migration_conservation.audit_run(root),
    )


def make_valid_bundle(root: Path) -> None:
    scan = [{"path": "/learning", "name": "10_course", "id": "course-id", "dir": True}]
    write_jsonl(root / "inventory/initial.scan.jsonl", scan)
    (root / "inventory/initial.scan.jsonl.errors").write_text("", encoding="utf-8")
    write_jsonl(root / "analysis/content-audit.jsonl", [{
        "target_id": "course-id",
        "path": "/learning/10_course",
        "status": "reviewed",
        "evidence": [
            {"method": "listing", "source": "initial.scan.jsonl", "finding": "contains lessons"},
            {"method": "document-sample", "source": "lesson.pdf#p1", "finding": "grade-one phonics"},
        ],
        "recommendation": "keep and rename",
        "confidence": "high",
    }])
    write_json(root / "plans/structure-contract.json", {})
    write_jsonl(root / "verification/final.scan.jsonl", scan)
    (root / "verification/final.scan.jsonl.errors").write_text("", encoding="utf-8")
    write_json(root / "verification/structure-audit.json", {"status": "passed", "violations": []})
    write_json(root / "verification/ai-review.json", {
        "status": "passed",
        "checks": [
            {"name": name, "status": "passed", "evidence": "independently verified"}
            for name in sorted(audit.REQUIRED_AI_CHECKS)
        ],
        "unresolved": [],
    })
    (root / "handoff").mkdir(parents=True, exist_ok=True)
    (root / "handoff/receipt.md").write_text("completed\n", encoding="utf-8")
    plan = [{"action_id": "B10-001", "op": "mkdir", "to": "/learning/staging", "reason": "prepare"}]
    write_jsonl(root / "actions/10.plan.jsonl", plan)
    write_jsonl(root / "actions/10.result.jsonl", [{**plan[0], "status": "verified"}])
    write_json(root / "run.json", {
        "schema_version": 1,
        "run_id": "2026-01-01-learning-reorg",
        "status": "completed",
        "partition": {"path": "/learning"},
        "focus_targets": [{"id": "course-id", "path": "/learning/10_course", "min_evidence": 2}],
        "files": {
            "initial_scan": "inventory/initial.scan.jsonl",
            "initial_errors": "inventory/initial.scan.jsonl.errors",
            "content_audit": "analysis/content-audit.jsonl",
            "structure_contract": "plans/structure-contract.json",
            "final_scan": "verification/final.scan.jsonl",
            "final_errors": "verification/final.scan.jsonl.errors",
            "structure_audit": "verification/structure-audit.json",
            "ai_review": "verification/ai-review.json",
            "migration_conservation": "verification/migration-conservation.json",
            "receipt": "handoff/receipt.md",
        },
        "batches": [{"plan": "actions/10.plan.jsonl", "result": "actions/10.result.jsonl"}],
    })
    refresh_migration_conservation_report(root)


class RunBundleTests(unittest.TestCase):
    def test_valid_final_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            result = audit.audit_bundle(root, final=True)
            self.assertEqual(result["status"], "passed")

    def test_in_progress_bundle_validates_plans_without_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            make_valid_bundle(run_dir)
            manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            manifest["status"] = "in_progress"
            manifest["batches"] = [{
                "name": "planned",
                "plan": "actions/10.plan.jsonl",
                "result": "actions/10.result.jsonl",
            }]
            (run_dir / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
            write_jsonl(
                run_dir / "actions/10.plan.jsonl",
                [{"action_id": "A1", "op": "mkdir", "to": "/partition/new", "reason": "plan"}],
            )
            refresh_preflight_report(run_dir)
            result = audit.audit_bundle(run_dir, final=False)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["checked"]["planned_actions"], 1)
            self.assertEqual(result["checked"]["focus_targets"], 1)
            self.assertEqual(result["checked"]["preflight_gate"], "passed")

    def test_in_progress_audit_requires_registered_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            result = audit.audit_bundle(root, final=False)
        self.assertIn("preflight_report_not_registered", {item["kind"] for item in result["violations"]})

    def test_same_batch_duplicate_action_id_reports_plan_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "actions/10.plan.jsonl", [
                {"action_id": "B10-001", "op": "rename"},
                {"action_id": "B10-001", "op": "move"},
            ])
            result = audit.audit_bundle(root, final=False)

        duplicates = [item for item in result["violations"] if item["kind"] == "duplicate_plan_action_id"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(
            duplicates[0],
            {
                "kind": "duplicate_plan_action_id",
                "action_id": "B10-001",
                "batch": 0,
                "plan": "actions/10.plan.jsonl",
                "line": 2,
                "first_seen": {
                    "batch": 0,
                    "plan": "actions/10.plan.jsonl",
                    "line": 1,
                },
            },
        )

    def test_cross_batch_duplicate_action_id_reports_both_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            manifest = audit.read_json(root / "run.json")
            manifest["batches"].append({
                "name": "second",
                "plan": "actions/20.plan.jsonl",
                "result": "actions/20.result.jsonl",
            })
            write_json(root / "run.json", manifest)
            write_jsonl(root / "actions/20.plan.jsonl", [{"action_id": "B10-001", "op": "move"}])
            write_jsonl(root / "actions/20.result.jsonl", [{"action_id": "B10-001", "status": "verified"}])
            result = audit.audit_bundle(root, final=True)

        duplicates = [item for item in result["violations"] if item["kind"] == "duplicate_plan_action_id"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["action_id"], "B10-001")
        self.assertEqual(duplicates[0]["batch"], 1)
        self.assertEqual(duplicates[0]["plan"], "actions/20.plan.jsonl")
        self.assertEqual(duplicates[0]["line"], 1)
        self.assertEqual(duplicates[0]["first_seen"], {
            "batch": 0,
            "plan": "actions/10.plan.jsonl",
            "line": 1,
        })

    def test_different_action_ids_across_batches_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            manifest = audit.read_json(root / "run.json")
            manifest["batches"].append({
                "name": "second",
                "plan": "actions/20.plan.jsonl",
                "result": "actions/20.result.jsonl",
            })
            write_json(root / "run.json", manifest)
            second_plan = [{"action_id": "B20-001", "op": "move"}]
            write_jsonl(root / "actions/20.plan.jsonl", second_plan)
            write_jsonl(root / "actions/20.result.jsonl", [{**second_plan[0], "status": "verified"}])
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        self.assertEqual(result["status"], "passed")

    def test_unregistered_obsolete_plan_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "actions/obsolete.plan.jsonl", [{"action_id": "B10-001", "op": "move"}])
            result = audit.audit_bundle(root, final=True)

        self.assertEqual(result["status"], "passed")

    def test_missing_action_id_keeps_historical_violation_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "actions/10.plan.jsonl", [
                {"op": "rename"},
                {"action_id": "  ", "op": "move"},
            ])
            result = audit.audit_bundle(root, final=False)

        invalid = [
            item for item in result["violations"]
            if item["kind"] == "invalid_or_duplicate_plan_action_id"
        ]
        self.assertEqual(len(invalid), 2)
        self.assertEqual([(item["batch"], item["plan"], item["line"]) for item in invalid], [
            (0, "actions/10.plan.jsonl", 1),
            (0, "actions/10.plan.jsonl", 2),
        ])

    def test_missing_focus_content_audit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "analysis/content-audit.jsonl", [{
                "target_id": "other-id",
                "status": "reviewed",
                "evidence": [{"method": "listing", "source": "scan", "finding": "other"}],
                "recommendation": "keep",
                "confidence": "high",
            }])
            result = audit.audit_bundle(root, final=True)
        self.assertIn("focus_target_not_content_audited", {item["kind"] for item in result["violations"]})

    def test_absolute_member_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            manifest = audit.read_json(root / "run.json")
            manifest["files"]["content_audit"] = "/tmp/audit.jsonl"
            write_json(root / "run.json", manifest)
            result = audit.audit_bundle(root, final=True)
        self.assertIn("invalid_run_file_path", {item["kind"] for item in result["violations"]})

    def test_nonempty_scan_error_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            (root / "verification/final.scan.jsonl.errors").write_text("LIST_FAIL /course\n", encoding="utf-8")
            result = audit.audit_bundle(root, final=True)
        self.assertIn("scan_errors_present", {item["kind"] for item in result["violations"]})

    def test_unclosed_action_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "actions/10.result.jsonl", [{"action_id": "B10-001", "status": "failed"}])
            result = audit.audit_bundle(root, final=True)
        self.assertIn("action_not_closed", {item["kind"] for item in result["violations"]})

    def test_verified_ledger_identity_mismatch_cannot_close_final_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            plan = [{"action_id": "B10-001", "op": "mkdir", "to": "/learning/staging", "reason": "prepare"}]
            write_jsonl(root / "actions/10.plan.jsonl", plan)
            write_jsonl(root / "actions/10.result.jsonl", [{
                **plan[0],
                "op": "rename",
                "status": "verified",
            }])
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        mismatches = [
            item for item in result["violations"]
            if item["kind"] == "verified_ledger_operation_identity_mismatch"
        ]
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["mismatches"], {
            "op": {"expected": "mkdir", "actual": "rename"},
        })

    def test_final_bundle_requires_registered_migration_conservation_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            manifest = audit.read_json(root / "run.json")
            manifest["files"].pop("migration_conservation")
            write_json(root / "run.json", manifest)
            result = audit.audit_bundle(root, final=True)

        self.assertIn(
            "migration_conservation_report_not_registered",
            {item["kind"] for item in result["violations"]},
        )

    def test_final_bundle_rejects_failed_or_stale_migration_conservation_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            report_path = root / "verification/migration-conservation.json"
            report = audit.read_json(report_path)
            report["status"] = "failed"
            write_json(report_path, report)
            failed = audit.audit_bundle(root, final=True)

            report = audit.read_json(report_path)
            report["status"] = "passed"
            report["hashes"]["run.json"] = "0" * 64
            write_json(report_path, report)
            stale = audit.audit_bundle(root, final=True)

        self.assertIn(
            "migration_conservation_report_not_passed",
            {item["kind"] for item in failed["violations"]},
        )
        self.assertIn(
            "migration_conservation_report_hash_mismatch",
            {item["kind"] for item in stale["violations"]},
        )

    def test_ai_review_requires_evidence_and_no_unresolved_items(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_json(root / "verification/ai-review.json", {
                "status": "passed",
                "checks": [{"name": "coverage", "status": "passed", "evidence": ""}],
                "unresolved": ["one missing course"],
            })
            result = audit.audit_bundle(root, final=True)
        kinds = {item["kind"] for item in result["violations"]}
        self.assertIn("ai_review_check_incomplete", kinds)
        self.assertIn("ai_review_has_unresolved_items", kinds)

    def test_ai_review_requires_named_semantic_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_json(root / "verification/ai-review.json", {
                "status": "passed",
                "checks": [{"name": "focus-target-coverage", "status": "passed", "evidence": "1/1"}],
                "unresolved": [],
            })
            result = audit.audit_bundle(root, final=True)
        self.assertIn("ai_review_required_checks_missing", {item["kind"] for item in result["violations"]})

    def test_content_audit_requires_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            rows = audit.read_jsonl(root / "analysis/content-audit.jsonl")
            rows[0].pop("confidence")
            write_jsonl(root / "analysis/content-audit.jsonl", rows)
            result = audit.audit_bundle(root, final=True)
        self.assertIn("content_confidence_missing_or_invalid", {item["kind"] for item in result["violations"]})

    def test_cli_returns_nonzero_for_incomplete_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            (root / "handoff/receipt.md").write_text("", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "--run-dir", str(root), "--final"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(process.returncode, 1)
        self.assertIn("receipt_empty", process.stdout)


if __name__ == "__main__":
    unittest.main()
