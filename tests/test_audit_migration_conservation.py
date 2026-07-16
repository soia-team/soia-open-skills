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


def write_bundle(
    root: Path,
    initial: list[dict],
    finals: list[list[dict]],
    plan: list[dict],
    ledger: list[dict],
    *,
    cleanup_plan: list[dict] | None = None,
    cleanup_ledger: list[dict] | None = None,
    cleanup_authorizations: list[dict] | None = None,
) -> None:
    write_jsonl(root / "inventory/initial.jsonl", initial)
    for index, rows in enumerate(finals, 1):
        write_jsonl(root / f"verification/final-{index}.jsonl", rows)
    write_jsonl(root / "actions/10.plan.jsonl", plan)
    write_jsonl(root / "actions/10.result.jsonl", ledger)
    manifest = {
        "files": {
            "initial_scan": "inventory/initial.jsonl",
            "final_scans": [f"verification/final-{index}.jsonl" for index in range(1, len(finals) + 1)],
        },
        "batches": [{"plan": "actions/10.plan.jsonl", "result": "actions/10.result.jsonl"}],
    }
    if cleanup_plan is not None or cleanup_ledger is not None:
        if cleanup_plan is None or cleanup_ledger is None:
            raise ValueError("cleanup plan and ledger must be supplied together")
        write_jsonl(root / "actions/cleanup.plan.jsonl", cleanup_plan)
        write_jsonl(root / "actions/cleanup.result.jsonl", cleanup_ledger)
        if cleanup_authorizations is None:
            cleanup_authorizations = [cleanup_authorization(action) for action in cleanup_plan]
        write_jsonl(root / "actions/cleanup.authorizations.jsonl", cleanup_authorizations)
        manifest["files"]["cleanup_authorizations"] = "actions/cleanup.authorizations.jsonl"
        manifest["cleanup_batches"] = [{
            "plan": "actions/cleanup.plan.jsonl",
            "result": "actions/cleanup.result.jsonl",
        }]
    write_json(root / "run.json", manifest)


def verified_cleanup_result(action: dict, **overrides: object) -> dict:
    result = {
        **action,
        "status": "verified",
        "ts": "2026-07-16T12:00:00+08:00",
        "verify": {
            "predelete": {"files": 0, "dirs": 0},
            "recycle_bin_status": "removed_to_recycle_bin_verified",
            "postdelete_absence_verified": True,
        },
    }
    result.update(overrides)
    return result


def cleanup_action(**overrides: object) -> dict:
    action = {
        "action_id": "CLEAN-1",
        "op": "trash",
        "from": "/business/empty",
        "file_id": "dir-1",
        "allow_missing": True,
        "reason": "approved empty-shell removal",
        "authorization_ref": "approval-2026-07-16",
    }
    action.update(overrides)
    return action


def cleanup_authorization(action: dict, **overrides: object) -> dict:
    authorization = {
        field: action.get(field)
        for field in ("authorization_ref", "action_id", "file_id", "from")
    }
    authorization.update({
        "decision": "approved",
        "authorized_at": "2026-07-16T11:59:00+08:00",
    })
    authorization.update(overrides)
    return authorization


