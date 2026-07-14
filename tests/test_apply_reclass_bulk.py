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


def result(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def listing(*names):
    rows = ["当前目录 /mock", "--------------------------------"]
    rows.extend(
        f"{index}  id-{index}  -  -  0  2025-01-01 00:00:00  2025-01-02 13:00:00  {name}"
        for index, name in enumerate(names)
    )
    return result(stdout="\n".join(rows) + "\n")


class BulkApplyReclassTests(unittest.TestCase):
    ROOT = "/library"

    def write_plan(self, root: Path, records: list[dict]) -> Path:
        path = root / "plan.jsonl"
        path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )
        return path

    def run_main(self, *args: str) -> str:
        old_argv = sys.argv
        output = io.StringIO()
        sys.argv = ["apply_reclass_bulk.py", *args]
        try:
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

    def test_third_concurrent_writer_is_blocked_before_cloud_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mkdir", "to": "/library/one", "reason": "locked"}],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.dict("os.environ", {"XDG_STATE_HOME": temp}, clear=False):
                with bulk.execution_slot("drive-1", 2), bulk.execution_slot("drive-1", 2):
                    with mock.patch.object(bulk, "run_aliyunpan") as run:
                        with self.assertRaises(SystemExit) as stopped:
                            self.run_main(
                                "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                                "--ledger", str(ledger), "--execute", "--resume",
                            )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_parallel_limit_rejects_more_than_two(self) -> None:
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
                        "--ledger", str(ledger), "--execute", "--max-parallel", "3",
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
