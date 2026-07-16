#!/usr/bin/env python3
"""Tests for the public long-series planning generator."""

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
SPEC = importlib.util.spec_from_file_location("plan_series_chunks", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
planner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


def file_row(parent: str, name: str, identifier: str | None = None) -> dict:
    return {"path": parent, "name": name, "id": identifier or name, "dir": False, "size": 1, "sha1": "0" * 40}


def dir_row(parent: str, name: str, identifier: str | None = None) -> dict:
    return {"path": parent, "name": name, "id": identifier or name, "dir": True, "size": None, "sha1": None}


class PlanSeriesChunksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = "/library/series"

    def test_natural_numeric_sorting_and_stable_actions(self) -> None:
        rows = [file_row(self.parent, name) for name in ("Episode 10.mp4", "Episode 2.mp4", "Episode 1.mp4")]
        rules = [{"parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$"}]
        with tempfile.TemporaryDirectory() as temp:
            rules_path = Path(temp) / "rules.json"
            rules_path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            loaded = planner.load_rules(rules_path)
            first, report, ok = planner.build_plan(rows, loaded)
            second, _, _ = planner.build_plan(rows, loaded)
        self.assertTrue(ok)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(first, second)
        moves = [item for item in first if item["op"] == "mv"]
        self.assertEqual([item["from"] for item in moves], [
            f"{self.parent}/Episode 1.mp4",
            f"{self.parent}/Episode 2.mp4",
            f"{self.parent}/Episode 10.mp4",
        ])
        groups = [item["group"] for item in first if item["op"] == "mkdir"]
        self.assertEqual(groups, ["10_001-002", "20_003"])
        self.assertEqual(
            [item["file_id"] for item in moves],
            ["Episode 1.mp4", "Episode 2.mp4", "Episode 10.mp4"],
        )

    def test_same_episode_regular_and_listening_media_stays_together(self) -> None:
        names = [
            "Lesson 01 正课.mp4", "Lesson 01 磨耳朵.mp4",
            "Lesson 02 正课.mp4", "Lesson 03 正课.mp4",
        ]
        rows = [file_row(self.parent, name) for name in names]
        rules = [{
            "parent": self.parent,
            "max_items": 2,
            "primary_pattern": r"\.mp4$",
            "episode_pattern": r"Lesson (?P<episode>\d+)",
        }]
        with tempfile.TemporaryDirectory() as temp:
            rules_path = Path(temp) / "rules.json"
            rules_path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, _, ok = planner.build_plan(rows, planner.load_rules(rules_path))
        self.assertTrue(ok)
        moves = [item for item in actions if item["op"] == "mv"]
        self.assertTrue(all(item["op"] == "mkdir" for item in actions[:2]))
        self.assertTrue(all(item["op"] == "mv" for item in actions[2:]))
        targets: dict[str, list[str]] = {}
        for item in moves:
            episode = item["from"].split("Lesson ")[1][:2]
            targets.setdefault(episode, []).append(item["to"])
        self.assertEqual(len(targets["01"]), 2)
        self.assertEqual(len(set(targets["01"])), 1)
        self.assertNotEqual(targets["01"][0], targets["02"][0])
        self.assertEqual(targets["02"][0], targets["03"][0])
        self.assertTrue(all("library" not in Path(item["to"]).name for item in actions if item["op"] == "mkdir"))

    def test_nul_in_cloud_path_is_rejected(self) -> None:
        with self.assertRaises(planner.InputError):
            planner.normalize_cloud_path("/library/bad\x00name")

    def test_numeric_episode_sort_ignores_spacing_variants(self) -> None:
        rows = [
            file_row(self.parent, "Lesson64 Part 1.mp4"),
            file_row(self.parent, "Lesson64 Part 2.mp4"),
            file_row(self.parent, "Lesson 61 Part 1.mp4"),
            file_row(self.parent, "Lesson 62.mp4"),
            file_row(self.parent, "Lesson 63.mp4"),
        ]
        rules = [{
            "parent": self.parent,
            "max_items": 3,
            "primary_pattern": r"\.mp4$",
            "episode_pattern": r"Lesson\s*(?P<episode>\d+)",
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, _, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertTrue(ok)
        groups = [item["group"] for item in actions if item["op"] == "mkdir"]
        self.assertEqual(groups, ["10_61-63", "20_64"])
        moves = [item for item in actions if item["op"] == "mv"]
        self.assertEqual(
            {item["from"]: item["group"] for item in moves},
            {
                f"{self.parent}/Lesson 61 Part 1.mp4": "10_61-63",
                f"{self.parent}/Lesson 62.mp4": "10_61-63",
                f"{self.parent}/Lesson 63.mp4": "10_61-63",
                f"{self.parent}/Lesson64 Part 1.mp4": "20_64",
                f"{self.parent}/Lesson64 Part 2.mp4": "20_64",
            },
        )

    def test_spaced_digit_episode_labels_are_compacted_in_group_names(self) -> None:
        rows = [
            file_row(self.parent, "第0 1集：一.mp4"),
            file_row(self.parent, "第0 2集：二.mp4"),
            file_row(self.parent, "第0 3集：三.mp4"),
        ]
        rules = [{
            "parent": self.parent,
            "max_items": 2,
            "primary_pattern": r"\.mp4$",
            "episode_pattern": r"第(?P<episode>\d\s*\d)集",
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, _, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertTrue(ok)
        self.assertEqual(
            [item["group"] for item in actions if item["op"] == "mkdir"],
            ["10_01-02", "20_03"],
        )

    def test_group_prefix_width_keeps_more_than_nine_groups_sorted(self) -> None:
        rows = [file_row(self.parent, f"Episode {number}.mp4") for number in range(1, 12)]
        rules = [{"parent": self.parent, "max_items": 1, "primary_pattern": r"\.mp4$"}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, _, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertTrue(ok)
        groups = [item["group"] for item in actions if item["op"] == "mkdir"]
        self.assertEqual(groups[0], "010_001")
        self.assertEqual(groups[8], "090_009")
        self.assertEqual(groups[9], "100_010")
        self.assertEqual(groups[10], "110_011")
        self.assertEqual(groups, sorted(groups))

    def test_subtitle_sidecar_follows_primary(self) -> None:
        rows = [
            file_row(self.parent, "Episode 01.mp4"),
            file_row(self.parent, "Episode 01.srt"),
            file_row(self.parent, "Episode 02.mp4"),
            file_row(self.parent, "Episode 03.mp4"),
        ]
        rules = [{
            "parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$",
            "sidecar_patterns": [r"\.srt$"],
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, report, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertTrue(ok)
        self.assertEqual(report["unresolved"], [])
        subtitle = next(item for item in actions if item.get("from", "").endswith(".srt"))
        primary = next(item for item in actions if item.get("from", "").endswith("Episode 01.mp4"))
        self.assertEqual(subtitle["to"], primary["to"])

    def test_continuous_spaces_are_preserved(self) -> None:
        rows = [file_row(self.parent, "Episode  1.mp4"), file_row(self.parent, "Episode  2.mp4"), file_row(self.parent, "Episode  3.mp4")]
        rules = [{"parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$"}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, _, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertTrue(ok)
        self.assertIn(f"{self.parent}/Episode  1.mp4", [item["from"] for item in actions if item["op"] == "mv"])

    def test_unresolved_direct_file_fails_without_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scan = root / "scan.jsonl"
            rules = root / "rules.json"
            plan = root / "plan.jsonl"
            report = root / "report.json"
            scan.write_text("\n".join(json.dumps(file_row(self.parent, name)) for name in ("01.mp4", "02.mp4", "03.mp4", "notes.txt")) + "\n", encoding="utf-8")
            rules.write_text(json.dumps({"series": [{"parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$"}]}), encoding="utf-8")
            process = subprocess.run([sys.executable, str(SCRIPT), "--scan", str(scan), "--rules", str(rules), "--out-plan", str(plan), "--out-report", str(report)], capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertFalse(plan.exists())
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], "failed")

    def test_direct_file_policy_leave_generates_explicitly_incomplete_plan(self) -> None:
        rows = [file_row(self.parent, name) for name in ("01.mp4", "02.mp4", "03.mp4", "notes.txt")]
        rules = [{"parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$", "direct_file_policy": "leave"}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, report, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertTrue(ok)
        self.assertEqual(report["status"], "planned_with_unresolved")
        self.assertFalse(report["complete"])
        self.assertEqual(report["unresolved"][0]["name"], "notes.txt")
        self.assertNotIn(f"{self.parent}/notes.txt", [item.get("from") for item in actions])

    def test_one_episode_over_limit_fails_instead_of_splitting(self) -> None:
        names = ["Lesson 01 正课.mp4", "Lesson 01 磨耳朵.mp4", "Lesson 01 复习.mp4"]
        rows = [file_row(self.parent, name) for name in names]
        rules = [{
            "parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$",
            "episode_pattern": r"Lesson (?P<episode>\d+)",
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, report, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertFalse(ok)
        self.assertEqual(actions, [])
        self.assertEqual(report["errors"][0]["kind"], "episode_exceeds_chunk_limit")

    def test_protected_file_has_no_action_and_is_reported(self) -> None:
        rows = [file_row(self.parent, name) for name in ("01.mp4", "02.mp4", "03.mp4")]
        rules = [{"parent": self.parent, "max_items": 1, "primary_pattern": r"\.mp4$", "protect": [r"^02\.mp4$"]}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, report, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertTrue(ok)
        self.assertEqual(report["status"], "planned_with_protected")
        self.assertEqual(report["protected"][0]["name"], "02.mp4")
        self.assertEqual(report["planned_protected"], [])
        self.assertNotIn(f"{self.parent}/02.mp4", [item.get("from") for item in actions])

    def test_protected_dir_plans_mkdir_and_protected_moves(self) -> None:
        rows = [file_row(self.parent, name) for name in ("01.mp4", "02.mp4", "03.mp4")]
        rules = [{
            "parent": self.parent,
            "max_items": 1,
            "primary_pattern": r"\.mp4$",
            "protect": [r"^02\.mp4$"],
            "protected_dir": "配套资料",
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            loaded = planner.load_rules(path)
            first, report, ok = planner.build_plan(rows, loaded)
            second, _, _ = planner.build_plan(rows, loaded)
        self.assertTrue(ok)
        self.assertEqual(first, second)
        self.assertEqual(report["status"], "planned")
        self.assertTrue(report["complete"])
        self.assertEqual([item["name"] for item in report["protected"]], ["02.mp4"])
        self.assertEqual([item["name"] for item in report["planned_protected"]], ["02.mp4"])
        protected_mkdir = next(item for item in first if item["action_id"] == "S01-PD-MK")
        self.assertEqual(protected_mkdir["op"], "mkdir")
        self.assertEqual(protected_mkdir["to"], f"{self.parent}/配套资料")
        protected_move = next(item for item in first if item["action_id"] == "S01-PD-M001")
        self.assertEqual(protected_move["op"], "mv")
        self.assertEqual(protected_move["from"], f"{self.parent}/02.mp4")
        self.assertEqual(protected_move["to"], f"{self.parent}/配套资料")
        self.assertEqual(protected_move["file_id"], "02.mp4")
        self.assertEqual(len({item["action_id"] for item in first}), len(first))

    def test_missing_file_id_fails_closed(self) -> None:
        rows = [{"path": self.parent, "name": "01.mp4", "dir": False, "size": 1, "sha1": "0" * 40}]
        rules = [{"parent": self.parent, "max_items": 1, "primary_pattern": r"\.mp4$"}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            with self.assertRaises(planner.InputError):
                planner.build_plan(rows, planner.load_rules(path))

    def test_protected_dir_must_be_one_safe_name(self) -> None:
        for protected_dir in ("", " ", " padded", "padded ", ".", "..", "a/b", r"a\b", "a/b/c", "bad\x00name"):
            with self.subTest(protected_dir=protected_dir), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "rules.json"
                path.write_text(json.dumps({"series": [{
                    "parent": self.parent,
                    "max_items": 1,
                    "primary_pattern": r"\.mp4$",
                    "protected_dir": protected_dir,
                }]}), encoding="utf-8")
                with self.assertRaises(planner.InputError):
                    planner.load_rules(path)

    def test_protected_dir_conflicting_with_generated_group_fails_without_plan(self) -> None:
        rows = [file_row(self.parent, name) for name in ("01.mp4", "02.mp4")]
        rules = [{
            "parent": self.parent,
            "max_items": 1,
            "primary_pattern": r"\.mp4$",
            "protected_dir": "10_001",
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, report, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertFalse(ok)
        self.assertEqual(actions, [])
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["errors"][0]["kind"], "protected_dir_conflicts_with_group")
        self.assertFalse(report["plan_generated"])

    def test_existing_protected_dir_target_is_refused(self) -> None:
        rows = [
            file_row(self.parent, "01.mp4"),
            file_row(self.parent, "02.mp4"),
            file_row(self.parent, "配套资料"),
        ]
        rules = [{
            "parent": self.parent,
            "max_items": 1,
            "primary_pattern": r"\.mp4$",
            "protect": [r"^02\.mp4$"],
            "protected_dir": "配套资料",
            "direct_file_policy": "leave",
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rules.json"
            path.write_text(json.dumps({"series": rules}), encoding="utf-8")
            actions, report, ok = planner.build_plan(rows, planner.load_rules(path))
        self.assertFalse(ok)
        self.assertEqual(actions, [])
        self.assertEqual(report["status"], "failed")
        conflict = next(error for error in report["errors"] if error["kind"] == "existing_target_conflict")
        self.assertEqual(conflict["target"], f"{self.parent}/配套资料")
        self.assertFalse(report["plan_generated"])

    def test_existing_output_is_refused_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scan = root / "scan.jsonl"
            rules = root / "rules.json"
            plan = root / "plan.jsonl"
            report = root / "report.json"
            scan.write_text(json.dumps(file_row(self.parent, "01.mp4")) + "\n", encoding="utf-8")
            rules.write_text(json.dumps({"series": [{"parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$"}]}), encoding="utf-8")
            plan.write_text("keep me\n", encoding="utf-8")
            process = subprocess.run([sys.executable, str(SCRIPT), "--scan", str(scan), "--rules", str(rules), "--out-plan", str(plan), "--out-report", str(report)], capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(plan.read_text(encoding="utf-8"), "keep me\n")

    def test_aggregate_scan_row_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scan = root / "scan.jsonl"
            rules = root / "rules.json"
            plan = root / "plan.jsonl"
            report = root / "report.json"
            scan.write_text(json.dumps({"path": self.parent, "name": "bundle", "dir": True, "agg_files": 3}) + "\n", encoding="utf-8")
            rules.write_text(json.dumps({"series": [{"parent": self.parent, "max_items": 2, "primary_pattern": r"\.mp4$"}]}), encoding="utf-8")
            process = subprocess.run([sys.executable, str(SCRIPT), "--scan", str(scan), "--rules", str(rules), "--out-plan", str(plan), "--out-report", str(report)], capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertFalse(plan.exists())
            self.assertIn("agg_files", process.stderr)


if __name__ == "__main__":
    unittest.main()
