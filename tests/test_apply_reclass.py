#!/usr/bin/env python3
"""Regression tests for the reclassification executor."""

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


apply_reclass = load_module(
    "apply_reclass_under_test",
    "skills/soia-pkm-alipan-curator/scripts/apply_reclass.py",
)


def result(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def listing(*names):
    rows = ["当前目录 /mock", "--------------------------------"]
    rows.extend(f"{index}  id-{index}  -  -  0  -  -  {name}" for index, name in enumerate(names))
    return result(stdout="\n".join(rows) + "\n")


class ApplyReclassTests(unittest.TestCase):
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
        sys.argv = ["apply_reclass.py", *args]
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                apply_reclass.main()
        finally:
            sys.argv = old_argv
        return output.getvalue()

    def test_dry_run_prints_preview_without_cli_or_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [
                    {"action_id": "A1", "op": "mkdir", "to": "/library/10_new", "reason": "classify"},
                    {
                        "action_id": "A2",
                        "op": "mv",
                        "from": "/library/old/course",
                        "to": "/library/10_new",
                        "reason": "classify",
                    },
                    {
                        "action_id": "A3",
                        "op": "rename",
                        "from": "/library/old-name",
                        "to": "/library/new-name",
                        "reason": "normalize",
                    },
                ],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                output = self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger)
                )

            run.assert_not_called()
            self.assertFalse(ledger.exists())
            self.assertIn("[1] mkdir - → /library/10_new · classify", output)
            self.assertIn("[2] mv /library/old/course → /library/10_new · classify", output)
            self.assertIn("统计: mkdir=1 mv=1 rename=1 total=3", output)

    def test_fail_fast_stops_before_third_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            targets = [f"/library/{name}" for name in ("one", "two", "three")]
            plan = self.write_plan(
                root,
                [{"action_id": f"A{i}", "op": "mkdir", "to": target, "reason": "test"} for i, target in enumerate(targets, 1)],
            )
            ledger = root / "ledger.jsonl"
            replies = [
                result(), listing(),
                result(), result(1, stderr="LIST_FAIL"), listing("一/"),
            ]
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=replies) as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute"
                    )

            self.assertEqual(stopped.exception.code, 1)
            write_calls = [call for call in run.call_args_list if call.args[0] == "mkdir"]
            self.assertEqual([call.args[2] for call in write_calls], targets[:2])
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["status"] for entry in entries], ["verified", "failed"])
            self.assertNotIn(targets[2], ledger.read_text(encoding="utf-8"))

    def test_resume_skips_completed_entry_and_runs_only_remaining(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = {"action_id": "A1", "op": "mkdir", "to": "/library/one", "reason": "first"}
            second = {"action_id": "A2", "op": "mkdir", "to": "/library/two", "reason": "second"}
            plan = self.write_plan(root, [first, second])
            ledger = root / "ledger.jsonl"
            ledger.write_text(
                json.dumps({**first, "status": "verified", "verify": {}, "ts": "old"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                apply_reclass, "run_aliyunpan", side_effect=[result(), listing()]
            ) as run:
                output = self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger),
                    "--execute", "--resume",
                )

            self.assertIn("已完成，--resume 跳过", output)
            self.assertEqual(run.call_args_list[0].args, ("mkdir", "drive-1", second["to"]))
            self.assertEqual(len(run.call_args_list), 2)
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[-1]["to"], second["to"])
            self.assertEqual(entries[-1]["status"], "verified")

    def test_out_of_bounds_plan_is_rejected_before_any_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{
                    "op": "mv",
                    "action_id": "A1",
                    "from": "/other/course",
                    "to": "/library/course",
                    "reason": "out of bounds",
                }],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute"
                    )

            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_archive_root_allows_explicit_cross_boundary_move(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{
                    "op": "mv",
                    "action_id": "A1",
                    "from": "/library/unclear",
                    "to": "/archive/review",
                    "reason": "classification remains uncertain",
                }],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                output = self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--archive-root", "/archive", "--ledger", str(ledger)
                )

            run.assert_not_called()
            self.assertIn("/library/unclear → /archive/review", output)

    def test_archive_path_is_rejected_without_archive_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{
                    "op": "mv",
                    "action_id": "A1",
                    "from": "/library/unclear",
                    "to": "/archive/review",
                    "reason": "classification remains uncertain",
                }],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit):
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute"
                    )

            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_precheck_list_fail_is_skipped_then_execution_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skipped = {
                "action_id": "A1",
                "op": "mv",
                "from": "/library/special path/course",
                "to": "/library/target",
                "reason": "unaddressable",
            }
            completed = {"action_id": "A2", "op": "mkdir", "to": "/library/next", "reason": "continue"}
            plan = self.write_plan(root, [skipped, completed])
            ledger = root / "ledger.jsonl"
            replies = [result(1, stderr="LIST_FAIL"), result(), listing()]
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute"
                )

            self.assertEqual([call.args[0] for call in run.call_args_list], ["ll", "mkdir", "ll"])
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["status"] for entry in entries], ["skipped", "verified"])
            self.assertEqual(entries[0]["verify"]["error"], "LIST_FAIL")

    def test_source_not_listed_is_skipped_then_execution_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skipped = {
                "action_id": "A1",
                "op": "mv",
                "from": "/library/old/course  double",
                "to": "/library/new",
                "reason": "collapsed name",
            }
            completed = {"action_id": "A2", "op": "mkdir", "to": "/library/next", "reason": "continue"}
            plan = self.write_plan(root, [skipped, completed])
            ledger = root / "ledger.jsonl"
            replies = [listing("课程 双空格/"), listing(), result(), listing()]
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=replies) as run:
                output = self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute"
                )

            self.assertEqual([call.args[0] for call in run.call_args_list], ["ll", "ll", "mkdir", "ll"])
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["status"] for entry in entries], ["skipped", "verified"])
            self.assertEqual(entries[0]["verify"]["error"], "SOURCE_NOT_LISTED")
            self.assertEqual(entries[0]["verify"]["missing_name"], "course  double")
            self.assertTrue(entries[0]["verify"]["ll"]["marker"])
            self.assertIn("SOURCE_NOT_LISTED", output)

    def test_resume_recognizes_move_that_landed_before_verification_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            moved = {
                "action_id": "A1",
                "op": "mv",
                "from": "/library/old/course",
                "to": "/library/new",
                "reason": "resume ambiguous write",
            }
            plan = self.write_plan(root, [moved])
            ledger = root / "ledger.jsonl"
            replies = [listing(), listing("course/")]
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute", "--resume"
                )

            self.assertEqual([call.args[0] for call in run.call_args_list], ["ll", "ll"])
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(entry["status"], "verified")
            self.assertEqual(entry["verify"]["stage"], "idempotent-resume")

    def test_mv_and_rename_use_terminal_ll_state_not_write_returncode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            moved = {
                "action_id": "A1",
                "op": "mv",
                "from": "/library/old/course",
                "to": "/library/new",
                "reason": "move",
            }
            renamed = {
                "action_id": "A2",
                "op": "rename",
                "from": "/library/new/course",
                "to": "/library/new/new-course",
                "reason": "rename",
            }
            plan = self.write_plan(root, [moved, renamed])
            ledger = root / "ledger.jsonl"
            replies = [
                listing("course/"), result(17, stderr="write return code is not evidence"),
                listing("course/"), listing(), listing("course/"),
                result(23, stderr="still not evidence"), listing("new-course/"),
            ]
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute"
                )

            write_calls = [call.args for call in run.call_args_list if call.args[0] in {"mv", "rename"}]
            self.assertEqual(
                write_calls,
                [
                    ("mv", "drive-1", moved["from"], moved["to"]),
                    ("rename", "drive-1", renamed["from"], renamed["to"]),
                ],
            )
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["status"] for entry in entries], ["verified", "verified"])

    def test_rename_must_stay_in_same_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{
                    "action_id": "A1",
                    "op": "rename",
                    "from": "/library/one/old",
                    "to": "/library/two/new",
                    "reason": "wrong parent",
                }],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit):
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute"
                    )

            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_normalized_path_cannot_escape_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{
                    "action_id": "A1",
                    "op": "mkdir",
                    "to": "/library/../../other/escape",
                    "reason": "path traversal",
                }],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit):
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute"
                    )

            run.assert_not_called()
            self.assertFalse(ledger.exists())


if __name__ == "__main__":
    unittest.main()
