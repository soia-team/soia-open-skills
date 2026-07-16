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


class ApplyReclassTests(unittest.TestCase):
    ROOT = "/library"

    def test_spec_loaded_executor_loads_sibling_gate_without_scripts_sys_path(self) -> None:
        scripts_dir = str((REPO_ROOT / "skills/soia-pkm-alipan-curator/scripts").resolve())
        original_path = list(sys.path)
        try:
            sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != Path(scripts_dir)]
            isolated = load_module(
                "apply_reclass_without_scripts_sys_path",
                "skills/soia-pkm-alipan-curator/scripts/apply_reclass.py",
            )
        finally:
            sys.path[:] = original_path

        self.assertTrue(hasattr(isolated.preflight_gate, "verify_preflight_gate"))
        self.assertTrue(hasattr(isolated.preflight_gate.audit_migration_conservation, "validate_cleanup_result_paths"))

    def test_cleanup_actions_are_rejected_before_runner_call(self) -> None:
        for op in ("delete", "remove", "trash"):
            with self.subTest(op=op), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                plan = self.write_plan(root, [{
                    "action_id": "C1",
                    "op": op,
                    "from": "/library/empty-shell",
                    "to": "/library/empty-shell",
                    "reason": "approved cleanup candidate",
                    "file_id": "shell-id",
                }])
                ledger = root / "ledger.jsonl"
                with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                    with self.assertRaises(ValueError) as raised:
                        apply_reclass.load_plan(plan, [self.ROOT])

                self.assertIn(apply_reclass.CLEANUP_ACTION_ERROR, str(raised.exception))
                run.assert_not_called()
                self.assertFalse(ledger.exists())


    def write_plan(self, root: Path, records: list[dict]) -> Path:
        records = [
            {
                **record,
                **(
                    {"file_id": file_id_for_name(apply_reclass.parent_and_name(record['from'])[1])}
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
        sys.argv = ["apply_reclass.py", *effective_args]
        try:
            with mock.patch.object(
                apply_reclass.preflight_gate,
                "verify_preflight_gate",
                return_value=GATE_PASSED if gate_result is None else gate_result,
            ):
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    apply_reclass.main()
        finally:
            sys.argv = old_argv
        return output.getvalue()

    def test_parse_ll_preserves_repeated_spaces_in_name(self) -> None:
        output = listing("央视纪录片  国语中字  1080P高清纪录片/").stdout

        self.assertEqual(
            apply_reclass.parse_ll(output),
            {"央视纪录片  国语中字  1080P高清纪录片": "file:央视纪录片__国语中字__1080P高清纪录片"},
        )

    def test_runner_is_located_from_portable_skill_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "portable-package" / "skills"
            runner = root / "soia-pkm-alipan-drive-ops" / "scripts" / "run_with_env.py"
            runner.parent.mkdir(parents=True)
            runner.write_text("# test runner\n", encoding="utf-8")
            synthetic_executor = root / "soia-pkm-alipan-curator" / "scripts" / "apply_reclass.py"
            with mock.patch.dict("os.environ", {apply_reclass.RUNNER_ENV: ""}, clear=False):
                with mock.patch.object(apply_reclass, "__file__", str(synthetic_executor)):
                    self.assertEqual(apply_reclass.alipan_runner_path(), runner.resolve())

    def test_runner_override_preserves_aliyunpan_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runner = Path(temp) / "runner.py"
            runner.write_text("# test runner\n", encoding="utf-8")
            with mock.patch.dict("os.environ", {apply_reclass.RUNNER_ENV: str(runner)}, clear=False):
                with mock.patch.object(apply_reclass.subprocess, "run", return_value=result()) as run:
                    apply_reclass.run_aliyunpan("ll", "drive-1", "/library/course  double")

            self.assertEqual(
                run.call_args.args[0],
                [sys.executable, str(runner), "--", "aliyunpan", "ll", "--driveId", "drive-1", "/library/course  double"],
            )

    def test_runner_errors_are_sanitized_without_bare_aliyunpan_fallback(self) -> None:
        secret_runner = "/private/session-token/run_with_env.py"
        with mock.patch.dict("os.environ", {apply_reclass.RUNNER_ENV: secret_runner}, clear=False):
            with mock.patch.object(apply_reclass.subprocess, "run") as run:
                unavailable = apply_reclass.run_aliyunpan("ll", "drive-1", "/library")
        self.assertEqual(unavailable.returncode, 127)
        self.assertEqual(unavailable.stderr, "RUNNER_UNAVAILABLE")
        self.assertNotIn("session-token", unavailable.stderr)
        run.assert_not_called()

        with mock.patch.object(apply_reclass, "alipan_runner_path", return_value=Path("/runner.py")):
            with mock.patch.object(apply_reclass.subprocess, "run", side_effect=OSError("/private/session-token")):
                failed = apply_reclass.run_aliyunpan("ll", "drive-1", "/library")
        self.assertEqual(failed.returncode, 255)
        self.assertEqual(failed.stderr, "RUNNER_EXECUTION_FAILED")
        self.assertNotIn("session-token", failed.stderr)

    def test_preflight_adapter_receives_run_and_plan_paths(self) -> None:
        with mock.patch.object(
            apply_reclass.preflight_gate,
            "verify_preflight_gate",
            return_value=GATE_PASSED,
        ) as verify:
            apply_reclass.require_preflight("/run-dir", "/run-dir/actions/plan.jsonl")
        verify.assert_called_once_with(
            Path("/run-dir"),
            plan_path=Path("/run-dir/actions/plan.jsonl"),
        )

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

    def test_execute_requires_run_dir_before_runner_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mkdir", "to": "/library/new", "reason": "gate"}],
            )
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute", auto_run_dir=False,
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_preflight_failures_reject_execute_before_runner(self) -> None:
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
                with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                    with self.assertRaises(SystemExit) as stopped:
                        self.run_main(
                            "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                            "--ledger", str(ledger), "--execute", gate_result=gate_result,
                        )
                self.assertEqual(stopped.exception.code, 2)
                run.assert_not_called()
                self.assertFalse(ledger.exists())

    def test_dry_run_with_run_dir_also_enforces_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(
                root,
                [{"action_id": "A1", "op": "mkdir", "to": "/library/new", "reason": "gate"}],
            )
            ledger = root / "ledger.jsonl"
            gate_result = {
                "status": "failed",
                "checked": {},
                "violations": [{"kind": "preflight_report_stale"}],
            }
            with mock.patch.object(apply_reclass, "run_aliyunpan") as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--run-dir", str(root), gate_result=gate_result,
                    )
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())

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

    def test_load_completed_uses_latest_ledger_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "ledger.jsonl"
            item = {"action_id": "A1", "op": "mkdir", "to": "/library/one"}
            ledger.write_text(
                json.dumps({**item, "status": "verified"}) + "\n"
                + json.dumps({**item, "status": "failed"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(apply_reclass.load_completed(ledger), set())

    def test_load_plan_requires_and_preserves_file_id_for_move(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(root, [{
                "action_id": "A1",
                "op": "mv",
                "from": "/library/old",
                "to": "/library/new",
                "reason": "move",
                "file_id": "stable-id",
            }])
            loaded = apply_reclass.load_plan(plan, [self.ROOT])
            self.assertEqual(loaded[0]["file_id"], "stable-id")

            missing_id = root / "missing-id.jsonl"
            missing_id.write_text(
                json.dumps({
                    "action_id": "A2", "op": "mv", "from": "/library/old",
                    "to": "/library/new", "reason": "move",
                }) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "缺少非空 file_id"):
                apply_reclass.load_plan(missing_id, [self.ROOT])

    def test_same_name_with_wrong_source_id_is_blocked_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            item = {
                "action_id": "A1",
                "op": "mv",
                "from": "/library/source/course",
                "to": "/library/target",
                "reason": "identity gate",
                "file_id": "expected-id",
            }
            plan = self.write_plan(root, [item])
            ledger = root / "ledger.jsonl"
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=[listing(("course/", "wrong-id"))]) as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute",
                    )

            self.assertEqual(stopped.exception.code, 1)
            self.assertFalse(any(call.args[0] == "mv" for call in run.call_args_list))
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(entry["verify"]["error"], "SOURCE_FILE_ID_MISMATCH")

    def test_wrong_target_id_after_move_is_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            item = {
                "action_id": "A1",
                "op": "mv",
                "from": "/library/source/course",
                "to": "/library/target",
                "reason": "identity gate",
                "file_id": "expected-id",
            }
            plan = self.write_plan(root, [item])
            ledger = root / "ledger.jsonl"
            replies = [
                listing(("course/", "expected-id")), listing(), result(),
                listing(("course/", "wrong-id")), listing(),
            ]
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=replies) as run:
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(
                        "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                        "--ledger", str(ledger), "--execute",
                    )

            self.assertEqual(stopped.exception.code, 1)
            self.assertEqual([call.args[0] for call in run.call_args_list], ["ll", "ll", "mv", "ll", "ll"])
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(entry["status"], "failed")
            self.assertEqual(entry["verify"]["target_file_id"], "wrong-id")

    def test_resume_does_not_skip_a_different_file_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            item = {
                "action_id": "A1",
                "op": "mv",
                "from": "/library/source/course",
                "to": "/library/target",
                "reason": "identity gate",
                "file_id": "new-id",
            }
            plan = self.write_plan(root, [item])
            ledger = root / "ledger.jsonl"
            ledger.write_text(
                json.dumps({**item, "file_id": "old-id", "status": "verified", "verify": {}, "ts": "old"}) + "\n",
                encoding="utf-8",
            )
            replies = [
                listing(("course/", "new-id")), listing(), result(),
                listing(("course/", "new-id")), listing(),
            ]
            with mock.patch.object(apply_reclass, "run_aliyunpan", side_effect=replies) as run:
                self.run_main(
                    "--plan", str(plan), "--driveId", "drive-1", "--root", self.ROOT,
                    "--ledger", str(ledger), "--execute", "--resume",
                )

            self.assertTrue(any(call.args[0] == "mv" for call in run.call_args_list))
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[-1]["file_id"], "new-id")
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
                listing("course/"), listing(), result(17, stderr="write return code is not evidence"),
                listing("course/"), listing(),
                listing("course/"), result(23, stderr="still not evidence"), listing(("new-course/", "file:course")),
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
