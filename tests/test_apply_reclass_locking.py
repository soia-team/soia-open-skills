#!/usr/bin/env python3
"""Adversarial locking tests for the single-action reclassification executor."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PASSED = {"status": "passed", "checked": {}, "violations": []}


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


single = load_module(
    "apply_reclass_locking_single_under_test",
    "skills/soia-pkm-alipan-curator/scripts/apply_reclass.py",
)
bulk = load_module(
    "apply_reclass_locking_bulk_under_test",
    "skills/soia-pkm-alipan-curator/scripts/apply_reclass_bulk.py",
)


def result(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def listing() -> subprocess.CompletedProcess:
    return result(
        stdout=(
            "当前目录 /mock\n"
            "--------------------------------\n"
            "1  id-new  -  -  0  2025-01-01 00:00:00  2025-01-02 13:00:00  new/\n"
        )
    )


class ApplyReclassLockingTests(unittest.TestCase):
    DRIVE_ID = "drive-1"

    def write_plan(self, root: Path) -> Path:
        plan = root / "plan.jsonl"
        plan.write_text(
            json.dumps(
                {"action_id": "A1", "op": "mkdir", "to": "/library/new", "reason": "lock test"},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return plan

    def run_main(self, plan: Path, ledger: Path) -> None:
        old_argv = sys.argv
        sys.argv = [
            "apply_reclass.py",
            "--plan", str(plan),
            "--driveId", self.DRIVE_ID,
            "--root", "/library",
            "--ledger", str(ledger),
            "--run-dir", "/mock/run",
            "--execute",
        ]
        try:
            single.main()
        finally:
            sys.argv = old_argv

    def test_bulk_lock_blocks_single_before_gate_or_cloud_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(root)
            ledger = root / "ledger.jsonl"
            with mock.patch.dict(os.environ, {"XDG_STATE_HOME": temp}, clear=False):
                with bulk.execution_slot(self.DRIVE_ID, 1):
                    with mock.patch.object(single.preflight_gate, "verify_preflight_gate") as gate:
                        with mock.patch.object(single, "run_aliyunpan") as run:
                            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                                with self.assertRaises(SystemExit) as stopped:
                                    self.run_main(plan, ledger)

            self.assertEqual(stopped.exception.code, 2)
            gate.assert_not_called()
            run.assert_not_called()
            self.assertFalse(ledger.exists())

    def test_single_lock_spans_gate_write_and_verify_then_releases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(root)
            ledger = root / "ledger.jsonl"

            def assert_bulk_is_locked() -> None:
                with self.assertRaises(RuntimeError):
                    with bulk.execution_slot(self.DRIVE_ID, 1):
                        self.fail("bulk writer lock must not be acquired")

            def verify_gate(*_args, **_kwargs):
                assert_bulk_is_locked()
                return GATE_PASSED

            def cloud_call(command, *_args):
                assert_bulk_is_locked()
                return result() if command == "mkdir" else listing()

            with mock.patch.dict(os.environ, {"XDG_STATE_HOME": temp}, clear=False):
                with mock.patch.object(
                    single.preflight_gate, "verify_preflight_gate", side_effect=verify_gate
                ) as gate:
                    with mock.patch.object(single, "run_aliyunpan", side_effect=cloud_call) as run:
                        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                            self.run_main(plan, ledger)

                with bulk.execution_slot(self.DRIVE_ID, 1):
                    pass

            self.assertEqual(gate.call_count, 1)
            self.assertEqual([call.args[0] for call in run.call_args_list], ["mkdir", "ll"])
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(entry["status"], "verified")

    def test_single_releases_lock_when_gate_rejects_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.write_plan(root)
            ledger = root / "ledger.jsonl"

            def reject_gate(*_args, **_kwargs):
                with self.assertRaises(RuntimeError):
                    with bulk.execution_slot(self.DRIVE_ID, 1):
                        self.fail("gate must run while the single writer lock is held")
                return {"status": "failed", "checked": {}, "violations": [{"kind": "stale"}]}

            with mock.patch.dict(os.environ, {"XDG_STATE_HOME": temp}, clear=False):
                with mock.patch.object(single.preflight_gate, "verify_preflight_gate", side_effect=reject_gate):
                    with mock.patch.object(single, "run_aliyunpan") as run:
                        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                            with self.assertRaises(SystemExit) as stopped:
                                self.run_main(plan, ledger)

                with bulk.execution_slot(self.DRIVE_ID, 1):
                    pass

            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
            self.assertFalse(ledger.exists())


if __name__ == "__main__":
    unittest.main()
