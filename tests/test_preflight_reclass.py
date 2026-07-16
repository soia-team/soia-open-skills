#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/soia-pkm-alipan-curator/scripts/preflight_reclass.py"
SPEC = importlib.util.spec_from_file_location("preflight_reclass", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
sys.path.insert(0, str(SCRIPT.parent))
SPEC.loader.exec_module(module)


def action(action_id: str, op: str, **values):
    return {"action_id": action_id, "op": op, "_plan": "p", "_line": 1, **values}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def ledger_row(planned: dict, status: str = "verified", **changes: object) -> dict:
    row = {key: value for key, value in planned.items() if not key.startswith("_")}
    row.update(changes)
    row["status"] = status
    return row


def cleanup_row(path: str, file_id: str, **changes: object) -> dict:
    row = {
        "path": path,
        "file_id": file_id,
        "files": 0,
        "dirs": 0,
        "decision": "user_approved_empty_cleanup",
        "status": "removed_to_recycle_bin_verified",
    }
    row.update(changes)
    return row


def make_gate_bundle(root: Path) -> tuple[Path, Path]:
    plan_path = root / "actions/10.plan.jsonl"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text('{"action_id":"A1","op":"mkdir","to":"/partition/new"}\n', encoding="utf-8")
    report_path = root / "verification/preflight-01.json"
    write_json(root / "run.json", {
        "schema_version": 1,
        "run_id": "gate-test",
        "status": "in_progress",
        "files": {"preflight_report": "verification/preflight-01.json"},
        "batches": [{"plan": "actions/10.plan.jsonl", "result": "actions/10.result.jsonl"}],
    })
    write_json(report_path, {
        "schema_version": 1,
        "status": "passed",
        "hashes": {
            "run.json": module.preflight_gate.sha256_file(root / "run.json"),
            "actions/10.plan.jsonl": module.preflight_gate.sha256_file(plan_path),
        },
    })
    return plan_path, report_path


class PreflightReclassTests(unittest.TestCase):
    def test_cleanup_actions_are_rejected_before_any_cloud_runner_call(self) -> None:
        for op in ("delete", "remove", "trash"):
            with self.subTest(op=op), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                plan_path = root / "actions/10.plan.jsonl"
                plan_path.parent.mkdir(parents=True)
                plan_path.write_text(
                    json.dumps({
                        "action_id": "C1",
                        "op": op,
                        "from": "/partition/empty-shell",
                        "to": "/partition/empty-shell",
                        "file_id": "shell-id",
                        "reason": "approved cleanup candidate",
                    }) + "\n",
                    encoding="utf-8",
                )
                write_json(root / "run.json", {
                    "schema_version": 1,
                    "files": {},
                    "batches": [{"plan": "actions/10.plan.jsonl"}],
                })
                with mock.patch.object(module, "require_alipan_runner") as require_runner, mock.patch.object(
                    module, "run_aliyunpan_ll"
                ) as run_runner:
                    with self.assertRaises(ValueError) as raised:
                        module.load_registered(root, ["/partition"])

                self.assertIn(module.CLEANUP_ACTION_ERROR, str(raised.exception))
                require_runner.assert_not_called()
                run_runner.assert_not_called()

    def test_default_runner_is_resolved_from_adjacent_atomic_skill(self) -> None:
        with mock.patch.dict(module.os.environ, {}, clear=False):
            module.os.environ.pop(module.RUNNER_ENV, None)
            expected = (
                SCRIPT.resolve().parents[2]
                / "soia-pkm-alipan-drive-ops"
                / "scripts"
                / "run_with_env.py"
            )
            self.assertEqual(module.alipan_runner_path(), expected)

    def test_runner_override_is_used_for_listing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = Path(temporary) / "run_with_env.py"
            runner.write_text("# mock runner\n", encoding="utf-8")
            completed = module.subprocess.CompletedProcess(
                [],
                0,
                "当前目录 /A\n",
                "",
            )
            with mock.patch.dict(module.os.environ, {module.RUNNER_ENV: str(runner)}), mock.patch.object(
                module.subprocess,
                "run",
                return_value=completed,
            ) as run:
                result = module.list_directory("drive-id", "/A", timeout=11, attempts=1)

        self.assertEqual(result["state"], "exists")
        run.assert_called_once_with(
            [
                sys.executable,
                str(runner),
                "--",
                "aliyunpan",
                "ll",
                "--driveId",
                "drive-id",
                "/A",
            ],
            capture_output=True,
            text=True,
            timeout=11,
        )

    def test_missing_runner_fails_without_bare_aliyunpan_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing-runner.py"
            with mock.patch.dict(module.os.environ, {module.RUNNER_ENV: str(missing)}), mock.patch.object(
                module.subprocess,
                "run",
            ) as run:
                with self.assertRaisesRegex(FileNotFoundError, "SOIA_ALIPAN_RUNNER"):
                    module.list_directory("drive-id", "/A", timeout=11, attempts=1)
        run.assert_not_called()

    def test_pure_gate_accepts_registered_current_evidence(self) -> None:
        manifest = {
            "files": {"preflight_report": "verification/preflight.json"},
            "batches": [{"plan": "actions/10.plan.jsonl"}],
        }
        hashes = {"run.json": "a" * 64, "actions/10.plan.jsonl": "b" * 64}
        result = module.preflight_gate.validate_preflight_gate(
            manifest=manifest,
            report_path="verification/preflight.json",
            report={"schema_version": 1, "status": "passed", "hashes": hashes},
            current_hashes=hashes,
            executor_plan_path="actions/10.plan.jsonl",
        )
        self.assertEqual(result["status"], "passed")

    def test_parse_ll_preserves_repeated_spaces_and_identity(self) -> None:
        output = "当前目录 /A\n0 id1 - ABCD 42 0 0 0 0 name  with  spaces.txt\n"
        state, entries = module.parse_ll(output)
        self.assertEqual(state, "exists")
        self.assertEqual(entries[0]["id"], "id1")
        self.assertEqual(entries[0]["name"], "name  with  spaces.txt")

    def test_replay_accepts_mkdir_move_then_rename(self) -> None:
        listings = [
            {"path": "/", "state": "exists", "entries": [{"id": "a", "name": "A", "dir": True}]},
            {"path": "/A", "state": "exists", "entries": [{"id": "id1", "name": "old", "dir": True}]},
        ]
        actions = [
            action("M1", "mkdir", to="/B"),
            action("M2", "mv", **{"from": "/A/old", "to": "/B", "file_id": "id1"}),
            action("M3", "rename", **{"from": "/B/old", "to": "/B/001_new", "file_id": "id1"}),
        ]
        statuses, violations = module.replay(actions, listings)
        self.assertEqual(violations, [])
        self.assertEqual(len(statuses), 3)

    def test_replay_blocks_destination_collision_and_wrong_id(self) -> None:
        listings = [
            {"path": "/A", "state": "exists", "entries": [{"id": "id1", "name": "old", "dir": False}]},
            {"path": "/B", "state": "exists", "entries": [{"id": "other", "name": "old", "dir": False}]},
        ]
        actions = [action("M", "mv", **{"from": "/A/old", "to": "/B", "file_id": "id1"})]
        _, violations = module.replay(actions, listings)
        self.assertEqual(violations[0]["kind"], "destination_collision")

        actions[0]["file_id"] = "wrong"
        _, violations = module.replay(actions, listings)
        self.assertEqual(violations[0]["kind"], "source_id_mismatch")

    def test_preexisting_mkdir_target_without_provenance_blocks_execution(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        statuses, violations = module.replay(
            [planned],
            [{"path": "/", "state": "exists", "entries": [
                {"id": "existing-dir", "name": "A", "dir": True},
            ]}],
        )

        self.assertEqual(statuses, [])
        self.assertIn(
            "mkdir_target_preexists_without_provenance",
            {item["kind"] for item in violations},
        )

    def test_verified_mkdir_requires_current_directory_identity(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        statuses, violations = module.replay(
            [planned],
            [{"path": "/A", "state": "exists", "entries": []}],
            {module.operation_key(planned)},
        )

        self.assertEqual(statuses, [])
        kinds = {item["kind"] for item in violations}
        self.assertIn("verified_mkdir_terminal_identity_missing", kinds)
        self.assertIn("mkdir_target_preexists_without_provenance", kinds)

    def test_verified_mkdir_with_fresh_directory_identity_is_already_verified(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        statuses, violations = module.replay(
            [planned],
            [{"path": "/", "state": "exists", "entries": [
                {"id": "created-dir", "name": "A", "dir": True},
            ]}],
            {module.operation_key(planned)},
        )

        self.assertEqual(violations, [])
        self.assertEqual(statuses, [{
            "action_id": "M1",
            "status": "already_verified",
            "target": "/A",
            "directory_id": "created-dir",
        }])

    def test_duplicate_mkdir_target_blocks_even_when_ledger_claims_both_verified(self) -> None:
        actions = [action("M1", "mkdir", to="/A"), action("M2", "mkdir", to="/A")]
        statuses, violations = module.replay(
            actions,
            [{"path": "/", "state": "exists", "entries": [
                {"id": "created-dir", "name": "A", "dir": True},
            ]}],
            {module.operation_key(item) for item in actions},
        )

        self.assertEqual([item["action_id"] for item in statuses], ["M1"])
        self.assertIn("duplicate_mkdir_target", {item["kind"] for item in violations})

    def test_partial_execution_marks_verified_chain_and_leaves_pending_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            actions = [
                action("A1", "mv", **{"from": "/A/old", "to": "/B", "file_id": "id1"}),
                action("A2", "rename", **{"from": "/B/old", "to": "/B/new", "file_id": "id1"}),
                action("A3", "mv", **{"from": "/A/pending", "to": "/B", "file_id": "id2"}),
            ]
            for planned in actions:
                planned["_batch"] = 1
            manifest = {"batches": [{"result": "actions/10.result.jsonl"}]}
            write_jsonl(
                root / "actions/10.result.jsonl",
                [ledger_row(actions[0]), ledger_row(actions[1], status="completed")],
            )
            verified, ledger_violations = module.load_resume_state(root, manifest, actions)
            listings = [
                {"path": "/A", "state": "exists", "entries": [
                    {"id": "id2", "name": "pending", "dir": False},
                ]},
                {"path": "/B", "state": "exists", "entries": [
                    {"id": "id1", "name": "new", "dir": False},
                ]},
            ]
            statuses, replay_violations = module.replay(actions, listings, verified)

        self.assertEqual(ledger_violations, [])
        self.assertEqual(replay_violations, [])
        self.assertEqual(
            [item["status"] for item in statuses],
            ["already_verified", "already_verified", "ready"],
        )
        self.assertEqual(module.summarize_action_statuses(statuses), {
            "ready_actions": 1,
            "already_verified_actions": 2,
            "superseded_actions": 0,
        })

    def test_forged_verified_ledger_is_rejected_when_terminal_is_absent(self) -> None:
        planned = action(
            "A1",
            "mv",
            **{"from": "/A/old", "to": "/B", "file_id": "id1"},
        )
        listings = [
            {"path": "/A", "state": "exists", "entries": [
                {"id": "id1", "name": "old", "dir": False},
            ]},
            {"path": "/B", "state": "exists", "entries": []},
        ]
        statuses, violations = module.replay(
            [planned],
            listings,
            {module.operation_key(planned)},
        )
        self.assertIn("verified_terminal_missing", {item["kind"] for item in violations})
        self.assertEqual([item["status"] for item in statuses], ["ready"])

    def test_verified_terminal_with_wrong_file_id_is_rejected(self) -> None:
        planned = action(
            "A1",
            "mv",
            **{"from": "/A/old", "to": "/B", "file_id": "id1"},
        )
        listings = [
            {"path": "/A", "state": "exists", "entries": []},
            {"path": "/B", "state": "exists", "entries": [
                {"id": "wrong-id", "name": "old", "dir": False},
            ]},
        ]
        _, violations = module.replay(
            [planned],
            listings,
            {module.operation_key(planned)},
        )
        self.assertIn("verified_terminal_id_mismatch", {item["kind"] for item in violations})

    def test_verified_chain_with_intermediate_ledger_gap_is_rejected(self) -> None:
        actions = [
            action("A1", "rename", **{"from": "/A/one", "to": "/A/two", "file_id": "id1"}),
            action("A2", "rename", **{"from": "/A/two", "to": "/A/three", "file_id": "id1"}),
            action("A3", "rename", **{"from": "/A/three", "to": "/A/four", "file_id": "id1"}),
        ]
        listings = [{
            "path": "/A",
            "state": "exists",
            "entries": [{"id": "id1", "name": "four", "dir": False}],
        }]
        _, violations = module.replay(
            actions,
            listings,
            {module.operation_key(actions[0]), module.operation_key(actions[2])},
        )
        self.assertIn("verified_chain_gap", {item["kind"] for item in violations})

    def test_reverse_plan_allows_later_verified_action_to_reoccupy_old_source(self) -> None:
        actions = [
            action("A1", "mv", **{"from": "/A/x", "to": "/B", "file_id": "id1"}),
            action("A2", "mv", **{"from": "/C/x", "to": "/A", "file_id": "id2"}),
        ]
        listings = [
            {"path": "/A", "state": "exists", "entries": [
                {"id": "id2", "name": "x", "dir": False},
            ]},
            {"path": "/B", "state": "exists", "entries": [
                {"id": "id1", "name": "x", "dir": False},
            ]},
            {"path": "/C", "state": "exists", "entries": []},
        ]
        statuses, violations = module.replay(
            actions,
            listings,
            {module.operation_key(item) for item in actions},
        )
        self.assertEqual(violations, [])
        self.assertEqual(
            [item["status"] for item in statuses],
            ["already_verified", "already_verified"],
        )

    def test_verified_ledger_wrong_file_id_is_not_a_registered_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            planned = action(
                "A1",
                "mv",
                **{"from": "/A/old", "to": "/B", "file_id": "id1"},
            )
            planned["_batch"] = 1
            manifest = {"batches": [{"result": "actions/10.result.jsonl"}]}
            write_jsonl(
                root / "actions/10.result.jsonl",
                [ledger_row(planned, file_id="wrong-id")],
            )
            verified, violations = module.load_resume_state(root, manifest, [planned])
        self.assertEqual(verified, set())
        self.assertIn(
            "verified_ledger_operation_not_registered",
            {item["kind"] for item in violations},
        )

    def test_latest_ledger_record_overrides_older_verified_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            planned = action(
                "A1",
                "mv",
                **{"from": "/A/old", "to": "/B", "file_id": "id1"},
            )
            planned["_batch"] = 1
            manifest = {"batches": [{"result": "actions/10.result.jsonl"}]}
            write_jsonl(
                root / "actions/10.result.jsonl",
                [ledger_row(planned, status="verified"), ledger_row(planned, status="failed")],
            )
            verified, violations = module.load_resume_state(root, manifest, [planned])
        self.assertEqual(verified, set())
        self.assertEqual(violations, [])

    def test_verified_empty_mkdir_cleanup_is_superseded_in_child_first_order(self) -> None:
        actions = [
            action("M1", "mkdir", to="/A"),
            action("M2", "mkdir", to="/A/B"),
            action("M3", "mkdir", to="/A/B/C"),
        ]
        evidence = [
            {**cleanup_row("/A/B/C", "dir-c"), "_line": 1, "_evidence": "cleanup.jsonl"},
            {**cleanup_row("/A/B", "dir-b", dirs=1), "_line": 2, "_evidence": "cleanup.jsonl"},
            {**cleanup_row("/A", "dir-a", dirs=1), "_line": 3, "_evidence": "cleanup.jsonl"},
        ]
        listings = [
            {"path": "/", "state": "exists", "entries": []},
            {"path": "/A", "state": "missing", "entries": []},
            {"path": "/A/B", "state": "missing", "entries": []},
        ]
        statuses, violations = module.replay(
            actions,
            listings,
            {module.operation_key(item) for item in actions},
            evidence,
        )
        self.assertEqual(violations, [])
        self.assertEqual([item["status"] for item in statuses], ["superseded"] * 3)
        self.assertEqual(module.summarize_action_statuses(statuses), {
            "ready_actions": 0,
            "already_verified_actions": 0,
            "superseded_actions": 3,
        })

    def test_forged_cleanup_evidence_status_is_rejected(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        evidence = [{
            **cleanup_row("/A", "dir-a", status="removed_without_recycle_bin_proof"),
            "_line": 1,
            "_evidence": "cleanup.jsonl",
        }]
        _, violations = module.replay(
            [planned],
            [{"path": "/", "state": "exists", "entries": []}],
            {module.operation_key(planned)},
            evidence,
        )
        kinds = {item["kind"] for item in violations}
        self.assertIn("invalid_cleanup_evidence_status", kinds)
        self.assertIn("verified_mkdir_terminal_missing", kinds)

    def test_cleanup_evidence_status_prefix_spoof_is_rejected(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        evidence = [{
            **cleanup_row("/A", "dir-a", status="removed_to_recycle_bin_failed"),
            "_line": 1,
            "_evidence": "cleanup.jsonl",
        }]
        _, violations = module.replay(
            [planned],
            [{"path": "/", "state": "exists", "entries": []}],
            {module.operation_key(planned)},
            evidence,
        )
        self.assertIn(
            "invalid_cleanup_evidence_status",
            {item["kind"] for item in violations},
        )

    def test_nonempty_cleanup_evidence_is_rejected(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        evidence = [{
            **cleanup_row("/A", "dir-a", files=1),
            "_line": 1,
            "_evidence": "cleanup.jsonl",
        }]
        _, violations = module.replay(
            [planned],
            [{"path": "/", "state": "exists", "entries": []}],
            {module.operation_key(planned)},
            evidence,
        )
        self.assertIn("cleanup_evidence_not_empty", {item["kind"] for item in violations})

    def test_cleanup_evidence_path_must_match_registered_mkdir(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        evidence = [{
            **cleanup_row("/Other", "dir-a"),
            "_line": 1,
            "_evidence": "cleanup.jsonl",
        }]
        _, violations = module.replay(
            [planned],
            [{"path": "/", "state": "exists", "entries": []}],
            {module.operation_key(planned)},
            evidence,
        )
        self.assertIn(
            "cleanup_evidence_path_not_registered",
            {item["kind"] for item in violations},
        )

    def test_cleanup_evidence_without_verified_ledger_is_rejected(self) -> None:
        planned = action("M1", "mkdir", to="/A")
        evidence = [{
            **cleanup_row("/A", "dir-a"),
            "_line": 1,
            "_evidence": "cleanup.jsonl",
        }]
        statuses, violations = module.replay(
            [planned],
            [{"path": "/", "state": "exists", "entries": []}],
            set(),
            evidence,
        )
        self.assertIn(
            "cleanup_evidence_without_verified_mkdir",
            {item["kind"] for item in violations},
        )
        self.assertEqual([item["status"] for item in statuses], ["ready"])

    def test_cleanup_evidence_parent_before_child_is_rejected(self) -> None:
        actions = [action("M1", "mkdir", to="/A"), action("M2", "mkdir", to="/A/B")]
        evidence = [
            {**cleanup_row("/A", "dir-a", dirs=1), "_line": 1, "_evidence": "cleanup.jsonl"},
            {**cleanup_row("/A/B", "dir-b"), "_line": 2, "_evidence": "cleanup.jsonl"},
        ]
        _, violations = module.replay(
            actions,
            [
                {"path": "/", "state": "exists", "entries": []},
                {"path": "/A", "state": "missing", "entries": []},
            ],
            {module.operation_key(item) for item in actions},
            evidence,
        )
        self.assertIn(
            "cleanup_evidence_parent_removed_before_child",
            {item["kind"] for item in violations},
        )

    def test_cleanup_authorization_tamper_invalidates_preflight_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path, report_path = make_gate_bundle(root)
            cleanup_plan_path = root / "actions/cleanup.plan.jsonl"
            cleanup_plan = {
                "action_id": "CLEAN-1",
                "op": "trash",
                "from": "/partition/new",
                "file_id": "dir-new",
                "allow_missing": True,
                "reason": "approved empty shell cleanup",
                "authorization_ref": "approval-2026-07-16",
            }
            authorization_path = root / "actions/cleanup.authorizations.jsonl"
            write_jsonl(cleanup_plan_path, [cleanup_plan])
            write_jsonl(authorization_path, [{
                "authorization_ref": cleanup_plan["authorization_ref"],
                "action_id": cleanup_plan["action_id"],
                "file_id": cleanup_plan["file_id"],
                "from": cleanup_plan["from"],
                "decision": "approved",
                "authorized_at": "2026-07-16T11:59:00+08:00",
            }])
            manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
            manifest["files"]["cleanup_authorizations"] = "actions/cleanup.authorizations.jsonl"
            manifest["cleanup_batches"] = [{
                "plan": "actions/cleanup.plan.jsonl",
                "result": "actions/cleanup.result.jsonl",
            }]
            write_json(root / "run.json", manifest)
            write_json(report_path, {
                "schema_version": 1,
                "status": "passed",
                "hashes": {
                    "run.json": module.preflight_gate.sha256_file(root / "run.json"),
                    "actions/10.plan.jsonl": module.preflight_gate.sha256_file(plan_path),
                    "actions/cleanup.plan.jsonl": module.preflight_gate.sha256_file(cleanup_plan_path),
                    "actions/cleanup.authorizations.jsonl": module.preflight_gate.sha256_file(authorization_path),
                },
            })
            _, _, generated_hashes = module.load_registered(root, ["/partition"])
            self.assertEqual(
                generated_hashes["actions/cleanup.authorizations.jsonl"],
                module.preflight_gate.sha256_file(authorization_path),
            )
            self.assertNotIn("actions/cleanup.result.jsonl", generated_hashes)
            self.assertEqual(module.preflight_gate.verify_preflight_gate(root)["status"], "passed")
            write_jsonl(
                authorization_path,
                [{
                    "authorization_ref": cleanup_plan["authorization_ref"],
                    "action_id": cleanup_plan["action_id"],
                    "file_id": cleanup_plan["file_id"],
                    "from": cleanup_plan["from"],
                    "decision": "tampered",
                    "authorized_at": "2026-07-16T11:59:00+08:00",
                }],
            )
            result = module.preflight_gate.verify_preflight_gate(root)
        self.assertIn(
            "preflight_cleanup_authorizations_changed",
            {item["kind"] for item in result["violations"]},
        )

    def test_empty_cleanup_evidence_tamper_invalidates_preflight_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path, report_path = make_gate_bundle(root)
            evidence_path = root / "verification/empty-cleanup.jsonl"
            write_jsonl(evidence_path, [cleanup_row("/partition/new", "dir-new")])
            manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
            manifest["files"]["empty_cleanup_evidence"] = "verification/empty-cleanup.jsonl"
            write_json(root / "run.json", manifest)
            write_json(report_path, {
                "schema_version": 1,
                "status": "passed",
                "hashes": {
                    "run.json": module.preflight_gate.sha256_file(root / "run.json"),
                    "actions/10.plan.jsonl": module.preflight_gate.sha256_file(plan_path),
                    "verification/empty-cleanup.jsonl": module.preflight_gate.sha256_file(evidence_path),
                },
            })

            _, _, generated_hashes = module.load_registered(root, ["/partition"])
            self.assertEqual(
                generated_hashes["verification/empty-cleanup.jsonl"],
                module.preflight_gate.sha256_file(evidence_path),
            )
            self.assertEqual(module.preflight_gate.verify_preflight_gate(root)["status"], "passed")
            write_jsonl(evidence_path, [cleanup_row("/partition/new", "dir-new", decision="tampered")])
            result = module.preflight_gate.verify_preflight_gate(root)

        self.assertIn(
            "preflight_cleanup_evidence_changed",
            {item["kind"] for item in result["violations"]},
        )

    def test_missing_listing_is_not_parse_failure(self) -> None:
        self.assertEqual(module.parse_ll("指定目录不存在: /A\n"), ("missing", []))

    def test_registered_passed_current_report_opens_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_gate_bundle(root)
            result = module.preflight_gate.verify_preflight_gate(root)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["checked"]["matched_plans"], 1)

    def test_unregistered_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_gate_bundle(root)
            manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
            manifest["files"].pop("preflight_report")
            write_json(root / "run.json", manifest)
            result = module.preflight_gate.verify_preflight_gate(root)
        self.assertEqual(result["violations"][0]["kind"], "preflight_report_not_registered")

    def test_stale_report_hash_coverage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, report_path = make_gate_bundle(root)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["hashes"].pop("actions/10.plan.jsonl")
            write_json(report_path, report)
            result = module.preflight_gate.verify_preflight_gate(root)
        kinds = {item["kind"] for item in result["violations"]}
        self.assertIn("preflight_report_stale", kinds)

    def test_changed_plan_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path, _ = make_gate_bundle(root)
            plan_path.write_text(
                '{"action_id":"A1","op":"mkdir","to":"/partition/changed"}\n',
                encoding="utf-8",
            )
            result = module.preflight_gate.verify_preflight_gate(root)
        self.assertIn("preflight_plan_changed", {item["kind"] for item in result["violations"]})

    def test_changed_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_gate_bundle(root)
            manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
            manifest["status"] = "approved"
            write_json(root / "run.json", manifest)
            result = module.preflight_gate.verify_preflight_gate(root)
        self.assertIn("preflight_manifest_changed", {item["kind"] for item in result["violations"]})

    def test_failed_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, report_path = make_gate_bundle(root)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["status"] = "failed"
            write_json(report_path, report)
            result = module.preflight_gate.verify_preflight_gate(root)
        self.assertIn("preflight_report_not_passed", {item["kind"] for item in result["violations"]})

    def test_report_path_must_belong_to_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            root.mkdir()
            make_gate_bundle(root)
            manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
            manifest["files"]["preflight_report"] = "../outside.json"
            write_json(root / "run.json", manifest)
            result = module.preflight_gate.verify_preflight_gate(root)
        self.assertEqual(result["violations"][0]["kind"], "preflight_report_path_outside_run")

    def test_executor_plan_must_be_registered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_gate_bundle(root)
            other_plan = root / "actions/other.plan.jsonl"
            other_plan.write_text("{}\n", encoding="utf-8")
            result = module.preflight_gate.verify_preflight_gate(root, plan_path=other_plan)
        self.assertIn("executor_plan_not_registered", {item["kind"] for item in result["violations"]})


if __name__ == "__main__":
    unittest.main()
