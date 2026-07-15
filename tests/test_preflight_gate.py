#!/usr/bin/env python3
"""Adversarial tests for the run-bundle execution preflight gate."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/soia-pkm-alipan-curator/scripts/preflight_gate.py"
SPEC = importlib.util.spec_from_file_location("preflight_gate_under_test", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
sys.modules["preflight_gate"] = gate
SPEC.loader.exec_module(gate)


def manifest(plans: list[str]) -> dict:
    return {
        "files": {"preflight_report": "verification/preflight.json"},
        "batches": [{"plan": plan} for plan in plans],
    }


def report(hashes: dict[str, str], drive_id: str = "drive-a") -> dict:
    return {
        "schema_version": 1,
        "status": "passed",
        "drive_id_sha256": gate.sha256_drive_id(drive_id),
        "hashes": hashes,
    }


class PreflightGateTests(unittest.TestCase):
    def test_executors_bind_their_current_drive_to_the_gate(self) -> None:
        scripts = (
            "apply_reclass.py",
            "apply_reclass_bulk.py",
        )
        script_dir = SCRIPT.parent
        sys.path.insert(0, str(script_dir))
        try:
            for script_name in scripts:
                spec = importlib.util.spec_from_file_location(
                    f"{script_name}_drive_binding_test",
                    script_dir / script_name,
                )
                if spec is None or spec.loader is None:
                    raise RuntimeError(f"cannot load {script_name}")
                executor = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = executor
                spec.loader.exec_module(executor)
                with mock.patch.object(
                    executor.preflight_gate,
                    "verify_preflight_gate",
                    return_value={"status": "passed"},
                ) as verify:
                    executor.require_preflight("/run", "/run/actions/plan.jsonl", "drive-a")
                verify.assert_called_once_with(
                    Path("/run"),
                    plan_path=Path("/run/actions/plan.jsonl"),
                    drive_id="drive-a",
                )
        finally:
            sys.path.remove(str(script_dir))

    def test_exact_registered_plan_hashes_and_execution_drive_pass(self) -> None:
        plans = ["actions/10.plan.jsonl", "actions/20.plan.jsonl"]
        hashes = {
            "run.json": "a" * 64,
            "actions/10.plan.jsonl": "b" * 64,
            "actions/20.plan.jsonl": "c" * 64,
        }

        result = gate.validate_preflight_gate(
            manifest=manifest(plans),
            report_path="verification/preflight.json",
            report=report(hashes),
            current_hashes=hashes,
            executor_plan_path=plans[0],
            drive_id="drive-a",
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["checked"]["matched_plans"], len(plans))
        self.assertTrue(result["checked"]["execution_drive_hash_matched"])

    def test_missing_current_hash_for_registered_plan_fails_closed(self) -> None:
        plans = ["actions/10.plan.jsonl", "actions/20.plan.jsonl"]
        report_hashes = {
            "run.json": "a" * 64,
            "actions/10.plan.jsonl": "b" * 64,
            "actions/20.plan.jsonl": "c" * 64,
        }
        current_hashes = {
            "run.json": "a" * 64,
            "actions/10.plan.jsonl": "b" * 64,
        }

        result = gate.validate_preflight_gate(
            manifest=manifest(plans),
            report_path="verification/preflight.json",
            report=report(report_hashes),
            current_hashes=current_hashes,
            drive_id="drive-a",
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checked"]["matched_plans"], 1)
        self.assertIn(
            {
                "kind": "preflight_plan_hash_missing",
                "plan": "actions/20.plan.jsonl",
                "source": "current",
            },
            result["violations"],
        )

    def test_adapter_rejects_execution_on_a_different_drive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            plan_path = run_dir / "actions/10.plan.jsonl"
            plan_path.parent.mkdir()
            plan_path.write_text('{"action_id":"A1","op":"mkdir","to":"/new"}\n', encoding="utf-8")
            run = manifest(["actions/10.plan.jsonl"])
            (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
            hashes = {
                "run.json": gate.sha256_file(run_dir / "run.json"),
                "actions/10.plan.jsonl": gate.sha256_file(plan_path),
            }
            report_path = run_dir / "verification/preflight.json"
            report_path.parent.mkdir()
            report_path.write_text(json.dumps(report(hashes, "drive-a")), encoding="utf-8")

            result = gate.verify_preflight_gate(
                run_dir,
                plan_path=plan_path,
                drive_id="drive-b",
            )

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["checked"]["execution_drive_hash_matched"])
        self.assertIn(
            "preflight_execution_drive_changed",
            {violation["kind"] for violation in result["violations"]},
        )

    def test_execution_rejects_report_without_a_drive_hash(self) -> None:
        hashes = {"run.json": "a" * 64, "actions/10.plan.jsonl": "b" * 64}
        stale_report = {
            "schema_version": 1,
            "status": "passed",
            "hashes": hashes,
        }

        result = gate.validate_preflight_gate(
            manifest=manifest(["actions/10.plan.jsonl"]),
            report_path="verification/preflight.json",
            report=stale_report,
            current_hashes=hashes,
            drive_id="drive-a",
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "preflight_report_stale",
            {violation["kind"] for violation in result["violations"]},
        )


if __name__ == "__main__":
    unittest.main()
