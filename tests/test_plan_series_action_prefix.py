#!/usr/bin/env python3
"""Tests for portable action ID namespaces in the series planner."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts" / "plan_series_chunks.py"
SPEC = importlib.util.spec_from_file_location("plan_series_chunks_action_prefix", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
planner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


PARENT = "/library/series"


def file_row(name: str) -> dict:
    return {"path": PARENT, "name": name, "id": name, "dir": False, "size": 1, "sha1": "0" * 40}


def rules_path(root: Path) -> Path:
    path = root / "rules.json"
    path.write_text(json.dumps({"series": [{
        "parent": PARENT,
        "max_items": 1,
        "primary_pattern": r"\.mp4$",
        "protect": [r"^README\.txt$"],
        "protected_dir": "配套资料",
    }]}), encoding="utf-8")
    return path


class PlanSeriesActionPrefixTests(unittest.TestCase):
    def test_prefix_is_applied_to_every_mkdir_and_mv_action(self) -> None:
        rows = [file_row("01.mp4"), file_row("02.mp4"), file_row("README.txt")]
        with tempfile.TemporaryDirectory() as temp:
            rules = planner.load_rules(rules_path(Path(temp)))
            actions, report, ok = planner.build_plan(rows, rules, "B49")

        self.assertTrue(ok)
        self.assertEqual(report["status"], "planned")
        self.assertTrue(actions)
        self.assertTrue(all(item["op"] in {"mkdir", "mv"} for item in actions))
        self.assertTrue(all(item["action_id"].startswith("B49-") for item in actions))
        self.assertIn("B49-S01-PD-MK", {item["action_id"] for item in actions})
        self.assertIn("B49-S01-G10-MK", {item["action_id"] for item in actions})
        self.assertEqual(len({item["action_id"] for item in actions}), len(actions))

    def test_cli_applies_valid_prefix_to_plan(self) -> None:
        rows = [file_row("01.mp4"), file_row("02.mp4")]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scan = root / "scan.jsonl"
            plan = root / "plan.jsonl"
            report = root / "report.json"
            scan.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            process = subprocess.run([
                sys.executable, str(SCRIPT),
                "--scan", str(scan),
                "--rules", str(rules_path(root)),
                "--out-plan", str(plan),
                "--out-report", str(report),
                "--action-prefix", "B49",
            ], capture_output=True, text=True)

            self.assertEqual(process.returncode, 0, process.stderr)
            actions = [json.loads(line) for line in plan.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(actions)
        self.assertTrue(all(item["action_id"].startswith("B49-") for item in actions))

    def test_cli_rejects_unsafe_or_overlong_prefix(self) -> None:
        rows = [file_row("01.mp4"), file_row("02.mp4")]
        invalid_prefixes = ("", "has space", "a/b", r"a\b", "a.b", "x" * 33)
        for prefix in invalid_prefixes:
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                scan = root / "scan.jsonl"
                plan = root / "plan.jsonl"
                report = root / "report.json"
                scan.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                process = subprocess.run([
                    sys.executable, str(SCRIPT),
                    "--scan", str(scan),
                    "--rules", str(rules_path(root)),
                    "--out-plan", str(plan),
                    "--out-report", str(report),
                    "--action-prefix", prefix,
                ], capture_output=True, text=True)
                self.assertNotEqual(process.returncode, 0)
                self.assertIn("action prefix", process.stderr)
                self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], "failed")
                self.assertFalse(plan.exists())

    def test_omitting_prefix_preserves_default_action_ids(self) -> None:
        rows = [file_row("01.mp4"), file_row("02.mp4")]
        with tempfile.TemporaryDirectory() as temp:
            rules = planner.load_rules(rules_path(Path(temp)))
            default_actions, default_report, default_ok = planner.build_plan(rows, rules)
            explicit_none_actions, explicit_none_report, explicit_none_ok = planner.build_plan(rows, rules, None)

        self.assertTrue(default_ok)
        self.assertTrue(explicit_none_ok)
        self.assertEqual(default_actions, explicit_none_actions)
        self.assertEqual(default_report, explicit_none_report)
        self.assertTrue(all(item["action_id"].startswith("S01-") for item in default_actions))


if __name__ == "__main__":
    unittest.main()
