#!/usr/bin/env python3
"""Tests for the curator large-run bundle audit."""

from __future__ import annotations

import importlib.util
import hashlib
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
    cleanup_authorizations = audit.preflight_gate.registered_cleanup_authorizations(manifest)
    if cleanup_authorizations is not None:
        hashes[cleanup_authorizations] = audit.preflight_gate.sha256_file(root / cleanup_authorizations)
    cleanup_evidence = audit.preflight_gate.registered_cleanup_evidence(manifest)
    if cleanup_evidence is not None:
        hashes[cleanup_evidence] = audit.preflight_gate.sha256_file(root / cleanup_evidence)
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


def refresh_catalog_publish_report(root: Path) -> None:
    manifest = audit.read_json(root / "run.json")
    report = audit.audit_catalog_publish.audit_catalog_publication(
        root,
        manifest["files"]["catalog_publish_manifest"],
        final=True,
    )
    write_json(root / manifest["files"]["catalog_publish_audit"], report)


def sha1_bytes(value: bytes) -> str:
    return hashlib.sha1(value).hexdigest()


def add_cleanup_batch(
    root: Path,
    plan: list[dict],
    ledger: list[dict],
    *,
    authorizations: list[dict] | None = None,
) -> None:
    manifest = audit.read_json(root / "run.json")
    if authorizations is None:
        authorizations = [cleanup_authorization(action) for action in plan]
    manifest["cleanup_batches"] = [{
        "plan": "actions/cleanup.plan.jsonl",
        "result": "actions/cleanup.result.jsonl",
    }]
    manifest["files"]["cleanup_authorizations"] = "actions/cleanup.authorizations.jsonl"
    write_jsonl(root / "actions/cleanup.plan.jsonl", plan)
    write_jsonl(root / "actions/cleanup.result.jsonl", ledger)
    write_jsonl(root / "actions/cleanup.authorizations.jsonl", authorizations)
    write_json(root / "run.json", manifest)


def cleanup_action(**overrides: object) -> dict:
    action = {
        "action_id": "CLEAN-COURSE",
        "op": "trash",
        "from": "/learning/10_course",
        "file_id": "course-id",
        "allow_missing": True,
        "reason": "user approved removal of the course shell",
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
    release_metadata = {
        "catalog_release_id": "2026.01.01.1",
        "index_updated_at": "2026-01-01T12:00:00+08:00",
        "snapshot_at": "2026-01-01T11:59:00+08:00",
        "catalog_schema_version": "1",
        "source_fingerprint": "sha256:test-fixture",
    }
    release_bytes = json.dumps(release_metadata, ensure_ascii=False).encode("utf-8")
    entry = root / "catalog/00-catalog.txt"
    detail = root / "catalog/learning-detail.txt"
    consumer = root / "catalog/consumer.md"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_bytes(release_bytes)
    detail.write_bytes(release_bytes)
    consumer.write_text(json.dumps(release_metadata, ensure_ascii=False), encoding="utf-8")
    write_json(root / "catalog/release-metadata.json", release_metadata)
    local_entry = {
        "logical_name": "catalog-entry", "path": "catalog/00-catalog.txt",
        "size": len(release_bytes), "sha1": sha1_bytes(release_bytes),
        "file_id": "catalog-entry-id", "role": "catalog_entry",
    }
    local_detail = {
        "logical_name": "learning-detail", "path": "catalog/learning-detail.txt",
        "size": len(release_bytes), "sha1": sha1_bytes(release_bytes),
        "file_id": "learning-detail-id", "role": "partition_detail", "partition": "learning",
    }
    remote_entry = {**local_entry, "path": "/00-catalog.xlsx"}
    remote_detail = {**local_detail, "path": "/00-details/learning.xlsx"}
    write_json(root / "catalog/catalog-publication.json", {
        "publication_status": "passed",
        "idempotence_status": "unchanged",
        **release_metadata,
        "expected_partitions": ["learning"],
        "artifacts": {"local": [local_entry, local_detail], "remote": [remote_entry, remote_detail]},
        "remote_inventory": [remote_entry, remote_detail],
        "consumer_audits": [{
            "path": "catalog/consumer.md",
            "old_file_ids": [],
            "old_file_id_references": 0,
        }],
    })
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
            "catalog_release_metadata": "catalog/release-metadata.json",
            "catalog_publish_manifest": "catalog/catalog-publication.json",
            "catalog_publish_audit": "verification/catalog-publish-audit.json",
            "ai_review": "verification/ai-review.json",
            "migration_conservation": "verification/migration-conservation.json",
            "receipt": "handoff/receipt.md",
        },
        "batches": [{"plan": "actions/10.plan.jsonl", "result": "actions/10.result.jsonl"}],
    })
    refresh_migration_conservation_report(root)
    refresh_catalog_publish_report(root)