class MigrationConservationTests(unittest.TestCase):
    def test_cleanup_result_canonical_alias_variants_are_rejected(self) -> None:
        aliases = [
            "actions/./cleanup.plan.jsonl",
            "actions/temporary/../cleanup.plan.jsonl",
            "actions//cleanup.plan.jsonl",
        ]
        for alias in aliases:
            with self.subTest(alias=alias):
                manifest = {
                    "files": {"initial_scan": "inventory/initial.jsonl"},
                    "batches": [],
                    "cleanup_batches": [{
                        "plan": "actions/cleanup.plan.jsonl",
                        "result": alias,
                    }],
                }
                with self.assertRaisesRegex(ValueError, "must not alias immutable/input member"):
                    audit.validate_cleanup_result_paths(manifest)

    def test_cleanup_result_path_rejects_run_directory_escape(self) -> None:
        manifest = {
            "files": {"initial_scan": "inventory/initial.jsonl"},
            "batches": [],
            "cleanup_batches": [{
                "plan": "actions/cleanup.plan.jsonl",
                "result": "actions/../../outside.result.jsonl",
            }],
        }
        with self.assertRaisesRegex(ValueError, "must stay inside the run directory"):
            audit.validate_cleanup_result_paths(manifest)

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

    def test_explicit_verified_cleanup_delete_is_the_only_missing_authorization(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        plan = [cleanup_action(action_id="DEL-1")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(
                root,
                initial,
                [[]],
                [],
                [],
                cleanup_plan=plan,
                cleanup_ledger=[verified_cleanup_result(plan[0])],
            )
            report = audit.audit_run(root)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["checked"]["authorized_missing"], 1)

    def test_final_cleanup_conservation_hashes_the_append_only_result_ledger(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        cleanup = [cleanup_action()]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(
                root,
                initial,
                [[]],
                [],
                [],
                cleanup_plan=cleanup,
                cleanup_ledger=[verified_cleanup_result(cleanup[0])],
            )
            report = audit.audit_run(root)

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["checked"]["registered_cleanup_batches"], 1)
        self.assertEqual(report["checked"]["authorized_missing"], 1)
        self.assertIn("actions/cleanup.plan.jsonl", report["hashes"])
        self.assertIn("actions/cleanup.authorizations.jsonl", report["hashes"])
        self.assertIn("actions/cleanup.result.jsonl", report["hashes"])

    def test_cleanup_authorization_and_result_timestamps_are_strict_and_ordered(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        action = cleanup_action()
        cases = [
            (
                "authorization lacks timezone",
                cleanup_authorization(action, authorized_at="2026-07-16T11:59:00"),
                verified_cleanup_result(action),
                "invalid_cleanup_authorization",
                "authorization_authorized_at_missing_or_invalid",
            ),
            (
                "result lacks timezone",
                cleanup_authorization(action),
                verified_cleanup_result(action, ts="2026-07-16T12:00:00"),
                "invalid_cleanup_authorization_evidence",
                "result_ts_missing_or_invalid",
            ),
            (
                "result predates authorization",
                cleanup_authorization(action, authorized_at="2026-07-16T12:01:00+08:00"),
                verified_cleanup_result(action, ts="2026-07-16T12:00:00+08:00"),
                "invalid_cleanup_authorization_evidence",
                "result_ts_before_authorized_at",
            ),
        ]
        for name, authorization, result, kind, expected_problem in cases:
            with self.subTest(name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                write_bundle(
                    root,
                    initial,
                    [[]],
                    [],
                    [],
                    cleanup_plan=[action],
                    cleanup_ledger=[result],
                    cleanup_authorizations=[authorization],
                )
                report = audit.audit_run(root)

            violations = [item for item in report["violations"] if item["kind"] == kind]
            self.assertTrue(violations)
            self.assertIn(expected_problem, violations[0]["problems"])

    def test_regular_batch_delete_is_rejected_and_cannot_authorize_missing(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        deletion = [cleanup_action(action_id="DEL-1", reason="wrong batch type")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [[]], deletion, [verified_cleanup_result(deletion[0])])
            report = audit.audit_run(root)

        self.assertEqual(report["checked"]["authorized_missing"], 0)
        self.assertIn("cleanup_action_in_regular_batch", {item["kind"] for item in report["violations"]})
        self.assertIn("initial_entity_missing", {item["kind"] for item in report["violations"]})

    def test_cleanup_authorization_requires_complete_plan_and_latest_result_evidence(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        valid_action = cleanup_action()
        missing_authorization = cleanup_action()
        missing_authorization.pop("authorization_ref")
        missing_ts = verified_cleanup_result(valid_action)
        missing_ts.pop("ts")
        missing_empty_counts = verified_cleanup_result(valid_action)
        missing_empty_counts["verify"] = {
            "recycle_bin_status": "removed_to_recycle_bin_verified",
            "postdelete_absence_verified": True,
        }
        wrong_recycle_status = verified_cleanup_result(valid_action)
        wrong_recycle_status["verify"] = {
            "predelete": {"files": 0, "dirs": 0},
            "recycle_bin_status": "delete_command_returned_zero",
            "postdelete_absence_verified": True,
        }
        absence_not_verified = verified_cleanup_result(valid_action)
        absence_not_verified["verify"] = {
            "predelete": {"files": 0, "dirs": 0},
            "recycle_bin_status": "removed_to_recycle_bin_verified",
            "postdelete_absence_verified": False,
        }
        cases = [
            (
                "missing authorization_ref",
                missing_authorization,
                [verified_cleanup_result(missing_authorization)],
                "plan_authorization_ref_missing_or_invalid",
            ),
            (
                "from does not match initial scan",
                cleanup_action(**{"from": "/business/other"}),
                [verified_cleanup_result(cleanup_action(**{"from": "/business/other"}))],
                "plan_from_mismatch",
            ),
            (
                "result authorization_ref does not match plan",
                valid_action,
                [verified_cleanup_result(valid_action, authorization_ref="different-approval")],
                "result_authorization_ref_mismatch",
            ),
            (
                "latest result is not verified",
                valid_action,
                [
                    verified_cleanup_result(valid_action),
                    verified_cleanup_result(valid_action, status="failed"),
                ],
                "result_status_not_verified",
            ),
            (
                "missing predelete zero counts",
                valid_action,
                [missing_empty_counts],
                "result_predelete_files_not_zero",
            ),
            (
                "wrong recycle-bin status",
                valid_action,
                [wrong_recycle_status],
                "result_recycle_bin_status_invalid",
            ),
            (
                "post-delete absence not verified",
                valid_action,
                [absence_not_verified],
                "result_postdelete_absence_not_verified",
            ),
            (
                "missing timestamp",
                valid_action,
                [missing_ts],
                "result_ts_missing_or_invalid",
            ),
            (
                "verified result has a different operation identity",
                valid_action,
                [verified_cleanup_result(valid_action, op="remove")],
                "result_operation_identity_mismatch",
            ),
        ]
        for name, action, ledger, expected_problem in cases:
            with self.subTest(name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    write_bundle(
                        root,
                        initial,
                        [[]],
                        [],
                        [],
                        cleanup_plan=[action],
                        cleanup_ledger=ledger,
                        cleanup_authorizations=[cleanup_authorization(
                            valid_action if name == "missing authorization_ref" else action
                        )],
                    )
                    report = audit.audit_run(root)

                evidence_violations = [
                    item for item in report["violations"]
                    if item["kind"] == "invalid_cleanup_authorization_evidence"
                ]
                self.assertEqual(report["checked"]["authorized_missing"], 0)
                self.assertEqual(len(evidence_violations), 1)
                self.assertIn(expected_problem, evidence_violations[0]["problems"])
                self.assertIn("initial_entity_missing", {item["kind"] for item in report["violations"]})

    def test_authorized_missing_original_path_cannot_be_reused_by_another_file_id(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        replacement = [{"path": "/business", "name": "empty", "id": "replacement-id", "dir": True}]
        cleanup = cleanup_action()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(
                root,
                initial,
                [replacement],
                [],
                [],
                cleanup_plan=[cleanup],
                cleanup_ledger=[verified_cleanup_result(cleanup)],
            )
            report = audit.audit_run(root)

        reuse = [
            item for item in report["violations"]
            if item["kind"] == "authorized_missing_original_path_reused"
        ]
        self.assertEqual(report["checked"]["authorized_missing"], 0)
        self.assertEqual(len(reuse), 1)
        self.assertEqual(reuse[0]["replacement_file_ids"], ["replacement-id"])

    def test_cleanup_result_identity_mismatch_is_also_reported_as_ledger_mismatch(self) -> None:
        initial = [{"path": "/business", "name": "empty", "id": "dir-1", "dir": True}]
        cleanup = cleanup_action()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(
                root,
                initial,
                [[]],
                [],
                [],
                cleanup_plan=[cleanup],
                cleanup_ledger=[verified_cleanup_result(cleanup, op="remove")],
            )
            report = audit.audit_run(root)

        self.assertIn(
            "verified_ledger_operation_identity_mismatch",
            {item["kind"] for item in report["violations"]},
        )

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

    def test_historic_cleanup_debt_reconciles_payload_but_blocks_final_complete(self) -> None:
        initial = [{"path": "/business", "name": "old-shell", "id": "dir-legacy", "dir": True}]
        debt = {
            "action_id": "legacy-action-001",
            "file_id": "dir-legacy",
            "from": "/business/old-shell",
            "classification": "legacy_process_debt",
            "recorded_at": "2026-07-16T12:00:00+08:00",
            "historic_plan": "evidence/legacy-action-001.plan.jsonl",
            "historic_result": "evidence/legacy-action-001.result.jsonl",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [[]], [], [])
            write_jsonl(root / debt["historic_plan"], [{"action_id": debt["action_id"], "op": "trash"}])
            write_jsonl(root / debt["historic_result"], [{"action_id": debt["action_id"], "status": "verified"}])
            manifest = audit.read_json(root / "run.json")
            manifest["files"]["cleanup_process_debt"] = "analysis/cleanup-process-debt.jsonl"
            write_jsonl(root / manifest["files"]["cleanup_process_debt"], [debt])
            write_json(root / "run.json", manifest)
            report = audit.audit_run(root)

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checked"]["payload_conservation"], "passed")
        self.assertEqual(report["checked"]["structural_process_debt"], "failed")
        self.assertEqual(report["checked"]["process_debt_reconciled_missing"], 1)
        self.assertEqual(report["checked"]["authorized_missing"], 0)
        kinds = {item["kind"] for item in report["violations"]}
        self.assertIn("cleanup_process_debt", kinds)
        self.assertNotIn("initial_entity_missing", kinds)
        self.assertIn("analysis/cleanup-process-debt.jsonl", report["hashes"])
        self.assertIn("evidence/legacy-action-001.result.jsonl", report["hashes"])

    def test_historic_cleanup_debt_rejects_post_hoc_authorized_at(self) -> None:
        initial = [{"path": "/business", "name": "old-shell", "id": "dir-legacy", "dir": True}]
        debt = {
            "action_id": "historic-action-unproven",
            "file_id": "dir-legacy",
            "from": "/business/old-shell",
            "classification": "authorization_unproven_execution",
            "recorded_at": "2026-07-16T12:00:00+08:00",
            "authorized_at": "2026-07-16T11:59:00+08:00",
            "historic_plan": "evidence/historic-action-unproven.plan.jsonl",
            "historic_result": "evidence/historic-action-unproven.result.jsonl",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bundle(root, initial, [[]], [], [])
            write_jsonl(root / debt["historic_plan"], [{"action_id": debt["action_id"], "op": "trash"}])
            write_jsonl(root / debt["historic_result"], [{"action_id": debt["action_id"], "status": "verified"}])
            manifest = audit.read_json(root / "run.json")
            manifest["files"]["cleanup_process_debt"] = "analysis/cleanup-process-debt.jsonl"
            write_jsonl(root / manifest["files"]["cleanup_process_debt"], [debt])
            write_json(root / "run.json", manifest)
            report = audit.audit_run(root)

        debt_violations = [
            item for item in report["violations"]
            if item["kind"] == "invalid_cleanup_process_debt"
        ]
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checked"]["authorized_missing"], 0)
        self.assertEqual(len(debt_violations), 1)
        self.assertIn("process_debt_must_not_have_authorized_at", debt_violations[0]["problems"])

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
