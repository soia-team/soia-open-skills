#!/usr/bin/env python3
"""Tests for the isolated bulk reclassification executor."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bulk = load_module(
    "apply_reclass_bulk_under_test",
    "skills/soia-pkm-alipan-curator/scripts/apply_reclass_bulk.py",
)
GATE_PASSED = {"status": "passed", "checked": {}, "violations": []}


def result(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def file_id_for_name(name: str) -> str:
    return f"file:{name.rstrip('/').replace(' ', '_')}"


def listing(*names):
    rows = ["当前目录 /mock", "--------------------------------"]
    rows.extend(
        f"{index}  {file_id}  -  -  0  2025-01-01 00:00:00  2025-01-02 13:00:00  {name}"
        for index, value in enumerate(names)
        for name, file_id in [value if isinstance(value, tuple) else (value, file_id_for_name(value))]
    )
    return result(stdout="\n".join(rows) + "\n")


class BulkApplyReclassTests(unittest.TestCase):
    ROOT = "/library"

    def write_plan(self, root: Path, records: list[dict]) -> Path:
        records = [
            {
                **record,
                **(
                    {"file_id": file_id_for_name(bulk.parent_and_name(record['from'])[1])}
                    if record["op"] != "mkdir" and "file_id" not in record
                    else {}
                ),
            }
            for record in records
        ]
        path = root / "plan.jsonl"
        path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )
        return path

    def run_main(
        self,
        *args: str,
        auto_run_dir: bool = True,
        gate_result: dict | None = None,
    ) -> str:
        old_argv = sys.argv
        output = io.StringIO()
        effective_args = list(args)
        if auto_run_dir and "--execute" in effective_args and "--run-dir" not in effective_args:
            effective_args.extend(["--run-dir", "/mock/run"])
        sys.argv = ["apply_reclass_bulk.py", *effective_args]
        try:
            with mock.patch.object(
                bulk.preflight_gate,
                "verify_preflight_gate",
                return_value=GATE_PASSED if gate_result is None else gate_result,
            ):
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    bulk.main()
        finally:
            sys.argv = old_argv
        return output.getvalue()

    def test_double_spaces_survive_parse_and_batch_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = "/library/old/course  one"
            second = "/library/old/course  two"
            plan = self.write_plan(
                root,
                [
                    {"action_id": "A1", "op": "mv", "from": first, "to": "/library/new", "reason": "classify"},
                    {"action_id": "A2", "op": "mv", "from": second, "to": "/library/new", "reason": "classify"},
                ],
            )
            ledger = root / "ledger.jsonl"
            replies = [listing("course  one", "course  two"), listing(), result(), listing(), listing("course  one", "course  two")]
            with mock.patch.object(bulk, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute", "--resume", "--batch-size", "2",
                )

            move = next(call for call in run.call_args_list if call.args[0] == "mv")
            self.assertEqual(move.args, ("mv", "drive-1", first, second, "/library/new"))

    def test_bulk_runner_override_preserves_aliyunpan_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runner = Path(temp) / "runner.py"
            runner.write_text("# test runner\n", encoding="utf-8")
            with mock.patch.dict("os.environ", {bulk.RUNNER_ENV: str(runner)}, clear=False):
                with mock.patch.object(bulk.subprocess, "run", return_value=result()) as run:
                    bulk.run_aliyunpan("mv", "drive-1", "/library/a  b", "/library/target")

            self.assertEqual(
                run.call_args.args[0],
                [sys.executable, str(runner), "--", "aliyunpan", "mv", "--driveId", "drive-1", "/library/a  b", "/library/target"],
            )

    def test_bulk_runner_errors_are_sanitized_without_bare_fallback(self) -> None:
        secret_runner = "/private/session-token/run_with_env.py"
        with mock.patch.dict("os.environ", {bulk.RUNNER_ENV: secret_runner}, clear=False):
            with mock.patch.object(bulk.subprocess, "run") as run:
                unavailable = bulk.run_aliyunpan("ll", "drive-1", "/library")
        self.assertEqual(unavailable.returncode, 127)
        self.assertEqual(unavailable.stderr, "RUNNER_UNAVAILABLE")
        self.assertNotIn("session-token", unavailable.stderr)
        run.assert_not_called()

    def test_bulk_preflight_adapter_receives_run_and_plan_paths(self) -> None:
        with mock.patch.object(
            bulk.preflight_gate,
            "verify_preflight_gate",
            return_value=GATE_PASSED,
        ) as verify:
            bulk.require_preflight("/run-dir", "/run-dir/actions/plan.jsonl")
        verify.assert_called_once_with(
            Path("/run-dir"),
            plan_path=Path("/run-dir/actions/plan.jsonl"),
        )

    def test_compatible_batch_issues_one_mv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [
                {"action_id": f"A{i}", "op": "mv", "from": f"/library/source/item-{i}", "to": "/library/target", "reason": "batch"}
                for i in range(1, 4)
            ]
            plan = self.write_plan(root, records)
            ledger = root / "ledger.jsonl"
            replies = [listing("item-1", "item-2", "item-3"), listing(), result(), listing(), listing("item-1", "item-2", "item-3")]
            with mock.patch.object(bulk, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute", "--resume", "--batch-size", "3",
                )

            writes = [call for call in run.call_args_list if call.args[0] == "mv"]
            self.assertEqual(len(writes), 1)
            self.assertEqual([json.loads(line)["status"] for line in ledger.read_text(encoding="utf-8").splitlines()], ["verified"] * 3)

    def test_resume_verifies_partially_landed_actions_and_moves_remaining_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [
                {"action_id": f"A{i}", "op": "mv", "from": f"/library/source/item-{i}", "to": "/library/target", "reason": "resume"}
                for i in range(1, 4)
            ]
            plan = self.write_plan(root, records)
            ledger = root / "ledger.jsonl"
            # item-1 is already in the target, while item-2 and item-3 remain.
            replies = [listing("item-2", "item-3"), listing("item-1"), listing("item-2", "item-3"), listing("item-1"), listing("item-1", "item-2", "item-3")]
            with mock.patch.object(bulk, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute", "--resume", "--batch-size", "3",
                )

            writes = [call for call in run.call_args_list if call.args[0] == "mv"]
            self.assertEqual([call.args for call in writes], [("mv", "drive-1", "/library/source/item-2", "/library/source/item-3", "/library/target")])
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["status"] for entry in entries], ["verified"] * 3)
            self.assertEqual(entries[0]["verify"]["stage"], "idempotent-resume")

    def test_same_name_with_wrong_source_id_blocks_batch_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            item = {
                "action_id": "A1", "op": "mv", "from": "/library/source/course",
                "to": "/library/target", "reason": "identity gate", "file_id": "expected-id",
            }
            plan = self.write_plan(root, [item])
            ledger = root / "ledger.jsonl"
            with mock.patch.object(
                bulk, "run_aliyunpan", side_effect=[listing(("course/", "wrong-id")), listing()]
            ) as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", "--resume",
                    )

            self.assertEqual(stopped.exception.code, 1)
            self.assertFalse(any(call.args[0] == "mv" for call in run.call_args_list))
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(entry["verify"]["error"], "SOURCE_FILE_ID_MISMATCH")

    def test_batch_terminal_wrong_target_id_is_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            item = {
                "action_id": "A1", "op": "mv", "from": "/library/source/course",
                "to": "/library/target", "reason": "identity gate", "file_id": "expected-id",
            }
            plan = self.write_plan(root, [item])
            ledger = root / "ledger.jsonl"
            replies = [
                listing(("course/", "expected-id")), listing(), result(),
                listing(), listing(("course/", "wrong-id")),
            ]
            with mock.patch.object(bulk, "run_aliyunpan", side_effect=replies):
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", "--resume",
                    )

            self.assertEqual(stopped.exception.code, 1)
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(entry["status"], "failed")
            self.assertEqual(entry["verify"]["target_file_id"], "wrong-id")

    def test_resume_different_file_id_does_not_skip_batch_move(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            item = {
                "action_id": "A1", "op": "mv", "from": "/library/source/course",
                "to": "/library/target", "reason": "identity gate", "file_id": "new-id",
            }
            plan = self.write_plan(root, [item])
            ledger = root / "ledger.jsonl"
            ledger.write_text(
                json.dumps({**item, "file_id": "old-id", "status": "verified", "verify": {}, "ts": "old"}) + "\n",
                encoding="utf-8",
            )
            replies = [
                listing(("course/", "new-id")), listing(), result(),
                listing(), listing(("course/", "new-id")),
            ]
            with mock.patch.object(bulk, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute", "--resume",
                )

            self.assertTrue(any(call.args[0] == "mv" for call in run.call_args_list))
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(entries[-1]["file_id"], "new-id")
            self.assertEqual(entries[-1]["status"], "verified")

    def test_terminal_missing_is_failed_and_fail_fast(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [
                {"action_id": "A1", "op": "mv", "from": "/library/source/one", "to": "/library/target", "reason": "fail"},
                {"action_id": "A2", "op": "mkdir", "to": "/library/should-not-run", "reason": "fail-fast"},
            ]
            plan = self.write_plan(root, records)
            ledger = root / "ledger.jsonl"
            # The source remains and the target never receives the item.
            replies = [listing("one"), listing(), result(), listing("one"), listing()]
            with mock.patch.object(bulk, "run_aliyunpan", side_effect=replies) as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", "--resume", "--batch-size", "2",
                    )

            self.assertEqual(stopped.exception.code, 1)
            self.assertFalse(any(call.args[0] == "mkdir" for call in run.call_args_list))
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(entries[0]["status"], "failed")
            self.assertEqual(entries[0]["verify"]["error"], "终态 ll 复核失败")

    def test_precheck_failure_closes_every_action_without_partial_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [
                {"action_id": "A1", "op": "mv", "from": "/library/source/present", "to": "/library/target", "reason": "batch"},
                {"action_id": "A2", "op": "mv", "from": "/library/source/missing", "to": "/library/target", "reason": "batch"},
            ]
            plan = self.write_plan(root, records)
            ledger = root / "ledger.jsonl"
            with mock.patch.object(
                bulk,
                "run_aliyunpan",
                side_effect=[listing("present"), listing()],
            ) as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", "--resume", "--batch-size", "2",
                    )

            self.assertEqual(stopped.exception.code, 1)
            self.assertFalse(any(call.args[0] == "mv" for call in run.call_args_list))
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["status"] for entry in entries], ["failed", "failed"])
            self.assertEqual(entries[0]["verify"]["error"], "BATCH_ABORTED_DUE_TO_PRECHECK")
            self.assertEqual(entries[1]["verify"]["error"], "SOURCE_NOT_LISTED")

    def test_dry_run_and_batch_size_validation_do_not_call_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mv", "from": "/library/a", "to": "/library/b", "reason": "preview"}],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(bulk, "run_aliyunpan") as run:
                output = self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--batch-size", "1",
                )
                self.assertIn("batch-size=1", output)
                run.assert_not_called()
            self.assertFalse(ledger.exists())

            with mock.patch.object(bulk, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--batch-size", "0",
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()

            with mock.patch.object(bulk, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--batch-size", "21",
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()

    def test_execute_requires_run_dir_before_bulk_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mkdir", "to": "/library/new", "reason": "gate"}],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(bulk, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", auto_run_dir=False,
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_bulk_preflight_failures_reject_before_runner(self) -> None:
        failures = (
            "preflight_report_missing",
            "preflight_report_stale",
            "executor_plan_not_registered",
        )
        for kind in failures:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                plan = self.write_plan(
                    root,
                    [{"action_id": "A1", "op": "mkdir", "to": "/library/new", "reason": "gate"}],
                )
                ledger = root / "ledger.jsonl"
                gate_result = {
                    "status": "failed",
                    "checked": {},
                    "violations": [{"kind": kind, "detail": "/private/must-not-leak"}],
                }
                with mock.patch.object(bulk, "run_aliyunpan") as run:
                    with self.assertRaises(SystemExit) as stopped:
                        self.run_main(
                            "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                            "--ledger", str(ledger), "--execute", gate_result=gate_result,
                        )
                self.assertEqual(stopped.exception.code, 2)
                run.assert_not_called()
                self.assertFalse(ledger.exists())

    def test_root_boundary_rejected_before_any_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mv", "from": "/other/a", "to": "/library/b", "reason": "boundary"}],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(bulk, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", "--resume", "--batch-size", "2",
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_parallel_two_is_rejected_before_cloud_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mkdir", "to": "/library/one", "reason": "locked"}],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(bulk, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", "--resume", "--max-parallel", "2",
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_parallel_limit_rejects_values_other_than_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mkdir", "to": "/library/one", "reason": "limit"}],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(bulk, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", "--max-parallel", "0",
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()

    def test_history_is_appended_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = {"action_id": "A1", "op": "mkdir", "to": "/library/one", "reason": "new"}
            plan = self.write_plan(root, [record])
            ledger = root / "ledger.jsonl"
            history = {**record, "status": "verified", "verify": {}, "ts": "history"}
            ledger.write_text(json.dumps(history, ensure_ascii=False) + "\n", encoding="utf-8")
            with mock.patch.object(bulk, "run_aliyunpan") as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute", "--resume", "--batch-size", "2",
                )
            self.assertEqual(ledger.read_text(encoding="utf-8").splitlines(), [json.dumps(history, ensure_ascii=False)])
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