class RunBundleTests(unittest.TestCase):
    def test_valid_final_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            result = audit.audit_bundle(root, final=True)
            self.assertEqual(result["status"], "passed")

    def test_verified_cleanup_exempts_missing_focus_target(self) -> None:
        cleanup = [cleanup_action()]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "verification/final.scan.jsonl", [
                {"path": "/learning", "name": "staging", "id": "staging-id", "dir": True},
            ])
            add_cleanup_batch(
                root,
                cleanup,
                [verified_cleanup_result(cleanup[0])],
                authorizations=[cleanup_authorization(cleanup_action())],
            )
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["checked"]["cleanup_batches"], 1)
        self.assertEqual(result["checked"]["planned_actions"], 2)
        self.assertNotIn(
            "focus_target_missing_from_final_scan",
            {item["kind"] for item in result["violations"]},
        )

    def test_forged_conservation_summary_cannot_exempt_missing_focus_target(self) -> None:
        unauthorized_action = cleanup_action()
        unauthorized_action.pop("authorization_ref")
        cleanup = [unauthorized_action]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "verification/final.scan.jsonl", [
                {"path": "/learning", "name": "staging", "id": "staging-id", "dir": True},
            ])
            add_cleanup_batch(root, cleanup, [verified_cleanup_result(cleanup[0])])
            manifest = audit.read_json(root / "run.json")
            write_json(root / "verification/migration-conservation.json", {
                "status": "passed",
                "checked": {"authorized_missing": 1},
                "hashes": audit.audit_migration_conservation.conservation_input_hashes(root, manifest),
            })
            result = audit.audit_bundle(root, final=True)

        kinds = {item["kind"] for item in result["violations"]}
        self.assertIn("focus_target_missing_from_final_scan", kinds)
        self.assertNotIn("migration_conservation_report_not_passed", kinds)

    def test_final_migration_report_blocks_reuse_of_authorized_missing_path(self) -> None:
        cleanup = [cleanup_action()]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "verification/final.scan.jsonl", [
                {
                    "path": "/learning",
                    "name": "10_course",
                    "id": "replacement-course-id",
                    "dir": True,
                },
            ])
            add_cleanup_batch(root, cleanup, [verified_cleanup_result(cleanup[0])])
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        kinds = {item["kind"] for item in result["violations"]}
        self.assertEqual(result["status"], "failed")
        self.assertIn("migration_conservation_report_not_passed", kinds)

    def test_cleanup_actions_share_the_global_action_id_namespace(self) -> None:
        cleanup = [cleanup_action(
            action_id="B10-001",
            allow_missing=False,
            reason="attempted duplicate action",
        )]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            add_cleanup_batch(root, cleanup, [verified_cleanup_result(cleanup[0])])
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        duplicates = [item for item in result["violations"] if item["kind"] == "duplicate_plan_action_id"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["action_id"], "B10-001")
        self.assertEqual(duplicates[0]["batch_group"], "cleanup_batches")

    def test_final_cleanup_action_must_close(self) -> None:
        cleanup = [cleanup_action(allow_missing=False, reason="attempted removal")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            add_cleanup_batch(root, cleanup, [verified_cleanup_result(cleanup[0], status="failed")])
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        unclosed = [item for item in result["violations"] if item["kind"] == "action_not_closed"]
        self.assertEqual(len(unclosed), 1)
        self.assertEqual(unclosed[0]["batch_group"], "cleanup_batches")

    def test_denied_cleanup_authorization_fails_nonfinal_audit(self) -> None:
        cleanup = [cleanup_action()]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            add_cleanup_batch(
                root,
                cleanup,
                [],
                authorizations=[cleanup_authorization(cleanup[0], decision="denied")],
            )
            result = audit.audit_bundle(root, final=False, require_preflight=False)

        invalid = [item for item in result["violations"] if item["kind"] == "invalid_cleanup_authorization"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(invalid), 1)
        self.assertIn("authorization_decision_not_approved", invalid[0]["problems"])

    def test_cleanup_result_paths_cannot_alias_inputs_or_each_other(self) -> None:
        with self.subTest("immutable input alias"), tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            cleanup = cleanup_action()
            add_cleanup_batch(root, [cleanup], [])
            manifest = audit.read_json(root / "run.json")
            manifest["cleanup_batches"][0]["result"] = "inventory/initial.scan.jsonl"
            write_json(root / "run.json", manifest)
            aliased = audit.audit_bundle(root, final=False, require_preflight=False)

        self.assertIn("invalid_cleanup_result_path", {item["kind"] for item in aliased["violations"]})

        with self.subTest("duplicate cleanup result"), tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            first = cleanup_action()
            second = cleanup_action(
                action_id="CLEAN-SECOND",
                **{"from": "/learning/other", "file_id": "other-id", "authorization_ref": "approval-second"},
            )
            add_cleanup_batch(root, [first], [])
            manifest = audit.read_json(root / "run.json")
            manifest["cleanup_batches"].append({
                "plan": "actions/cleanup-second.plan.jsonl",
                "result": "actions/cleanup.result.jsonl",
            })
            write_jsonl(root / "actions/cleanup-second.plan.jsonl", [second])
            write_jsonl(root / "actions/cleanup.authorizations.jsonl", [
                cleanup_authorization(first),
                cleanup_authorization(second),
            ])
            write_json(root / "run.json", manifest)
            duplicate = audit.audit_bundle(root, final=False, require_preflight=False)

        self.assertIn("invalid_cleanup_result_path", {item["kind"] for item in duplicate["violations"]})

    def test_cleanup_result_canonical_alias_variants_fail_closed(self) -> None:
        aliases = [
            "actions/./cleanup.plan.jsonl",
            "actions/temporary/../cleanup.plan.jsonl",
            "actions//cleanup.plan.jsonl",
        ]
        for alias in aliases:
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                make_valid_bundle(root)
                cleanup = cleanup_action()
                add_cleanup_batch(root, [cleanup], [])
                manifest = audit.read_json(root / "run.json")
                manifest["cleanup_batches"][0]["result"] = alias
                write_json(root / "run.json", manifest)
                result = audit.audit_bundle(root, final=False, require_preflight=False)

            self.assertIn(
                "invalid_cleanup_result_path",
                {item["kind"] for item in result["violations"]},
            )

    def test_cleanup_result_path_rejects_run_directory_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            cleanup = cleanup_action()
            add_cleanup_batch(root, [cleanup], [])
            manifest = audit.read_json(root / "run.json")
            manifest["cleanup_batches"][0]["result"] = "actions/../../outside.result.jsonl"
            write_json(root / "run.json", manifest)
            result = audit.audit_bundle(root, final=False, require_preflight=False)

        self.assertIn(
            "invalid_cleanup_result_path",
            {item["kind"] for item in result["violations"]},
        )

    def test_cleanup_ledger_history_tamper_invalidates_final_conservation(self) -> None:
        cleanup = cleanup_action()
        verified = verified_cleanup_result(cleanup)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "verification/final.scan.jsonl", [
                {"path": "/learning", "name": "staging", "id": "staging-id", "dir": True},
            ])
            add_cleanup_batch(root, [cleanup], [
                {**cleanup, "status": "failed", "reason": "transient provider error"},
                verified,
            ])
            refresh_migration_conservation_report(root)
            write_jsonl(root / "actions/cleanup.result.jsonl", [verified])
            result = audit.audit_bundle(root, final=True)

        mismatches = [
            item for item in result["violations"]
            if item["kind"] == "migration_conservation_report_hash_mismatch"
        ]
        self.assertTrue(any(item["member"] == "actions/cleanup.result.jsonl" for item in mismatches))

    def test_historic_cleanup_debt_blocks_final_complete_without_claiming_authorization(self) -> None:
        debt = {
            "action_id": "historic-action-unproven",
            "file_id": "course-id",
            "from": "/learning/10_course",
            "classification": "authorization_unproven_execution",
            "recorded_at": "2026-07-16T12:00:00+08:00",
            "historic_plan": "evidence/historic-action-unproven.plan.jsonl",
            "historic_result": "evidence/historic-action-unproven.result.jsonl",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            write_jsonl(root / "verification/final.scan.jsonl", [])
            write_jsonl(root / debt["historic_plan"], [{"action_id": debt["action_id"], "op": "trash"}])
            write_jsonl(root / debt["historic_result"], [{"action_id": debt["action_id"], "status": "verified"}])
            manifest = audit.read_json(root / "run.json")
            manifest["files"]["cleanup_process_debt"] = "analysis/cleanup-process-debt.jsonl"
            write_jsonl(root / manifest["files"]["cleanup_process_debt"], [debt])
            write_json(root / "run.json", manifest)
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        kinds = {item["kind"] for item in result["violations"]}
        self.assertEqual(result["status"], "failed")
        self.assertIn("cleanup_process_debt_blocks_final_complete", kinds)

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

    def test_final_scans_plural_declaration_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            business_rows = [{"path": "/learning", "name": "10_course", "id": "course-id", "dir": True}]
            archive_rows = [
                {"path": "/learning", "name": "staging", "id": "staging-id", "dir": True},
                {"path": "/learning", "name": "90_archive", "id": "archive-id", "dir": True},
            ]
            write_jsonl(root / "verification/final-business.scan.jsonl", business_rows)
            write_jsonl(root / "verification/final-archive.scan.jsonl", archive_rows)
            manifest = audit.read_json(root / "run.json")
            manifest["files"].pop("final_scan")
            manifest["files"]["final_scans"] = [
                "verification/final-business.scan.jsonl",
                "verification/final-archive.scan.jsonl",
            ]
            write_json(root / "run.json", manifest)
            refresh_migration_conservation_report(root)
            result = audit.audit_bundle(root, final=True)

        kinds = {item["kind"] for item in result["violations"]}
        self.assertNotIn("run_file_not_declared", kinds)
        self.assertNotIn("final_scan_empty", kinds)
        self.assertEqual(
            result["checked"]["final_scan_rows"],
            len(business_rows) + len(archive_rows),
        )
        self.assertEqual(result["status"], "passed")

    def test_final_scans_missing_member_file_reports_run_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            manifest = audit.read_json(root / "run.json")
            manifest["files"].pop("final_scan")
            manifest["files"]["final_scans"] = ["verification/never-written.scan.jsonl"]
            write_json(root / "run.json", manifest)
            result = audit.audit_bundle(root, final=True)

        missing = [item for item in result["violations"] if item["kind"] == "run_file_missing"]
        self.assertEqual(missing, [{
            "kind": "run_file_missing",
            "file": "final_scans[0]",
            "path": "verification/never-written.scan.jsonl",
        }])
        self.assertEqual(result["status"], "failed")

    def test_final_scans_empty_array_reports_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            manifest = audit.read_json(root / "run.json")
            manifest["files"].pop("final_scan")
            manifest["files"]["final_scans"] = []
            write_json(root / "run.json", manifest)
            result = audit.audit_bundle(root, final=True)

        kinds = {item["kind"] for item in result["violations"]}
        self.assertIn("invalid_final_scan_declaration", kinds)
        self.assertIn("final_scan_empty", kinds)
        self.assertEqual(result["status"], "failed")

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

    def test_final_cloud_write_requires_catalog_publication_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            manifest = audit.read_json(root / "run.json")
            manifest["files"].pop("catalog_publish_manifest")
            write_json(root / "run.json", manifest)
            result = audit.audit_bundle(root, final=True)

        self.assertIn(
            "catalog_publish_file_not_registered",
            {item["kind"] for item in result["violations"]},
        )
        self.assertEqual(result["checked"]["catalog_publish"], "failed")

    def test_final_rejects_stale_catalog_publication_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_bundle(root)
            report_path = root / "verification/catalog-publish-audit.json"
            report = audit.read_json(report_path)
            report["checked"]["expected_partitions"] = 999
            write_json(report_path, report)
            result = audit.audit_bundle(root, final=True)

        self.assertIn(
            "catalog_publish_audit_stale_or_mismatched",
            {item["kind"] for item in result["violations"]},
        )
        self.assertEqual(result["checked"]["catalog_publish"], "failed")

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
